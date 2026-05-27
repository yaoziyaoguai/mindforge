"""Web Recall Service — BM25 检索和索引状态。

中文学习型说明：从 web_facade 提取的 recall/search 逻辑。
仅处理 human_approved 卡片的本地 BM25 lexical recall，
不涉及 RAG/embedding/vector DB。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mindforge.config import MindForgeConfig
    from mindforge_web.schemas import RecallResponse, RecallStatus


class WebRecallService:
    """BM25 检索服务 — 主路径功能。

    中文学习型说明：封装 BM25 lexical recall 和 index status 查询。
    只查询 human_approved 卡片，不调用 LLM 或 embedding。
    """

    def __init__(self, cfg: MindForgeConfig) -> None:
        self._cfg = cfg

    def recall(self, query: str, *, context: str | None = None) -> RecallResponse:
        """执行 BM25 local lexical recall — 仅 human_approved cards。"""
        from pathlib import Path

        from mindforge.recall_service import RecallQuery, RecallServiceError, run_bm25_recall
        from mindforge_web.schemas import (
            NextAction,
            RecallHit,
            RecallResponse,
            RecallStatus,
        )
        from mindforge_web.presenters import (
            build_graph_builder,
            get_graph_neighbor_count,
        )

        index = self.recall_status()
        if not query.strip():
            return RecallResponse(
                query=query,
                hits=[],
                index=index,
                empty_state=NextAction(
                    label="Search approved cards",
                    description="输入关键词后会用本地 lexical recall 查询 human_approved cards。",
                    action_key="search_approved_cards",
                    description_key="search_approved_cards.desc",
                ),
            )
        try:
            result = run_bm25_recall(
                self._cfg,
                RecallQuery(
                    query=query,
                    track=None,
                    project=None,
                    tags=(),
                    source_type=None,
                    status="human_approved",
                    include_drafts=False,
                    since=None,
                    until=None,
                    limit=10,
                    output_format="json",
                    explain=False,
                ),
            )
        except RecallServiceError as exc:
            return RecallResponse(
                query=query,
                hits=[],
                index=index,
                warnings=[str(exc)],
                empty_state=NextAction(
                    label="Adjust query",
                    description="Recall query 无法执行，请缩短或调整关键词。",
                    action_key="adjust_query",
                    description_key="adjust_query.desc",
                ),
            )

        graph_builder = None
        if context == "graph":
            graph_builder = build_graph_builder(self._cfg)

        return RecallResponse(
            query=query,
            hits=[
                RecallHit(
                    score=hit.score,
                    title=hit.title,
                    card_ref=hit.id or Path(hit.rel_path).name,
                    detail_href=f"/library?card={hit.id or hit.rel_path}",
                    rel_path=hit.rel_path,
                    status=hit.status,
                    track=hit.track,
                    projects=list(hit.projects),
                    tags=list(hit.tags),
                    source_type=hit.source_type,
                    why_this_matched=hit.why_this_matched,
                    graph_neighbor_count=get_graph_neighbor_count(
                        graph_builder, hit.id or hit.rel_path
                    ) if graph_builder else None,
                    graph_shared_tag_count=len(hit.tags) if graph_builder else None,
                )
                for hit in result.hits
            ],
            index=RecallStatus(
                index_path=str(result.index.path),
                index_exists=result.index.path.exists(),
                approved_card_count=result.index.card_counts.get("human_approved", 0),
                available=True,
                next_action=NextAction(
                    label="Rebuild index",
                    description="索引缺失或 stale 时可重建本地 BM25 index。",
                    command="mindforge index rebuild",
                    action_key="rebuild_index",
                    description_key="rebuild_index.desc",
                )
                if result.index.suggest_rebuild
                else None,
            ),
            warnings=list(result.warnings),
            empty_state=None
            if result.hits
            else NextAction(
                label="Try another query",
                description="没有命中 approved cards；换一个关键词或先 approve draft。",
                action_key="try_another_query",
                description_key="try_another_query.desc",
            ),
        )

    def recall_status(self, approved_count: int | None = None) -> RecallStatus:
        """BM25 索引状态查询 — 报告 approved card 数量和索引可用性。"""
        from mindforge.lexical_index import default_index_path
        from mindforge_web.schemas import NextAction, RecallStatus

        count = approved_count
        if count is None:
            count = self._card_status_counts().get("human_approved", 0)
        index_path = default_index_path(self._cfg.state.workdir)
        return RecallStatus(
            index_path=str(index_path),
            index_exists=index_path.exists(),
            approved_card_count=count,
            available=True,
            next_action=NextAction(
                label="Approve drafts",
                description="Recall 默认只查询 human_approved cards。",
                href="/drafts",
                action_key="review_drafts",
                description_key="review_drafts.desc",
            )
            if count == 0
            else None,
        )

    def _card_status_counts(self) -> dict[str, int]:
        """统计各状态卡片数量 — 供 recall_status 使用。"""
        from mindforge.cards import iter_cards

        counts: dict[str, int] = {}
        try:
            scan = iter_cards(self._cfg.vault.root, self._cfg.vault.cards_dir)
            for cs in scan.cards:
                s = cs.status or "unknown"
                counts[s] = counts.get(s, 0) + 1
        except Exception:
            pass
        return counts
