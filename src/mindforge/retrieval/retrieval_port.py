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
from datetime import datetime
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from mindforge.lexical_index import BM25Index, HybridHit, SearchHit


class RetrievalPort(ABC):
    """词法全文检索抽象端口。

    实现方：Bm25RetrievalEngine (default)、未来的 SqliteFts5Engine 等。
    """

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


__all__ = ["RetrievalPort"]
