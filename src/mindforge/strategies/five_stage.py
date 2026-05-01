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


def build_five_stage_strategy(ctx: StrategyContext) -> KnowledgeStrategy:
    """根据 :class:`StrategyContext` 构造默认五段策略。

    返回值是 ``Pipeline`` 实例本身 —— 它结构性满足
    :class:`KnowledgeStrategy` Protocol，无需 wrap。
    """

    pipeline = Pipeline(
        client=ctx.client,
        logger=ctx.logger,  # type: ignore[arg-type]
        prompts_dir=ctx.prompts_dir,
        prompt_versions=ctx.prompt_versions,
        triage_threshold=ctx.triage_threshold,
        learning_tracks_text=ctx.learning_tracks_text,
    )
    return pipeline
