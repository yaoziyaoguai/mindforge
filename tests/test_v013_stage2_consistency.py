"""v0.13 Stage 2 — onboarding consolidation 一致性测试。

目标:

- 守住 bundled user config 使用新的 ``llm.models/default_model`` 语义;
- 守住 canonical roadmap / usage 的 excluded 列表不漂移;
- 守住 legacy ``provider`` / ``llm`` CLI 不再作为产品 surface 暴露;
- 守住 provider readiness JSON 输出 schema 稳定 (含 invariants)。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from mindforge.cli import app
from mindforge.provider_readiness import build_readiness_report
from mindforge.real_smoke import run_synthetic_real_smoke

runner = CliRunner()


@pytest.fixture
def clean_env(monkeypatch):
    """中和 .env 自动加载并清掉所有 alias 声明的 api_key/base_url env。

    中文学习型说明：provider readiness 仍是内部 service contract，但
    ``mindforge provider`` / ``mindforge llm`` 已迁移出用户 CLI 主路径；
    测试直接调用 service，避免为了测试把 legacy command group 加回来。
    """
    monkeypatch.setattr("mindforge.cli.load_dotenv_silently", lambda *_a, **_k: None)
    from mindforge.assets_runtime import bundled_asset_path_for_process
    from mindforge.app_context import load_app_config
    cfg = load_app_config(bundled_asset_path_for_process("configs", "mindforge.yaml"))
    for mc in cfg.llm.models.values():
        if mc.api_key_env:
            monkeypatch.delenv(mc.api_key_env, raising=False)
        if mc.base_url_env:
            monkeypatch.delenv(mc.base_url_env, raising=False)
    return monkeypatch


def test_bundled_config_active_provider_is_real_dogfood():
    """package user config 默认 LLM 语义必须是 models/default_model。

    fake provider 仍保留给 CI/offline demo/deterministic tests；新用户主配置
    不再暴露 active_profile/profile/fake alias。
    """
    text = Path("src/mindforge/assets/configs/mindforge.user.yaml").read_text(encoding="utf-8")
    assert "default_model: main" in text
    assert "models:" in text
    assert "API keys are stored in local secret store" in text
    assert "api_key_env:" not in text
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        assert not stripped.startswith("active:")
        assert not stripped.startswith("active_profile:")
        assert not stripped.startswith("profiles:")


def test_provider_readiness_json_schema(clean_env):
    from mindforge.assets_runtime import bundled_asset_path_for_process
    from mindforge.app_context import load_app_config

    cfg = load_app_config(bundled_asset_path_for_process("configs", "mindforge.yaml"))
    report = build_readiness_report(cfg.llm)
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
    # real dogfood default config 缺 key 时必须清楚显示 profile_only，不 fallback fake。
    assert report["opt_in"]["opt_in_state"] == "profile_only"


def test_provider_cli_surface_removed_from_typer_registry():
    """legacy provider command 不再是完整 Typer command group。"""
    result = runner.invoke(app, ["provider", "readiness"])
    assert result.exit_code == 2
    assert "No such command" in result.output


def test_llm_ping_and_provider_readiness_agree_on_real_profile_missing_env(clean_env):
    """真实模型默认配置缺 key 时，readiness 与 smoke guard 语义一致。

    这里不调用真实 provider，只验证 presence-only 诊断与 smoke guard
    都不会 fake 成功。
    """

    from mindforge.assets_runtime import bundled_asset_path_for_process
    from mindforge.app_context import load_app_config

    cfg = load_app_config(bundled_asset_path_for_process("configs", "mindforge.yaml"))
    smoke = run_synthetic_real_smoke(cfg.llm, allow_real=True)
    assert smoke["ran"] is False
    assert "profile_only" in smoke["blocker"]

    report = build_readiness_report(cfg.llm)
    assert report["opt_in"]["opt_in_state"] == "profile_only"
    assert report["opt_in"]["can_run_real_smoke"] is False


def test_capability_matrix_section_consistency():
    """Canonical docs 不能撤销已声明的 excluded 不变量。

    Roadmap / Usage 必须保持关闭状态语义 (no real-by-default,
    no auto-approval, no real vault writes, no Cubox real ingestion);
    """
    text = Path("README.md").read_text(encoding="utf-8")
    assert "Real LLM enabled by default" in text
    assert "External account ingestion" in text
    assert "Hidden automatic approval" in text
    assert "does not automatically modify a real private vault" in text
