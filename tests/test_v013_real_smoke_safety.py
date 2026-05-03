"""v0.13 Stage 1 — synthetic real-LLM smoke 安全断言。

核心契约:

- 未传 ``allow_real`` → 拒绝, 不调任何 provider;
- ``opt_in_state != 'ready'`` → 拒绝;
- 任意路径返回值的 ``human_approved`` / ``written`` 永远 False;
- 任意路径返回值不含 api_key value;
- ``build_synthetic_prompt`` 是 zero-arg, 不接受 caller-supplied 输入;
- 真实路径走 ``llm.factory.build_providers`` (用 monkeypatch 验证;
  绝不发真 HTTP)。
"""

from __future__ import annotations

from dataclasses import dataclass


from mindforge.llm.base import LLMProvider, LLMRequest, LLMResult, ProviderError
from mindforge.real_smoke import build_synthetic_prompt, run_synthetic_real_smoke


class _StubProvider(LLMProvider):
    """符合 LLMProvider 契约的 stub: ``generate(LLMRequest) -> LLMResult``。

    用真实契约 stub 而不是 ad-hoc duck-typed object, 是为了让测试
    捕获 real_smoke 与真实 provider 接口的漂移 — 这是 Stage 3
    最关键的修复点。
    """

    type = "openai_compatible"
    name = "stub"

    def __init__(self, response: str = "ok") -> None:
        self._response = response

    def generate(self, request: LLMRequest) -> LLMResult:
        return LLMResult(
            text=self._response,
            tokens_in=len(request.prompt) // 4,
            tokens_out=len(self._response) // 4,
            latency_ms=1,
        )


@dataclass(frozen=True)
class _FakeMC:
    type: str
    api_key_env: str | None = None
    base_url_env: str | None = None
    model: str | None = "stub-model"


@dataclass(frozen=True)
class _FakeLLMConfig:
    active_profile: str
    profiles: dict
    models: dict


def _cfg_fake() -> _FakeLLMConfig:
    return _FakeLLMConfig(
        active_profile="fake",
        profiles={"fake": {"triage": "fake_only"}},
        models={"fake_only": _FakeMC(type="fake")},
    )


def _cfg_real_with_key(env_var: str) -> _FakeLLMConfig:
    return _FakeLLMConfig(
        active_profile="real",
        profiles={"real": {"triage": "openai_main"}},
        models={
            "openai_main": _FakeMC(
                type="openai_compatible", api_key_env=env_var
            ),
        },
    )


def test_synthetic_prompt_is_zero_arg_and_constant():
    p1 = build_synthetic_prompt()
    p2 = build_synthetic_prompt()
    assert p1 == p2
    assert "human approval" in p1.lower()
    # 没有 caller 注入面: 函数签名零参数
    import inspect
    sig = inspect.signature(build_synthetic_prompt)
    assert len(sig.parameters) == 0


def test_refuses_without_allow_real():
    out = run_synthetic_real_smoke(_cfg_fake(), allow_real=False)
    assert out["ran"] is False
    assert out["human_approved"] is False
    assert out["written"] is False
    assert "allow-real" in out["blocker"].lower()


def test_refuses_when_profile_is_fake_even_with_allow_real():
    out = run_synthetic_real_smoke(_cfg_fake(), allow_real=True)
    assert out["ran"] is False
    assert out["human_approved"] is False
    assert out["written"] is False


def test_refuses_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("MF_FAKE_TEST_KEY_NO_VALUE", raising=False)
    out = run_synthetic_real_smoke(
        _cfg_real_with_key("MF_FAKE_TEST_KEY_NO_VALUE"), allow_real=True
    )
    assert out["ran"] is False
    assert out["opt_in_state"] in ("profile_only", "blocked")
    assert out["human_approved"] is False
    assert out["written"] is False


def test_no_path_returns_api_key_value(monkeypatch):
    secret = "super-secret-value-must-never-leak-9876543210"
    monkeypatch.setenv("MF_FAKE_TEST_KEY_LEAK_CHECK", secret)
    cfg = _cfg_real_with_key("MF_FAKE_TEST_KEY_LEAK_CHECK")

    def _stub_build_providers(_cfg):
        return {"openai_main": _StubProvider("ok")}

    monkeypatch.setattr(
        "mindforge.llm.factory.build_providers", _stub_build_providers
    )
    out = run_synthetic_real_smoke(cfg, allow_real=True)
    assert out["ran"] is True
    assert out["human_approved"] is False
    assert out["written"] is False
    assert out["output_artifact"] == "ai_draft_preview"
    assert secret not in repr(out)


