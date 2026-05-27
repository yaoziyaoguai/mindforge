"""CLI adapter runtime tests — apply_provider_selection 行为验证。

中文学习型说明：验证 CLI adapter 层 provider selection 在 zero-config /
placeholder model / fake provider 等边界下的自动 fallback 行为。
"""

from __future__ import annotations

from pathlib import Path

from mindforge.cli_runtime import apply_provider_selection
from mindforge.config import (
    LLMConfig,
    MindForgeConfig,
    ModelConfig,
    SourcesConfig,
    VaultConfig,
)


# ---------------------------------------------------------------------------
# helper: 构造最小 MindForgeConfig（只改 llm 部分）
# ---------------------------------------------------------------------------


def _base_config(project_root: Path | None = None, **llm_kw: object) -> MindForgeConfig:
    vault = VaultConfig(
        root=Path("/tmp/mf-test/vault"),
        inbox_root="00-Inbox",
        cards_dir="20-Knowledge-Cards",
        archive_dir="90-Archive/Skipped",
    )
    sources = SourcesConfig(enabled=(), registry={})
    llm = LLMConfig(**{"active_profile": "fake", "profiles": {}, "models": {}, **llm_kw})  # type: ignore[arg-type]
    raw: dict = {}
    if project_root is not None:
        raw["_mindforge_project"] = {"root": str(project_root)}
    return MindForgeConfig(  # type: ignore[call-arg]
        version=0.7,
        vault=vault,
        sources=sources,
        state=None,  # type: ignore[arg-type]
        triage=None,  # type: ignore[arg-type]
        llm=llm,
        prompts=None,  # type: ignore[arg-type]
        logging=None,  # type: ignore[arg-type]
        raw=raw,
    )


# ---------------------------------------------------------------------------
# P0: placeholder model → auto-fallback to fake provider
# ---------------------------------------------------------------------------


def test_empty_models_triggers_fake_fallback() -> None:
    """空 models → apply_provider_selection 自动回退 fake provider。"""
    cfg = _base_config(models={})
    result = apply_provider_selection(cfg, provider=None, legacy_profile=None)
    assert result.llm.active_profile == "fake"
    assert "fake_fast" in result.llm.models
    assert "fake_strong" in result.llm.models


def test_placeholder_model_without_secrets_keeps_user_provider_as_is(tmp_path: Path) -> None:
    """placeholder model 有完整 metadata 但无 API key → 不触发 fake fallback。

    中文学习型说明：模型已配置但缺少 API key（needs_setup）不是 demo 状态；
    用户显式配置了模型表明确实想用真实 provider。此时应保持原样，让后续
    processing runtime 给出可操作错误提示。
    """
    placeholder = ModelConfig(
        alias="main",
        provider="openai_compatible",
        type="openai_compatible",
        base_url="https://your-router.example.com/v1",
        model="your-model-name",
        timeout_seconds=30,
        max_retries=1,
    )
    cfg = _base_config(
        project_root=tmp_path,
        active_profile="main",
        profiles={"main": {"triage": "main", "distill": "main", "link_suggestion": "main", "review_questions": "main", "action_extraction": "main"}},
        models={"main": placeholder},
        default_model="main",
        routing={s: "main" for s in ("triage", "distill", "link_suggestion", "review_questions", "action_extraction")},
    )
    # tmp_path 下无 secrets.json → model_setup_readiness 返回 "needs_setup"
    # 但 apply_provider_selection 不应自动回退 fake — 用户显式配置了模型
    result = apply_provider_selection(cfg, provider=None, legacy_profile=None)
    assert result.llm.active_profile == "main"


def test_placeholder_model_explicit_real_provider_not_overwritten() -> None:
    """用户显式 --provider real → 不触发 fake fallback。"""
    placeholder = ModelConfig(
        alias="main",
        provider="openai_compatible",
        type="openai_compatible",
        base_url="https://your-router.example.com/v1",
        model="your-model-name",
        timeout_seconds=30,
        max_retries=1,
    )
    cfg = _base_config(
        active_profile="main",
        profiles={"main": {"triage": "main", "distill": "main", "link_suggestion": "main", "review_questions": "main", "action_extraction": "main"}},
        models={"main": placeholder},
        default_model="main",
    )
    # 显式选择 provider → 不触发 auto-fallback
    result = apply_provider_selection(cfg, provider="main", legacy_profile=None)
    assert result.llm.active_profile == "main"


def test_explicit_fake_provider_bypasses_model_readiness(tmp_path: Path) -> None:
    """显式 --provider fake → 直接注入 fake profile，不走 readiness 检查。"""
    placeholder = ModelConfig(
        alias="main",
        provider="openai_compatible",
        type="openai_compatible",
        base_url="https://your-router.example.com/v1",
        model="your-model-name",
        timeout_seconds=30,
        max_retries=1,
    )
    cfg = _base_config(
        project_root=tmp_path,
        active_profile="main",
        profiles={"main": {"triage": "main"}},
        models={"main": placeholder},
        default_model="main",
    )
    result = apply_provider_selection(cfg, provider="fake", legacy_profile=None)
    assert result.llm.active_profile == "fake"
    assert "fake_fast" in result.llm.models


def test_legacy_profile_flag_still_works() -> None:
    """--profile fake（legacy）仍然有效。"""
    result = apply_provider_selection(_base_config(models={}), provider=None, legacy_profile="fake")
    assert result.llm.active_profile == "fake"
