"""v4.1 Graph Backend contract tests — 验证 GraphRepository 的 Repository Pattern 契约。

中文学习型说明：所有测试使用合成数据，不调用真实 LLM / embedding。
验证 GraphRepository 可通过不同 GraphPort 实现正确工作（可替换性契约）。
"""

from __future__ import annotations

from mindforge.relations.graph_builder import DeterministicGraphBuilder
from mindforge.relations.graph_models import EdgeType, GraphNode, NodeType
from mindforge.relations.graph_repository import GraphRepository


def _make_cards(*specs: tuple[str, str, str | None, list[str], list[str]]):
    """构建合成卡片数据（匹配 relation engine 的窄输入结构）。"""
    return [
        {
            "id": cid,
            "title": title,
            "status": "human_approved",
            "source_id": src,
            "tags": tags,
            "wiki_sections": sections,
            "run_id": None,
            "source_location_index": None,
        }
        for cid, title, src, tags, sections in specs
    ]


class TestGraphRepositoryContract:
    """GraphRepository 基本契约测试。"""

    def test_find_node_returns_correct_node(self):
        """find_node 返回正确的节点。"""
        cards = _make_cards(
            ("c1", "Test Card", "src/doc.md", ["ai"], ["Intro"]),
        )
        backend = DeterministicGraphBuilder(cards)
        repo = GraphRepository(backend)
        node = repo.find_node("c1", NodeType.CARD)
        assert node is not None
        assert node.id == "c1"
        assert node.label == "Test Card"
        assert node.type == NodeType.CARD

    def test_find_node_returns_none_for_missing(self):
        """不存在的节点返回 None。"""
        cards = _make_cards(("c1", "Only", None, [], []))
        backend = DeterministicGraphBuilder(cards)
        repo = GraphRepository(backend)
        assert repo.find_node("c999", NodeType.CARD) is None

    def test_node_exists(self):
        """node_exists 正确判断节点存在性。"""
        cards = _make_cards(("c1", "Exists", None, [], []))
        backend = DeterministicGraphBuilder(cards)
        repo = GraphRepository(backend)
        assert repo.node_exists("c1", NodeType.CARD) is True
        assert repo.node_exists("c999", NodeType.CARD) is False

    def test_find_edges_returns_edges(self):
        """find_edges 返回节点间的关系边。"""
        cards = _make_cards(
            ("c1", "Card A", "src/doc.md", ["ai"], []),
            ("c2", "Card B", "src/doc.md", ["ai"], []),
        )
        backend = DeterministicGraphBuilder(cards)
        repo = GraphRepository(backend)
        edges = repo.find_edges("c1")
        assert len(edges) > 0
        edge_types = {e.edge_type for e in edges}
        assert EdgeType.SHARES_TAG in edge_types or EdgeType.RELATED_BY_SOURCE in edge_types

    def test_find_edges_with_type_filter(self):
        """find_edges 支持按 edge_type 过滤。"""
        cards = _make_cards(
            ("c1", "Card A", "src/doc.md", ["ai"], []),
            ("c2", "Card B", "src/doc.md", ["ai"], []),
        )
        backend = DeterministicGraphBuilder(cards)
        repo = GraphRepository(backend)
        edges = repo.find_edges("c1", edge_types={EdgeType.SHARES_TAG})
        for e in edges:
            assert e.edge_type == EdgeType.SHARES_TAG

    def test_find_edges_between(self):
        """find_edges_between 返回两节点间的边。"""
        cards = _make_cards(
            ("c1", "Card A", "src/doc.md", ["ai"], []),
            ("c2", "Card B", "src/doc.md", ["ai"], []),
        )
        backend = DeterministicGraphBuilder(cards)
        repo = GraphRepository(backend)
        edges = repo.find_edges_between("c1", "c2")
        assert len(edges) > 0

    def test_find_subgraph_card_centered(self):
        """find_subgraph 以卡片为中心构建子图。"""
        cards = _make_cards(
            ("c1", "Center", "src/doc.md", ["ai"], ["Intro"]),
            ("c2", "Neighbor A", "src/doc.md", ["ai"], []),
            ("c3", "Neighbor B", "src/doc.md", ["dl"], []),
        )
        backend = DeterministicGraphBuilder(cards)
        repo = GraphRepository(backend)
        graph = repo.find_subgraph("c1", NodeType.CARD, depth=2)
        assert graph.center_id == "c1"
        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0

    def test_find_card_subgraph_convenience(self):
        """find_card_subgraph 便捷方法。"""
        cards = _make_cards(
            ("c1", "Center", "src/doc.md", ["ai"], []),
            ("c2", "Related", "src/doc.md", ["ai"], []),
        )
        backend = DeterministicGraphBuilder(cards)
        repo = GraphRepository(backend)
        graph = repo.find_card_subgraph("c1")
        assert graph.center_type == NodeType.CARD
        assert len(graph.nodes) >= 1

    def test_find_source_subgraph(self):
        """find_source_subgraph 以 Source 为中心构建子图。"""
        cards = _make_cards(
            ("c1", "Card A", "src/doc.md", ["ai"], []),
            ("c2", "Card B", "src/doc.md", ["dl"], []),
        )
        backend = DeterministicGraphBuilder(cards)
        repo = GraphRepository(backend)
        graph = repo.find_source_subgraph("src/doc.md")
        assert graph.center_type == NodeType.SOURCE
        assert len(graph.nodes) >= 2

    def test_find_tag_subgraph(self):
        """find_tag_subgraph 以 Tag 为中心构建子图。"""
        cards = _make_cards(
            ("c1", "Card A", "s1", ["ai"], []),
            ("c2", "Card B", "s2", ["ai"], []),
        )
        backend = DeterministicGraphBuilder(cards)
        repo = GraphRepository(backend)
        graph = repo.find_tag_subgraph("ai")
        assert graph.center_type == NodeType.TAG
        assert len(graph.nodes) >= 2

    def test_find_path_between_nodes(self):
        """find_path 查找两节点间的路径。"""
        cards = _make_cards(
            ("c1", "A", "src/doc.md", ["ai"], []),
            ("c2", "B", "src/doc.md", ["ai"], []),
        )
        backend = DeterministicGraphBuilder(cards)
        repo = GraphRepository(backend)
        paths = repo.find_path("c1", "c2", max_depth=2)
        assert len(paths) > 0

    def test_find_path_no_path(self):
        """无路径时返回空列表。"""
        cards = _make_cards(
            ("c1", "Isolated", None, [], []),
            ("c2", "Also Isolated", None, [], []),
        )
        backend = DeterministicGraphBuilder(cards)
        repo = GraphRepository(backend)
        paths = repo.find_path("c1", "c2", max_depth=2)
        assert paths == []

    def test_find_neighbors(self):
        """find_neighbors 返回节点的直接邻居。"""
        cards = _make_cards(
            ("c1", "Center", "src/doc.md", ["ai"], []),
            ("c2", "Neighbor 1", "src/doc.md", ["ai"], []),
            ("c3", "Neighbor 2", "src/doc.md", ["ai"], []),
        )
        backend = DeterministicGraphBuilder(cards)
        repo = GraphRepository(backend)
        neighbors = repo.find_neighbors("c1")
        neighbor_ids = {n.id for n in neighbors}
        assert "c2" in neighbor_ids or "c3" in neighbor_ids


