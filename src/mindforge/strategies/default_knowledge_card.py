"""DefaultKnowledgeCardStrategy — v0.10 Slice 2 最小生产实现。

为什么有这个模块
================

``five_stage`` 是当前默认策略，它把素材送入 5-stage LLM pipeline，
产出 ``card_payload``（既有 schema）。但这条路径要求 prompts 目录、
prompt 版本表、learning tracks 文本，且行为深度依赖 LLM provider 的
具体输出。它适合"完整流水线"场景，不适合"我只想从一份 SourceDocument
得到一张 in-memory ai_draft 卡片"的场景（review preview / dry-run /
非五段策略实验）。

``DefaultKnowledgeCardStrategy`` 解决后者：

- 输入只有 ``SourceDocument`` 一种；
- 输出固定 10 字段的 ``card_payload``，``status`` 恒为 ``"ai_draft"``；
- 不调用任何 LLM（即使 ``StrategyContext.client`` 是 FakeProvider 也不
  调用），完全离线、确定性；
- 不写任何文件、不开任何 socket、不依赖 prompts / vault / approver；
- 不感知具体 SourceAdapter 的字段（只读 ``SourceDocument`` 的契约
  字段），保持 source-agnostic。

为什么把 schema 放在策略模块里？
================================

Schema 与策略**同生共死**：换策略 = 换 payload 形态。把 schema 放在
CLI / processor / approval 任意一层都意味着"这一层必须知道每个策略
的形态"，违反 Information Hiding。本策略对外只承诺 ``run(doc)``
返回 ``PipelineOutcome``；payload 的字段名 / 类型 / 默认值都封装在
本模块内部，调用方只能消费，不能定义。

为什么 strategy 永远不产出已审核状态？
======================================

AI 只能生成 ``ai_draft``。已审核状态是显式人审动作的产物，由
``approver.py`` / ``approval_service.py`` 在用户明确 approve 时才能产生。
如果 strategy 自己写已审核状态，整个 review 闸门会被绕过 —— 这条边界由
``test_payload_does_not_carry_approved_fields`` 和
``test_status_is_ai_draft`` 守护，禁止回退。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..processors.pipeline import PipelineOutcome
from ..sources.base import SourceDocument
from .base import StrategyContext


# ---------------------------------------------------------------------------
# 10 字段 payload schema（与 docs/ROADMAP.md §Default contract 对齐）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KnowledgeCardPayload:
    """10 字段卡片 payload。frozen → 调用方无法事后篡改字段。

    字段语义见 docs/ROADMAP.md §v0.9.x Default contract。
    """

    title: str
    one_sentence_summary: str
    key_takeaways: list[str] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)
    questions_for_review: list[str] = field(default_factory=list)
    source_evidence: list[dict[str, Any]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    confidence: str = "low"
    limitations: str = ""
    status: str = "ai_draft"

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "one_sentence_summary": self.one_sentence_summary,
            "key_takeaways": list(self.key_takeaways),
            "concepts": list(self.concepts),
            "questions_for_review": list(self.questions_for_review),
            "source_evidence": list(self.source_evidence),
            "tags": list(self.tags),
            "confidence": self.confidence,
            "limitations": self.limitations,
            "status": self.status,
        }


# ---------------------------------------------------------------------------
# 内部辅助：从 SourceDocument 派生确定性内容
# ---------------------------------------------------------------------------


_SENTENCE_SPLIT = re.compile(r"(?<=[。\.!?！？])\s+")


def _first_sentence(text: str) -> str:
    """提取首句作为 one_sentence_summary 的兜底。

    完全确定性：无随机、无 LLM。如果 raw_text 为空则返回空串。
    """

    text = (text or "").strip()
    if not text:
        return ""
    parts = _SENTENCE_SPLIT.split(text, maxsplit=1)
    return parts[0].strip()


def _build_payload(doc: SourceDocument) -> KnowledgeCardPayload:
    """SourceDocument → KnowledgeCardPayload 的纯函数映射。"""

    title = (doc.title or "").strip() or "Untitled"
    summary = _first_sentence(doc.raw_text)
    # source_evidence 只携带 provenance 指针，不复制原文本（避免 payload 体量膨胀）
    evidence: list[dict[str, Any]] = [
        {
            "source_id": doc.source_id,
            "source_type": doc.source_type,
            "source_path": doc.source_path,
            "content_hash": doc.content_hash,
            "adapter_name": doc.adapter_name or "",
        }
    ]
    return KnowledgeCardPayload(
        title=title,
        one_sentence_summary=summary,
        key_takeaways=[],
        concepts=[],
        questions_for_review=[],
        source_evidence=evidence,
        tags=list(doc.tags or []),
        confidence="low",
        limitations="本卡片由 DefaultKnowledgeCardStrategy 离线生成，未经 LLM 审阅；"
        "仅作为 ai_draft 提交人审，不可自动晋升为已审核状态。",
        status="ai_draft",
    )


# ---------------------------------------------------------------------------
# 策略类
# ---------------------------------------------------------------------------


class DefaultKnowledgeCardStrategy:
    """SourceDocument → ai_draft KnowledgeCardPayload 的离线确定性策略。

    与 ``Pipeline``（five_stage）不同：本策略不调用 LLM、不读 prompts、
    不依赖 learning tracks 文本。它是一条"最小可消费的 ai_draft 通路"，
    适合 review preview / smoke / 后续真实 LLM 策略的 schema 对齐。

    满足 ``KnowledgeStrategy`` Protocol（结构性）：暴露可写 ``logger``
    字段 + ``run(doc) -> PipelineOutcome`` 方法。
    """

    def __init__(self, *, logger: Any = None) -> None:
        self.logger = logger

    def run(self, doc: SourceDocument) -> PipelineOutcome:
        payload = _build_payload(doc)
        return PipelineOutcome(
            status="processed",
            card_payload=payload.to_dict(),
        )


# ---------------------------------------------------------------------------
# 工厂
# ---------------------------------------------------------------------------


def build_default_knowledge_card_strategy(ctx: StrategyContext) -> DefaultKnowledgeCardStrategy:
    """构造 DefaultKnowledgeCardStrategy 实例。

    ``ctx.client`` / ``ctx.prompts_dir`` / ``ctx.prompt_versions`` /
    ``ctx.learning_tracks_text`` / ``ctx.triage_threshold`` 都不被本
    策略消费 —— 故意保留 context 形态一致以便 registry 工厂签名统一，
    且为未来的 LLM 增强策略变体留出兼容入口。
    """

    return DefaultKnowledgeCardStrategy(logger=ctx.logger)


__all__ = [
    "DefaultKnowledgeCardStrategy",
    "KnowledgeCardPayload",
    "build_default_knowledge_card_strategy",
]
