"""v0.13 Stage 2 — onboarding consolidation 一致性测试。

目标:

- 守住 ``configs/mindforge.yaml`` 默认 ``active_profile: fake`` 不被
  静默切到真实 profile;
- 守住 canonical roadmap / usage 的 excluded 列表不漂移;
- 守住 ``mindforge llm ping`` 与 ``mindforge provider readiness`` 在
  fake-default 下给出语义一致的判定;
- 守住 provider readiness JSON 输出 schema 稳定 (含 invariants)。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mindforge.cli import app

runner = CliRunner()


@pytest.fixture
def clean_env(monkeypatch):
    """中和 .env 自动加载并清掉所有 alias 声明的 api_key/base_url env;
    保证 readiness/ping 测试不被开发者本地 shell 状态污染。"""
    monkeypatch.setattr("mindforge.cli.load_dotenv_silently", lambda *_a, **_k: None)
    from mindforge.app_context import load_app_config
    cfg = load_app_config(Path("configs/mindforge.yaml"))
    for mc in cfg.llm.models.values():
        if mc.api_key_env:
            monkeypatch.delenv(mc.api_key_env, raising=False)
        if mc.base_url_env:
            monkeypatch.delenv(mc.base_url_env, raising=False)
    return monkeypatch


def test_default_config_active_profile_is_fake():
    """configs/mindforge.yaml 默认 profile 必须是 fake。

    这是 fake-default 安全契约的最外层防线: 一旦默认 profile 被改成
    真实 provider, 所有 'real-opt-in' 文档与测试失去保护意义。
    """
    text = Path("configs/mindforge.yaml").read_text(encoding="utf-8")
    # 容忍注释行; 仅断言至少一处 active_profile: fake (无引号)
    found = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped.startswith("active_profile:"):
            value = stripped.split(":", 1)[1].strip().strip("'\"")
            assert value == "fake", (
                f"default active_profile must be 'fake'; got {value!r}"
            )
            found = True
    assert found, "active_profile key not found in configs/mindforge.yaml"


def test_provider_readiness_json_schema(clean_env):
    result = runner.invoke(
        app,
        ["provider", "readiness", "--config", "configs/mindforge.yaml", "--format", "json"],
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    # schema 稳定性: 三段 + invariants 五字段
    assert set(report.keys()) == {"provider", "opt_in", "invariants"}
    assert set(report["opt_in"].keys()) >= {"opt_in_state", "blockers", "can_run_real_smoke"}
    invariants = report["invariants"]
    for k in (
        "fake_is_default",
        "secret_value_not_returned",
        "human_approval_required",
        "synthetic_only_smoke_input",
        "real_output_is_review_only",
    ):
        assert invariants[k] is True, f"invariant {k} flipped"
    # default config → opt_in_state must be fake_default
    assert report["opt_in"]["opt_in_state"] == "fake_default"


def test_readiness_unknown_format_rejected():
    result = runner.invoke(
        app,
        ["provider", "readiness", "--config", "configs/mindforge.yaml", "--format", "xml"],
    )
    assert result.exit_code == 2


def test_llm_ping_and_provider_readiness_agree_on_fake_default(clean_env):
    """两个 surface 在 fake-default 下都不应该报告 missing required env。

    避免 readiness 与 llm ping 在 'fake 是否安全' 这个最基本判断上
    出现漂移; 漂移 = 用户看到两份矛盾报告 = 安全契约信任下降。
    """

    ping = runner.invoke(app, ["llm", "ping", "--config", "configs/mindforge.yaml"])
    assert ping.exit_code == 0, ping.output
    # fake provider 没有 required env, 不应该出现 MISSING
    assert "MISSING" not in ping.output

    readiness = runner.invoke(
        app,
        ["provider", "readiness", "--config", "configs/mindforge.yaml", "--format", "json"],
    )
    assert readiness.exit_code == 0
    report = json.loads(readiness.output)
    assert report["opt_in"]["opt_in_state"] == "fake_default"
    assert report["opt_in"]["can_run_real_smoke"] is False


def test_capability_matrix_section_consistency():
    """Canonical docs 不能撤销已声明的 excluded 不变量。

    Roadmap / Usage 必须保持关闭状态语义 (no real-by-default,
    no auto-approval, no real vault writes, no Cubox real ingestion);
    """
    text = Path("README.md").read_text(encoding="utf-8")
    assert "Real LLM enabled by default" in text
    assert "Real Cubox API calls enabled by default" in text
    assert "Hidden automatic approval" in text
    assert "does not automatically modify a real private vault" in text
