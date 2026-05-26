"""Dogfood Report & Source-to-Card Lifecycle API schemas.

中文学习型说明：Dogfood 是 internal 工具（开发者/维护者使用），Lifecycle 是主路径
能力。两者都完全自包含（不引用其他 schema 模块），因此可安全提取到独立文件。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ============================================================================
# v2.5 Dogfood Report schemas
# ============================================================================


class DogfoodTrendPoint(BaseModel):
    """单个时间点的统计快照。"""
    date: str  # ISO date
    total_cards: int
    approved_cards: int
    draft_cards: int


class DogfoodReportResponse(BaseModel):
    """v2.5 U3 工作台使用报告 — 结构化分析数据，不调用 LLM。"""

    generated_at: str  # ISO datetime

    # 当前状态
    total_cards: int
    approved_count: int
    draft_count: int
    approval_rate: float  # 0.0-1.0
    source_count: int

    # Graph 密度
    graph_total_relations: int
    graph_density: float  # relations per card
    community_count: int

    # Wiki 状态
    wiki_section_count: int
    wiki_stale: bool

    # 搜索
    search_index_exists: bool
    search_index_path: str = ""

    # 导入/导出
    imported_card_count: int
    exported_count: int  # 导出操作次数（当前版本近似以卡片数估算）
    import_error_count: int

    # 健康
    health_issue_count: int

    # 趋势（最近 N 天，当前版本基于现有数据近似）
    trend_summary: str
    maintenance_suggestions: list[str] = Field(default_factory=list)


# ============================================================================
# v2.5 U2 Source-to-Card Lifecycle
# ============================================================================


class SourceLifecycleItem(BaseModel):
    """单个 source 的卡片生命周期统计。"""
    source_id: str
    source_title: str
    total_cards: int
    ai_draft_count: int
    human_approved_count: int
    imported_count: int
    error_count: int


class LifecycleResponse(BaseModel):
    """Source-to-Card 生命周期总览 — v2.5 U2。

    中文学习型说明：展示每个 source 产出的卡片在各状态下的数量，
    帮助用户理解知识流转（Source → ai_draft → human_approved）。
    """
    sources: list[SourceLifecycleItem] = Field(default_factory=list)
    total_sources: int
    total_cards: int
    total_approved: int
    total_drafts: int
