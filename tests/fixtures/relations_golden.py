"""M3 Related Cards golden fixtures — TDD §5.2。

5 cards 覆盖 6 种关系类型。
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SyntheticRelationCard:
    """用于关系测试的合成卡片"""
    id: str
    source_id: str | None = None
    tags: tuple[str, ...] = ()
    wiki_sections: tuple[str, ...] = ()
    status: str = "human_approved"
    review_batch: str | None = None
    source_location_index: int | None = None


@dataclass
class RelationsFixture:
    cards: list[SyntheticRelationCard] = field(default_factory=list)
    query_card_id: str = "c1"
    expected_related_ids: list[str] = field(default_factory=list)
    expected_no_relation_ids: list[str] = field(default_factory=list)


def build_relations_fixture() -> RelationsFixture:
    cards = [
        SyntheticRelationCard(
            id="c1", source_id="src_1",
            tags=("auth", "security"),
            wiki_sections=("Authentication",),
        ),
        SyntheticRelationCard(
            id="c2", source_id="src_1",
            tags=("auth",),
            wiki_sections=("Authentication",),
        ),
        SyntheticRelationCard(
            id="c3", source_id="src_2",
            tags=("database",),
            wiki_sections=("Database",),
        ),
        SyntheticRelationCard(
            id="c4", source_id="src_2",
            tags=("database", "migration"),
            wiki_sections=("Database",),
        ),
        SyntheticRelationCard(
            id="c5", source_id="src_3",
            tags=("api",),
            wiki_sections=("API Layer",),
        ),
    ]

    return RelationsFixture(
        cards=cards,
        query_card_id="c1",
        expected_related_ids=["c2"],  # same_source + same_tag + same_wiki_section
        expected_no_relation_ids=["c5"],  # 无共享 source/tag/section
    )
