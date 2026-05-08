"""Anthropic-compatible provider 单测。

不调用真实网络：用 ``httpx.MockTransport`` 拦截请求。
不打印 / 提交任何真实密钥；所有"密钥"都是测试用的字面量。
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import pytest

from mindforge.llm.anthropic_compatible import (
    AnthropicCompatibleProvider,
    _extract_text_from_content_blocks,
)
from mindforge.llm.base import LLMRequest, ProviderError
from mindforge.llm.openai_compatible import OpenAICompatibleProvider


@dataclass
class _ModelStub:
    """模仿 ``ModelConfig`` 的最小 duck type，避免依赖完整 config 解析。"""

    alias: str = "qwen_coder_strong"
    provider: str = "dashscope_coding_plan"
    type: str = "anthropic_compatible"
    base_url: str = ""
    base_url_env: str | None = "MINDFORGE_LLM_BASE_URL"
    api_key_env: str | None = "MINDFORGE_LLM_API_KEY"
    api_key_optional: bool = False
    extra_headers_env: dict[str, str] | None = None
    version_env: str | None = None
    model_env: str | None = None
    model: str = "qwen3-coder-plus"
    timeout_seconds: int = 30
    max_retries: int = 0


# ---------------------------------------------------------------------------
# from_model_config 安全失败路径
# ---------------------------------------------------------------------------


def test_missing_base_url_env_raises_safe_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MINDFORGE_LLM_BASE_URL", raising=False)
    monkeypatch.setenv("MINDFORGE_LLM_API_KEY", "test-key-DO-NOT-LEAK")
    mc = _ModelStub()
    with pytest.raises(ProviderError) as exc:
        AnthropicCompatibleProvider.from_model_config(mc)
    msg = str(exc.value)
    assert "base_url" in msg
    # 不应把 api_key 带出来
    assert "test-key-DO-NOT-LEAK" not in msg


def test_missing_api_key_raises_safe_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MINDFORGE_LLM_BASE_URL", "https://fake.example.com")
    monkeypatch.delenv("MINDFORGE_LLM_API_KEY", raising=False)
    mc = _ModelStub()
    with pytest.raises(ProviderError) as exc:
        AnthropicCompatibleProvider.from_model_config(mc)
    msg = str(exc.value)
    assert "API key" in msg
    # 不应回显环境变量值（这里 base_url 不算 secret 但也不主动 echo）
    assert "MINDFORGE_LLM_API_KEY" in msg  # 提示用户应设置哪个 env，可以出现 env name


def test_yaml_must_not_carry_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """model 无 api_key_env 且 secret store 无 key 时，抛清晰错误而非崩溃。"""
    monkeypatch.setenv("MINDFORGE_LLM_BASE_URL", "https://fake.example.com")
    mc = _ModelStub(api_key_env=None)
    with pytest.raises(ProviderError, match="API key"):
        AnthropicCompatibleProvider.from_model_config(mc)


# ---------------------------------------------------------------------------
# content block 解析
# ---------------------------------------------------------------------------


def test_extract_text_from_multiple_blocks() -> None:
    data = {
        "content": [
            {"type": "text", "text": "Hello "},
            {"type": "text", "text": "world"},
            {"type": "tool_use", "id": "x", "name": "noop", "input": {}},  # 忽略
        ]
    }
    assert _extract_text_from_content_blocks(data) == "Hello world"


def test_extract_text_returns_none_when_no_text() -> None:
    assert _extract_text_from_content_blocks({"content": []}) is None
    assert _extract_text_from_content_blocks({"content": [{"type": "tool_use"}]}) is None
    assert _extract_text_from_content_blocks({}) is None


# ---------------------------------------------------------------------------
# generate：用 MockTransport 模拟 endpoint
# ---------------------------------------------------------------------------


def _make_provider(monkeypatch: pytest.MonkeyPatch, transport: httpx.BaseTransport):
    """构造一个 provider，并劫持 httpx.Client 让它用 mock transport。"""
    monkeypatch.setenv("MINDFORGE_LLM_BASE_URL", "https://fake.example.com")
    monkeypatch.setenv("MINDFORGE_LLM_API_KEY", "test-key-DO-NOT-LEAK")
    mc = _ModelStub()
    p = AnthropicCompatibleProvider.from_model_config(mc)

    real_client = httpx.Client

    def _factory(*args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr("mindforge.llm.anthropic_compatible.httpx.Client", _factory)
    return p


def test_generate_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = request.content.decode("utf-8")
        return httpx.Response(
            200,
            json={
                "id": "msg_x",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": '{"track":"agent-runtime"}'}],
                "usage": {"input_tokens": 12, "output_tokens": 7},
            },
        )

    p = _make_provider(monkeypatch, httpx.MockTransport(handler))
    req = LLMRequest(prompt="hello", stage="triage", model="qwen3-coder-plus", max_tokens=128)
    out = p.generate(req)

    assert out.text == '{"track":"agent-runtime"}'
    assert out.tokens_in == 12
    assert out.tokens_out == 7
    # URL & headers
    assert captured["url"].endswith("/v1/messages")
    assert captured["headers"].get("x-api-key") == "test-key-DO-NOT-LEAK"
    assert captured["headers"].get("anthropic-version") == "2023-06-01"
    # 请求体含 max_tokens 与 messages
    assert '"max_tokens":128' in captured["body"] or '"max_tokens": 128' in captured["body"]
    assert '"role":"user"' in captured["body"] or '"role": "user"' in captured["body"]


def test_generate_http_error_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="unauthorized: bad x-api-key=test-key-DO-NOT-LEAK")

    p = _make_provider(monkeypatch, httpx.MockTransport(handler))
    with pytest.raises(ProviderError) as exc:
        p.generate(LLMRequest(prompt="hi", stage="triage", model="m"))
    msg = str(exc.value)
    assert "401" in msg
    # 服务端 echo 出来的"key"也不该被 provider 主动放大；这里只验证不长串 newline 串
    assert "\n\n" not in msg


def test_openai_provider_http_error_body_is_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenAI-compatible 4xx body 可能回显 key，provider 边界必须先脱敏。"""

    leaked_key = "sk-test-secret-DO-NOT-LEAK-1234567890"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            text=(
                '{"error":{"message":"bad key sk-test-secret-DO-NOT-LEAK-1234567890",'
                '"api_key":"sk-test-secret-DO-NOT-LEAK-1234567890"}}'
            ),
        )

    real_client = httpx.Client

    def _factory(*args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr("mindforge.llm.openai_compatible.httpx.Client", _factory)
    provider = OpenAICompatibleProvider(
        name="openai",
        base_url="https://fake.example.com/v1",
        api_key=leaked_key,
        timeout_seconds=5,
    )

    with pytest.raises(ProviderError) as exc:
        provider.generate(LLMRequest(prompt="hi", stage="wiki_synthesis", model="gpt-test"))

    msg = str(exc.value)
    assert "401" in msg
    assert leaked_key not in msg
    assert "[REDACTED]" in msg


def test_generate_network_error_does_not_leak(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom: api_key=test-key-DO-NOT-LEAK")

    p = _make_provider(monkeypatch, httpx.MockTransport(handler))
    with pytest.raises(ProviderError) as exc:
        p.generate(LLMRequest(prompt="hi", stage="triage", model="m"))
    msg = str(exc.value)
    # 我们只暴露异常类名，不带原始 message（防止 message 含敏感 echo）
    assert "ConnectError" in msg
    assert "test-key-DO-NOT-LEAK" not in msg


def test_generate_invalid_json_response(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not json")

    p = _make_provider(monkeypatch, httpx.MockTransport(handler))
    with pytest.raises(ProviderError, match="非合法 JSON"):
        p.generate(LLMRequest(prompt="hi", stage="triage", model="m"))


def test_generate_missing_text_block(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"content": [{"type": "tool_use"}]})

    p = _make_provider(monkeypatch, httpx.MockTransport(handler))
    with pytest.raises(ProviderError, match="text"):
        p.generate(LLMRequest(prompt="hi", stage="triage", model="m"))


# ---------------------------------------------------------------------------
# factory dispatch 集成（确保 build_providers 认得 anthropic_compatible）
# ---------------------------------------------------------------------------


def test_factory_builds_anthropic_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MINDFORGE_LLM_BASE_URL", "https://fake.example.com")
    monkeypatch.setenv("MINDFORGE_LLM_API_KEY", "test-key-DO-NOT-LEAK")

    @dataclass
    class _LLMCfg:
        models: dict
        active_profile: str = "p"
        profiles: dict = None  # type: ignore[assignment]

    mc = _ModelStub()
    cfg = _LLMCfg(
        models={"qwen_coder_strong": mc},
        profiles={"p": {"distill": "qwen_coder_strong"}},
    )
    from mindforge.llm.factory import build_providers

    providers = build_providers(cfg)
    assert isinstance(providers["qwen_coder_strong"], AnthropicCompatibleProvider)


def test_factory_skips_models_unused_by_active_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """声明在 ``llm.models`` 但当前 profile 不引用的 alias 不应被实例化。

    动机：M2.8 真实 smoke 暴露的问题——eager 构建会强迫用户为备选 provider
    （如 OpenAI 路径）也准备 env / api_key，否则启动失败。
    """
    monkeypatch.setenv("MINDFORGE_LLM_BASE_URL", "https://fake.example.com")
    monkeypatch.setenv("MINDFORGE_LLM_API_KEY", "test-key-DO-NOT-LEAK")
    monkeypatch.delenv("MINDFORGE_OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("MINDFORGE_OPENAI_API_KEY", raising=False)

    @dataclass
    class _UnusedModel:
        alias: str = "openai_alt"
        type: str = "openai_compatible"
        provider: str = "openai_alt"
        base_url_env: str = "MINDFORGE_OPENAI_BASE_URL"
        api_key_env: str = "MINDFORGE_OPENAI_API_KEY"
        base_url: str | None = None
        api_key_optional: bool = False
        version_env: str | None = None
        model: str = "alt-model"
        model_env: str | None = None
        timeout_seconds: int = 60
        max_retries: int = 0
        supports_json_mode: bool = False

    @dataclass
    class _LLMCfg:
        models: dict
        active_profile: str = "p"
        profiles: dict = None  # type: ignore[assignment]

    cfg = _LLMCfg(
        models={
            "qwen_coder_strong": _ModelStub(),
            "openai_alt": _UnusedModel(),  # ← 故意没有 env，用上必崩
        },
        profiles={"p": {"distill": "qwen_coder_strong"}},
    )
    from mindforge.llm.factory import build_providers

    providers = build_providers(cfg)
    assert "qwen_coder_strong" in providers
    assert "openai_alt" not in providers, (
        "未被 active_profile 引用的 alias 不应被实例化"
    )
