"""Health and Quality schemas.

中文学习型说明：这些 schema 涵盖知识健康诊断（孤立卡片、低质量、
过期 Wiki 等结构性问题的检测报告）和卡片质量评估（rubric 评分、
质量等级、警告）的核心契约。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthIssueResponse(BaseModel):
    code: str
    severity: str
    message: str
    suggested_action: str
    reason: str = ""
    affected_card_ids: list[str] = Field(default_factory=list)


class HealthReportResponse(BaseModel):
    summary: str
    stats: dict[str, int] = Field(default_factory=dict)
    issues: list[HealthIssueResponse] = Field(default_factory=list)
    maintenance_suggestions: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    ok: bool
    app: str = "MindForge Local Console"
    local_only: bool = True
    report: HealthReportResponse | None = None


class QualityRubricScoreResponse(BaseModel):
    dimension: str
    score: float
    max_score: float = 1.0
    notes: str = ""


class QualityWarningResponse(BaseModel):
    code: str
    severity: str
    message: str
    suggestion: str = ""


class CardQualityResponse(BaseModel):
    card_id: str
    overall_level: str  # "high" | "medium" | "low"
    overall_level_label: str  # "高质量" | "中质量" | "低质量"
    overall_score: float
    rubric_scores: list[QualityRubricScoreResponse]
    warnings: list[QualityWarningResponse]
    card_type: str | None = None
    regenerate_suggestion: str | None = None
    split_candidate: bool = False
    merge_candidate: bool = False
