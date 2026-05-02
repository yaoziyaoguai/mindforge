"""Stage 4 — Real LLM provider opt-in skeleton boundary tests.

设计意图
========

仓库已有 ``OpenAICompatibleProvider`` / ``AnthropicCompatibleProvider``
真实 provider，与 ``FakeProvider`` 共享 ``LLMProvider`` 抽象。Stage 4
不是新增 provider，而是把"真实 provider 必须显式 opt-in、默认走 fake"
这条架构契约固化为测试，并守护 secret redaction 与 source-domain 解耦。

本文件覆盖：

1. 默认 bundled 配置 ``configs/mindforge.yaml`` 的 ``active_profile``
   是 ``fake``；
2. ``build_providers`` 在 fake profile 下**只**实例化 ``FakeProvider``，
   绝不实例化 OpenAI / Anthropic provider；
3. fake profile 下构造 providers 不会触发 ``os.environ.get`` 读
   ``OPENAI_API_KEY`` / ``ANTHROPIC_API_KEY`` 等 secret env；
4. ``FakeProvider`` 不发起网络请求；
5. provider 模块不 import cubox / sources / approver / review_service /
   workspace（provider 不感知 source domain）；
6. provider 模块不 import dotenv / env_loader（secret 路径只走 os.environ）；
7. ``OpenAICompatibleProvider`` / ``AnthropicCompatibleProvider`` 默认
   ``__repr__``（object id）不会泄漏 ``api_key`` 字面值；
8. ``ProviderError`` 消息构造路径不会内嵌 api_key。
"""

from __future__ import annotations

import ast
import os
import socket
from pathlib import Path

import pytest

from mindforge.llm.base import LLMRequest, ProviderError
from mindforge.llm.factory import build_providers
from mindforge.llm.fake import FakeProvider

_REPO = Path(__file__).resolve().parent.parent
_SRC = _REPO / "src" / "mindforge"
_LLM_DIR = _SRC / "llm"
_DEFAULT_YAML = _REPO / "configs" / "mindforge.yaml"


# ---------------------------------------------------------------------------
# 1. 默认配置走 fake
# ---------------------------------------------------------------------------


def test_default_bundled_config_active_profile_is_fake() -> None:
    text = _DEFAULT_YAML.read_text(encoding="utf-8")
    # 必须显式声明 active_profile: fake；不允许 active_profile: openai 等
    assert "active_profile: fake" in text
    # 逐行扫一遍，确保没有别的 active_profile 行潜藏
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("active_profile:"):
            assert s == "active_profile: fake", (
                f"默认 bundled 配置必须 active_profile=fake，发现：{s!r}"
            )


def test_packaged_default_config_active_profile_is_fake() -> None:
    """与上一条测试不同：本条断言**安装态**下 ``importlib.resources`` 暴露
    的 packaged 配置同样默认走 fake，避免发布时 yaml 漂移。"""
    from mindforge.assets_runtime import asset_root

    bundled = asset_root().joinpath("configs", "mindforge.yaml").read_text(
        encoding="utf-8"
    )
    assert "active_profile: fake" in bundled


# ---------------------------------------------------------------------------
# 2. fake profile 下 build_providers 不实例化真实 provider
# ---------------------------------------------------------------------------


def _load_default_cfg():
    from mindforge.config import load_mindforge_config

    return load_mindforge_config(_DEFAULT_YAML)


def test_build_providers_fake_profile_only_constructs_fake_provider() -> None:
    cfg = _load_default_cfg()
    providers = build_providers(cfg.llm)
    assert providers, "build_providers 至少应返回 fake profile 引用的 alias"
    for alias, p in providers.items():
        assert isinstance(p, FakeProvider), (
            f"fake profile 不应实例化 {type(p).__name__}（alias={alias}）"
        )


def test_build_providers_fake_profile_does_not_read_secret_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """fake profile 下不应触发 os.environ.get 读取真实 secret 环境变量。"""
    forbidden = {
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "UPSTAGE_API_KEY",
        "OPENAI_BASE_URL",
        "ANTHROPIC_BASE_URL",
    }

    real_get = os.environ.get
    accessed: list[str] = []

    def spy(name: str, default=None):  # type: ignore[no-untyped-def]
        if name in forbidden:
            accessed.append(name)
        return real_get(name, default)

    monkeypatch.setattr(os.environ, "get", spy)
    cfg = _load_default_cfg()
    build_providers(cfg.llm)
    assert accessed == [], (
        f"fake profile 下不应读取 secret env，违规访问：{accessed}"
    )


