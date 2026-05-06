"""产品表面与测试替身隔离契约。

中文学习型说明：MindForge 的端到端测试应该替身化 LLM 返回，而不是把
``fake provider`` 或 deterministic strategy 包装成用户能力。本文件只锁定
用户可见语义：正式 extraction strategy 是 Knowledge Card Strategy；
``five_stage`` 是 legacy/internal pipeline alias；deterministic baselines 默认
隐藏，不能作为 production active_strategy。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from mindforge.assets_runtime import asset_root
from mindforge.cli import app
from mindforge.config import MindForgeConfig, StrategyConfig, load_mindforge_config
from mindforge.llm import LLMResult, ResolvedModel, StageCallResult
from mindforge.process_service import ProcessAssets, ProcessRuntime, ProviderSelection
from mindforge.processors.pipeline import _build_card_payload
from mindforge.process_executor import build_pipeline
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
    assert meta.display_name == "Knowledge Card Strategy"
    assert meta.production_ready is True
    assert meta.user_recommended is True


def test_strategies_list_hides_internal_baselines_by_default() -> None:
    result = runner.invoke(app, ["strategies", "list"])

    assert result.exit_code == 0, result.output
    out = result.output
    assert "knowledge_card" in out
    assert "Knowledge Card Strategy" in out
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


def test_strategies_show_legacy_alias_explains_canonical_strategy() -> None:
    result = runner.invoke(app, ["strategies", "show", "five_stage"])

    assert result.exit_code == 0, result.output
    assert "legacy alias" in result.output.lower()
    assert "knowledge_card" in result.output
    assert "Knowledge Card Strategy" in result.output


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
    stub，但仍应构造 Knowledge Card Strategy，并走 triage/distill/link/review/
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
    main, _, developer = text.partition("Developer Testing")

    assert "--provider fake" not in main
    assert "default_knowledge_card" not in main
    assert "concept_extraction" not in main
    assert "Knowledge Card Strategy" in main
    assert "FakeLLMClient" in developer or "StubLLM" in developer


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
