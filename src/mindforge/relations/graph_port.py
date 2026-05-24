"""v0.6 GraphPort — 知识图谱访问的抽象接口。

中文学习型说明：GraphPort 定义了图查询的统一边界，隔离具体实现。
当前默认实现是 DeterministicGraphBuilder（基于 in-memory computation），
未来可替换为 Kuzu/SQLite FTS 等后端，只要实现同一接口即可。

设计约束：
- 只读接口 — graph 构建和查询不修改卡片状态
- 所有方法返回 graph_models 中定义的数据类型
- 不依赖具体存储引擎（不在接口中暴露 Kuzu/SQLite/DuckDB 细节）
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from mindforge.relations.graph_models import Graph, GraphEdge, GraphNode, NodeType


class GraphPort(ABC):
    """知识图谱访问的抽象端口。

    实现方：DeterministicGraphBuilder (default)、未来的 KuzuGraphBackend 等。
    """

    @abstractmethod
    def get_node(self, node_id: str, node_type: NodeType) -> GraphNode | None:
        """按 ID 和类型查找单个节点。"""
        ...

    @abstractmethod
    def get_edges(
        self,
        node_id: str,
        *,
        edge_types: set[EdgeType] | None = None,
        direction: str = "both",
    ) -> list[GraphEdge]:
        """获取与指定节点相关的所有边。

        Args:
            node_id: 节点 ID
            edge_types: 可选过滤边类型
            direction: "outgoing" | "incoming" | "both"
        """
        ...

    @abstractmethod
    def get_graph(
        self,
        center_id: str,
        center_type: NodeType,
        *,
        depth: int = 2,
    ) -> Graph:
        """构建以指定节点为中心的知识图谱。

        Args:
            center_id: 中心节点 ID
            center_type: 中心节点类型
            depth: 图深度（1 = 仅邻居, 2 = 邻居的邻居）

        Returns:
            Graph 对象，包含中心节点的 depth-hop 邻居及所有边
        """
        ...

    @abstractmethod
    def get_path(
        self,
        source_id: str,
        target_id: str,
        *,
        max_depth: int = 4,
    ) -> list[list[GraphEdge]]:
        """查找两节点间的路径（用于 provenance trail 等场景）。

        Returns:
            路径列表，每条路径是 GraphEdge 序列。空列表表示无路径。
        """
        ...


# 导入放底部以避免循环引用（GraphPort 不依赖具体 EdgeType，但 get_edges 的参数类型引用它）
from mindforge.relations.graph_models import EdgeType  # noqa: E402, F811


__all__ = ["GraphPort"]
