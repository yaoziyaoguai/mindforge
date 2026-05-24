"""v2.3 GraphPort contract tests — 图访问端口抽象的形式化验证。

中文学习型说明：验证 GraphPort 抽象契约和 DeterministicGraphBuilder 实现。
所有测试使用合成数据，不调用 LLM、不做 embedding。
"""

from __future__ import annotations

import pytest

from mindforge.relations.graph_port import GraphPort
from mindforge.relations.graph_builder import DeterministicGraphBuilder
from mindforge.relations.graph_models import Graph, NodeType


def _make_minimal_cards() -> list[dict[str, object]]:
    """构造最小合成卡片数据用于 builder 初始化。"""
    return [
        {
            "id": "c1", "title": "Card One",
            "source_id": "src_1", "tags": ["ai"],
            "wiki_sections": ["ML"], "status": "human_approved",
            "run_id": "r1", "source_location_index": 0,
        },
        {
            "id": "c2", "title": "Card Two",
            "source_id": "src_1", "tags": ["ai", "db"],
            "wiki_sections": ["ML", "DB"], "status": "human_approved",
            "run_id": "r1", "source_location_index": 1,
        },
    ]


class TestGraphPortContract:
    """GraphPort 抽象契约测试。"""

    def test_builder_is_graph_port(self):
        """DeterministicGraphBuilder 是 GraphPort 的子类。"""
        builder = DeterministicGraphBuilder(_make_minimal_cards())
        assert isinstance(builder, GraphPort)

    def test_graph_port_is_abstract(self):
        """GraphPort 不可直接实例化。"""
        with pytest.raises(TypeError):
            GraphPort()  # type: ignore[abstract]

    def test_builder_has_required_methods(self):
        """DeterministicGraphBuilder 实现所有必需方法。"""
        builder = DeterministicGraphBuilder(_make_minimal_cards())
        for method in ["get_node", "get_edges", "get_graph", "get_path"]:
            assert hasattr(builder, method)
            assert callable(getattr(builder, method))

    def test_graph_port_methods_are_abstract(self):
        """所有 GraphPort 方法都是 abstractmethod。"""
        for name in ["get_node", "get_edges", "get_graph", "get_path"]:
            method = getattr(GraphPort, name)
            assert getattr(method, "__isabstractmethod__", False), f"{name} should be abstract"

    def test_get_graph_returns_graph_type(self):
        """get_graph 返回 Graph 类型。"""
        builder = DeterministicGraphBuilder(_make_minimal_cards())
        graph = builder.get_graph("c1", NodeType.CARD, depth=1)
        assert isinstance(graph, Graph)
        assert graph.center_id == "c1"


class TestDeterministicGraphBuilder:
    """DeterministicGraphBuilder 实现行为测试。"""

    def test_builder_with_empty_cards(self):
        """无数据时 builder 初始化成功。"""
        builder = DeterministicGraphBuilder([])
        result = builder.get_node("nothing", NodeType.CARD)
        assert result is None

    def test_builder_deterministic(self):
        """相同输入 → 相同图（确定性验证）。"""
        cards = _make_minimal_cards()
        b1 = DeterministicGraphBuilder(cards)
        b2 = DeterministicGraphBuilder(cards)
        g1 = b1.get_graph("c1", NodeType.CARD, depth=1)
        g2 = b2.get_graph("c1", NodeType.CARD, depth=1)
        assert g1.center_id == g2.center_id
        assert len(g1.nodes) == len(g2.nodes)
        assert len(g1.edges) == len(g2.edges)

    def test_get_path_returns_list(self):
        """get_path 返回列表。"""
        builder = DeterministicGraphBuilder(_make_minimal_cards())
        paths = builder.get_path("c1", "c2", max_depth=2)
        assert isinstance(paths, list)

    def test_get_edges_filters_by_direction(self):
        """get_edges 的方向参数生效。"""
        builder = DeterministicGraphBuilder(_make_minimal_cards())
        # outgoing 和 incoming 应返回列表
        out = builder.get_edges("c1", direction="outgoing")
        inc = builder.get_edges("c1", direction="incoming")
        both = builder.get_edges("c1", direction="both")
        assert isinstance(out, list)
        assert isinstance(inc, list)
        assert isinstance(both, list)
