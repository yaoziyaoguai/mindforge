"""M5 Knowledge Health Report — SDD §9, TDD §6。

确定性健康检查：review backlog, orphans, low quality, duplicates, wiki stale。
所有建议只读，不自动修改卡片。
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field

from mindforge.cards import CardSummary, iter_cards, read_card_body
from mindforge.checkpoint import Checkpoint, CheckpointError
from mindforge.config import MindForgeConfig
from mindforge.review_service import build_weekly_review
from mindforge.wiki_service import get_wiki_status


# ──────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────

class Severity(str, enum.Enum):
    CRITICAL = "critical"
    WARN = "warn"
    INFO = "info"


@dataclass(frozen=True)
class HealthIssue:
    code: str
    severity: Severity
    message: str
    suggested_action: str
    reason: str = ""
    affected_card_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class HealthReport:
    issues: tuple[HealthIssue, ...]
    summary: str
    stats: dict[str, int] = field(default_factory=dict)
    maintenance_suggestions: tuple[str, ...] = ()


class KnowledgeHealthReport(HealthReport):
    """M5 公开报告类型；继承 HealthReport 以保持旧单元测试兼容。"""


# ──────────────────────────────────────────────
# Thresholds
# ──────────────────────────────────────────────

BACKLOG_THRESHOLD = 3  # ≥3 pending drafts → warn


# ──────────────────────────────────────────────
# Health computation
# ──────────────────────────────────────────────

def compute_health_report(
    *,
    cards: list[dict[str, object]],
    pending_drafts: int = 0,
    wiki_stale_sections: tuple[str, ...] = (),
    source_warnings: tuple[str, ...] = (),
    card_wiki_refs: dict[str, tuple[str, ...]] | None = None,
    card_related_count: dict[str, int] | None = None,
) -> HealthReport:
    """计算知识库健康报告。

    不修改任何卡片，不执行任何 mutation。
    """
    issues: list[HealthIssue] = []
    stats = {
        "total_cards": len(cards),
        "approved": sum(1 for c in cards if c.get("status") == "human_approved"),
        "pending_drafts": pending_drafts,
        "missing_provenance": 0,
        "low_quality": 0,
        "orphans": 0,
        "duplicates": 0,
        "stale_wiki": len(wiki_stale_sections),
        "source_warnings": len(source_warnings),
    }

    # 1. Review backlog
    if pending_drafts >= BACKLOG_THRESHOLD:
        issues.append(HealthIssue(
            code="review_backlog",
            severity=Severity.WARN,
            message=f"{pending_drafts} pending drafts awaiting review",
            reason="pending_drafts is above the review backlog threshold",
            suggested_action="Review pending drafts and approve or reject each card. Consider processing in batches.",
        ))

    # 1b. Pending drafts count（信息性，便于 M5 报告显式展示）
    if 0 < pending_drafts < BACKLOG_THRESHOLD:
        issues.append(HealthIssue(
            code="pending_drafts",
            severity=Severity.INFO,
            message=f"{pending_drafts} pending draft(s) awaiting review",
            reason="ai_draft cards exist and require explicit human decision",
            suggested_action="Review pending drafts when convenient; do not auto-approve them.",
        ))

    # 2. Missing provenance
    missing_provenance = [
        str(c["id"]) for c in cards
        if c.get("status") == "human_approved"
        and not all(c.get(key) for key in ("source_id", "source_path", "source_type", "adapter_name"))
    ]
    stats["missing_provenance"] = len(missing_provenance)
    if missing_provenance:
        issues.append(HealthIssue(
            code="missing_provenance",
            severity=Severity.WARN,
            message=f"{len(missing_provenance)} approved card(s) missing provenance metadata",
            reason="approved cards should retain source_id/source_path/source_type/adapter_name for traceability",
            suggested_action="Review affected cards and restore provenance from state/runs/source archive if available.",
            affected_card_ids=tuple(missing_provenance),
        ))

    # 3. Low quality
    low_cards = [
        str(c["id"]) for c in cards
        if c.get("quality_level") == "low" and c.get("status") == "human_approved"
    ]
    stats["low_quality"] = len(low_cards)
    if low_cards:
        severity = Severity.CRITICAL if len(low_cards) >= 5 else Severity.WARN
        issues.append(HealthIssue(
            code="low_quality",
            severity=severity,
            message=f"{len(low_cards)} approved cards with low quality score",
            reason="approved cards have deterministic quality_level=low",
            suggested_action=f"Review and potentially regenerate: {', '.join(low_cards[:3])}{'...' if len(low_cards) > 3 else ''}. Consider splitting or enriching content.",
            affected_card_ids=tuple(low_cards),
        ))

    # 4. Orphans (only when context is provided)
    if card_wiki_refs is not None or card_related_count is not None:
        wiki_refs = card_wiki_refs or {}
        related_counts = card_related_count or {}
        orphan_ids: list[str] = []
        for c in cards:
            cid = str(c["id"])
            if c.get("status") != "human_approved":
                continue
            has_wiki = bool(wiki_refs.get(cid, ()))
            has_related = related_counts.get(cid, 0) > 0
            if not has_wiki and not has_related:
                orphan_ids.append(cid)
    else:
        orphan_ids = []

    if orphan_ids:
        stats["orphans"] = len(orphan_ids)
        severity = Severity.CRITICAL if len(orphan_ids) / max(len(cards), 1) > 0.2 else Severity.WARN
        issues.append(HealthIssue(
            code="orphans",
            severity=severity,
            message=f"{len(orphan_ids)} orphan cards found — not referenced by Wiki or related cards",
            reason="approved cards have no wiki reference and no deterministic related cards",
            suggested_action="Check if these cards belong to a Wiki section. Consider linking them to related cards or wiki sections.",
            affected_card_ids=tuple(orphan_ids),
        ))

    # 5. Duplicates
    dup_pairs = _detect_duplicates(cards)
    stats["duplicates"] = len(dup_pairs)
    if dup_pairs:
        affected = [id for pair in dup_pairs for id in pair]
        issues.append(HealthIssue(
            code="duplicates",
            severity=Severity.INFO,
            message=f"{len(dup_pairs)} potential duplicate card pairs found",
            reason="card titles have high token overlap",
            suggested_action=f"Review pairs: {', '.join(f'{a}↔{b}' for a, b in dup_pairs[:3])}. Consider merging if content truly overlaps.",
            affected_card_ids=tuple(affected),
        ))

    # 6. Wiki stale
    if wiki_stale_sections:
        issues.append(HealthIssue(
            code="wiki_stale",
            severity=Severity.WARN,
            message=f"{len(wiki_stale_sections)} Wiki sections marked stale",
            reason="final Wiki is missing approved cards or sections need rebuild",
            suggested_action=f"Rebuild wiki to refresh stale sections: {', '.join(wiki_stale_sections[:3])}.",
            affected_card_ids=(),
        ))

    # 7. Source extraction warnings / unsupported attempts
    if source_warnings:
        issues.append(HealthIssue(
            code="source_warnings",
            severity=Severity.INFO,
            message=f"{len(source_warnings)} source warning(s) recorded",
            reason="; ".join(source_warnings[:3]),
            suggested_action="Review skipped/failed source attempts and re-import only after format or dependency issues are fixed.",
        ))

    # Summary
    critical = sum(1 for i in issues if i.severity == Severity.CRITICAL)
    warn = sum(1 for i in issues if i.severity == Severity.WARN)
    info = sum(1 for i in issues if i.severity == Severity.INFO)
    summary_parts: list[str] = []
    if critical:
        summary_parts.append(f"{critical} critical")
    if warn:
        summary_parts.append(f"{warn} warnings")
    if info:
        summary_parts.append(f"{info} informational")
    summary = f"Health check: {', '.join(summary_parts)} issue(s)." if summary_parts else "Health check: all clear."

    suggestions = tuple(_maintenance_suggestions(issues))
    return HealthReport(
        issues=tuple(issues),
        summary=summary,
        stats=stats,
        maintenance_suggestions=suggestions,
    )


def build_knowledge_health_report(cfg: MindForgeConfig) -> KnowledgeHealthReport:
    """从真实 MindForge config/vault 构建只读 Knowledge Health Report。

    中文学习型说明：M5 是维护诊断入口，不是修复器。这里只读 cards/wiki/state，
    不写卡片、不改 human_approved、不自动 approve，也不调用 LLM/API。
    """
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    cards = [_card_to_health_dict(card) for card in scan.cards]
    pending_drafts = sum(1 for card in scan.cards if card.status == "ai_draft")
    pending_drafts = max(pending_drafts, _review_backlog_count(cfg))
    wiki_stale = _wiki_stale_sections(cfg)
    source_warnings = _source_warnings(cfg)
    approved_cards = [card for card in scan.cards if card.status == "human_approved"]
    card_wiki_refs = _card_wiki_refs(cfg, approved_cards)
    related_count = _card_related_count(approved_cards)
    report = compute_health_report(
        cards=cards,
        pending_drafts=pending_drafts,
        wiki_stale_sections=wiki_stale,
        source_warnings=source_warnings,
        card_wiki_refs=card_wiki_refs,
        card_related_count=related_count,
    )
    return KnowledgeHealthReport(
        issues=report.issues,
        summary=report.summary,
        stats=report.stats,
        maintenance_suggestions=report.maintenance_suggestions,
    )


def _card_to_health_dict(card: CardSummary) -> dict[str, object]:
    return {
        "id": card.id or card.path.stem,
        "status": card.status,
        "quality_level": _quality_level(card),
        "source_id": card.source_id,
        "source_path": card.source_path,
        "source_type": card.source_type,
        "adapter_name": card.adapter_name,
        "tags": list(card.tags),
        "title": card.title or card.path.stem,
    }


def _quality_level(card: CardSummary) -> str:
    try:
        body = read_card_body(card.path)
    except (OSError, ValueError):
        body = ""
    if len(body.strip()) < 80:
        return "low"
    return "medium"


def _review_backlog_count(cfg: MindForgeConfig) -> int:
    try:
        review = build_weekly_review(cfg)
    except Exception:  # noqa: BLE001 - health report must stay diagnostic-only
        return 0
    return len(review.overdue) + len(review.due_this_week) + review.draft_cards_count


def _wiki_stale_sections(cfg: MindForgeConfig) -> tuple[str, ...]:
    try:
        status = get_wiki_status(cfg)
    except Exception:  # noqa: BLE001
        return ()
    if not status.exists and status.approved_card_count:
        return ("Main-Wiki.md missing",)
    if status.is_stale:
        return (f"Main-Wiki.md missing {status.new_approved_count} approved card(s)",)
    return ()


def _card_wiki_refs(cfg: MindForgeConfig, approved_cards: list[CardSummary]) -> dict[str, tuple[str, ...]]:
    wiki_path = cfg.vault.root / "30-Wiki" / "Main-Wiki.md"
    try:
        text = wiki_path.read_text(encoding="utf-8") if wiki_path.is_file() else ""
    except OSError:
        text = ""
    refs: dict[str, tuple[str, ...]] = {}
    for card in approved_cards:
        cid = card.id or card.path.stem
        refs[cid] = ("Main-Wiki.md",) if cid in text or card.rel_path in text else ()
    return refs


def _card_related_count(approved_cards: list[CardSummary]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for card in approved_cards:
        cid = card.id or card.path.stem
        count = 0
        for other in approved_cards:
            if other is card:
                continue
            if card.source_id and card.source_id == other.source_id:
                count += 1
                continue
            if set(card.tags) & set(other.tags):
                count += 1
                continue
            if card.track and card.track == other.track:
                count += 1
        counts[cid] = count
    return counts


def _source_warnings(cfg: MindForgeConfig) -> tuple[str, ...]:
    warnings: list[str] = []
    try:
        cp = Checkpoint.load(cfg.state.state_path)
    except (CheckpointError, OSError):
        return ()
    for item in cp.all_items():
        if item.status in {"failed", "skipped"} and item.error_message:
            warnings.append(item.error_message)
    return tuple(warnings)


def _maintenance_suggestions(issues: list[HealthIssue]) -> list[str]:
    suggestions: list[str] = []
    for issue in issues:
        if issue.suggested_action not in suggestions:
            suggestions.append(issue.suggested_action)
    return suggestions


def _detect_duplicates(cards: list[dict[str, object]]) -> list[tuple[str, str]]:
    """简单 title Jaccard overlap 检测潜在重复。"""
    pairs: list[tuple[str, str]] = []
    approved = [c for c in cards if c.get("status") == "human_approved"]
    for i in range(len(approved)):
        for j in range(i + 1, len(approved)):
            a_title = str(approved[i].get("title", ""))
            b_title = str(approved[j].get("title", ""))
            if not a_title or not b_title:
                continue
            score = _title_jaccard(a_title.lower(), b_title.lower())
            if score >= 0.5:
                pairs.append((str(approved[i]["id"]), str(approved[j]["id"])))
    return pairs


def _title_jaccard(a: str, b: str) -> float:
    a_tokens = set(a.split())
    b_tokens = set(b.split())
    if not a_tokens or not b_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / len(a_tokens | b_tokens)
