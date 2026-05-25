"""v4.1 GraphRepository — GraphPort 的 Repository Pattern 封装。

中文学习型说明：GraphRepository 遵循 Repository 模式，将 GraphPort 的
底层查询原语封装为语义更清晰的仓库方法。业务层通过 GraphRepository
访问图数据，不直接依赖 GraphPort 的具体实现。

设计约束：
- 纯只读，不修改后端数据
- 不引入新依赖
- 支持后端替换（in-memory ↔ Kuzu ↔ SQLite）的契约测试
"""

from __future__ import annotations

from mindforge.relations.graph_models import Graph, GraphEdge, GraphNode, NodeType, EdgeType
from mindforge.relations.graph_port import GraphPort


class GraphRepository:
    """图数据的 Repository 模式封装。

    中文学习型说明：GraphRepository 不拥有图的构建逻辑（那是 GraphPort 实现
    的职责），它只是在 GraphPort 抽象之上提供一致的命名和访问模式。

    使用方式：
        backend = DeterministicGraphBuilder(cards)
        repo = GraphRepository(backend)
        graph = repo.find_subgraph("card_1", NodeType.CARD, depth=2)
    """

    def __init__(self, backend: GraphPort) -> None:
        self._backend = backend

    # ── Node Queries ───────────────────────────────

    def find_node(self, node_id: str, node_type: NodeType) -> GraphNode | None:
        """按 ID 和类型查找单个节点。"""
        return self._backend.get_node(node_id, node_type)

    def node_exists(self, node_id: str, node_type: NodeType) -> bool:
        """检查节点是否存在。"""
        return self._backend.get_node(node_id, node_type) is not None

    # ── Edge Queries ───────────────────────────────

    def find_edges(
        self,
        node_id: str,
        *,
        edge_types: set[EdgeType] | None = None,
        direction: str = "both",
    ) -> list[GraphEdge]:
        """获取与指定节点相关的所有边。"""
        return self._backend.get_edges(
            node_id, edge_types=edge_types, direction=direction,
        )

    def find_edges_between(
        self,
        source_id: str,
        target_id: str,
    ) -> list[GraphEdge]:
        """获取两节点间的所有出边。"""
        all_edges = self._backend.get_edges(source_id, direction="outgoing")
        return [e for e in all_edges if e.target_id == target_id]

    # ── Subgraph Queries ───────────────────────────

    def find_subgraph(
        self,
        center_id: str,
        center_type: NodeType,
        *,
        depth: int = 2,
    ) -> Graph:
        """以指定节点为中心构建子图。"""
        return self._backend.get_graph(center_id, center_type, depth=depth)

    def find_card_subgraph(self, card_id: str, *, depth: int = 1) -> Graph:
        """以卡片为中心构建子图（便捷方法）。"""
        return self._backend.get_graph(card_id, NodeType.CARD, depth=depth)

    def find_source_subgraph(self, source_id: str, *, depth: int = 1) -> Graph:
        """以 Source 为中心构建子图（便捷方法）。"""
        return self._backend.get_graph(source_id, NodeType.SOURCE, depth=depth)

    def find_tag_subgraph(self, tag: str, *, depth: int = 1) -> Graph:
        """以 Tag 为中心构建子图（便捷方法）。"""
        return self._backend.get_graph(tag, NodeType.TAG, depth=depth)

    # ── Path Queries ───────────────────────────────

    def find_path(
        self,
        source_id: str,
        target_id: str,
        *,
        max_depth: int = 4,
    ) -> list[list[GraphEdge]]:
        """查找两节点间的所有路径（用于 provenance trail）。"""
        return self._backend.get_path(source_id, target_id, max_depth=max_depth)

    # ── Neighbor Queries ───────────────────────────

    def find_neighbors(
        self,
        node_id: str,
        *,
        direction: str = "both",
    ) -> list[GraphNode]:
        """获取节点的直接邻居节点（去重）。"""
        edges = self._backend.get_edges(node_id, direction=direction)
        seen: set[str] = set()
        neighbors: list[GraphNode] = []
        for edge in edges:
            neighbor_id = edge.target_id if edge.source_id == node_id else edge.source_id
            if neighbor_id in seen or neighbor_id == node_id:
                continue
            seen.add(neighbor_id)
            # 尝试获取邻居节点（类型未知，尝试 CARD）
            node = self._backend.get_node(neighbor_id, NodeType.CARD)
            if node is None:
                # fallback: 创建最小节点表示
                node = GraphNode(
                    id=neighbor_id,
                    type=NodeType.CARD,
                    label=neighbor_id,
                )
            neighbors.append(node)
        return neighbors

    # ── Backend Access ──────────────────────────────

    @property
    def backend(self) -> GraphPort:
        """获取底层 GraphPort 实现（用于需要底层访问的场景）。"""
        return self._backend


__all__ = ["GraphRepository"]