class TestGraphRepositoryBackendSubstitutability:
    """GraphRepository 的可替换性契约测试。

    中文学习型说明：验证同一个 GraphRepository 方法集可通过不同的 GraphPort
    实现获得一致的行为。这是 Repository Pattern 和端口-适配器架构的核心保证。
    """

    def test_same_methods_work_with_different_backends(self):
        """相同的 Repository 方法在两个不同 GraphPort 实例上均能正常工作。"""
        cards = _make_cards(
            ("c1", "Card A", "src/doc.md", ["ai"], []),
            ("c2", "Card B", "src/doc.md", ["ai"], []),
        )

        # 两个不同的 GraphPort 实例（相同数据、不同构建器实例）
        backend1 = DeterministicGraphBuilder(cards)
        backend2 = DeterministicGraphBuilder(cards)

        repo1 = GraphRepository(backend1)
        repo2 = GraphRepository(backend2)

        # 相同查询应返回相同结果
        g1 = repo1.find_card_subgraph("c1")
        g2 = repo2.find_card_subgraph("c1")

        assert g1.center_id == g2.center_id
        assert len(g1.nodes) == len(g2.nodes)
        assert len(g1.edges) == len(g2.edges)

    def test_repository_is_readonly(self):
        """GraphRepository 不修改底层 GraphPort 的数据。"""
        cards = _make_cards(
            ("c1", "Card A", "src/doc.md", ["ai"], []),
            ("c2", "Card B", "src/doc.md", ["ai"], []),
        )
        backend = DeterministicGraphBuilder(cards)
        repo = GraphRepository(backend)

        # 多次查询应返回一致结果
        g1 = repo.find_card_subgraph("c1")
        g2 = repo.find_card_subgraph("c1")

        assert g1.center_id == g2.center_id
        assert len(g1.nodes) == len(g2.nodes)

    def test_backend_property_access(self):
        """可通过 .backend 属性访问底层 GraphPort 实现。"""
        cards = _make_cards(("c1", "Only", "src/doc.md", [], []))
        backend = DeterministicGraphBuilder(cards)
        repo = GraphRepository(backend)
        assert repo.backend is backend
        assert isinstance(repo.backend, DeterministicGraphBuilder)


class TestGraphRepositoryBoundary:
    """GraphRepository 边界测试。"""

    def test_graph_port_is_abstract(self):
        """GraphPort 仍是 ABC，不能直接实例化。"""
        import inspect
        from mindforge.relations.graph_port import GraphPort
        assert inspect.isabstract(GraphPort)

    def test_graph_repository_accepts_any_graph_port(self):
        """GraphRepository 接受任何实现了 GraphPort 的对象。"""
        from mindforge.relations.graph_port import GraphPort

        class FakeGraphPort(GraphPort):
            def get_node(self, node_id, node_type):
                return GraphNode(id=node_id, type=node_type, label="fake")

            def get_edges(self, node_id, *, edge_types=None, direction="both"):
                return []

            def get_graph(self, center_id, center_type, *, depth=2):
                from mindforge.relations.graph_models import Graph
                return Graph(
                    center_id=center_id, center_type=center_type, depth=depth,
                    nodes=(), edges=(),
                )

            def get_path(self, source_id, target_id, *, max_depth=4):
                return []

        fake = FakeGraphPort()
        repo = GraphRepository(fake)
        node = repo.find_node("test", NodeType.CARD)
        assert node is not None
        assert node.label == "fake"
        edges = repo.find_edges("test")
        assert edges == []

    def test_no_external_dependencies(self):
        """GraphRepository 不引入外部依赖。"""
        import ast
        from pathlib import Path
        src = Path(__file__).resolve().parent.parent.parent / "src" / "mindforge" / "relations" / "graph_repository.py"
        tree = ast.parse(src.read_text(encoding="utf-8"))
        forbidden = {"openai", "anthropic", "kuzu", "networkx", "sqlite3", "chromadb"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden, f"禁止引入: {alias.name}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden, f"禁止引入: {node.module}"
