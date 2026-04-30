"""Review service：集中 weekly review 的复习业务聚合边界。

中文学习型说明：
本模块只负责把 Knowledge Card 的安全摘要聚合成结构化 weekly review 结果。
它不依赖 Typer/Rich/console，不负责 Markdown/JSON 渲染，不写卡片，不读取 `.env`，
不调用 LLM，也不改变 approval 状态。CLI 可以依赖本模块；本模块不能反向依赖 CLI。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .cards import CardLoadError, CardSummary, filter_cards, iter_cards
from .config import MindForgeConfig


@dataclass(frozen=True)
class WeeklyReviewWindow:
    """weekly review 的时间窗口。

    `week_start -> generated_at` 表示过去一周；`due_end` 表示未来 7 天到期；
    `preview_end` 保持 CLI 既有行为，用于下一周预览窗口（约未来 8-14 天）。
    """

    generated_at: datetime
    week_start: datetime
    due_end: datetime
    preview_end: datetime


@dataclass(frozen=True)
class FocusTrack:
    """纯计数 focus signal；不是 LLM 推荐，也不做语义推断。"""

    track: str
    score: int


@dataclass(frozen=True)
class ProjectCardCount:
    """项目分布计数，只来自 human_approved 卡片的 frontmatter projects 字段。"""

    project: str
    card_count: int


@dataclass(frozen=True)
class WeeklyReviewEmptyState:
    """weekly review 空状态的结构化原因，供 CLI 决定如何表达。"""

    reason: str
    approved_card_count: int
    has_draft_cards: bool


@dataclass(frozen=True)
class WeeklyReviewResult:
    """weekly review 的结构化结果；不包含任何渲染后的 Markdown/JSON 字符串。"""

    window: WeeklyReviewWindow
    approved_cards: tuple[CardSummary, ...]
    draft_cards_count: int
    overdue: tuple[CardSummary, ...]
    due_this_week: tuple[CardSummary, ...]
    reviewed_this_week: tuple[CardSummary, ...]
    forgotten_or_partial: tuple[CardSummary, ...]
    suggested_focus_tracks: tuple[FocusTrack, ...]
    project_distribution: tuple[ProjectCardCount, ...]
    next_week_preview: tuple[CardSummary, ...]
    scan_errors: tuple[CardLoadError, ...]
    empty_state: WeeklyReviewEmptyState | None

    @property
    def has_weekly_work(self) -> bool:
        return bool(
            self.overdue
            or self.due_this_week
            or self.reviewed_this_week
            or self.forgotten_or_partial
            or self.next_week_preview
        )


def calculate_weekly_review_window(now: datetime | None = None) -> WeeklyReviewWindow:
    """计算 weekly review 时间窗口。

    允许测试传入固定 `now`，生产路径默认使用本地 timezone-aware 当前时间。
    service 自己不读取配置、不读 env，也不写任何状态。
    """

    generated_at = now or datetime.now().astimezone()
    if generated_at.tzinfo is None:
        generated_at = generated_at.astimezone()
    return WeeklyReviewWindow(
        generated_at=generated_at,
        week_start=generated_at - timedelta(days=7),
        due_end=generated_at + timedelta(days=7),
        preview_end=generated_at + timedelta(days=14),
    )


def build_weekly_review(
    cfg: MindForgeConfig,
    *,
    now: datetime | None = None,
) -> WeeklyReviewResult:
    """聚合 weekly review 数据，默认只使用 `human_approved` 卡片。

    这是 review service 的核心边界：`ai_draft` 可以被计数为存在草稿，但绝不能
    进入 overdue/due/reviewed/focus/project distribution 等正式 review 数据。
    """

    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    approved = tuple(filter_cards(scan.cards, status="human_approved"))
    draft_count = sum(1 for card in scan.cards if card.status == "ai_draft")
    window = calculate_weekly_review_window(now)

    overdue: list[CardSummary] = []
    due_this_week: list[CardSummary] = []
    next_week_preview: list[CardSummary] = []
    forgotten_or_partial: list[CardSummary] = []
    reviewed_this_week: list[CardSummary] = []
    track_counts: dict[str, int] = {}
    project_counts: dict[str, int] = {}

    for card in approved:
        if card.review_after is not None:
            review_after = _align_tz(card.review_after, window.generated_at)
            if review_after <= window.generated_at:
                overdue.append(card)
            elif review_after <= window.due_end:
                due_this_week.append(card)
            elif review_after <= window.preview_end:
                next_week_preview.append(card)
        if card.reviewed_at is not None:
            reviewed_at = _align_tz(card.reviewed_at, window.generated_at)
            if reviewed_at >= window.week_start:
                reviewed_this_week.append(card)
        if card.last_review_result in ("partial", "forgotten"):
            forgotten_or_partial.append(card)
        if card.track:
            track_counts[card.track] = track_counts.get(card.track, 0) + 1
        for project in card.projects:
            project_counts[project] = project_counts.get(project, 0) + 1

    suggested_focus = _suggest_focus_tracks(overdue + due_this_week, forgotten_or_partial)
    project_distribution = tuple(
        ProjectCardCount(project=project, card_count=count)
        for project, count in sorted(project_counts.items(), key=lambda item: -item[1])
    )

    empty_state = _build_empty_state(
        approved_card_count=len(approved),
        draft_cards_count=draft_count,
        has_weekly_work=bool(
            overdue
            or due_this_week
            or reviewed_this_week
            or forgotten_or_partial
            or next_week_preview
        ),
    )

    return WeeklyReviewResult(
        window=window,
        approved_cards=approved,
        draft_cards_count=draft_count,
        overdue=tuple(overdue),
        due_this_week=tuple(due_this_week),
        reviewed_this_week=tuple(reviewed_this_week),
        forgotten_or_partial=tuple(forgotten_or_partial),
        suggested_focus_tracks=suggested_focus,
        project_distribution=project_distribution,
        next_week_preview=tuple(next_week_preview),
        scan_errors=scan.errors,
        empty_state=empty_state,
    )


def _suggest_focus_tracks(
    due_cards: list[CardSummary],
    forgotten_or_partial: list[CardSummary],
) -> tuple[FocusTrack, ...]:
    """按 backlog + forgotten 计数生成 focus signal；不做语义推断。"""

    focus_score: dict[str, int] = {}
    for card in due_cards:
        if card.track:
            focus_score[card.track] = focus_score.get(card.track, 0) + 1
    for card in forgotten_or_partial:
        if card.track:
            focus_score[card.track] = focus_score.get(card.track, 0) + 2
    return tuple(
        FocusTrack(track=track, score=score)
        for track, score in sorted(focus_score.items(), key=lambda item: -item[1])[:5]
    )


def _build_empty_state(
    *,
    approved_card_count: int,
    draft_cards_count: int,
    has_weekly_work: bool,
) -> WeeklyReviewEmptyState | None:
    if has_weekly_work:
        return None
    if approved_card_count == 0 and draft_cards_count > 0:
        reason = "only_ai_draft_cards"
    elif approved_card_count == 0:
        reason = "no_approved_cards"
    else:
        reason = "no_weekly_review_work"
    return WeeklyReviewEmptyState(
        reason=reason,
        approved_card_count=approved_card_count,
        has_draft_cards=draft_cards_count > 0,
    )


def _align_tz(value: datetime, reference: datetime) -> datetime:
    """把 naive frontmatter datetime 对齐到本次 review 的 timezone。"""

    if value.tzinfo is None:
        return value.replace(tzinfo=reference.tzinfo)
    return value


__all__ = [
    "FocusTrack",
    "ProjectCardCount",
    "WeeklyReviewEmptyState",
    "WeeklyReviewResult",
    "WeeklyReviewWindow",
    "build_weekly_review",
    "calculate_weekly_review_window",
]
