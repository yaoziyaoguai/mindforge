"""v0.8 RetrievalPort — 全文检索的抽象接口。

中文学习型说明：RetrievalPort 定义了词法检索的统一边界，隔离具体实现
（纯 Python BM25 / SQLite FTS5 / 未来的后端）。recall_service.py 依赖
RetrievalPort 而非具体引擎，便于替换和 benchmark。

设计约束：
- 零 embedding / 零 RAG / 零 vector DB（硬红线）
- 所有方法返回词法检索结果，不做语义搜索
- 不依赖具体存储引擎
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

if TYPE_CHECKING:
    from mindforge.lexical_index import BM25Index, HybridHit, SearchHit


@dataclass(frozen=True)
class IndexLoadResult:
    """load_or_build_index() 的结构化返回结果。

    封装索引加载/构建的全部状态，避免 recall_service 直接访问
    lexical_index 内部细节。这是 RetrievalPort 边界的核心数据契约。
    """

    index: Any
    """已加载或构建的索引对象（BM25Index 或未来后端的等价物）。"""

    source: str
    """索引来源标识：'disk' / 'memory-temp' / 'memory-rebuilt-stale' / 'memory-rebuilt-error'。"""

    used_disk: bool
    """是否直接使用了磁盘上的现有索引（无需重建）。"""

    stale: bool
    """索引是否过期（config hash 不匹配或 cards 与索引不一致）。"""

    warnings: tuple[str, ...] = ()
    """索引加载过程中产生的非致命警告。"""


class RetrievalPort(ABC):
    """词法全文检索抽象端口。

    实现方：Bm25RetrievalEngine (default)、未来的 SqliteFts5Engine 等。

    v3.6.1 新增 load_or_build_index() — 将索引生命周期管理纳入端口边界，
    使 recall_service 无需直接依赖 lexical_index 模块。
    """

    @abstractmethod
    def load_or_build_index(
        self,
        index_path: Path,
        cards: Iterable[Any],
        *,
        field_weights: dict[str, float] | None = None,
        k1: float = 1.2,
        b: float = 0.75,
        config_hash: str | None = None,
    ) -> IndexLoadResult:
        """加载或构建检索索引。

        优先从磁盘加载已有索引；若索引不存在、与当前配置不匹配、
        或与 cards 集合不一致，则自动在内存中重建。

        Args:
            index_path: 磁盘索引文件路径
            cards: 卡片摘要可迭代对象
            field_weights: BM25 各字段权重配置
            k1: BM25 k1 参数
            b: BM25 b 参数
            config_hash: 当前配置的 hash，用于检测配置变更

        Returns:
            IndexLoadResult 包含索引对象和加载状态
        """
        ...

    @abstractmethod
    def search(
        self,
        index: BM25Index,
        query: str,
        *,
        status_filter: str | None = "human_approved",
        include_drafts: bool = False,
        track: str | None = None,
        project: str | None = None,
        tags: Iterable[str] = (),
        source_type: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 20,
    ) -> list[SearchHit]:
        """对索引执行词法搜索；先 pre-filter 再打分。"""
        ...

    @abstractmethod
    def hybrid_search(
        self,
        index: BM25Index,
        query: str,
        *,
        weights: dict[str, float] | None = None,
        cards: Iterable | None = None,
        now: datetime | None = None,
        status_filter: str | None = "human_approved",
        include_drafts: bool = False,
        track: str | None = None,
        project: str | None = None,
        tags: Iterable[str] = (),
        source_type: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 20,
    ) -> list[HybridHit]:
        """hybrid 排序检索：bm25 + value_score + review_due 三路加权。"""
        ...


__all__ = ["IndexLoadResult", "RetrievalPort"]
