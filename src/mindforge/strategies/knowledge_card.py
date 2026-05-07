"""用户可见的 Knowledge Card Strategy。

中文学习型说明：``five_stage`` 是当前生产策略的内部实现管线名，不应该继续
作为产品名称泄漏给普通用户。这个模块提供 canonical strategy identity：
用户、config、card provenance 都优先看到 ``knowledge_card``；内部仍复用
既有五段 pipeline，避免重造一条平行执行路径。
"""

from __future__ import annotations

from .five_stage import build_five_stage_strategy


STRATEGY_ID = "knowledge_card"
STRATEGY_VERSION = "0.10.0"
STRATEGY_DISPLAY_NAME = "Knowledge Card Strategy"
STRATEGY_DESCRIPTION = (
    "生产默认知识卡片策略：内部执行 triage → distill → link_suggestion → "
    "review_questions → action_extraction 五段 prompt pipeline，生成 ai_draft "
    "Knowledge Card，必须经人工 approve 才成为正式知识。"
)
STRATEGY_PROVIDER_MODE = "real_opt_in"
STRATEGY_SAFETY_POLICY = "ai_draft_only"
STRATEGY_OUTPUT_SCHEMA_ID = f"{STRATEGY_ID}@1"
STRATEGY_STATUS = "implemented"
STRATEGY_ROLE = "production_default"
STRATEGY_PRODUCTION_READY = True
STRATEGY_USER_RECOMMENDED = True
STRATEGY_CANONICAL_ID = STRATEGY_ID
STRATEGY_LEGACY_ALIASES = ("five_stage",)
STRATEGY_WARNING = ""


__all__ = [
    "STRATEGY_CANONICAL_ID",
    "STRATEGY_DESCRIPTION",
    "STRATEGY_DISPLAY_NAME",
    "STRATEGY_ID",
    "STRATEGY_LEGACY_ALIASES",
    "STRATEGY_OUTPUT_SCHEMA_ID",
    "STRATEGY_PRODUCTION_READY",
    "STRATEGY_PROVIDER_MODE",
    "STRATEGY_ROLE",
    "STRATEGY_SAFETY_POLICY",
    "STRATEGY_STATUS",
    "STRATEGY_USER_RECOMMENDED",
    "STRATEGY_VERSION",
    "STRATEGY_WARNING",
    "build_five_stage_strategy",
]
