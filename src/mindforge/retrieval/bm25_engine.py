"""v0.8 Bm25RetrievalEngine — 基于现有 BM25 实现的 RetrievalPort 适配器。

将 lexical_index 的 search() / hybrid_search() 函数包装为 RetrievalPort 接口。
不做功能变更，纯粹是适配层。
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from mindforge import lexical_index as lx
from mindforge.retrieval.retrieval_port import RetrievalPort


class Bm25RetrievalEngine(RetrievalPort):
    """BM25 词法检索引擎，委托到现有 lexical_index 实现。"""

    def search(
        self,
        index: lx.BM25Index,
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
    ) -> list[lx.SearchHit]:
        return lx.search(
            index,
            query,
            status_filter=status_filter,
            include_drafts=include_drafts,
            track=track,
            project=project,
            tags=tags,
            source_type=source_type,
            since=since,
            until=until,
            limit=limit,
        )

    def hybrid_search(
        self,
        index: lx.BM25Index,
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
    ) -> list[lx.HybridHit]:
        return lx.hybrid_search(
            index,
            query,
            weights=weights,
            cards=cards,
            now=now,
            status_filter=status_filter,
            include_drafts=include_drafts,
            track=track,
            project=project,
            tags=tags,
            source_type=source_type,
            since=since,
            until=until,
            limit=limit,
        )


__all__ = ["Bm25RetrievalEngine"]
