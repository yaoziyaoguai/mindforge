"""v3.1 — Dogfood 报告服务（从 web_facade.py 拆分）。

从 WebFacade.dogfood_report() 提取纯函数，接受 cfg 和外部依赖作为参数。
不包含 WebFacade 内部状态引用，便于独立测试和复用。
"""

from __future__ import annotations

from datetime import datetime, timezone

from mindforge.cards import iter_cards
from mindforge.config import MindForgeConfig
from mindforge.wiki_service import get_wiki_status

from ..schemas import DogfoodReportResponse


def compute_dogfood_report(
    cfg: MindForgeConfig,
    *,
    search_index_exists: bool = False,
    search_index_path: str = "",
    health_issue_count: int = 0,
) -> DogfoodReportResponse:
    """计算工作台使用报告 — 纯本地数据聚合，不调用 LLM。"""
    now = datetime.now(timezone.utc).isoformat()

    # 扫描所有卡片
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    cards = list(scan.cards)

    total = len(cards)
    approved = [c for c in cards if c.status == "human_approved"]
    drafts = [c for c in cards if c.status == "ai_draft"]
    imported = [c for c in cards if c.status == "imported"]

    approved_count = len(approved)
    draft_count = len(drafts)
    imported_count = len(imported)
    error_count = len(scan.errors)

    approval_rate = approved_count / total if total > 0 else 0.0

    # 统计 source 数（去重 source_id）
    source_ids = {c.source_id for c in cards if c.source_id}
    source_count = len(source_ids)

    # Graph 密度
    relation_count = _compute_relation_count(approved)
    graph_density = relation_count / total if total > 0 else 0.0

    community_count = len(source_ids)

    # Wiki 状态
    wiki_section_count, wiki_stale = _wiki_status(cfg)

    # 搜索索引状态与健康问题数由调用方计算后传入

    # 趋势总结（确定性生成，不调 LLM）
    trend_summary = _build_trend_summary(total, approval_rate, draft_count, graph_density)

    # 维护建议
    suggestions = _build_suggestions(
        total, draft_count, search_index_exists, wiki_stale, health_issue_count,
    )

    return DogfoodReportResponse(
        generated_at=now,
        total_cards=total,
        approved_count=approved_count,
        draft_count=draft_count,
        approval_rate=round(approval_rate, 4),
        source_count=source_count,
        graph_total_relations=relation_count,
        graph_density=round(graph_density, 4),
        community_count=community_count,
        wiki_section_count=wiki_section_count,
        wiki_stale=wiki_stale,
        search_index_exists=search_index_exists,
        search_index_path=search_index_path,
        imported_card_count=imported_count,
        exported_count=approved_count,
        import_error_count=error_count,
        health_issue_count=health_issue_count,
        trend_summary=trend_summary,
        maintenance_suggestions=suggestions,
    )


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------


def _compute_relation_count(approved: list) -> int:
    """使用 DeterministicGraphBuilder 获取唯一边数。

    中文学习型说明：扫描已确认卡片的共享标签/来源/Wiki 章节关系，
    计算唯一无向边总数。纯确定性计算，不调 LLM/embedding。
    """
    from pathlib import Path

    from mindforge.relations.graph_builder import DeterministicGraphBuilder

    if not approved:
        return 0

    try:
        # 构建 relation records（与 web_facade._relation_record 同构）
        records: list[dict[str, object]] = []
        for card in approved:
            card_id = card.id or card.rel_path
            records.append({
                "id": card_id,
                "title": card.title or Path(card.rel_path).stem,
                "status": card.status,
                "source_id": card.source_id,
                "tags": list(card.tags),
                "wiki_sections": list(card.wiki_sections),
                "run_id": card.run_id,
                "source_location_index": card.source_location_index,
            })

        builder = DeterministicGraphBuilder(records)
        first_id = approved[0].id or approved[0].rel_path
        graph = builder.get_graph(first_id, depth=1)
        edges_seen: set[tuple[str, str]] = set()
        for edge in graph.edges:
            pair = (edge.source, edge.target)
            if pair not in edges_seen and (pair[1], pair[0]) not in edges_seen:
                edges_seen.add(pair)
        return len(edges_seen)
    except Exception:
        pass
    return 0


def _wiki_status(cfg: MindForgeConfig) -> tuple[int, bool]:
    """获取 Wiki 状态，失败时返回 (0, False)。"""
    try:
        ws = get_wiki_status(cfg)
        return ws.approved_card_count, ws.is_stale
    except Exception:
        return 0, False


def _build_trend_summary(
    total: int, approval_rate: float, draft_count: int, graph_density: float,
) -> str:
    """确定性生成趋势摘要文本。"""
    parts = [f"总卡片 {total} 张" if total > 0 else "暂无卡片"]
    if total > 0:
        parts.append(f"确认率 {approval_rate:.0%}")
        if draft_count > 0:
            parts.append(f"{draft_count} 张待审")
    if graph_density > 0:
        parts.append(f"图密度 {graph_density:.1f} 关系/卡片")
    return " · ".join(parts) + "。"


def _build_suggestions(
    total: int,
    draft_count: int,
    search_index_exists: bool,
    wiki_stale: bool,
    health_issue_count: int,
) -> list[str]:
    """确定性生成维护建议。"""
    suggestions: list[str] = []
    if draft_count > 0:
        suggestions.append(f"审阅 {draft_count} 张待确认草稿以提高知识库覆盖率。")
    if not search_index_exists:
        suggestions.append("搜索索引尚未构建，前往搜索页触发索引构建。")
    if wiki_stale:
        suggestions.append("Wiki 可能过期，考虑重新构建以包含最新确认的卡片。")
    if health_issue_count > 0:
        suggestions.append(f"知识健康报告发现 {health_issue_count} 项需关注，请查看详情。")
    if total == 0:
        suggestions.append("知识库为空，导入资料或粘贴 Markdown 内容开始构建知识库。")
    return suggestions
