"""产品表面与测试替身隔离契约。

中文学习型说明：MindForge 的端到端测试应该替身化 LLM 返回，而不是把
``fake provider`` 或 deterministic strategy 包装成用户能力。本文件只锁定
用户可见语义：正式 production workflow 是 Knowledge Card Workflow；
``five_stage`` 是 legacy/internal pipeline alias；deterministic baselines 默认
隐藏，不能作为 production active_strategy。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from rich.console import Console
from typer.testing import CliRunner

from mindforge.assets_runtime import asset_root
from mindforge.cli import app
from mindforge.config import MindForgeConfig, StrategyConfig, load_mindforge_config
from mindforge.llm import LLMResult, ResolvedModel, StageCallResult
from mindforge.process_service import ProcessAssets, ProcessRuntime, ProviderSelection
from mindforge.processors.pipeline import _build_card_payload
from mindforge.process_executor import build_pipeline
from mindforge.presenters.local_status import render_local_status
from mindforge.services.doctor import compute_doctor_hints, config_doctor_rows
from mindforge.services.local_status import LocalStatusSnapshot
from mindforge.sources.base import SourceDocument, compute_content_hash
from mindforge.strategies import DEFAULT_STRATEGY_NAME, get_strategy_metadata
from mindforge.strategy_selection import (
    StrategySelectionError,
    resolve_strategy_selection,
)


runner = CliRunner()


def test_default_public_strategy_is_knowledge_card() -> None:
    assert DEFAULT_STRATEGY_NAME == "knowledge_card"
    meta = get_strategy_metadata("knowledge_card")
    assert meta.display_name == "Knowledge Card Workflow"
    assert meta.production_ready is True
    assert meta.user_recommended is True


def test_strategies_list_hides_internal_baselines_by_default() -> None:
    result = runner.invoke(app, ["strategies", "list"])

    assert result.exit_code == 0, result.output
    out = result.output
    assert "knowledge_card" in out
    assert "Knowledge Card Workflow" in out
    assert "default_knowledge_card" not in out
    assert "concept_extraction" not in out
    assert "action_item" not in out


def test_strategies_list_include_internal_shows_debug_fixtures() -> None:
    result = runner.invoke(app, ["strategies", "list", "--include-internal"])

    assert result.exit_code == 0, result.output
    out = result.output
    assert "knowledge_card" in out
    assert "default_knowledge_card" in out
    assert "concept_extraction" in out
    assert "action_item" in out
    assert "internal_baseline" in out
    assert "fake-first" not in out
    assert "回退路径" not in out
    assert "默认离线可跑" not in out
    assert "fake provider 默认" not in out


def test_strategies_show_legacy_alias_explains_canonical_strategy() -> None:
    result = runner.invoke(app, ["strategies", "show", "five_stage"])

    assert result.exit_code == 0, result.output
    assert "legacy alias" in result.output.lower()
    assert "knowledge_card" in result.output
    assert "Knowledge Card Strategy" in result.output
    assert "(not used by this strategy)" not in result.output


def test_internal_strategy_show_requires_include_internal() -> None:
    result = runner.invoke(app, ["strategies", "show", "default_knowledge_card"])

    assert result.exit_code != 0
    assert "--include-internal" in result.output


def test_active_strategy_default_and_legacy_alias_resolve_to_canonical(
) -> None:
    cfg = _bundled_config()
    assert cfg.strategy.active == "knowledge_card"

    legacy_cfg = _replace_strategy(cfg, "five_stage")
    selected = resolve_strategy_selection(legacy_cfg)
    assert selected.strategy_id == "knowledge_card"
    assert selected.metadata.canonical_id == "knowledge_card"
    assert selected.legacy_alias == "five_stage"


@pytest.mark.parametrize("strategy_id", ["default_knowledge_card", "concept_extraction", "action_item"])
def test_internal_strategy_cannot_be_active_without_dev_mode(
    strategy_id: str,
) -> None:
    cfg = _replace_strategy(_bundled_config(), strategy_id)

    with pytest.raises(StrategySelectionError, match="internal|not production|planned"):
        resolve_strategy_selection(cfg)


def test_knowledge_card_pipeline_writes_canonical_strategy_id() -> None:
    """新生成 card provenance 应写用户可见 canonical id，而不是内部 pipeline 名。

    大模型可以在测试里 stub，但 strategy runtime path 不能替换成
    deterministic strategy；这里直接测生产 pipeline envelope 的身份字段。
    """

    payload = _build_card_payload(
        doc=_source_doc(),
        track="agent-runtime",
        value_score=8,
        distill={
            "slug": "production-path-alignment",
            "title": "Production Path Alignment",
            "tags": ["strategy"],
            "confidence": 0.7,
            "source_excerpt": "Tests should stub LLM responses, not strategy.",
            "ai_summary_bullets": ["Use production strategy with injected LLM stubs."],
            "ai_inference_bullets": [],
            "reusable_prompts_or_principles": ["Fake model output, not strategy runtime."],
        },
        link_suggestion={"suggested_links": [], "project_hooks": []},
        review_questions={"review_questions": []},
        action_extraction={"action_items": []},
    )

    assert payload["strategy_id"] == "knowledge_card"
    assert payload["review_hints"]["title"] == "Production Path Alignment"


def test_knowledge_card_strategy_can_run_with_injected_stub_llm() -> None:
    """测试替身化 LLM response，而不是替换 strategy runtime path。

    中文学习型说明：这是 production/test path alignment 的核心。大模型返回可以
    stub，但仍应构造 Knowledge Card Workflow，并走 triage/distill/link/review/
    action 五段 prompt pipeline，最后得到 canonical ``knowledge_card`` envelope。
    """

    cfg = _bundled_config()
    pipeline = build_pipeline(
        cfg=cfg,
        runtime=_bundled_runtime(),
        strategy="knowledge_card",
        llm_client=_StubLLMClient(),
    )
    pipeline.logger = _NoOpLogger()  # type: ignore[attr-defined]

    outcome = pipeline.run(_source_doc())

    assert outcome.status == "processed"
    assert outcome.card_payload is not None
    assert outcome.card_payload["strategy_id"] == "knowledge_card"
    assert set(outcome.stages_meta) == {
        "triage",
        "distill",
        "link_suggestion",
        "review_questions",
        "action_extraction",
    }


def test_readme_main_path_does_not_recommend_fake_or_internal_strategies() -> None:
    text = Path("README.md").read_text(encoding="utf-8")
    main, _, developer = text.partition("## 开发者")

    for token in ("mindforge demo", "fake", "Cubox", "cubox", "dogfood", "active_profile", "profiles"):
        assert token not in main, f"{token!r} must not appear in the user-facing README path"
    assert "--provider fake" not in main
    assert "default_knowledge_card" not in main
    assert "concept_extraction" not in main
    assert "Knowledge Card Workflow" in main


def test_example_config_does_not_contain_legacy_tokens() -> None:
    """configs/mindforge_example.yaml 不包含 legacy 配置标记。"""
    text = Path("configs/mindforge_example.yaml").read_text(encoding="utf-8")
    forbidden = ["active_profile", "profiles:", "fake_fast", "fake_strong",
                 "api_key_env", "base_url_env", "model_env", "anthropic_coding_plan",
                 "all_local", "active_profile: fake"]
    for token in forbidden:
        assert token not in text, f"forbidden token {token!r} found in example config"


def test_example_config_routing_refs_valid_models() -> None:
    """example config 的 routing 和 wiki.model 都引用 llm.models 中存在的 model id。"""
    import yaml
    data = yaml.safe_load(Path("configs/mindforge_example.yaml").read_text(encoding="utf-8"))
    models = set(data["llm"]["models"].keys())
    for step, model_id in data["llm"]["routing"].items():
        assert model_id in models, f"routing.{step}={model_id!r} not in models {models}"
    if "wiki" in data and "model" in data["wiki"]:
        assert data["wiki"]["model"] in models, f"wiki.model not in models {models}"


def test_readme_references_example_config() -> None:
    """README 引用了 mindforge_example.yaml。"""
    text = Path("README.md").read_text(encoding="utf-8")
    assert "mindforge_example.yaml" in text


def test_llm_provider_doc_references_example_config() -> None:
    """docs/LLM_PROVIDER_CONFIG.md 引用了 mindforge_example.yaml。"""
    text = Path("docs/LLM_PROVIDER_CONFIG.md").read_text(encoding="utf-8")
    assert "mindforge_example.yaml" in text


def test_llm_provider_doc_hides_legacy_and_internal_paths() -> None:
    """LLM 配置文档也必须以 Web Setup + real model 为主路径。"""

    text = Path("docs/LLM_PROVIDER_CONFIG.md").read_text(encoding="utf-8")
    for token in (
        "fake",
        "dogfood",
        "Cubox",
        "cubox",
        "active_profile",
        "profiles",
        "api_key_env",
        "base_url_env",
        "model_env",
        ".env",
    ):
        assert token not in text, f"{token!r} leaked into LLM provider docs"


def test_readme_first_stage_dogfood_contract_is_explicit() -> None:
    """README 锁定第一阶段 dogfood 表面，避免重新漂回 legacy/provider 文案。

    中文学习型说明：这不是业务逻辑测试，而是产品承诺测试。README 是 GitHub
    新用户的第一入口，必须把本地配置、secret store、路径和 Wiki 手动边界说清楚。
    """

    text = Path("README.md").read_text(encoding="utf-8")
    main, _, developer = text.partition("## 开发者")

    assert "configs/mindforge_example.yaml" in text
    assert "configs/mindforge.yaml" in text
    assert "本地运行时配置" in text
    assert "secret store" in text
    assert ".mindforge/secrets.json" in text
    assert "Web Add Source" in text
    assert "必须绝对路径" in text
    assert "anthropic" in text
    assert "anthropic_compatible" in text
    assert "openai" in text
    assert "openai_compatible" in text
    assert "LLM synthesis 必须由用户在 Wiki 页面或 CLI 手动触发" in text
    assert "not RAG / not embedding / no vector DB" in text
    assert "vault/" in text
    assert "本地知识库" in text
    assert "不提交" in text
    assert "支持相对路径" in text
    assert "解析为绝对路径" in text

    for token in ("active_profile", "profiles", "fake_fast", "fake_strong", "mindforge demo", "Cubox", "dogfood"):
        assert token not in main, f"{token!r} must not appear in the user-facing README path"

    assert developer  # legacy/dev notes may still exist after the developer boundary.


def test_cli_primary_help_hides_internal_demo_cubox_env_profile_surfaces() -> None:
    """普通用户 CLI 主 help 只能展示第一阶段真实主路径。

    中文学习型说明：fake/demo/Cubox/env/profile 可以继续作为测试或开发内部实现
    存在，但不能再出现在 root help 里作为普通用户入口。
    """
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0, result.output
    out = result.output
    for token in (
        "demo",
        "dogfood",
        "cubox",
        "Cubox",
        "fake",
        "profile",
        "active_profile",
        "profiles",
        ".env",
        "env",
        "provider readiness",
        "profile_only",
    ):
        assert token not in out, f"{token!r} leaked into root help"
    for token in ("web", "status", "doctor", "watch", "import", "approve", "library", "trash", "wiki", "prompts", "recall"):
        assert token in out


def test_cli_commands_map_hides_internal_demo_cubox_env_profile_surfaces() -> None:
    """``mindforge commands`` 是普通用户命令地图，不列开发/测试 fixture。"""
    result = runner.invoke(app, ["commands"])

    assert result.exit_code == 0, result.output
    out = result.output
    for token in ("demo", "dogfood", "cubox", "Cubox", "fake", "profile", "active_profile", "profiles", ".env", "env"):
        assert token not in out, f"{token!r} leaked into commands map"
    assert "mindforge web" in out
    assert "mindforge watch add" in out
    assert "mindforge approve list" in out


def test_cli_direct_help_does_not_expose_retired_mode_surfaces() -> None:
    """隐藏入口的 help 也不能成为第二套产品说明书。

    中文学习型说明：Typer 的 ``hidden=True`` 只会从 root help 移除命令，
    但用户仍可能直达 ``command --help``。第一阶段产品语义必须统一到
    real model setup / local secret store / source import-watch / background
    processing / review-approve，不能通过隐藏 help 继续教授旧模式。
    """

    checks = [
        ["demo", "--help"],
        ["cubox", "--help"],
        ["dogfood", "--help"],
        ["provider", "--help"],
        ["llm", "--help"],
        ["process", "--help"],
        ["watch", "add", "--help"],
        ["import", "--help"],
    ]

    for args in checks:
        result = runner.invoke(app, args)
        out = result.output
        for token in (
            "fake-default",
            "fake provider",
            "dogfooding",
            "Cubox 本地",
            "Cubox JSON",
            "active_profile",
            "legacy profiles",
            "provider/profile",
            ".env",
            "env presence",
        ):
            assert token not in out, f"{token!r} leaked from {' '.join(args)}"


def test_cli_status_presenter_hides_legacy_provider_env_and_source_labels() -> None:
    """status 输出是普通用户入口，只展示模型设置和通用 source 类别。

    中文学习型说明：service 层为了兼容历史状态仍可能携带 profile/env/Cubox
    元数据；presenter 必须在用户主路径把它们翻译成第一阶段产品语义。
    """

    snapshot = LocalStatusSnapshot(
        config_path="/tmp/mindforge/configs/mindforge.yaml",
        vault={
            "path": "/tmp/mindforge/vault",
            "exists": True,
            "readable": True,
            "looks_like_mindforge": True,
            "is_real_environment": False,
        },
        workspace={
            "state_item_count": 1,
            "runs_path": "/tmp/mindforge/.mindforge/runs",
            "state_counts": {"ai_draft": 1},
            "source_counts": {"cubox_markdown": 1},
        },
        provider={
            "active_profile": "legacy",
            "opt_in_state": "profile_only",
            "network_called": False,
        },
        cubox={"token_present": True},
        env_keys=[{"name": "SECRET_TOKEN", "configured": True, "sources": ["process"]}],
        sources=[],
        cards={"total": 1, "by_status": {"ai_draft": 1}, "scan_error_count": 0},
        recall={"mode": "local lexical recall", "index_exists": False, "approved_card_count": 0},
        safety={
            "vault_path": "/tmp/mindforge/vault",
            "provider_state": "profile_only",
            "write_mode": "explicit_approval_required",
            "pending_drafts": 1,
        },
        next_actions=["mindforge approve list"],
        warnings=["Model setup may need review; status checks still do not call LLM."],
    )

    console = Console(record=True, width=120)
    render_local_status(console, snapshot)
    out = console.export_text()

    assert "model setup=needs setup" in out
    assert "imported_file" in out
    for token in ("active_profile", "profile_only", "Cubox", "cubox_markdown", ".env", "SECRET_TOKEN"):
        assert token not in out


def test_doctor_logic_hides_demo_env_and_profile_hints() -> None:
    """doctor 的建议必须指向真实 Setup，而不是历史 demo/profile 路径。"""

    cfg = _bundled_config()
    out = "\n".join(
        [" ".join(row) for row in config_doctor_rows(cfg)]
        + [f"{priority} {message}" for priority, message in compute_doctor_hints(cfg, [])]
    )

    assert "model setup" in out
    for token in ("mindforge demo", "demo vault", "active_profile", ".env", "dogfood", "fake"):
        assert token not in out


def test_readme_quickstart_documents_clean_clone_bootstrap() -> None:
    """README 必须说明 clean clone 后 `mindforge web` 会创建本地 runtime config。"""

    text = Path("README.md").read_text(encoding="utf-8")
    quickstart = text.split("## 快速开始", 1)[1].split("\n## ", 1)[0]

    assert "mindforge web" in quickstart
    assert "首次运行" in quickstart
    assert "configs/mindforge.yaml" in quickstart
    assert "configs/mindforge_example.yaml" in text
    assert "local secret store" in text
    assert "API key 不写 YAML" in text


def _source_doc() -> SourceDocument:
    raw = "A normal synthetic document about production/test path alignment."
    return SourceDocument(
        source_id="plain_markdown:alignment",
        source_type="plain_markdown",
        source_path="/tmp/alignment.md",
        title="Production Path Alignment",
        raw_text=raw,
        content_hash=compute_content_hash(raw),
        adapter_name="PlainMarkdownAdapter",
    )


def _bundled_config() -> MindForgeConfig:
    return load_mindforge_config(asset_root().joinpath("configs", "mindforge.yaml"))  # type: ignore[arg-type]


def _bundled_runtime() -> ProcessRuntime:
    prompts_root = asset_root().joinpath("prompts")
    tracks_text = asset_root().joinpath("configs", "learning_tracks.yaml").read_text(encoding="utf-8")  # type: ignore[union-attr]
    return ProcessRuntime(
        provider=ProviderSelection(active_profile="stub", requires_real_env=False),
        assets=ProcessAssets(
            prompts_dir=prompts_root,
            tracks_text=tracks_text,
            template_path=None,
            template_text=None,
        ),
        bypass_triage_gate=False,
    )


class _StubLLMClient:
    def resolve_model_for_stage(self, stage: str) -> ResolvedModel:
        return ResolvedModel(
            stage=stage,
            model_alias="stub_alias",
            provider="stub",
            actual_model="stub-model",
            type="stub",
        )

    def generate(self, *, stage: str, prompt: str, options=None) -> StageCallResult:  # type: ignore[no-untyped-def]
        payloads = {
            "triage": {
                "track": "agent-runtime",
                "value_score": 8,
                "should_process": True,
                "reason": "stubbed production-path triage",
                "topic_keywords": ["strategy", "testing"],
            },
            "distill": {
                "title": "Production Path Alignment",
                "slug": "production-path-alignment",
                "tags": ["strategy", "testing"],
                "confidence": 0.75,
                "source_excerpt": "Tests should stub LLM responses, not strategy runtime.",
                "ai_summary_bullets": ["Stub the model, keep the Knowledge Card Strategy."],
                "ai_inference_bullets": [],
                "reusable_prompts_or_principles": ["Fake model output, not strategy runtime."],
            },
            "link_suggestion": {"suggested_links": [], "project_hooks": []},
            "review_questions": {
                "review_questions": [
                    {
                        "angle": "architecture",
                        "question": "Why should tests stub LLM responses instead of strategy?",
                        "expected_points": ["same runtime path"],
                    }
                ]
            },
            "action_extraction": {"action_items": []},
        }
        import json

        return StageCallResult(
            resolved=self.resolve_model_for_stage(stage),
            result=LLMResult(
                text=json.dumps(payloads[stage], ensure_ascii=False),
                tokens_in=max(1, len(prompt) // 8),
                tokens_out=16,
                latency_ms=0,
                raw={"stub": True},
            ),
        )


class _NoOpLogger:
    run_id = "stubbed-production-path"

    def emit(self, event: str, **fields: object) -> None:
        return None


def _replace_strategy(cfg: MindForgeConfig, active: str) -> MindForgeConfig:
    return MindForgeConfig(
        version=cfg.version,
        vault=cfg.vault,
        sources=cfg.sources,
        state=cfg.state,
        triage=cfg.triage,
        llm=cfg.llm,
        prompts=cfg.prompts,
        logging=cfg.logging,
        review=cfg.review,
        telemetry=cfg.telemetry,
        obsidian=cfg.obsidian,
        search=cfg.search,
        strategy=StrategyConfig(active=active),
        raw=cfg.raw,
    )
