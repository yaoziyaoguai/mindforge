"""ConceptExtractionStrategy — v0.11 Slice 3 deterministic skeleton.

为什么有这个模块
================

v0.11 StrategyRegistry 的目标之一是让用户 **看到多个策略**，而不是只
看到 ``default_knowledge_card`` 与 ``five_stage``。但是在 v0.12 真正
引入 declarative custom strategy 之前，registry 必须先有第三个**官方
内建**策略作为 multi-strategy discovery UX 的最小演示载体。

``ConceptExtractionStrategy`` 就是这个第三个策略：

- **离线确定性**：``provider_mode = "deterministic"``。不依赖 LLM、不
  读 ``.env``、不联网、不写 vault；只对 ``SourceDocument.raw_text``
  做纯 Python 词频/标题切分，永远在任何环境下可跑。
- **预览级骨架**：``status = "preview"``。其输出已经满足公共 envelope
  契约（``strategy_id`` / ``schema_version`` / ``status="ai_draft"`` /
  ``source_evidence`` / ``structured_payload`` / ``review_hints``），
  足以被 writer / presenter 安全消费；但 ``structured_payload`` 内部
  的 ``concepts`` 列表本身只是基于词频的占位实现，不打算与未来真正
  的语义概念抽取对齐 —— 因此明示 preview，提醒用户 "可见可跑，但
  语义还会继续演化"。

  ``preview`` 与 ``planned`` 的区别（v0.11 Slice 4 将正式守护这条边界）：

  - ``planned`` = 注册元数据但**不可执行**，调用应在 registry 边界
    被礼貌拒绝；
  - ``preview`` = 可执行，但语义/字段集合仍在演化。本策略选 preview。

- **不承担**：
    - 不调用 LLM；不引用 ``LLMClient``；不调用 provider；
    - 不读 ``.env``；不联网；不写文件；
    - 不感知 source 来源（不依赖具体 SourceAdapter 字段，只读
      ``SourceDocument`` 公共契约）；
    - 不产生已审核状态字面量 —— 已审核状态只能由 ``approver`` 在
      显式人审动作中生成，本策略输出 ``status="ai_draft"`` 不可逆。

设计原则
========

本模块**不**做 anything fancy。它的存在意义是让 multi-strategy 发现
UX 在没有真实 LLM 的前提下也能展示给用户。具体的概念抽取算法（NLP
/ embedding / LLM 引导）属于未来策略，本模块只承诺：

- 输入：``SourceDocument``；
- 输出：满足公共 envelope 的 ``PipelineOutcome``；
- 不调 LLM、不读 .env、不联网、不写 vault。

中文学习型注释
==============

把 "deterministic skeleton" 翻成大白话：本模块就是一个"先把架子立起来
让用户看见有多个策略可选"的最小可跑实现，避免 v0.11 Slice 3 的多策略
UX 变成"两个 Slice 1+2 老策略的样品架"。
"""

from __future__ import annotations

import re
from typing import Any

from ..processors.pipeline import PipelineOutcome
from ..sources.base import SourceDocument
from .base import StrategyContext


STRATEGY_ID = "concept_extraction"
STRATEGY_VERSION = "0.11.0"
ENVELOPE_SCHEMA_VERSION = "1"
STRATEGY_DISPLAY_NAME = "Concept Extraction (Preview Skeleton)"
STRATEGY_DESCRIPTION = (
    "离线确定性骨架策略：基于词频从 source 文本提取候选概念词，"
    "全程不依赖 LLM / .env / 网络；作为 v0.11 multi-strategy discovery "
    "UX 的最小演示载体，语义仍在演化中。"
)
STRATEGY_PROVIDER_MODE = "deterministic"
STRATEGY_SAFETY_POLICY = "ai_draft_only"
STRATEGY_OUTPUT_SCHEMA_ID = f"{STRATEGY_ID}@{ENVELOPE_SCHEMA_VERSION}"
# v0.11 Slice 3：preview = 可执行但语义/字段还在演化；与 implemented
# 严格区分，让 CLI strategies list 能向用户表达"这个策略已经能跑，但
# 别按生产质量要求"。
STRATEGY_STATUS = "preview"


# ---------------------------------------------------------------------------
# 内部确定性概念抽取（纯 Python，无外部依赖）
# ---------------------------------------------------------------------------


# 极简英文 + 中文常见停用词集合。**故意保持小**：本模块是 skeleton，
# 不打算与未来真正的概念抽取对齐；扩大停用词表反而会让人误以为这就是
# 生产实现。
_STOPWORDS: frozenset[str] = frozenset(
    {
        "the", "and", "for", "with", "that", "this", "from", "are", "was",
        "were", "but", "not", "you", "your", "have", "has", "had", "into",
        "out", "its", "their", "our", "his", "her", "they", "them", "than",
        "then", "when", "what", "which", "who", "whom", "how", "why",
        "of", "to", "in", "on", "at", "by", "as", "is", "be", "an", "a",
        "or", "if", "it", "we", "i",
        # 中文常见非概念词（极简）
        "的", "了", "和", "是", "在", "也", "就", "都", "而", "及", "与",
        "或", "等", "把", "被", "让", "对", "于", "从", "到", "以",
    }
)

