"""Review Typer adapter.

中文学习型说明：review 命令族只消费 human_approved frontmatter 安全字段；
``mark`` 是唯一写 review 字段的入口，weekly 的结构化聚合在 review_service，
展示在 review_presenter。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import typer

from .cli_cards import card_to_safe_dict as _card_to_safe_dict
from .cli_cards import filters_dict as _filters_dict
from .cli_cards import safe_date as _safe_date
from .cli_runtime import console, load_cfg
from .run_logger import RunLogger

review_app = typer.Typer(add_completion=False, help="复习候选与标记（M4）")

# ---------------------------------------------------------------------------
# review due
# ---------------------------------------------------------------------------


@review_app.command("due")
def review_due(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    limit: int = typer.Option(10, "--limit"),
    track: str | None = typer.Option(None, "--track"),
    project: str | None = typer.Option(None, "--project"),
    include_drafts: bool = typer.Option(False, "--include-drafts"),
    include_missing_review_after: bool = typer.Option(
        False,
        "--include-missing-review-after",
        help="把从未 review 过的卡片也列入候选",
    ),
    output_format: str = typer.Option(
        "markdown", "--format", help="markdown | json"
    ),
) -> None:
    """列出到期 / 接近到期的复习候选（默认仅 human_approved）。"""
    from .cards import filter_cards, iter_cards

    cfg = load_cfg(config, read_env=False)
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    base = filter_cards(
        scan.cards,
        track=track,
        project=project,
        status="human_approved",
        include_drafts=include_drafts,
    )
    now = datetime.now().astimezone()
    due: list = []
    for c in base:
        if c.review_after is None:
            if include_missing_review_after:
                due.append(c)
            continue
        # 比较时统一用 timezone-aware
        ra = c.review_after
        if ra.tzinfo is None:
            ra = ra.replace(tzinfo=now.tzinfo)
        if ra <= now:
            due.append(c)
    # 排序
    def _k(c):  # type: ignore[no-untyped-def]
        has_after = 0 if c.review_after is not None else 1
        ra = c.review_after or datetime.max.replace(tzinfo=now.tzinfo)
        return (has_after, ra, -(c.value_score or 0), c.id or c.path.name)

    due.sort(key=_k)
    due = due[:limit]

    with RunLogger(cfg.state.runs_path, command="review-due") as logger:  # type: ignore[attr-defined]
        logger.emit(
            "review_due_listed",
            count=len(due),
            filters=_filters_dict(
                track=track,
                project=project,
                include_drafts=include_drafts,
                include_missing_review_after=include_missing_review_after,
                limit=limit,
            ),
            output_format=output_format,
        )

    if output_format == "json":
        import json as _json

        print(_json.dumps(
            {
                "version": 1,
                "count": len(due),
                "items": [_card_to_safe_dict(c) for c in due],
            },
            ensure_ascii=False,
            indent=2,
        ))
        return

    if not due:
        console.print("[yellow]当前没有到期复习候选。[/yellow]")
        return
    console.print(f"[bold]Review Due[/bold] · {len(due)} 项")
    for c in due:
        console.print(
            f"- [{c.id or c.path.stem}] {c.title or '(untitled)'} · "
            f"track={c.track or '-'} · review_after={_safe_date(c.review_after)} · "
            f"value_score={c.value_score if c.value_score is not None else '-'}"
        )


# ---------------------------------------------------------------------------
# review mark
# ---------------------------------------------------------------------------


@review_app.command("mark")
def review_mark(
    card: Path = typer.Option(..., "--card"),
    result: str = typer.Option(..., "--result", help="remembered | partial | forgotten"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只打印将写入的字段，不修改卡片"),
    note: str | None = typer.Option(None, "--note", help="可选 review note；仅写入 frontmatter 的 last_review_note 字段，绝不写入 body"),
) -> None:
    """记录一次 review 结果到卡片 frontmatter（4-5 字段写入）。

    v0.4 增量：
    - ``--dry-run``：只打印将写入字段，**不**修改文件；
    - ``--note``：可选简短 note，写入 frontmatter ``last_review_note``，
      **绝不**插入卡片 body（避免污染 AI/Human 写作区）。
    """
    from .reviewer import ReviewError, mark_card_review

    cfg = load_cfg(config, read_env=False)
    with RunLogger(cfg.state.runs_path, command="review-mark") as logger:  # type: ignore[attr-defined]
        logger.emit(
            "review_mark_started", card_path=str(card), result=result,
            filters=_filters_dict(dry_run=dry_run, note_provided=note is not None),
        )
        try:
            outcome = mark_card_review(card, result, cfg=cfg, dry_run=dry_run, note=note)
        except ReviewError as e:
            logger.emit(
                "review_mark_failed",
                card_path=str(card),
                error_message=str(e),
                result=result,
            )
            console.print(f"[red]review mark 失败：{e}[/red]")
            raise typer.Exit(code=e.exit_code) from e
        logger.emit(
            "review_mark_completed",
            card_path=str(outcome.card_path),
            result=outcome.result,
            prev_review_count=outcome.prev_review_count,
            new_review_count=outcome.new_review_count,
            review_after=outcome.review_after.isoformat(),
            filters=_filters_dict(dry_run=dry_run, note_provided=note is not None),
        )
    prefix = "[yellow]DRY-RUN[/yellow] would mark" if dry_run else "[green]✔ reviewed[/green]"
    console.print(
        f"{prefix} {outcome.card_path}  "
        f"(result={outcome.result}, count: {outcome.prev_review_count} → "
        f"{outcome.new_review_count}, next_review_after={_safe_date(outcome.review_after)})"
    )


# ---------------------------------------------------------------------------
# v0.4 review scheduling MVP — 本地复习计划，不是后台调度
# ---------------------------------------------------------------------------


def _bucket_review(c, *, now: datetime) -> str:
    """v0.4：把卡片按 review_after 分到 overdue / today / upcoming / missing。

    - 没有 review_after → ``missing``
    - review_after <= now            → ``overdue``
    - review_after 在今天（同一日历日）→ ``today``
    - 否则 → ``upcoming``

    时区处理：CardSummary.review_after 可能 naive；统一对齐到 ``now`` 的 tzinfo。
    """
    if c.review_after is None:
        return "missing"
    ra = c.review_after
    if ra.tzinfo is None:
        ra = ra.replace(tzinfo=now.tzinfo)
    if ra <= now:
        return "overdue"
    if ra.date() == now.date():
        return "today"
    return "upcoming"


@review_app.command("schedule")
def review_schedule(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    days: int = typer.Option(7, "--days", min=1, max=365, help="未来 N 天计划（默认 7）"),
    track: str | None = typer.Option(None, "--track"),
    project: str | None = typer.Option(None, "--project"),
    include_missing_review_after: bool = typer.Option(
        False, "--include-missing-review-after",
        help="把从未 review 过的 human_approved 卡片也纳入计划（按今天）",
    ),
    output_format: str = typer.Option("markdown", "--format", help="markdown | json | ical"),
    output_path: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    """生成未来 N 天的本地复习计划，按日期分组。

    设计强约束（请勿放宽）：
    - **本地纯计算**：不调 LLM，不读 .env，不发 HTTP，不修改卡片；
    - **不**是后台任务 / 系统提醒；只是把"哪天该复习哪些卡片"写到 stdout 或 --output；
    - 默认仅 ``status: human_approved``；过期卡片归到"今天"分桶（避免被忘掉）；
    - ``--format ical`` 只是**生成本地 .ics 文件**，**不**接系统日历、**不**请求权限、
      **不**联网；用户可手动导入 macOS Calendar / Outlook / Google Calendar，
      但导入与否完全由用户决定。
    """
    from .cards import filter_cards, iter_cards

    cfg = load_cfg(config, read_env=False)
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    base = filter_cards(scan.cards, track=track, project=project, status="human_approved")
    now = datetime.now().astimezone()
    horizon = now + timedelta(days=days)

    # 按日期分组：date -> list[card]
    by_day: dict[str, list] = {}
    for c in base:
        if c.review_after is None:
            if include_missing_review_after:
                by_day.setdefault(now.date().isoformat(), []).append(c)
            continue
        ra = c.review_after
        if ra.tzinfo is None:
            ra = ra.replace(tzinfo=now.tzinfo)
        # overdue → 归到今天（必须复习）
        if ra <= now:
            by_day.setdefault(now.date().isoformat(), []).append(c)
            continue
        if ra > horizon:
            continue
        by_day.setdefault(ra.date().isoformat(), []).append(c)

    days_sorted = sorted(by_day.items())
    total = sum(len(v) for v in by_day.values())

    with RunLogger(cfg.state.runs_path, command="review-schedule") as logger:  # type: ignore[attr-defined]
        logger.emit(
            "review_due_listed",
            count=total,
            filters=_filters_dict(
                track=track, project=project, schedule_days=days,
                include_missing_review_after=include_missing_review_after,
            ),
            output_format=output_format,
        )

    if output_format == "ical":
        # v0.4.1 — 本地 iCalendar 导出。**纯文本生成**，不接系统日历、不联网。
        # 每张待复习卡片 = 一个 VEVENT；description 仅含安全摘要 + path。
        ics = _render_ics(days_sorted, generated_at=now, horizon_days=days)
        if output_path:
            output_path.write_text(ics, encoding="utf-8")
            console.print(f"[green]✓[/green] 已写入 {output_path}")
        else:
            print(ics)
        return

    if output_format == "json":
        import json as _json
        payload = _json.dumps({
            "version": 1,
            "horizon_days": days,
            "generated_at": now.isoformat(timespec="seconds"),
            "total": total,
            "days": [
                {"date": d, "count": len(items), "items": [_card_to_safe_dict(c) for c in items]}
                for d, items in days_sorted
            ],
        }, ensure_ascii=False, indent=2)
        if output_path:
            output_path.write_text(payload + "\n", encoding="utf-8")
            console.print(f"[green]✓[/green] 已写入 {output_path}")
        else:
            print(payload)
        return

    # markdown
    lines = [f"# Review Schedule · 未来 {days} 天 · {total} 项\n",
             f"_generated_at: {now.isoformat(timespec='seconds')}_\n"]
    if not days_sorted:
        lines.append("\n_(没有需要复习的卡片)_\n")
    for d, items in days_sorted:
        lines.append(f"\n## {d} · {len(items)} 项\n")
        for c in items:
            lines.append(
                f"- [{c.id or c.path.stem}] {c.title or '(untitled)'}  "
                f"`track={c.track or '-'}` `value_score={c.value_score if c.value_score is not None else '-'}`  "
                f"`path={c.rel_path}`"
            )
    out = "\n".join(lines) + "\n"
    if output_path:
        output_path.write_text(out, encoding="utf-8")
        console.print(f"[green]✓[/green] 已写入 {output_path}")
    else:
        print(out)


@review_app.command("backlog")
def review_backlog(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    track: str | None = typer.Option(None, "--track"),
    project: str | None = typer.Option(None, "--project"),
    limit: int = typer.Option(50, "--limit"),
    output_format: str = typer.Option("markdown", "--format", help="markdown | json"),
) -> None:
    """展示复习 backlog：overdue / today / upcoming / missing 四桶。

    与 ``review schedule`` 的差异：
    - schedule 关注"未来 N 天的计划"；
    - backlog 关注"当前积压"，把 overdue / missing 当成第一公民。
    """
    from .cards import filter_cards, iter_cards

    cfg = load_cfg(config, read_env=False)
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    base = filter_cards(scan.cards, track=track, project=project, status="human_approved")
    now = datetime.now().astimezone()

    buckets: dict[str, list] = {"overdue": [], "today": [], "upcoming": [], "missing": []}
    for c in base:
        buckets[_bucket_review(c, now=now)].append(c)
    # 限流并稳定排序
    for k, lst in buckets.items():
        lst.sort(key=lambda c: (
            c.review_after or datetime.max.replace(tzinfo=now.tzinfo),
            -(c.value_score or 0),
            c.id or c.path.name,
        ))
        buckets[k] = lst[:limit]

    total = sum(len(v) for v in buckets.values())

    with RunLogger(cfg.state.runs_path, command="review-backlog") as logger:  # type: ignore[attr-defined]
        logger.emit(
            "review_due_listed",
            count=total,
            filters=_filters_dict(track=track, project=project, limit=limit),
            output_format=output_format,
        )

    if output_format == "json":
        import json as _json
        print(_json.dumps({
            "version": 1,
            "generated_at": now.isoformat(timespec="seconds"),
            "total": total,
            "buckets": {
                k: {"count": len(items), "items": [_card_to_safe_dict(c) for c in items]}
                for k, items in buckets.items()
            },
        }, ensure_ascii=False, indent=2))
        return

    print(f"# Review Backlog · {total} 项")
    for label, key in (("⚠ Overdue", "overdue"), ("Today", "today"),
                       ("Upcoming", "upcoming"), ("Missing review_after", "missing")):
        items = buckets[key]
        print(f"\n## {label} · {len(items)} 项")
        if not items:
            print("_(none)_")
            continue
        for c in items:
            print(
                f"- [{c.id or c.path.stem}] {c.title or '(untitled)'}  "
                f"`review_after={_safe_date(c.review_after)}` "
                f"`reviews={c.review_count}` "
                f"`last={c.last_review_result or '-'}`  "
                f"`track={c.track or '-'}` `path={c.rel_path}`"
            )


@review_app.command("stats")
def review_stats(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    as_json: bool = typer.Option(False, "--json", help="机器可读输出"),
) -> None:
    """复习统计：总数 / overdue / today / upcoming(7d) / missing / 已 review 数 /
    平均 review 次数 / 结果分布（remembered/partial/forgotten）。

    全程纯统计，**不**修改卡片，**不**触发 LLM。
    """
    from .cards import filter_cards, iter_cards

    cfg = load_cfg(config, read_env=False)
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    base = filter_cards(scan.cards, status="human_approved")
    now = datetime.now().astimezone()
    horizon = now + timedelta(days=7)

    overdue = today = upcoming_7 = missing = reviewed = 0
    counts_sum = 0
    breakdown: dict[str, int] = {"remembered": 0, "partial": 0, "forgotten": 0}
    for c in base:
        b = _bucket_review(c, now=now)
        if b == "overdue":
            overdue += 1
        elif b == "today":
            today += 1
        elif b == "missing":
            missing += 1
        else:
            ra = c.review_after.replace(tzinfo=now.tzinfo) if c.review_after and c.review_after.tzinfo is None else c.review_after
            if ra and ra <= horizon:
                upcoming_7 += 1
        if c.review_count > 0:
            reviewed += 1
            counts_sum += c.review_count
        if c.last_review_result in breakdown:
            breakdown[c.last_review_result] += 1

    avg = round(counts_sum / reviewed, 2) if reviewed else 0.0

    with RunLogger(cfg.state.runs_path, command="review-stats") as logger:  # type: ignore[attr-defined]
        logger.emit("review_due_listed", count=len(base), output_format="json" if as_json else "compact")

    payload = {
        "version": 1,
        "generated_at": now.isoformat(timespec="seconds"),
        "total_human_approved": len(base),
        "due_today": today,
        "overdue": overdue,
        "upcoming_7_days": upcoming_7,
        "missing_review_after": missing,
        "reviewed_count": reviewed,
        "average_review_count": avg,
        "result_breakdown": breakdown,
    }
    if as_json:
        import json as _json
        print(_json.dumps(payload, ensure_ascii=False, indent=2))
        return
    console.print(f"[bold]Review Stats[/bold] · human_approved={len(base)}")
    console.print(f"  overdue            : {overdue}")
    console.print(f"  due_today          : {today}")
    console.print(f"  upcoming_7_days    : {upcoming_7}")
    console.print(f"  missing_review_after: {missing}")
    console.print(f"  reviewed_count     : {reviewed}")
    console.print(f"  average_reviews    : {avg}")
    console.print(
        f"  results            : remembered={breakdown['remembered']} "
        f"partial={breakdown['partial']} forgotten={breakdown['forgotten']}"
    )


# ---------------------------------------------------------------------------
# v0.4.1 — review weekly + iCal helpers
# ---------------------------------------------------------------------------


def _ics_escape(s: str) -> str:
    """RFC 5545 §3.3.11 文本转义：\\ , ; 与换行。"""
    return (
        (s or "")
        .replace("\\", "\\\\")
        .replace(",", "\\,")
        .replace(";", "\\;")
        .replace("\n", "\\n")
        .replace("\r", "")
    )


def _render_ics(days_sorted: list, *, generated_at: datetime, horizon_days: int) -> str:
    """生成 RFC 5545 极简 .ics 文本。

    设计契约：
    - **完全本地纯文本生成**；不调任何系统 API、不联网、不读 .env；
    - 每张待复习卡片 → 一个 VEVENT（全天事件）；
    - SUMMARY 仅含 card title（来自 frontmatter，安全字段）；
    - DESCRIPTION 仅含 ``track / value_score / path``——绝不含 raw_text /
      Source Excerpt / Human Note / prompt / completion / api_key；
    - UID 用 ``card.id@mindforge.local`` 保证多次导出去重。
    """
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//MindForge//Review Schedule//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:MindForge Review (next {horizon_days}d)",
    ]
    dtstamp = generated_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for date_str, items in days_sorted:
        date_compact = date_str.replace("-", "")
        next_date_compact = (
            datetime.fromisoformat(date_str) + timedelta(days=1)
        ).strftime("%Y%m%d")
        for c in items:
            uid = f"{c.id or c.path.stem}@mindforge.local"
            summary = _ics_escape(f"Review: {c.title or '(untitled)'}")
            desc = _ics_escape(
                f"track={c.track or '-'}\n"
                f"value_score={c.value_score if c.value_score is not None else '-'}\n"
                f"path={c.rel_path}"
            )
            lines += [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{dtstamp}",
                f"DTSTART;VALUE=DATE:{date_compact}",
                f"DTEND;VALUE=DATE:{next_date_compact}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{desc}",
                "STATUS:CONFIRMED",
                "TRANSP:TRANSPARENT",
                "END:VEVENT",
            ]
    lines.append("END:VCALENDAR")
    # RFC 5545 推荐 CRLF
    return "\r\n".join(lines) + "\r\n"


@review_app.command("weekly")
def review_weekly(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    output_format: str = typer.Option("markdown", "--format", help="markdown | json"),
    output_path: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    """生成本周复习 / 学习状态周报。

    设计契约（务必守住）：
    - **不调 LLM**：所有 section 都是 frontmatter 的结构化汇总；
    - **不**写卡片；
    - 仅引用 frontmatter 安全字段：title / track / projects / value_score /
      review_after / review_count / last_review_result；
    - "suggested_focus_tracks" 只是按 backlog + forgotten 计数排序，
      **不**做语义推断、**不**预测下周。
    """
    from .review_presenter import (
        build_weekly_review_json,
        render_weekly_review_markdown,
    )
    from .review_service import build_weekly_review

    cfg = load_cfg(config, read_env=False)
    result = build_weekly_review(cfg)

    with RunLogger(cfg.state.runs_path, command="review-weekly") as logger:  # type: ignore[attr-defined]
        logger.emit(
            "review_due_listed",
            count=len(result.overdue) + len(result.due_this_week),
            output_format=output_format,
        )

    if output_format == "json":
        import json as _json
        payload = _json.dumps(
            build_weekly_review_json(result),
            ensure_ascii=False,
            indent=2,
        )
        if output_path:
            output_path.write_text(payload + "\n", encoding="utf-8")
            console.print(f"[green]✓[/green] 已写入 {output_path}")
        else:
            print(payload)
        return

    out = render_weekly_review_markdown(result)
    if output_path:
        output_path.write_text(out, encoding="utf-8")
        console.print(f"[green]✓[/green] 已写入 {output_path}")
    else:
        print(out)


def _review_learning_tasks(
    overdue: list,
    due_this_week: list,
    forgotten_or_partial: list,
) -> str:
    """薄包装：委托 ``review_presenter.render_weekly_learning_tasks``。

    保留是为了向后兼容（如果有其他模块或 helper 引用此符号）。本函数
    自身**不**包含业务，唯一作用是 forward 到 presenter。未来一轮可
    彻底删除。
    """
    from .review_presenter import render_weekly_learning_tasks

    return render_weekly_learning_tasks(overdue, due_this_week, forgotten_or_partial)


def _review_next_actions(has_weekly_work: bool) -> list[str]:
    """薄包装：委托 ``review_presenter.render_weekly_next_actions``。

    保留向后兼容；本函数自身**不**包含业务，唯一作用是 forward 到
    presenter。未来一轮可彻底删除。
    """
    from .review_presenter import render_weekly_next_actions

    return render_weekly_next_actions(has_weekly_work)
