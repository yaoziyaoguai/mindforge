"""KnowledgeStrategy seam 行为测试。

验收点：
- ``Pipeline`` 结构性满足 ``KnowledgeStrategy`` Protocol；
- 默认策略名 ``"knowledge_card"`` 在 registry 中可解析；
- 未知策略名抛 ``UnknownStrategyError``，不静默回退；
- ``StrategyContext`` 字段映射到 ``Pipeline.__init__`` 完全一致；
- 默认策略产出的 ``PipelineOutcome`` 与直接使用 ``Pipeline`` 的产出相同。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mindforge.processors.pipeline import Pipeline, PipelineOutcome
from mindforge.strategies import (
    DEFAULT_STRATEGY_NAME,
    KnowledgeStrategy,
    StrategyContext,
    UnknownStrategyError,
    available_strategies,
    build_five_stage_strategy,
    build_strategy,
)


class _FakeClient:
    pass


class _FakeVersions:
    def for_stage(self, stage: str) -> str:
        return "v1"


def _make_ctx(*, logger=None) -> StrategyContext:
    return StrategyContext(
        client=_FakeClient(),  # type: ignore[arg-type]
        prompts_dir=Path("/tmp"),
        prompt_versions=_FakeVersions(),
        triage_threshold=10,
        learning_tracks_text="tracks: []\n",
        logger=logger,
    )


def test_default_strategy_name_is_knowledge_card() -> None:
    assert DEFAULT_STRATEGY_NAME == "knowledge_card"


def test_available_strategies_contains_default() -> None:
    assert DEFAULT_STRATEGY_NAME in available_strategies()


def test_build_strategy_returns_pipeline_for_default() -> None:
    ctx = _make_ctx()
    strat = build_strategy(DEFAULT_STRATEGY_NAME, ctx)
    assert isinstance(strat, Pipeline)


def test_build_five_stage_factory_produces_pipeline_directly() -> None:
    ctx = _make_ctx()
    strat = build_five_stage_strategy(ctx)
    assert isinstance(strat, Pipeline)


def test_pipeline_satisfies_knowledge_strategy_protocol() -> None:
    ctx = _make_ctx()
    strat = build_strategy(DEFAULT_STRATEGY_NAME, ctx)
    assert isinstance(strat, KnowledgeStrategy)


def test_unknown_strategy_raises_structured_error() -> None:
    ctx = _make_ctx()
    with pytest.raises(UnknownStrategyError) as excinfo:
        build_strategy("does_not_exist", ctx)
    assert "does_not_exist" in str(excinfo.value)
    assert DEFAULT_STRATEGY_NAME in str(excinfo.value)


def test_strategy_context_fields_map_to_pipeline_attributes() -> None:
    ctx = _make_ctx()
    strat = build_strategy(DEFAULT_STRATEGY_NAME, ctx)
    assert strat.client is ctx.client
    assert strat.prompts_dir == ctx.prompts_dir
    assert strat.prompt_versions is ctx.prompt_versions
    assert strat.triage_threshold == ctx.triage_threshold
    assert strat.learning_tracks_text == ctx.learning_tracks_text


def test_strategy_logger_is_mutable_after_construction() -> None:
    ctx = _make_ctx(logger=None)
    strat = build_strategy(DEFAULT_STRATEGY_NAME, ctx)
    assert strat.logger is None
    sentinel = object()
    strat.logger = sentinel  # type: ignore[assignment]
    assert strat.logger is sentinel


def test_available_strategies_returns_sorted_tuple() -> None:
    names = available_strategies()
    assert isinstance(names, tuple)
    assert list(names) == sorted(names)


def test_pipeline_outcome_type_imported_from_strategy_run_signature() -> None:
    ctx = _make_ctx()
    strat = build_strategy(DEFAULT_STRATEGY_NAME, ctx)
    assert callable(strat.run)
    annotations = getattr(strat.run, "__annotations__", {})
    assert annotations.get("return") in (PipelineOutcome, "PipelineOutcome")


# ---------------------------------------------------------------------------
# v0.10 fake-first seam 回归保护
#
# 这些测试把"StrategyContext 不强制依赖真实 LLMClient"这条架构契约固化为
# 可执行检查。一旦未来有人给 ``client`` 移除默认值，或在工厂里偷偷读取
# os.environ 启动真实 provider，这里就会红灯。
# ---------------------------------------------------------------------------


def test_strategy_context_can_be_built_with_no_arguments() -> None:
    """StrategyContext 必须能零参构造。

    无 LLM 策略（``DefaultKnowledgeCardStrategy``）和测试 fixture 都依赖
    这一点；任何使其变成必填的改动都会破坏 fake-first seam。
    """
    ctx = StrategyContext()
    assert ctx.client is None
    assert ctx.logger is None


def test_strategy_context_client_is_optional_in_annotations() -> None:
    """``StrategyContext.client`` 的注解必须包含 None。

    防止后续重构把 ``Optional`` 静默去掉。注解是字符串（PEP 563），
    简单子串匹配即可。
    """
    annotation = StrategyContext.__dataclass_fields__["client"].type
    assert "None" in str(annotation), (
        f"StrategyContext.client 注解必须为 Optional，实际：{annotation!r}"
    )


def test_five_stage_factory_rejects_missing_client_loudly() -> None:
    """LLM 策略缺 client 时必须立即失败，不能静默走到 None.attribute 才崩。"""
    ctx = StrategyContext()  # client=None
    with pytest.raises(ValueError, match="client"):
        build_five_stage_strategy(ctx)
