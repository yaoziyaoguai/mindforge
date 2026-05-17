"""M1 Card Quality 数据模型 — SDD §3.1。

Quality metadata 为只读附属，不自动修改卡片 body/status（RFC §6 AD-2）。
所有模型使用 frozen dataclass，确保不可变性。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class QualityLevel(str, Enum):
    """质量等级 — SDD §5.2。"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CardType(str, Enum):
    """卡片知识类型 — SDD §5.4 规则分类。"""
    FACT = "fact"
    CLAIM = "claim"
    DECISION = "decision"
    METHOD = "method"
    RISK = "risk"
    QUESTION = "question"
    INSIGHT = "insight"


@dataclass(frozen=True)
class QualityRubricScore:
    """单个 rubric 维度的评分 — SDD §5.1。

    5 个维度：completeness, structure, specificity, source_citation, consistency。
    每个维度 score 为 0.0-1.0，max_score 默认为 1.0。
    """
    dimension: str
    score: float
    max_score: float = 1.0
    notes: str = ""


@dataclass(frozen=True)
class QualityWarning:
    """质量警告 — SDD §5.3。

    code: too_short / missing_sections / no_source_citation / vague_language / possible_duplicate
    severity: info / warn / critical
    """
    code: str
    severity: str
    message: str
    suggestion: str = ""


@dataclass(frozen=True)
class CardQuality:
    """卡片质量元数据（只读附属）— SDD §3.1。

    附属于 ai_draft / human_approved，不自动修改卡片 status/body。
    overall_score 为 0-100 的归一化总分。
    """
    overall_level: QualityLevel
    overall_score: float
    rubric_scores: tuple[QualityRubricScore, ...]
    warnings: tuple[QualityWarning, ...]
    card_type: CardType | None = None
    regenerate_suggestion: str | None = None
    split_candidate: bool = False
    merge_candidate: bool = False
    dedup_candidates: tuple[str, ...] = ()

    @property
    def level_label(self) -> str:
        """中文等级标签。"""
        return {"high": "高质量", "medium": "中质量", "low": "低质量"}.get(
            self.overall_level.value, self.overall_level.value
        )