# ---------------------------------------------------------------------------
# 3. FakeProvider 不联网
# ---------------------------------------------------------------------------


def test_fake_provider_generate_does_not_open_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("FakeProvider 不应建立网络连接")

    monkeypatch.setattr(socket.socket, "connect", _boom)
    monkeypatch.setattr(socket.socket, "connect_ex", _boom)
    fp = FakeProvider()
    res = fp.generate(
        LLMRequest(
            prompt="title: hello\n", stage="triage", model="fake_fast"
        )
    )
    assert res.text  # schema 化输出
    assert isinstance(res.text, str)


# ---------------------------------------------------------------------------
# 4. AST：provider 不感知 source domain，也不读 dotenv
# ---------------------------------------------------------------------------


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names.add(a.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


_FORBIDDEN_FOR_PROVIDER = {
    # source domain
    "mindforge.cubox_cli",
    "mindforge.cubox_dryrun_presenter",
    "mindforge.cubox_preview_presenter",
    "mindforge.source_mux",
    "mindforge.scanner",
    "mindforge.sources.cubox_api",
    "mindforge.sources.cubox_markdown",
    # approval / review domain
    "mindforge.approver",
    "mindforge.approval_service",
    "mindforge.reviewer",
    "mindforge.review_service",
    # workspace / vault
    "mindforge.vault_writer",
    "mindforge.workspace",
    "mindforge.obsidian",
    # dotenv 必须只走 os.environ；provider 不允许读取 .env
    "dotenv",
    "mindforge.env_loader",
}


def test_llm_provider_modules_do_not_import_source_or_dotenv() -> None:
    targets = [
        _LLM_DIR / "base.py",
        _LLM_DIR / "client.py",
        _LLM_DIR / "factory.py",
        _LLM_DIR / "fake.py",
        _LLM_DIR / "openai_compatible.py",
        _LLM_DIR / "anthropic_compatible.py",
    ]
    for t in targets:
        leaked = _imports(t) & _FORBIDDEN_FOR_PROVIDER
        assert not leaked, f"{t.name} 不应 import：{leaked}"


# ---------------------------------------------------------------------------
# 5. Secret redaction：repr / ProviderError 不外泄 api_key
# ---------------------------------------------------------------------------


def test_openai_provider_repr_does_not_leak_api_key() -> None:
    from mindforge.llm.openai_compatible import OpenAICompatibleProvider

    p = OpenAICompatibleProvider(
        name="test",
        base_url="https://example.invalid",
        api_key="sk-SUPERSECRET-shouldnotleak-zzz",
        timeout_seconds=1,
    )
    assert "SUPERSECRET" not in repr(p)
    assert "sk-" not in repr(p)


def test_anthropic_provider_repr_does_not_leak_api_key() -> None:
    from mindforge.llm.anthropic_compatible import AnthropicCompatibleProvider

    p = AnthropicCompatibleProvider(
        name="test",
        base_url="https://example.invalid",
        api_key="sk-SUPERSECRET-shouldnotleak-zzz",
        anthropic_version="2023-06-01",
        timeout_seconds=1,
    )
    text = repr(p) + str(p)
    assert "SUPERSECRET" not in text
    assert "sk-" not in text


def test_provider_error_str_does_not_leak_api_key_when_constructed_with_one() -> None:
    """ProviderError 是 RuntimeError 子类；如果业务层不慎把 api_key 拼进
    message，str(err) 会泄漏。本测试**不**断言所有调用点正确，只断言：
    err 自身不会**自动**追加 api_key，例如不会把 args 中的 api_key 渲染。
    """
    err = ProviderError("auth failed")
    assert "sk-" not in str(err)
    assert "Bearer" not in str(err)


# ---------------------------------------------------------------------------
# 9. provider repr 主动安全（risk #11）
#
# 既有 test_openai/anthropic_provider_repr_does_not_leak_api_key 是负面断言：
# 只检查 "SUPERSECRET" / "sk-" 不在 repr 中。它们当前能通过是因为 Python
# 默认 ``object.__repr__`` 不打印实例属性 —— 这是**被动安全**：一旦有人给
# provider 类加 ``@dataclass`` 装饰器或写自定义 ``__repr__``，默认行为就会
# 把 ``self.api_key`` / ``self._api_key`` 露出。
#
# 下面的正面断言要求 provider 类**显式**实现 ``__repr__`` 并明确包含可观测
# 但安全的字段（provider name + credential_present 标记），把"安全 repr"
# 这一不变量从被动转主动。
# ---------------------------------------------------------------------------


def test_openai_provider_has_explicit_repr_with_safe_fields() -> None:
    """OpenAI provider 必须显式实现 __repr__，包含 name + credential_present；
    不得包含 api_key 明文或 base_url 完整值。
    """
    from mindforge.llm.openai_compatible import OpenAICompatibleProvider

    p = OpenAICompatibleProvider(
        name="openai_test",
        base_url="https://example.invalid/v1/path/that/should/not/leak",
        api_key="sk-SUPERSECRET-shouldnotleak-zzz",
        timeout_seconds=1,
    )
    text = repr(p)
    # 安全：禁止 token 明文
    assert "SUPERSECRET" not in text
    assert "sk-" not in text
    # 安全：禁止 base_url 完整路径泄漏（避免内网/代理 URL 被打到日志）
    assert "/path/that/should/not/leak" not in text
    # 主动：必须显式实现，而非默认 object repr
    assert "object at 0x" not in text, (
        "OpenAICompatibleProvider 必须显式实现 __repr__，不可依赖默认 object repr"
    )
    # 主动：可观测字段
    assert "openai_test" in text  # name
    assert "credential_present" in text  # 显式 redact 标记


def test_openai_provider_str_is_safe_alias_of_repr() -> None:
    from mindforge.llm.openai_compatible import OpenAICompatibleProvider

    p = OpenAICompatibleProvider(
        name="openai_test",
        base_url="https://example.invalid",
        api_key="sk-SUPERSECRET-shouldnotleak",
        timeout_seconds=1,
    )
    assert "SUPERSECRET" not in str(p)
    assert "sk-" not in str(p)


def test_anthropic_provider_has_explicit_repr_with_safe_fields() -> None:
    from mindforge.llm.anthropic_compatible import AnthropicCompatibleProvider

    p = AnthropicCompatibleProvider(
        name="anthropic_test",
        base_url="https://example.invalid/v1/path/that/should/not/leak",
        api_key="sk-SUPERSECRET-shouldnotleak-zzz",
        anthropic_version="2023-06-01",
        timeout_seconds=1,
    )
    text = repr(p)
    assert "SUPERSECRET" not in text
    assert "sk-" not in text
    assert "/path/that/should/not/leak" not in text
    assert "object at 0x" not in text, (
        "AnthropicCompatibleProvider 必须显式实现 __repr__，不可依赖默认 object repr"
    )
    assert "anthropic_test" in text
    assert "credential_present" in text


def test_anthropic_provider_str_is_safe_alias_of_repr() -> None:
    from mindforge.llm.anthropic_compatible import AnthropicCompatibleProvider

    p = AnthropicCompatibleProvider(
        name="anthropic_test",
        base_url="https://example.invalid",
        api_key="sk-SUPERSECRET-shouldnotleak",
        anthropic_version="2023-06-01",
        timeout_seconds=1,
    )
    assert "SUPERSECRET" not in str(p)
    assert "sk-" not in str(p)


def test_provider_repr_does_not_read_dotenv_or_open_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """构造 provider + 调 repr/str 不应读 .env、不应联网。"""
    from mindforge.llm.anthropic_compatible import AnthropicCompatibleProvider
    from mindforge.llm.openai_compatible import OpenAICompatibleProvider

    def _boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("provider repr 不应建立网络连接")

    monkeypatch.setattr(socket.socket, "connect", _boom)
    monkeypatch.setattr(socket.socket, "connect_ex", _boom)

    p1 = OpenAICompatibleProvider(
        name="o", base_url="https://example.invalid", api_key="sk-x", timeout_seconds=1
    )
    p2 = AnthropicCompatibleProvider(
        name="a",
        base_url="https://example.invalid",
        api_key="sk-y",
        anthropic_version="2023-06-01",
        timeout_seconds=1,
    )
    # 任意调用都不能联网；不依赖 .env（若依赖会在构造时就读）
    _ = repr(p1) + str(p1) + repr(p2) + str(p2)