_TOKEN_RE = re.compile(r"[A-Za-z\u4e00-\u9fff][A-Za-z0-9\u4e00-\u9fff_\-]{2,}")


def _extract_concepts(text: str, *, top_n: int = 8) -> list[str]:
    """按词频抽取 top-N 候选概念词。

    纯确定性：同一文本输入永远得到同一输出。**不**做语义合并、词形还原、
    停用词大表 —— 这些都是未来语义版策略的事，本骨架不冒充。
    """

    if not text:
        return []
    counts: dict[str, int] = {}
    for raw in _TOKEN_RE.findall(text):
        token = raw.lower()
        if token in _STOPWORDS:
            continue
        if token.isdigit():
            continue
        counts[token] = counts.get(token, 0) + 1
    # 先按频次降序、再按字典序升序 —— 让输出在频次相同时仍是稳定顺序。
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [token for token, _ in ordered[:top_n]]


def _derive_title(doc: SourceDocument) -> str:
    """从 SourceDocument 派生标题。

    优先用显式 ``title``；缺省用 ``raw_text`` 第一非空行的前 80 字符。
    与 ``default_knowledge_card`` 的派生逻辑保持一致风格，但**故意**
    不共用辅助函数 —— 两个策略各自演化，避免引入"共享 helper"耦合。
    """

    if getattr(doc, "title", None):
        return str(doc.title).strip()[:80] or "(untitled)"
    for line in (doc.raw_text or "").splitlines():
        line = line.strip()
        if line:
            return line[:80]
    return "(untitled)"


def _wrap_envelope(
    concepts: list[str], title: str, doc: SourceDocument
) -> dict[str, Any]:
    """把骨架抽取结果封装为 v0.10 公共 envelope。

    顶层契约严格对齐 ``default_knowledge_card._wrap_envelope``：
    ``status`` 永远 ``"ai_draft"``，``source_evidence`` 是 dict，
    ``review_hints`` 提供 presenter 安全 fallback；strategy-specific
    字段全部下沉到 ``structured_payload``，让 writer / presenter 不必
    认识 concept_extraction 内部 schema 即可消费。
    """

    one_line = (
        f"概念候选（确定性骨架，共 {len(concepts)} 个）：" + ", ".join(concepts)
        if concepts
        else "未提取到概念候选（输入文本过短或全部命中停用词）。"
    )
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
        "structured_payload": {
            "title": title,
            "concepts": concepts,
            "extraction_method": "frequency_skeleton_v1",
            "limitations": (
                "本字段由 ConceptExtractionStrategy 离线词频抽取生成，"
                "未做语义合并/词形还原/停用词扩展；仅作 ai_draft 供人审。"
            ),
        },
        "review_hints": {
            "title": title,
            "one_line": one_line,
        },
    }


# ---------------------------------------------------------------------------
# 策略类
# ---------------------------------------------------------------------------


class ConceptExtractionStrategy:
    """SourceDocument → ai_draft envelope 的离线确定性概念抽取策略。

    与 ``Pipeline``（five_stage）和 ``DefaultKnowledgeCardStrategy`` 一样，
    满足 ``KnowledgeStrategy`` Protocol（结构性）：暴露可写 ``logger``
    字段 + ``run(doc) -> PipelineOutcome`` 方法。

    纯函数式：状态仅有 ``logger``（用于 RunLogger 注入）；多次 ``run``
    输出对同一文档恒等。
    """

    def __init__(self, *, logger: Any = None) -> None:
        self.logger = logger

    def run(self, doc: SourceDocument) -> PipelineOutcome:
        concepts = _extract_concepts(doc.raw_text or "")
        title = _derive_title(doc)
        envelope = _wrap_envelope(concepts, title, doc)
        return PipelineOutcome(
            status="processed",
            card_payload=envelope,
        )


# ---------------------------------------------------------------------------
# 工厂
# ---------------------------------------------------------------------------


def build_concept_extraction_strategy(ctx: StrategyContext) -> ConceptExtractionStrategy:
    """构造 ``ConceptExtractionStrategy`` 实例。

    与 ``DefaultKnowledgeCardStrategy`` 的工厂同构：``ctx.client`` /
    ``ctx.prompts_dir`` / ``ctx.prompt_versions`` /
    ``ctx.learning_tracks_text`` / ``ctx.triage_threshold`` 全部不被
    本策略消费。保持签名同构是为了让 registry 工厂表无需为每个策略
    分支特化签名。
    """

    return ConceptExtractionStrategy(logger=ctx.logger)


__all__ = [
    "ConceptExtractionStrategy",
    "ENVELOPE_SCHEMA_VERSION",
    "STRATEGY_DESCRIPTION",
    "STRATEGY_DISPLAY_NAME",
    "STRATEGY_ID",
    "STRATEGY_OUTPUT_SCHEMA_ID",
    "STRATEGY_PROVIDER_MODE",
    "STRATEGY_SAFETY_POLICY",
    "STRATEGY_STATUS",
    "STRATEGY_VERSION",
    "build_concept_extraction_strategy",
]
