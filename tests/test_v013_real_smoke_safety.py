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


from mindforge.real_smoke import build_synthetic_prompt, run_synthetic_real_smoke


@dataclass(frozen=True)
class _FakeMC:
    type: str
    api_key_env: str | None = None
    base_url_env: str | None = None


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
    # 即使 ready, 也用 monkeypatch 拦住真实 provider 构建, 验证返回值不含 secret
    cfg = _cfg_real_with_key("MF_FAKE_TEST_KEY_LEAK_CHECK")

    class _StubProvider:
        def complete(self, prompt: str) -> str:
            return "ok"

    def _stub_build_providers(_cfg):
        return {"openai_main": _StubProvider()}

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

    class _StubProvider:
        def complete(self, prompt: str) -> str:
            return "stub-ok"

    def _stub_build_providers(_cfg):
        calls["factory"] += 1
        return {"openai_main": _StubProvider()}

    monkeypatch.setattr(
        "mindforge.llm.factory.build_providers", _stub_build_providers
    )
    out = run_synthetic_real_smoke(cfg, allow_real=True)
    assert out["ran"] is True
    assert calls["factory"] == 1
    assert out["alias"] == "openai_main"
    assert out["provider_type"] == "openai_compatible"


def test_excerpt_scrubs_apparent_secrets(monkeypatch):
    monkeypatch.setenv("MF_FAKE_TEST_KEY_SCRUB", "x")
    cfg = _cfg_real_with_key("MF_FAKE_TEST_KEY_SCRUB")

    class _StubProvider:
        def complete(self, prompt: str) -> str:
            return "leaked sk-ABCDEFGHIJKLMNOP1234567890 something"

    monkeypatch.setattr(
        "mindforge.llm.factory.build_providers",
        lambda _c: {"openai_main": _StubProvider()},
    )
    out = run_synthetic_real_smoke(cfg, allow_real=True)
    assert "sk-ABCDEFGHIJKLMNOP1234567890" not in out["output_excerpt_safe"]
    assert "<redacted>" in out["output_excerpt_safe"]
