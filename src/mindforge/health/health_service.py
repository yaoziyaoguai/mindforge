"""M5 Knowledge Health Report — SDD §9, TDD §6。

确定性健康检查：review backlog, orphans, low quality, duplicates, wiki stale。
所有建议只读，不自动修改卡片。
"""

from __future__ import annotations

import enum
from dataclasses import dataclass


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
    affected_card_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class HealthReport:
    issues: tuple[HealthIssue, ...]
    summary: str


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
    card_wiki_refs: dict[str, tuple[str, ...]] | None = None,
    card_related_count: dict[str, int] | None = None,
) -> HealthReport:
    """计算知识库健康报告。

    不修改任何卡片，不执行任何 mutation。
    """
    issues: list[HealthIssue] = []

    # 1. Review backlog
    if pending_drafts >= BACKLOG_THRESHOLD:
        issues.append(HealthIssue(
            code="review_backlog",
            severity=Severity.WARN,
            message=f"{pending_drafts} pending drafts awaiting review",
            suggested_action="Review pending drafts and approve or reject each card. Consider processing in batches.",
        ))

    # 2. Low quality
    low_cards = [
        str(c["id"]) for c in cards
        if c.get("quality_level") == "low" and c.get("status") == "human_approved"
    ]
    if low_cards:
        severity = Severity.CRITICAL if len(low_cards) >= 5 else Severity.WARN
        issues.append(HealthIssue(
            code="low_quality",
            severity=severity,
            message=f"{len(low_cards)} approved cards with low quality score",
            suggested_action=f"Review and potentially regenerate: {', '.join(low_cards[:3])}{'...' if len(low_cards) > 3 else ''}. Consider splitting or enriching content.",
            affected_card_ids=tuple(low_cards),
        ))

    # 3. Orphans (only when context is provided)
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
        severity = Severity.CRITICAL if len(orphan_ids) / max(len(cards), 1) > 0.2 else Severity.WARN
        issues.append(HealthIssue(
            code="orphans",
            severity=severity,
            message=f"{len(orphan_ids)} orphan cards found — not referenced by Wiki or related cards",
            suggested_action="Check if these cards belong to a Wiki section. Consider linking them to related cards or wiki sections.",
            affected_card_ids=tuple(orphan_ids),
        ))

    # 4. Duplicates
    dup_pairs = _detect_duplicates(cards)
    if dup_pairs:
        affected = [id for pair in dup_pairs for id in pair]
        issues.append(HealthIssue(
            code="duplicates",
            severity=Severity.INFO,
            message=f"{len(dup_pairs)} potential duplicate card pairs found",
            suggested_action=f"Review pairs: {', '.join(f'{a}↔{b}' for a, b in dup_pairs[:3])}. Consider merging if content truly overlaps.",
            affected_card_ids=tuple(affected),
        ))

    # 5. Wiki stale
    if wiki_stale_sections:
        issues.append(HealthIssue(
            code="wiki_stale",
            severity=Severity.WARN,
            message=f"{len(wiki_stale_sections)} Wiki sections marked stale",
            suggested_action=f"Rebuild wiki to refresh stale sections: {', '.join(wiki_stale_sections[:3])}.",
            affected_card_ids=(),
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

    return HealthReport(issues=tuple(issues), summary=summary)


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
