"""v0.8 Bm25RetrievalEngine — 基于现有 BM25 实现的 RetrievalPort 适配器。

将 lexical_index 的 search() / hybrid_search() 函数包装为 RetrievalPort 接口。
不做功能变更，纯粹是适配层。

v3.6.1 新增 load_or_build_index() — 将索引生命周期管理纳入端口边界，
使 recall_service 无需直接依赖 lexical_index 模块的索引加载细节。

v4.9 新增 Bm25Config — 将 BM25 参数封装为可测试、可比较的配置对象，
支持 golden tuning tests。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from mindforge import lexical_index as lx
from mindforge.retrieval.retrieval_port import IndexLoadResult, RetrievalPort


@dataclass(frozen=True)
class Bm25Config:
    """BM25 检索引擎的完整参数配置。

    中文学习型说明：所有参数变更必须有对应的 golden test 记录预期行为。
    不引入 grid search 或自动调参。tokenizer 保持纯 Python split-based。

    Attributes:
        field_weights: 各字段权重（title=5.0, source_title=3.0, tags=3.0, ...）
        k1: BM25 term frequency saturation 参数，默认 1.2
        b: BM25 document length normalization 参数，默认 0.75
    """

    field_weights: dict[str, float]
    k1: float = 1.2
    b: float = 0.75

    @classmethod
    def defaults(cls) -> "Bm25Config":
        """返回 MindForge 默认 BM25 配置。"""
        return cls(
            field_weights={
                "title": 5.0,
                "source_title": 3.0,
                "track": 2.0,
                "tags": 3.0,
                "projects": 2.0,
                "source_type": 1.0,
                "body_summary": 1.0,
                "body_actions": 1.0,
                "body_principles": 1.0,
                "body_risks": 1.0,
            },
            k1=1.2,
            b=0.75,
        )


class Bm25RetrievalEngine(RetrievalPort):
    """BM25 词法检索引擎，委托到现有 lexical_index 实现。

    中文学习型说明：此引擎是 RetrievalPort 的唯一生产实现。
    未来如需 SQLite FTS5 / DuckDB FTS 等后端，只需实现相同接口即可替换，
    recall_service 无需改动。
    """

    # ── Index Lifecycle (v3.6.1) ──────────────────────────

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
        """加载或构建 BM25 索引 — 封装磁盘加载/内存重建/过期检测全部逻辑。

        中文学习型说明：此方法将原本散落在 recall_service.py 中的索引
        生命周期逻辑收敛到 RetrievalPort 边界内，recall_service 不再需要
        知道 BM25Index.load / build_index / diff_index 等细节。
        """
        fw = field_weights or {}
        cur_k1 = k1
        cur_b = b
        cur_hash = config_hash or ""
        warnings: list[str] = []

        index: lx.BM25Index
        used_disk = False
        index_stale = False
        index_source = "memory-temp"

        if index_path.exists():
            try:
                index = lx.BM25Index.load(index_path)
                if index.config_hash and index.config_hash != cur_hash:
                    index_stale = True
                    index_source = "memory-rebuilt-stale"
                    index = lx.build_index(
                        cards, field_weights=fw, k1=cur_k1, b=cur_b, config_hash=cur_hash,
                    )
                else:
                    disk_diff = lx.diff_index(index, cards)
                    if disk_diff.fresh:
                        used_disk = True
                        index_source = "disk"
                    else:
                        index_stale = True
                        index_source = "memory-rebuilt-stale"
                        warnings.append(
                            "提示：磁盘索引与当前 vault cards 不一致；"
                            "本次内存即时重建。建议运行 `mindforge index rebuild`。"
                        )
                        index = lx.build_index(
                            cards, field_weights=fw, k1=cur_k1, b=cur_b, config_hash=cur_hash,
                        )
            except (lx.IndexFormatError, OSError, ValueError) as e:
                index_source = "memory-rebuilt-error"
                warnings.append(f"索引文件不可用（{e}）；改为内存即时构建。")
                index = lx.build_index(
                    cards, field_weights=fw, k1=cur_k1, b=cur_b, config_hash=cur_hash,
                )
        else:
            warnings.append(
                "提示：尚无索引文件，本次内存即时构建。"
                "建议运行 `mindforge index rebuild` 以加速后续查询。"
            )
            index = lx.build_index(
                cards, field_weights=fw, k1=cur_k1, b=cur_b, config_hash=cur_hash,
            )

        return IndexLoadResult(
            index=index,
            source=index_source,
            used_disk=used_disk,
            stale=index_stale,
            warnings=tuple(warnings),
        )

    # ── Search ────────────────────────────────────────────

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
