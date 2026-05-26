"""Recall / BM25 Search schemas.

中文学习型说明：这些 schema 涵盖 BM25 词法检索的请求/响应契约。
RecallResponse 引用 RecallStatus（provider 模块）表示索引状态，
这是跨 domain 的合法依赖 — recall 结果需要表达索引可用性。
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from mindforge_web.schemas.common import NextAction
from mindforge_web.schemas.provider import RecallStatus


class RecallHit(BaseModel):
    score: float
    title: str | None
    card_ref: str | None = None
    detail_href: str | None = None
    rel_path: str
    status: str
    track: str | None
    projects: list[str]
    tags: list[str]
    source_type: str | None
    why_this_matched: str
    # v0.6 R6: graph context enrichment（context=graph 时填充）
    graph_neighbor_count: int | None = None
    graph_shared_tag_count: int | None = None


class RecallResponse(BaseModel):
    query: str
    hits: list[RecallHit]
    index: RecallStatus
    warnings: list[str] = Field(default_factory=list)
    empty_state: NextAction | None = None
