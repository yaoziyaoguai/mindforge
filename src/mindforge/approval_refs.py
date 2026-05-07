"""Pending approval ref resolution.

中文学习型说明：本模块只负责把用户友好的 pending ref（编号、short ref、
title slug、card id 或 path）解析成唯一 card path。它不执行 approve，不写卡片，
也不刷新 index；这样 approve UX 可以变短，但人审写入边界仍留在
approval_service / approver。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .approval_service import (
    ApprovalListQuery,
    ApprovalServiceError,
    list_approval_candidates,
    resolve_user_card_path,
)
from .cards import CardSummary
from .config import MindForgeConfig


@dataclass(frozen=True)
class ApprovalPendingRef:
    """一条待审核卡片的短引用；只是选择目标，不代表 approve 决策。"""

    number: int
    short_ref: str
    title_slug: str
    card_id: str | None
    title: str | None
    rel_path: str
    path: Path


@dataclass(frozen=True)
class ApprovalRefLookupResult:
    """短 ref / 编号 / card id / path 的解析结果；不执行 approve。"""

    card_path: Path | None
    match: ApprovalPendingRef | None = None
    matches: tuple[ApprovalPendingRef, ...] = ()
    error: ApprovalServiceError | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.card_path is not None


def build_pending_approval_refs(
    cfg: MindForgeConfig,
    query: ApprovalListQuery | None = None,
) -> tuple[ApprovalPendingRef, ...]:
    """为当前 pending ai_draft 生成稳定短引用；只读 card frontmatter。"""

    result = list_approval_candidates(
        cfg,
        query or ApprovalListQuery(statuses=("ai_draft",), limit=10**9),
    )
    return build_pending_approval_refs_from_rows(result.candidates)


def build_pending_approval_refs_from_rows(
    rows: tuple[CardSummary, ...] | list[CardSummary],
) -> tuple[ApprovalPendingRef, ...]:
    """根据已扫描 rows 生成显示编号，避免 presenter 重新扫描文件系统。"""

    return tuple(
        ApprovalPendingRef(
            number=idx,
            short_ref=short_ref_for_card(card),
            title_slug=slugify(card.title or card.path.stem),
            card_id=card.id,
            title=card.title,
            rel_path=card.rel_path,
            path=card.path,
        )
        for idx, card in enumerate(rows, start=1)
    )


def resolve_pending_approval_ref(
    cfg: MindForgeConfig,
    ref: str | Path | None,
    query: ApprovalListQuery | None = None,
) -> ApprovalRefLookupResult:
    """把用户输入的短 ref 解析成唯一 pending card path；不写文件。"""

    if ref is None or str(ref).strip() == "":
        return ApprovalRefLookupResult(
            card_path=None,
            error=ApprovalServiceError(
                "missing_ref",
                "approve 需要明确 pending 编号、short ref、card id 或 card path",
                exit_code=2,
            ),
        )

    raw = str(ref).strip()
    refs = build_pending_approval_refs(cfg, query)
    if raw.isdigit():
        return _resolve_number(raw, refs)

    normalized = slugify(raw)
    exact = [
        candidate
        for candidate in refs
        if raw == candidate.card_id
        or raw == candidate.rel_path
        or normalized in {candidate.short_ref, candidate.title_slug}
    ]
    if len(exact) == 1:
        return _single_match(exact[0])
    if len(exact) > 1:
        return _ambiguous(raw, exact)

    resolved_path = resolve_user_card_path(cfg, Path(raw))
    if resolved_path.ok:
        assert resolved_path.path is not None
        by_path = [candidate for candidate in refs if candidate.path == resolved_path.path.resolve()]
        if len(by_path) == 1:
            return _single_match(by_path[0])
        return ApprovalRefLookupResult(
            card_path=None,
            error=ApprovalServiceError(
                "not_pending",
                f"card exists but is not in pending ai_draft list: {raw}",
                exit_code=2,
            ),
        )

    prefix = [
        candidate
        for candidate in refs
        if candidate.short_ref.startswith(normalized)
        or candidate.title_slug.startswith(normalized)
        or (candidate.card_id or "").startswith(raw)
    ]
    if len(prefix) == 1:
        return _single_match(prefix[0])
    if len(prefix) > 1:
        return _ambiguous(raw, prefix)

    return ApprovalRefLookupResult(
        card_path=None,
        matches=refs,
        error=ApprovalServiceError(
            "ref_not_found",
            f"未找到 pending approve ref：{raw}",
            exit_code=2,
        ),
    )


_DATE_PREFIX_RE = re.compile(r"^\d{8}--")
_SLUG_TOKEN_RE = re.compile(r"[A-Za-z0-9\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]+")


def short_ref_for_card(card: CardSummary) -> str:
    stem = Path(card.rel_path).stem
    stem = _DATE_PREFIX_RE.sub("", stem)
    return slugify(stem or card.title or card.id or card.path.stem)


def slugify(value: str) -> str:
    tokens = _SLUG_TOKEN_RE.findall(value.lower())
    return "-".join(tokens)


def _single_match(match: ApprovalPendingRef) -> ApprovalRefLookupResult:
    return ApprovalRefLookupResult(
        card_path=match.path,
        match=match,
        matches=(match,),
    )


def _resolve_number(
    raw: str,
    refs: tuple[ApprovalPendingRef, ...],
) -> ApprovalRefLookupResult:
    number = int(raw)
    for candidate in refs:
        if candidate.number == number:
            return _single_match(candidate)
    return ApprovalRefLookupResult(
        card_path=None,
        matches=refs,
        error=ApprovalServiceError(
            "number_not_found",
            f"pending 编号不存在：{raw}",
            exit_code=2,
        ),
    )


def _ambiguous(
    raw: str,
    matches: list[ApprovalPendingRef],
) -> ApprovalRefLookupResult:
    return ApprovalRefLookupResult(
        card_path=None,
        matches=tuple(matches),
        error=ApprovalServiceError(
            "ambiguous_ref",
            f"approve ref ambiguous: {raw}",
            exit_code=2,
        ),
    )


__all__ = [
    "ApprovalPendingRef",
    "ApprovalRefLookupResult",
    "build_pending_approval_refs",
    "build_pending_approval_refs_from_rows",
    "resolve_pending_approval_ref",
    "short_ref_for_card",
    "slugify",
]
