"""DefaultKnowledgeCardStrategy — v0.10 Slice 2 production + Slice 4 envelope.

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
- 输出**公共 envelope**（v0.10 Slice 4 引入），``status`` 恒为
  ``"ai_draft"``；
- 不调用任何 LLM（即使 ``StrategyContext.client`` 是 FakeProvider 也不
  调用），完全离线、确定性；
- 不写任何文件、不开任何 socket、不依赖 prompts / vault / approver；
- 不感知具体 SourceAdapter 的字段（只读 ``SourceDocument`` 的契约
  字段），保持 source-agnostic。

公共 envelope（v0.10 Slice 4）
==============================

为支持未来多 strategy（v0.11 StrategyRegistry）与可选 custom strategy
（v0.12），所有 strategy 的 ``card_payload`` 必须满足同一组顶层契约：

- ``strategy_id``：注册名；
- ``strategy_version``：实现版本；
- ``schema_version``：envelope 模式版本；
- ``status``：恒 ``"ai_draft"``；
- ``source_evidence``：provenance 指针 dict；
- ``structured_payload``：strategy-specific 字段集中于此 —— 外层
  writer / presenter / approval 不读 strategy-specific keys；
- ``review_hints``：presenter 安全 fallback 渲染用最小 headline。

为什么把 schema 放在策略模块里？
================================

Schema 与策略**同生共死**：换策略 = 换 ``structured_payload`` 形态。
把 strategy-specific schema 放在 CLI / processor / approval 任意一层
都意味着"这一层必须知道每个策略的形态"，违反 Information Hiding。本
策略对外只承诺 ``run(doc) -> PipelineOutcome``；envelope 顶层契约由公
共测试守护，``structured_payload`` 字段名 / 类型 / 默认值都封装在本模
块内部，调用方只能消费，不能定义。

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


STRATEGY_ID = "default_knowledge_card"
STRATEGY_VERSION = "0.10.0"
ENVELOPE_SCHEMA_VERSION = "1"


# ---------------------------------------------------------------------------
# 10 字段 structured_payload schema（与 docs/ROADMAP.md §Default contract 对齐）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KnowledgeCardPayload:
    """10 字段 structured_payload。frozen → 调用方无法事后篡改字段。

    字段语义见 docs/ROADMAP.md §v0.9.x Default contract。Slice 4 起这
    10 个字段被装入 envelope 的 ``structured_payload`` 子字典，而非
    envelope 顶层。
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


def _wrap_envelope(payload: KnowledgeCardPayload, doc: SourceDocument) -> dict[str, Any]:
    """把 strategy-specific payload 封装为 v0.10 公共 envelope。

    设计要点：

    - ``status`` 提到 envelope 顶层，与 strategy_id 一同构成"AI 生成、
      未审"的对外承诺；任何 strategy 都不能在此处填已审核状态。
    - ``source_evidence`` 是 dict（单一来源 provenance）；
      ``structured_payload`` 内部仍保留 list-of-dict 形式以兼容多 evidence
      的策略，但**外层** writer/presenter 只消费 envelope 顶层 dict 形态。
    - ``review_hints`` 提供 presenter 即便不认识 ``structured_payload``
      内部结构也能渲染的最小 headline；这是"未知 strategy 仍可安全
      preview"契约的根基。
    - **不**包含 vault path / approval byline / 已审核状态字段；这条边界
      由 ``test_payload_does_not_carry_approved_fields`` 守护。
    """

    return {
        "strategy_id": STRATEGY_ID,
        "strategy_version": STRATEGY_VERSION,
        "schema_version": ENVELOPE_SCHEMA_VERSION,
        "status": "ai_draft",
        "source_evidence": {
            "source_id": doc.source_id,
            "source_type": doc.source_type,
            "content_hash": doc.content_hash,
            "source_path": doc.source_path,
            "adapter_name": doc.adapter_name or "",
        },
        "structured_payload": payload.to_dict(),
        "review_hints": {
            "title": payload.title,
            "one_line": payload.one_sentence_summary,
        },
    }


# ---------------------------------------------------------------------------
# 策略类
# ---------------------------------------------------------------------------


class DefaultKnowledgeCardStrategy:
    """SourceDocument → ai_draft envelope 的离线确定性策略。

    与 ``Pipeline``（five_stage）不同：本策略不调用 LLM、不读 prompts、
    不依赖 learning tracks 文本。它是一条"最小可消费的 ai_draft 通路"，
    适合 review preview / smoke / 后续真实 LLM 策略的 envelope 对齐。

    满足 ``KnowledgeStrategy`` Protocol（结构性）：暴露可写 ``logger``
    字段 + ``run(doc) -> PipelineOutcome`` 方法。
    """

    def __init__(self, *, logger: Any = None) -> None:
        self.logger = logger

    def run(self, doc: SourceDocument) -> PipelineOutcome:
        payload = _build_payload(doc)
        envelope = _wrap_envelope(payload, doc)
        return PipelineOutcome(
            status="processed",
            card_payload=envelope,
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
    "ENVELOPE_SCHEMA_VERSION",
    "KnowledgeCardPayload",
    "STRATEGY_ID",
    "STRATEGY_VERSION",
    "build_default_knowledge_card_strategy",
]
