"""M6 Local Graph golden fixtures — TDD §7.2。

5 cards 构成一个 center_card + 3 neighbors + 1 unrelated 的 graph。
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SyntheticGraphCard:
    """用于 graph 测试的合成卡片"""
    id: str
    source_id: str | None = None
    tags: tuple[str, ...] = ()
    wiki_sections: tuple[str, ...] = ()


@dataclass
class GraphGoldenFixture:
    cards: list[SyntheticGraphCard] = field(default_factory=list)
    center_id: str = "center_card"
    expected_nodes: set[str] = field(default_factory=set)
    expected_edge_count_min: int = 0


def build_graph_golden() -> GraphGoldenFixture:
    cards = [
        SyntheticGraphCard(
            id="center_card", source_id="src_1",
            tags=("auth", "security"),
            wiki_sections=("Authentication",),
        ),
        SyntheticGraphCard(
            id="neighbor_1", source_id="src_1",
            tags=("auth",),
            wiki_sections=("Authentication",),
        ),
        SyntheticGraphCard(
            id="neighbor_2", source_id="src_1",
            tags=("security",),
            wiki_sections=(),
        ),
        SyntheticGraphCard(
            id="neighbor_3", source_id="src_2",
            tags=("auth",),
            wiki_sections=("Authentication",),
        ),
        SyntheticGraphCard(
            id="unrelated", source_id="src_3",
            tags=("database",),
            wiki_sections=("Database",),
        ),
    ]

    return GraphGoldenFixture(
        cards=cards,
        center_id="center_card",
        expected_nodes={
            "center_card", "neighbor_1", "neighbor_2", "neighbor_3",
            "src_1", "auth", "security", "Authentication",
        },
        expected_edge_count_min=3,
    )
