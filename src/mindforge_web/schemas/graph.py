"""Graph API schemas — lab/internal.

中文学习型说明：这些 schema 是 /graph 和 /discovery API 的响应契约。
包含 v3.7 ontology 的 8 种 NodeType 和 14 种 EdgeType。
注意：Graph/Sensemaking 是 lab/internal 功能，不是主路径产品。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RelationEvidenceResponse(BaseModel):
    """图中边的可解释证据。"""
    reason: str
    evidence: str
    strength: float
    detail: dict = Field(default_factory=dict)


class GraphNodeResponse(BaseModel):
    """v3.7 ontology: 8 种 NodeType。"""
    id: str
    type: Literal["card", "source", "wiki_section", "tag", "community", "topic", "entity", "concept_candidate"]
    label: str
    href: str | None = None
    card_count: int = 0


class GraphEdgeResponse(BaseModel):
    """v3.7 ontology: 14 种 EdgeType，每条边携带 RelationEvidence。"""
    source_id: str
    target_id: str
    edge_type: Literal[
        "derived_from", "has_tag", "in_section",
        "shares_tag", "related_by_source", "related_by_wiki_section",
        "similar_title_or_term", "links_to",
        "contains", "includes", "belongs_to_topic",
        "wiki_section_reference",
        "mentions_candidate", "resolves_to",
    ]
    evidence: RelationEvidenceResponse


class GraphResponse(BaseModel):
    center_id: str
    center_type: Literal["card", "source", "wiki_section", "tag", "community", "topic", "entity", "concept_candidate"]
    depth: int
    nodes: list[GraphNodeResponse] = Field(default_factory=list)
    edges: list[GraphEdgeResponse] = Field(default_factory=list)


class GraphEdgeDetailResponse(BaseModel):
    source_id: str
    target_id: str
    edges: list[GraphEdgeResponse] = Field(default_factory=list)
