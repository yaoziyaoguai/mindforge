"""默认策略：五段 pipeline 包装工厂。

本模块**不**实现新行为 —— 它只是把 ``processors.pipeline.Pipeline`` 的
构造器封装成一个工厂函数，让 :func:`registry.build_strategy` 能按名字
调用。

为什么必须复用现有 Pipeline？
=============================

``Pipeline`` 类在 v0.7.x 之前就经历了 ``test_process_e2e`` /
``test_process_service`` / pipeline-level 单测的反复验证。如果在 seam 这
一层重写五段调用，会引入"两条 ai_draft 生成路径"的脏味道并破坏 byte-
level 输出一致性。本工厂仅做 ``return Pipeline(...)``，是最薄的可复用
方式。
"""

from __future__ import annotations

from ..processors.pipeline import Pipeline
from .base import KnowledgeStrategy, StrategyContext


STRATEGY_ID = "five_stage"
STRATEGY_VERSION = "0.10.0"
STRATEGY_DISPLAY_NAME = "Five-Stage Pipeline"
STRATEGY_DESCRIPTION = (
    "默认 LLM 驱动策略：triage → distill → link_suggestion → review_questions"
    " → action_extraction 五段链路，输出 17 字段 Knowledge Card；"
    "通过 fake provider 默认离线可跑，真实 LLM 仅在显式 opt-in 时启用。"
)
# v0.11 Slice 2：UX 元数据。provider_mode=real_opt_in 表示该策略可调真实
# LLM，但默认走 fake provider；safety_policy 锁定 ai_draft，不会自动 approve；
# output_schema_id 与 envelope.strategy_id@schema_version 对齐。
STRATEGY_PROVIDER_MODE = "real_opt_in"
STRATEGY_SAFETY_POLICY = "ai_draft_only"
STRATEGY_OUTPUT_SCHEMA_ID = f"{STRATEGY_ID}@1"


def build_five_stage_strategy(ctx: StrategyContext) -> KnowledgeStrategy:
    """根据 :class:`StrategyContext` 构造默认五段策略。

    返回值是 ``Pipeline`` 实例本身 —— 它结构性满足
    :class:`KnowledgeStrategy` Protocol，无需 wrap。

    five_stage 真正调用 LLM，因此显式校验 ``ctx.client``：StrategyContext
    把 client 设为 Optional 是为了让无 LLM 策略也能干净构造，但 LLM 策略
    必须在工厂入口拒掉缺失，避免 None 沿调用栈渗透到 prompt 调用处再以
    AttributeError 形式爆炸。
    """

    if ctx.client is None:
        raise ValueError(
            "build_five_stage_strategy 需要 StrategyContext.client，但收到 None；"
            "请在 context 中传入 LLMClient（或选择不依赖 LLM 的策略）。"
        )

    pipeline = Pipeline(
        client=ctx.client,
        logger=ctx.logger,  # type: ignore[arg-type]
        prompts_dir=ctx.prompts_dir,
        prompt_versions=ctx.prompt_versions,
        triage_threshold=ctx.triage_threshold,
        learning_tracks_text=ctx.learning_tracks_text,
    )
    return pipeline


__all__ = [
    "STRATEGY_DESCRIPTION",
    "STRATEGY_DISPLAY_NAME",
    "STRATEGY_ID",
    "STRATEGY_OUTPUT_SCHEMA_ID",
    "STRATEGY_PROVIDER_MODE",
    "STRATEGY_SAFETY_POLICY",
    "STRATEGY_VERSION",
    "build_five_stage_strategy",
]
