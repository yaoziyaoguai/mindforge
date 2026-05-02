"""v0.13 Stage 1 — provider readiness 单元测试 (fake-default + real opt-in).

覆盖语义不变量:

- 默认 fake → opt_in_state == "fake_default"; can_run_real_smoke False;
- 仅 env (api_key 存在但 profile 仍 fake) → opt_in_state == "env_only";
- 仅 profile 切换但 alias api_key 缺失 → opt_in_state == "profile_only";
- profile + api_key 齐全 → opt_in_state == "ready";
- inspect 永不返回 env value;
- render 输出含 fake-default / real provider opt-in / secret value
  not printed / human approval required / synthetic-only smoke input
  五个稳定 token。
"""

from __future__ import annotations

from dataclasses import dataclass


from mindforge.provider_readiness import (
    build_readiness_report,
    classify_real_opt_in,
    inspect_provider_config,
    render_readiness_report,
)


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


def _cfg_default_fake() -> _FakeLLMConfig:
    return _FakeLLMConfig(
        active_profile="fake",
        profiles={"fake": {"triage": "fake_only"}},
        models={"fake_only": _FakeMC(type="fake")},
    )


def _cfg_real_profile_no_key() -> _FakeLLMConfig:
    return _FakeLLMConfig(
        active_profile="real",
        profiles={"real": {"triage": "openai_main"}},
        models={
            "openai_main": _FakeMC(
                type="openai_compatible", api_key_env="MF_FAKE_TEST_KEY_AAA"
            ),
        },
    )


def _cfg_real_profile_with_key() -> _FakeLLMConfig:
    return _FakeLLMConfig(
        active_profile="real",
        profiles={"real": {"triage": "openai_main"}},
        models={
            "openai_main": _FakeMC(
                type="openai_compatible", api_key_env="MF_FAKE_TEST_KEY_BBB"
            ),
        },
    )


def _cfg_fake_profile_with_env_key() -> _FakeLLMConfig:
    return _FakeLLMConfig(
        active_profile="fake",
        profiles={"fake": {"triage": "fake_only"}},
        models={
            "fake_only": _FakeMC(type="fake"),
            "openai_main": _FakeMC(
                type="openai_compatible", api_key_env="MF_FAKE_TEST_KEY_CCC"
            ),
        },
    )


def test_fake_default_state(monkeypatch):
    monkeypatch.delenv("MF_FAKE_TEST_KEY_AAA", raising=False)
    monkeypatch.delenv("MF_FAKE_TEST_KEY_BBB", raising=False)
    report = build_readiness_report(_cfg_default_fake())
    assert report["opt_in"]["opt_in_state"] == "fake_default"
    assert report["opt_in"]["can_run_real_smoke"] is False
    assert report["invariants"]["fake_is_default"] is True


def test_env_only_state_when_api_key_set_but_profile_is_fake(monkeypatch):
    monkeypatch.setenv("MF_FAKE_TEST_KEY_CCC", "value-not-read-by-tests")
    report = build_readiness_report(_cfg_fake_profile_with_env_key())
    assert report["opt_in"]["opt_in_state"] == "env_only"
    assert report["opt_in"]["can_run_real_smoke"] is False


def test_profile_only_state_when_key_missing(monkeypatch):
    monkeypatch.delenv("MF_FAKE_TEST_KEY_AAA", raising=False)
    report = build_readiness_report(_cfg_real_profile_no_key())
    assert report["opt_in"]["opt_in_state"] == "profile_only"
    assert "openai_main" in " ".join(report["opt_in"]["blockers"])
    assert report["opt_in"]["can_run_real_smoke"] is False


def test_ready_state_when_profile_switched_and_key_present(monkeypatch):
    monkeypatch.setenv("MF_FAKE_TEST_KEY_BBB", "value-not-read-by-tests")
    report = build_readiness_report(_cfg_real_profile_with_key())
    assert report["opt_in"]["opt_in_state"] == "ready"
    assert report["opt_in"]["can_run_real_smoke"] is True


def test_inspect_does_not_return_env_value(monkeypatch):
    secret = "super-secret-value-must-never-leak-1234567890"
    monkeypatch.setenv("MF_FAKE_TEST_KEY_BBB", secret)
    report = inspect_provider_config(_cfg_real_profile_with_key())
    flat = repr(report)
    assert secret not in flat
    aliases = report["aliases"]
    assert any(a["api_key_present"] is True for a in aliases)
    for a in aliases:
        # presence-only: 不应包含任何 value-like 字段
        assert "api_key" not in {k for k in a if k != "api_key_env" and k != "api_key_present"}


def test_render_contains_required_tokens(monkeypatch):
    monkeypatch.delenv("MF_FAKE_TEST_KEY_AAA", raising=False)
    text = render_readiness_report(build_readiness_report(_cfg_default_fake()))
    for token in [
        "fake-default",
        "real provider opt-in",
        "secret value not printed",
        "human approval required",
        "synthetic-only smoke input",
    ]:
        assert token in text, f"missing token: {token!r}"


def test_classify_alone_is_pure_function():
    provider = {
        "active_profile": "fake",
        "aliases": [
            {
                "alias": "fake_only",
                "type": "fake",
                "api_key_env": None,
                "api_key_present": False,
                "base_url_env_present": False,
                "in_active_profile": True,
            }
        ],
        "active_alias_count": 1,
        "active_aliases_missing_key": [],
    }
    out = classify_real_opt_in(provider)
    assert out["opt_in_state"] == "fake_default"
    assert out["can_run_real_smoke"] is False
    assert out["blockers"] == []