def test_real_path_uses_factory(monkeypatch):
    monkeypatch.setenv("MF_FAKE_TEST_KEY_FACTORY_PROOF", "x")
    cfg = _cfg_real_with_key("MF_FAKE_TEST_KEY_FACTORY_PROOF")

    calls = {"factory": 0}

    def _stub_build_providers(_cfg):
        calls["factory"] += 1
        return {"openai_main": _StubProvider("stub-ok")}

    monkeypatch.setattr(
        "mindforge.llm.factory.build_providers", _stub_build_providers
    )
    out = run_synthetic_real_smoke(cfg, allow_real=True)
    assert out["ran"] is True
    assert calls["factory"] == 1
    assert out["alias"] == "openai_main"
    assert out["provider_type"] == "openai_compatible"
    # Stage 3 新增: audit-trail 必须暴露 LLMResult metadata 字段
    # (None 也算暴露 — 关键是 schema 稳定)
    assert "tokens_in" in out
    assert "tokens_out" in out
    assert "latency_ms" in out


def test_excerpt_scrubs_apparent_secrets(monkeypatch):
    monkeypatch.setenv("MF_FAKE_TEST_KEY_SCRUB", "x")
    cfg = _cfg_real_with_key("MF_FAKE_TEST_KEY_SCRUB")

    def _stub_build_providers(_cfg):
        return {
            "openai_main": _StubProvider(
                "leaked sk-ABCDEFGHIJKLMNOP1234567890 something"
            )
        }

    monkeypatch.setattr(
        "mindforge.llm.factory.build_providers",
        _stub_build_providers,
    )
    out = run_synthetic_real_smoke(cfg, allow_real=True)
    assert "sk-ABCDEFGHIJKLMNOP1234567890" not in out["output_excerpt_safe"]
    assert "<redacted>" in out["output_excerpt_safe"]


def test_real_smoke_uses_llm_provider_contract(monkeypatch):
    """Stage 3 关键回归: real_smoke 必须通过 LLMProvider.generate(LLMRequest)
    与 provider 通讯, 不能依赖任何 ad-hoc method (如 .complete/.chat)。

    这条测试在 v0.13 Stage 1 实现下会失败 — 修复后 (Stage 3) 才通过。
    """
    monkeypatch.setenv("MF_FAKE_TEST_KEY_CONTRACT", "x")
    cfg = _cfg_real_with_key("MF_FAKE_TEST_KEY_CONTRACT")

    captured: dict = {}

    class _ContractCheckProvider(LLMProvider):
        type = "openai_compatible"
        name = "contract"

        def generate(self, request: LLMRequest) -> LLMResult:
            captured["request_type"] = type(request).__name__
            captured["prompt_present"] = bool(request.prompt)
            captured["stage"] = request.stage
            captured["model"] = request.model
            return LLMResult(text="contract-ok", tokens_in=10, tokens_out=2, latency_ms=5)

    monkeypatch.setattr(
        "mindforge.llm.factory.build_providers",
        lambda _c: {"openai_main": _ContractCheckProvider()},
    )
    out = run_synthetic_real_smoke(cfg, allow_real=True)
    assert out["ran"] is True
    assert captured["request_type"] == "LLMRequest"
    assert captured["prompt_present"] is True
    assert captured["stage"] == "provider_smoke"
    assert captured["model"]  # non-empty
    assert out["tokens_in"] == 10
    assert out["tokens_out"] == 2
    assert out["latency_ms"] == 5
    assert out["output_excerpt_safe"] == "contract-ok"


def test_provider_error_is_caught_and_does_not_leak_message(monkeypatch):
    """provider 抛 ProviderError 时必须降级为 blocker, 不把 server message
    回显出来 (server 返回可能含敏感信息)。"""
    monkeypatch.setenv("MF_FAKE_TEST_KEY_PERR", "x")
    cfg = _cfg_real_with_key("MF_FAKE_TEST_KEY_PERR")

    secret_in_message = "leaky-server-detail-do-not-show-9999"

    class _RaisingProvider(LLMProvider):
        type = "openai_compatible"
        name = "raising"

        def generate(self, request: LLMRequest) -> LLMResult:
            raise ProviderError(f"http 401: {secret_in_message}")

    monkeypatch.setattr(
        "mindforge.llm.factory.build_providers",
        lambda _c: {"openai_main": _RaisingProvider()},
    )
    out = run_synthetic_real_smoke(cfg, allow_real=True)
    assert out["ran"] is False
    assert "ProviderError" in out["blocker"]
    assert secret_in_message not in repr(out)
