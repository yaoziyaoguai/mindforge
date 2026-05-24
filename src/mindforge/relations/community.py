"""v1.2 Knowledge Community — 确定性知识社区检测。

中文学习型说明：借鉴 GraphRAG 的社区概念，但完全不使用 LLM 或社区检测算法。
"知识社区"的定义是纯确定性的：共享 source document / tag / wiki section 的卡片群。

每个社区附带纯文本描述（非 LLM 生成），让用户理解"这个知识群是什么"。
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict


@dataclass(frozen=True)
class KnowledgeCommunity:
    """确定性知识社区。

    属性：
        community_type: 社区类型（source / tag / wiki_section）
        shared_entity: 共享实体名称（source path / tag name / section title）
        member_count: 成员卡片数量
        member_card_ids: 成员卡片 ID 列表
        description: 确定性文本描述（非 LLM 生成）
    """
    community_type: str  # "source", "tag", "wiki_section"
    shared_entity: str
    member_count: int
    member_card_ids: tuple[str, ...]
    description: str


def detect_communities(
    cards: list[dict[str, object]],
    *,
    min_members: int = 2,
) -> list[KnowledgeCommunity]:
    """从卡片列表中检测知识社区。

    Args:
        cards: 卡片记录列表
        min_members: 最少成员数阈值（社区至少需要 N 张卡片）

    Returns:
        KnowledgeCommunity 列表，按 member_count 降序排列。
    """
    communities: list[KnowledgeCommunity] = []

    # Source communities
    source_groups: dict[str, list[str]] = defaultdict(list)
    for c in cards:
        sid = c.get("source_id")
        if sid:
            source_groups[str(sid)].append(str(c["id"]))

    for src, member_ids in source_groups.items():
        if len(member_ids) >= min_members:
            communities.append(KnowledgeCommunity(
                community_type="source",
                shared_entity=src,
                member_count=len(member_ids),
                member_card_ids=tuple(member_ids),
                description=_source_description(src, len(member_ids)),
            ))

    # Tag communities
    tag_groups: dict[str, list[str]] = defaultdict(list)
    for c in cards:
        for tag in (c.get("tags") or []):
            tag_groups[str(tag)].append(str(c["id"]))

    for tag, member_ids in tag_groups.items():
        if len(member_ids) >= min_members:
            communities.append(KnowledgeCommunity(
                community_type="tag",
                shared_entity=f"#{tag}",
                member_count=len(member_ids),
                member_card_ids=tuple(member_ids),
                description=_tag_description(tag, len(member_ids)),
            ))

    # Wiki section communities
    section_groups: dict[str, list[str]] = defaultdict(list)
    for c in cards:
        for sec in (c.get("wiki_sections") or []):
            section_groups[str(sec)].append(str(c["id"]))

    for sec, member_ids in section_groups.items():
        if len(member_ids) >= min_members:
            communities.append(KnowledgeCommunity(
                community_type="wiki_section",
                shared_entity=sec,
                member_count=len(member_ids),
                member_card_ids=tuple(member_ids),
                description=_section_description(sec, len(member_ids)),
            ))

    communities.sort(key=lambda c: c.member_count, reverse=True)
    return communities


def _source_description(source_path: str, count: int) -> str:
    return f"来自来源文档「{source_path}」的 {count} 张知识卡片"


def _tag_description(tag: str, count: int) -> str:
    return f"共享标签 #{tag} 的 {count} 张知识卡片"


def _section_description(section: str, count: int) -> str:
    return f"属于 Wiki 章节「{section}」的 {count} 张知识卡片"


__all__ = ["KnowledgeCommunity", "detect_communities"]
