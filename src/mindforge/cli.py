"""mindforge — 命令行入口（typer）。

v0.1 当前命令：
- ``mindforge scan``    — 扫描 inbox，派发到 adapter，更新 state.json；不调 LLM。
- ``mindforge process`` — 跑 5 stage pipeline，写入 Knowledge Card。
- ``mindforge status``  — 打印 state.json 的状态汇总（按 status / source_type）。
- ``mindforge llm ping``— 只校验 active_profile 涉及的模型 env 是否齐全，不发 HTTP。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .checkpoint import Checkpoint
from .config import ConfigError, MindForgeConfig, load_mindforge_config
from .env_loader import load_dotenv_silently
from .llm import LLMClient, build_providers
from .models import ItemState, StageRecord
from .processors import Pipeline
from .run_logger import (
    EVENT_SOURCE_ERROR,
    EVENT_SOURCE_SEEN,
    EVENT_SOURCE_SKIPPED_OR_UNCHANGED,
    EVENT_STATE_WRITTEN,
    EVENT_STATUS_REPORTED,
    RunLogger,
    summarize_latest_run,
)
from .scanner import Scanner
from .writer import CardWriter

app = typer.Typer(
    add_completion=True,
    help=(
        "MindForge — 多源接入的本地 AI 知识加工管线。\n\n"
        "常用命令：\n"
        "  scan / process / status      — 把 inbox 文件加工成 Knowledge Cards\n"
        "  approve --card <path>        — 把 ai_draft 卡片晋升为 human_approved\n"
        "  recall / review due          — 检索与复习已审核卡片\n"
        "  project context <name> [...] — 拼装可粘贴给编程助手的项目上下文包\n"
        "  project update-evidence <n>  — 幂等写入 30-Projects/<n>.md 受控区块\n"
        "  telemetry status / summary   — 查看本地命令使用统计（不上传）\n"
        "  llm ping                     — 校验 LLM provider env（不发 HTTP）\n"
        "  version                      — 打印版本与运行配置摘要（不含 secret）\n"
    ),
    pretty_exceptions_enable=False,  # 默认抑制 traceback；--debug 时由 main() 重新放开
)
llm_app = typer.Typer(add_completion=False, help="LLM provider 工具子命令（不触发业务 pipeline）")
app.add_typer(llm_app, name="llm")
console = Console()


# ---------------------------------------------------------------------------
# 全局 --debug 回调：仅设置 env，由 main() 决定是否打印 traceback
# 选用 env 而非全局变量是为了：1) 跨进程友好；2) helper 可直接 os.environ 检查。
# ---------------------------------------------------------------------------


@app.callback()
def _global_options(
    debug: bool = typer.Option(
        False,
        "--debug",
        help="出错时打印完整 traceback；默认仅打印简短错误信息。",
    ),
    vault: Path | None = typer.Option(
        None,
        "--vault",
        help="临时覆盖配置中的 vault.root（不修改 yaml）。优先级：CLI > config > 默认。",
    ),
) -> None:
    """全局选项。

    --debug 与 --vault 都通过 env 透传，避免与子命令的 typer.Context 耦合。
    """
    import os

    if debug:
        os.environ["MINDFORGE_DEBUG"] = "1"
    else:
        os.environ.pop("MINDFORGE_DEBUG", None)
    if vault is not None:
        # 写绝对路径，避免 cwd 漂移
        os.environ["MINDFORGE_VAULT_OVERRIDE"] = str(vault.expanduser().resolve())
    else:
        # 重要：每次 CLI 调用未传 --vault 时必须清空，避免跨调用污染
        # （测试套尤其敏感；一次性 CLI 用户感知不到）
        os.environ.pop("MINDFORGE_VAULT_OVERRIDE", None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_cfg(config_path: Path) -> MindForgeConfig:
    # 入口处加载 .env（静默，不打印 value，env > dotfile）
    load_dotenv_silently(Path.cwd())
    if not config_path.exists():
        console.print(f"[red]✗ 配置文件不存在：{config_path}[/red]")
        console.print(
            "[dim]提示：可以从仓库中的 configs/mindforge.yaml 复制一份到目标位置，"
            "再用 --config 指定，或直接在仓库根运行命令。[/dim]"
        )
        raise typer.Exit(code=2)
    try:
        cfg = load_mindforge_config(config_path)
    except ConfigError as e:
        console.print(f"[red]✗ 配置错误：{e}[/red]")
        console.print(
            "[dim]提示：请检查 vault.root、sources.enabled、llm.active_profile "
            "三个字段是否合法。[/dim]"
        )
        raise typer.Exit(code=2) from e

    # ── --vault override（CLI > config）─────────────────────────────────
    # 仅替换 vault.root，其他子字段（inbox_root / cards_dir / projects_dir）保留。
    # 这样用户可以"同一份 yaml + 不同 vault"复用，无需复制配置。
    import os as _os
    from dataclasses import replace as _replace

    override = _os.environ.get("MINDFORGE_VAULT_OVERRIDE")
    if override:
        new_vault = _replace(cfg.vault, root=Path(override))
        cfg = _replace(cfg, vault=new_vault)
    return cfg


def _override_active_profile(cfg: MindForgeConfig, profile: str | None) -> MindForgeConfig:
    """如果 CLI 传了 --profile，就基于现有 cfg 派生一份临时 LLMConfig。

    不修改 yaml；只影响本次进程。失败时友好报错。
    """
    if not profile:
        return cfg
    if profile not in cfg.llm.profiles:
        console.print(
            f"[red]--profile {profile!r} 不在 llm.profiles 中；"
            f"已知：{sorted(cfg.llm.profiles)}[/red]"
        )
        raise typer.Exit(code=2)
    from dataclasses import replace
    new_llm = replace(cfg.llm, active_profile=profile)
    return replace(cfg, llm=new_llm)


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------


@app.command()
def scan(
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="mindforge.yaml 路径",
    ),
    write_state: bool = typer.Option(
        True,
        "--write-state/--no-write-state",
        help="是否把扫描结果写入 state.json（默认写入）",
    ),
) -> None:
    """扫描 inbox 目录，把每个文件解析为 SourceDocument 并登记到 state.json。"""
    cfg = _load_cfg(config)
    scanner = Scanner(cfg)  # type: ignore[arg-type]
    cp = Checkpoint.load(cfg.state.state_path, backup=cfg.state.backup_state)  # type: ignore[attr-defined]

    seen = 0
    new_or_changed = 0
    failed = 0
    table = Table(title="MindForge scan", show_lines=False)
    table.add_column("source_type")
    table.add_column("path", overflow="fold")
    table.add_column("status")
    table.add_column("hash", overflow="fold")

    with RunLogger(cfg.state.runs_path, command="scan") as logger:  # type: ignore[attr-defined]
        for result in scanner.iter_results():
            seen += 1
            if not result.ok:
                failed += 1
                table.add_row(
                    result.source_type,
                    str(result.path),
                    "[red]failed[/red]",
                    result.error or "",
                )
                logger.emit(
                    EVENT_SOURCE_ERROR,
                    source_type=result.source_type,
                    adapter_name=result.adapter_name,
                    path=str(result.path),
                    error_message=result.error or "",
                )
                continue

            doc = result.document
            assert doc is not None
            candidate = ItemState(
                source_id=doc.source_id,
                source_type=doc.source_type,
                adapter_name=result.adapter_name,
                source_path=doc.source_path,
                content_hash=doc.content_hash,
                first_seen_at=datetime.now(),
            )
            existing = cp.get(doc.source_type, doc.source_path)
            before_hash = existing.content_hash if existing else None
            merged = cp.upsert_seen(candidate)
            changed = before_hash != merged.content_hash or existing is None
            if changed:
                new_or_changed += 1
                label = "[green]new/changed[/green]"
                logger.emit(
                    EVENT_SOURCE_SEEN,
                    source_id=merged.source_id,
                    source_type=merged.source_type,
                    adapter_name=merged.adapter_name,
                    source_path=merged.source_path,
                    content_hash=merged.content_hash,
                    status=merged.status,
                )
            else:
                label = "unchanged"
                logger.emit(
                    EVENT_SOURCE_SKIPPED_OR_UNCHANGED,
                    source_id=merged.source_id,
                    source_type=merged.source_type,
                    adapter_name=merged.adapter_name,
                    source_path=merged.source_path,
                    content_hash=merged.content_hash,
                    status=merged.status,
                )
            table.add_row(doc.source_type, doc.source_path, label, doc.content_hash[:18] + "...")

        console.print(table)
        console.print(
            f"扫描完成：共 [bold]{seen}[/bold] 个文件，"
            f"新增/变更 [green]{new_or_changed}[/green]，失败 [red]{failed}[/red]"
        )

        if write_state:
            cp.save(active_profile=cfg.llm.active_profile)  # type: ignore[attr-defined]
            console.print(f"已写入 state.json → {cfg.state.state_path}")  # type: ignore[attr-defined]
            logger.emit(
                EVENT_STATE_WRITTEN,
                path=str(cfg.state.state_path),  # type: ignore[attr-defined]
                items_count=len(list(cp.all_items())),
            )
        else:
            console.print("[yellow]--no-write-state：state.json 未写入[/yellow]")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


@app.command()
def status(
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="mindforge.yaml 路径",
    ),
) -> None:
    """打印 state.json 的当前状态汇总。"""
    cfg = _load_cfg(config)
    cp = Checkpoint.load(cfg.state.state_path)  # type: ignore[attr-defined]

    items = list(cp.all_items())
    by_status = cp.count_by_status()
    by_source = cp.count_by_source_type()

    with RunLogger(cfg.state.runs_path, command="status") as logger:  # type: ignore[attr-defined]
        logger.emit(
            EVENT_STATUS_REPORTED,
            path=str(cfg.state.state_path),  # type: ignore[attr-defined]
            items_count=len(items),
            counts={"by_status": dict(by_status), "by_source_type": dict(by_source)},
            active_profile=cp.active_profile or "",
        )

    console.print(f"[bold]MindForge status[/bold] · active_profile={cp.active_profile or '(unset)'}")
    console.print(f"state.json: {cfg.state.state_path}")  # type: ignore[attr-defined]
    console.print(f"runs dir : {cfg.state.runs_path}")  # type: ignore[attr-defined]
    console.print(f"items 总数：{len(items)}")

    # 最近一次 run 摘要（非敏感字段）
    summary = summarize_latest_run(cfg.state.runs_path)  # type: ignore[attr-defined]
    if summary is None:
        console.print("[yellow]最近一次 run：(无)[/yellow]")
    else:
        flag = "[red]failed[/red]" if summary.failed else "[green]ok[/green]"
        console.print(
            f"最近一次 run · {flag} · cmd=[bold]{summary.command or '?'}[/bold] · "
            f"run_id={summary.run_id} · events={summary.event_count} · "
            f"started={summary.started_at} · last={summary.last_event}@{summary.last_event_at}"
        )
        console.print(f"  log: {summary.path}")

    if not items:
        console.print("[yellow]state.json 为空。先运行 `mindforge scan`。[/yellow]")
        return

    t1 = Table(title="按 status 分布")
    t1.add_column("status")
    t1.add_column("count", justify="right")
    for k in sorted(by_status):
        t1.add_row(k, str(by_status[k]))
    console.print(t1)

    t2 = Table(title="按 source_type 分布")
    t2.add_column("source_type")
    t2.add_column("count", justify="right")
    for k in sorted(by_source):
        t2.add_row(k, str(by_source[k]))
    console.print(t2)

    # ai_draft 提醒（v0.1 反污染机制）
    drafts = [i for i in items if i.status == "processed"]
    if drafts:
        console.print(
            f"[yellow]提示：{len(drafts)} 张卡片仍处于 processed (ai_draft) 状态，"
            "审核后请把 frontmatter 的 status 改为 human_approved。[/yellow]"
        )


# ---------------------------------------------------------------------------
# approve — M3 反 AI 污染闸门：显式人工把 ai_draft 卡片晋升为 human_approved
# 详见 docs/M3_HUMAN_APPROVAL_PROTOCOL.md
# ---------------------------------------------------------------------------


approve_app = typer.Typer(
    no_args_is_help=False,
    help=(
        "把 Knowledge Card 从 ai_draft 显式晋升为 human_approved。\n\n"
        "为什么 approve 必须是显式人工动作：\n"
        "  - long-term memory 的入口；批准的卡片会进入 recall / project context 的"
        "正式输出，会被复用到多个项目，影响后续判断。\n"
        "  - 如果允许 LLM 自动 approve，AI 误差会被无限放大；MindForge 的"
        "差异化前提之一就是 source-grounded + human-approved。\n\n"
        "常用：\n"
        "  approve --card <path>     — 单卡晋升（最安全主路径）\n"
        "  approve --source-id <id>  — 基于 state.json 反查卡片再晋升\n"
        "  approve list              — 列出可 approve 的 ai_draft 卡片（安全摘要）\n"
        "  approve --all --dry-run   — 预览批量晋升（不写文件）\n"
    ),
)
app.add_typer(approve_app, name="approve")


def _do_single_approve(
    card_path: Path,
    cfg: MindForgeConfig,
) -> None:
    """单卡晋升执行体（callback / source-id 路径共用）。"""
    from .approver import ApprovalError, approve_card

    with RunLogger(cfg.state.runs_path, command="approve") as logger:  # type: ignore[attr-defined]
        logger.emit("approval_started", card_path=str(card_path))
        try:
            outcome = approve_card(card_path, cfg=cfg)
        except ApprovalError as e:
            logger.emit(
                "approval_failed",
                card_path=str(card_path),
                error_message=str(e),
                prev_status=e.prev_status or "",
            )
            console.print(f"[red]approve 失败：{e}[/red]")
            raise typer.Exit(code=e.exit_code) from e

        completed_fields: dict[str, object] = {
            "card_path": str(outcome.card_path),
            "status": outcome.new_status,
            "prev_status": outcome.prev_status,
            "approval_method": outcome.approval_method,
            "idempotent": outcome.kind == "already_approved",
        }
        if outcome.approved_at is not None:
            completed_fields["approved_at"] = outcome.approved_at.isoformat()
        if outcome.state_missing:
            completed_fields["state_missing"] = True
        logger.emit("approval_completed", **completed_fields)

    if outcome.kind == "already_approved":
        console.print(
            f"[yellow]已是 human_approved（幂等）：{outcome.card_path}[/yellow]"
        )
    else:
        console.print(
            f"[green]✔ approved[/green] {outcome.card_path}  "
            f"(prev={outcome.prev_status} → {outcome.new_status}, "
            f"method={outcome.approval_method})"
        )
        if outcome.state_missing:
            console.print(
                "[yellow]注意：state.json 中找不到对应 item，仅更新了卡片文件。[/yellow]"
            )


@approve_app.callback(invoke_without_command=True)
def approve(
    ctx: typer.Context,
    card: Path | None = typer.Option(
        None,
        "--card",
        help="要晋升的 Knowledge Card 文件路径（必须是 ai_draft 状态）",
    ),
    source_id: str | None = typer.Option(
        None,
        "--source-id",
        help="按 state.json 中的 source_id 反查卡片路径再晋升（card_path 必须已记录）",
    ),
    all_: bool = typer.Option(
        False,
        "--all",
        help="批量晋升所有 ai_draft（默认拒绝；必须再加 --dry-run 预览，或 --confirm 真正执行）",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="仅打印将要 approve 的卡片，不写文件、不改 state",
    ),
    confirm: bool = typer.Option(
        False,
        "--confirm",
        help="--all 真正执行所需的显式确认（搭配可选 --limit）",
    ),
    limit: int = typer.Option(
        0,
        "--limit",
        min=0,
        help="--all 时最多处理多少张（0=全部）",
    ),
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="mindforge.yaml 路径",
    ),
) -> None:
    """显式人工 approve；默认走 --card 主路径。"""
    if ctx.invoked_subcommand is not None:
        return  # 让子命令接管
    cfg = _load_cfg(config)

    # ── --card 主路径 ─────────────────────────────────────────────
    if card is not None:
        _do_single_approve(card, cfg)
        return

    # ── --source-id：state.json 反查 card_path ───────────────────
    if source_id is not None:
        from .checkpoint import Checkpoint

        cp = Checkpoint.load(cfg.state.state_path)
        match: ItemState | None = None
        for it in cp.items.values():
            if it.source_id == source_id:
                match = it
                break
        if match is None:
            console.print(f"[red]✗ state.json 中未找到 source_id={source_id}[/red]")
            raise typer.Exit(code=2)
        if not match.card_path:
            console.print(
                f"[red]✗ source_id={source_id} 还没有 card_path（也许尚未 process）[/red]"
            )
            raise typer.Exit(code=3)
        card_abs = (cfg.vault.cards_path / match.card_path).resolve()
        if not card_abs.is_file():
            # 兼容：card_path 可能是 vault-root 相对
            alt = (cfg.vault.root / match.card_path).resolve()
            card_abs = alt if alt.is_file() else card_abs
        _do_single_approve(card_abs, cfg)
        return

    # ── --all 批量路径 ──────────────────────────────────────────
    if all_:
        _do_bulk_approve(cfg, dry_run=dry_run, confirm=confirm, limit=limit)
        return

    # 没给任何动作 → 友好提示
    console.print(
        "[yellow]请提供动作：--card <path> / --source-id <id> / --all --dry-run / approve list[/yellow]"
    )
    raise typer.Exit(code=2)


def _do_bulk_approve(
    cfg: MindForgeConfig, *, dry_run: bool, confirm: bool, limit: int
) -> None:
    """--all 批量晋升执行体。

    为什么默认拒绝：批量批准是把"AI 草稿"一次性升级为"长期记忆"的危险动作，
    必须显式 ``--confirm`` 才能写入。``--dry-run`` 仅展示候选列表。
    """
    from .cards import iter_cards

    res = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    drafts = [c for c in res.cards if c.status == "ai_draft"]
    if limit > 0:
        drafts = drafts[:limit]

    if not drafts:
        console.print("[dim](no ai_draft cards found)[/dim]")
        return

    console.print(f"[bold]{len(drafts)} 张 ai_draft 待 approve：[/bold]")
    for c in drafts:
        console.print(f"  - {c.rel_path}  [dim]({c.title or '?'})[/dim]")

    if dry_run:
        console.print("[dim](--dry-run 已启用，未写任何文件)[/dim]")
        return
    if not confirm:
        console.print(
            "[red]✗ 批量 approve 是危险动作；请加 --dry-run 预览，或确认无误后再加 --confirm[/red]"
        )
        raise typer.Exit(code=2)

    # 真正批量执行
    ok = 0
    fail = 0
    for c in drafts:
        try:
            _do_single_approve(c.path, cfg)
            ok += 1
        except typer.Exit:
            fail += 1
    console.print(f"[bold]批量 approve 完成：成功 {ok} / 失败 {fail}[/bold]")


@approve_app.command("list")
def approve_list(
    status: str = typer.Option(
        "ai_draft",
        "--status",
        help="按 status 过滤（默认 ai_draft）；多个用逗号分隔",
    ),
    project: str | None = typer.Option(None, "--project", help="按 projects 字段过滤"),
    track: str | None = typer.Option(
        None, "--track", help="按 learning track 过滤（精确匹配）"
    ),
    limit: int = typer.Option(50, "--limit", min=1, help="最多展示多少张"),
    format_: str = typer.Option(
        "table", "--format", help="table | json", case_sensitive=False
    ),
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"), "--config", "-c", help="mindforge.yaml 路径"
    ),
) -> None:
    """列出可 approve 的卡片（安全字段摘要；不读卡片正文）。"""
    from .cards import iter_cards

    cfg = _load_cfg(config)
    wanted = {s.strip() for s in status.split(",") if s.strip()}
    res = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    rows = []
    for c in res.cards:
        if wanted and c.status not in wanted:
            continue
        if project and project not in c.projects:
            continue
        if track and c.track != track:
            continue
        rows.append(c)
    rows = rows[:limit]

    if format_.lower() == "json":
        import json as _json

        out = [
            {
                "title": c.title,
                "path": c.rel_path,
                "status": c.status,
                "track": c.track,
                "projects": list(c.projects),
                "source_type": c.source_type,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "value_score": c.value_score,
            }
            for c in rows
        ]
        console.print_json(_json.dumps({"count": len(out), "items": out}))
        return

    if not rows:
        console.print("[dim](no cards match)[/dim]")
        return
    table = Table(title=f"approve list (status in {sorted(wanted)})")
    for col in ("title", "status", "track", "projects", "source_type", "value_score", "path"):
        table.add_column(col, overflow="fold")
    for c in rows:
        table.add_row(
            c.title or "?",
            c.status,
            c.track or "-",
            ",".join(c.projects) or "-",
            c.source_type or "-",
            "" if c.value_score is None else str(c.value_score),
            c.rel_path,
        )
    console.print(table)
    console.print(f"[dim]({len(rows)} shown)[/dim]")


# ---------------------------------------------------------------------------
# process — M2 主入口：跑五 stage + 写 Card
# ---------------------------------------------------------------------------


@app.command()
def process(
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="mindforge.yaml 路径",
    ),
    file: Path | None = typer.Option(
        None,
        "--file",
        "-f",
        help="只处理该单文件（绝对或相对 vault 的路径）",
    ),
    limit: int | None = typer.Option(
        None,
        "--limit",
        "-n",
        help="本次最多处理多少条",
    ),
    profile: str | None = typer.Option(
        None,
        "--profile",
        "-p",
        help="临时覆盖 llm.active_profile（仅本次进程，不改 yaml）",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="跑完整 pipeline 但不写卡片、不写 state.json；仅 runs/*.jsonl 留痕",
    ),
    prompts_dir: Path = typer.Option(
        Path("prompts"),
        "--prompts-dir",
        help="prompts 根目录",
    ),
    tracks: Path = typer.Option(
        Path("configs/learning_tracks.yaml"),
        "--tracks",
        help="learning_tracks.yaml 路径（作为 triage prompt 的上下文）",
    ),
    template: Path = typer.Option(
        Path("templates/knowledge_card.md.j2"),
        "--template",
        help="Knowledge Card 模板路径",
    ),
) -> None:
    """对 inbox 中已 scan 的文件跑 5 stage pipeline，落地 Knowledge Card。

    硬约束：原始 source 文件不被改写；卡片默认 ``status: ai_draft``，
    必须人工修改 frontmatter 才晋升 ``human_approved``。
    """
    cfg = _load_cfg(config)
    cfg = _override_active_profile(cfg, profile)
    if dry_run:
        console.print("[yellow]--dry-run：不会写卡片、不会写 state.json[/yellow]")
    console.print(f"active_profile = [bold]{cfg.llm.active_profile}[/bold]")

    scanner = Scanner(cfg)
    cp = Checkpoint.load(cfg.state.state_path, backup=cfg.state.backup_state)

    providers = build_providers(cfg.llm)
    client = LLMClient(llm_config=cfg.llm, providers=providers)

    template_path = template
    writer = CardWriter(
        vault_root=cfg.vault.root,
        cards_dir=cfg.vault.cards_dir,
        template_path=template_path,
    )

    tracks_text = tracks.read_text("utf-8") if tracks.exists() else ""
    pipeline = Pipeline(
        client=client,
        logger=None,  # type: ignore[arg-type]
        prompts_dir=prompts_dir,
        prompt_versions=cfg.prompts,
        triage_threshold=cfg.triage.value_score_threshold,
        learning_tracks_text=tracks_text,
    )

    counts = {"processed": 0, "skipped": 0, "failed": 0, "seen": 0}

    with RunLogger(cfg.state.runs_path, command="process") as logger:
        pipeline.logger = logger
        for result in scanner.iter_results():
            if file is not None and Path(result.path).resolve() != file.resolve():
                continue
            counts["seen"] += 1
            if not result.ok:
                counts["failed"] += 1
                logger.emit(
                    EVENT_SOURCE_ERROR,
                    source_type=result.source_type,
                    adapter_name=result.adapter_name,
                    path=str(result.path),
                    error_message=result.error or "",
                )
                continue

            doc = result.document
            assert doc is not None

            # 把 source 登记到 checkpoint（沿用 scan 的 upsert 语义）
            candidate = ItemState(
                source_id=doc.source_id,
                source_type=doc.source_type,
                adapter_name=result.adapter_name,
                source_path=doc.source_path,
                content_hash=doc.content_hash,
                first_seen_at=datetime.now(),
            )
            item = cp.upsert_seen(candidate)

            outcome = pipeline.run(doc)

            now = datetime.now()
            item.status = outcome.status  # type: ignore[assignment]
            item.last_run_id = logger.run_id
            item.processed_at = now
            item.error_message = outcome.error_message
            for stage_name, meta in outcome.stages_meta.items():
                item.stages[stage_name] = StageRecord(
                    stage=stage_name,  # type: ignore[arg-type]
                    model_alias=meta["model_alias"],
                    provider=meta["provider"],
                    actual_model=meta["actual_model"],
                    prompt_version=meta["prompt_version"],
                    status=meta["status"],
                    processed_at=now,
                    tokens_in=meta.get("tokens_in"),
                    tokens_out=meta.get("tokens_out"),
                    latency_ms=meta.get("latency_ms"),
                )

            if outcome.status == "skipped":
                counts["skipped"] += 1
                triage_parsed = outcome.triage.parsed if outcome.triage else {}
                item.track = triage_parsed.get("track")
                item.value_score = triage_parsed.get("value_score")
                logger.emit(
                    "source_processed",
                    source_id=doc.source_id,
                    source_type=doc.source_type,
                    adapter_name=result.adapter_name,
                    source_path=doc.source_path,
                    content_hash=doc.content_hash,
                    status="skipped",
                    track=item.track or "",
                    value_score=item.value_score or 0,
                    skip_reason=outcome.skip_reason or "",
                )
                console.print(f"[yellow]skipped[/yellow] {doc.source_path} :: {outcome.skip_reason}")
            elif outcome.status == "failed":
                counts["failed"] += 1
                logger.emit(
                    "source_processed",
                    source_id=doc.source_id,
                    source_type=doc.source_type,
                    adapter_name=result.adapter_name,
                    source_path=doc.source_path,
                    content_hash=doc.content_hash,
                    status="failed",
                    stage_failed=outcome.error_stage or "",
                    error_message=outcome.error_message or "",
                )
                console.print(
                    f"[red]failed[/red] {doc.source_path} @ stage={outcome.error_stage}: {outcome.error_message}"
                )
            else:  # processed
                counts["processed"] += 1
                triage_parsed = outcome.triage.parsed if outcome.triage else {}
                item.track = triage_parsed.get("track")
                item.value_score = triage_parsed.get("value_score")
                # 渲染并写卡片
                source_dict = {
                    "source_id": doc.source_id,
                    "source_type": doc.source_type,
                    "adapter_name": result.adapter_name,
                    "source_path": doc.source_path,
                    "source_url": doc.source_url or "",
                    "title": doc.title or "",
                }
                run_dict = {
                    "created_at": now.isoformat(timespec="seconds"),
                    "prompts": {"distill_version": cfg.prompts.distill},  # type: ignore[attr-defined]
                    "profile": cfg.llm.active_profile,  # type: ignore[attr-defined]
                    "stage_models": {
                        s: {"alias": m["model_alias"], "provider": m["provider"], "model": m["actual_model"]}
                        for s, m in outcome.stages_meta.items()
                    },
                    "run_id": logger.run_id,
                }
                if dry_run:
                    console.print(
                        f"[cyan]dry-run[/cyan] would-write {doc.source_path}"
                        f" → {cfg.vault.cards_path / (item.track or 'unrouted')}"
                    )
                    logger.emit(
                        "source_processed",
                        source_id=doc.source_id,
                        source_type=doc.source_type,
                        adapter_name=result.adapter_name,
                        source_path=doc.source_path,
                        content_hash=doc.content_hash,
                        status="processed",
                        track=item.track or "",
                        value_score=item.value_score or 0,
                    )
                else:
                    wr = writer.write(card_payload=outcome.card_payload or {}, source=source_dict, run=run_dict)
                    item.card_path = str(wr.path.relative_to(cfg.vault.root))
                    logger.emit(
                        "card_written",
                        output_file=str(wr.path),
                        source_id=doc.source_id,
                        source_type=doc.source_type,
                        track=item.track or "",
                        value_score=item.value_score or 0,
                        card_conflict="true" if wr.conflict else "false",
                    )
                    logger.emit(
                        "source_processed",
                        source_id=doc.source_id,
                        source_type=doc.source_type,
                        adapter_name=result.adapter_name,
                        source_path=doc.source_path,
                        content_hash=doc.content_hash,
                        status="processed",
                        track=item.track or "",
                        value_score=item.value_score or 0,
                        output_file=str(wr.path),
                    )
                    tag = "[yellow]conflict[/yellow]" if wr.conflict else "[green]processed[/green]"
                    console.print(f"{tag} {doc.source_path} → {wr.path}")

            if limit is not None and counts["seen"] >= limit:
                break

        if not dry_run:
            cp.save(active_profile=cfg.llm.active_profile)
            logger.emit(
                EVENT_STATE_WRITTEN,
                path=str(cfg.state.state_path),
                items_count=len(list(cp.all_items())),
            )

    console.print(
        f"\n[bold]process 完成[/bold]：seen={counts['seen']} "
        f"processed={counts['processed']} skipped={counts['skipped']} failed={counts['failed']}"
    )


# ---------------------------------------------------------------------------
# llm ping — 只校验 active_profile 涉及的 env，不发 HTTP
# ---------------------------------------------------------------------------


@llm_app.command("ping")
def llm_ping(
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="mindforge.yaml 路径",
    ),
    profile: str | None = typer.Option(
        None,
        "--profile",
        "-p",
        help="临时覆盖 active_profile",
    ),
) -> None:
    """校验当前 active_profile 涉及的所有模型 env 是否齐全。

    本命令**不发任何 HTTP 请求**，不消耗配额。它只回答：
    - active_profile 涉及哪些 alias / provider / type / 真实 model 名
    - 每个模型需要哪些 env，是否已 set（不打印 value！只报告 set / unset）
    """
    import os
    cfg = _load_cfg(config)
    cfg = _override_active_profile(cfg, profile)

    profile_map = cfg.llm.profiles[cfg.llm.active_profile]
    aliases_used = sorted(set(profile_map.values()))

    console.print(f"active_profile = [bold]{cfg.llm.active_profile}[/bold]")
    table = Table(title="LLM Provider 校验（不发 HTTP）", show_lines=True)
    table.add_column("alias")
    table.add_column("provider")
    table.add_column("type")
    table.add_column("model (resolved)")
    table.add_column("env required")
    table.add_column("env status")

    all_ok = True
    for alias in aliases_used:
        mc = cfg.llm.models[alias]
        actual_model = mc.model
        if mc.model_env and os.environ.get(mc.model_env):
            actual_model = os.environ[mc.model_env]

        env_reqs: list[tuple[str, str, bool]] = []
        if mc.base_url_env:
            env_reqs.append(("base_url", mc.base_url_env, not bool(mc.base_url)))
        if mc.api_key_env:
            env_reqs.append(("api_key", mc.api_key_env, not mc.api_key_optional))
        if mc.version_env:
            env_reqs.append(("version", mc.version_env, False))
        if mc.model_env:
            env_reqs.append(("model", mc.model_env, False))

        status_lines: list[str] = []
        for label, var, required in env_reqs:
            present = bool(os.environ.get(var))
            mark = "[green]set[/green]" if present else (
                "[red]MISSING[/red]" if required else "[yellow]unset (optional)[/yellow]"
            )
            status_lines.append(f"{label}={var} {mark}")
            if required and not present:
                all_ok = False

        env_required_summary = "\n".join(
            f"{lbl} ← {var}{' (required)' if req else ' (optional)'}"
            for lbl, var, req in env_reqs
        ) or "(none)"
        env_status_summary = "\n".join(status_lines) or "(none)"

        table.add_row(
            alias,
            mc.provider,
            mc.type,
            actual_model or "(empty)",
            env_required_summary,
            env_status_summary,
        )

    console.print(table)
    if all_ok:
        console.print("[green]✓ 所需 env 全部齐备；可以进行 smoke test。[/green]")
    else:
        console.print("[red]✗ 有必填 env 未设置。请在 .env 或 shell export 后重试。[/red]")
        raise typer.Exit(code=1)


# ===========================================================================
# M4 — review / recall / project memory
# ===========================================================================
#
# 设计原则（详见 docs/M4_RECALL_REVIEW_PROTOCOL.md）：
# - 五个命令全部不调 LLM、不读 .env、不改源文件、不写 state.json
# - review mark 是唯一允许写卡片 review 字段的命令（沿用 M3 "审计入口必须
#   唯一" 原则）
# - recall / project context 默认只看 status=human_approved；--include-drafts
#   显式打开

review_app = typer.Typer(add_completion=False, help="复习候选与标记（M4）")
project_app = typer.Typer(add_completion=False, help="项目记忆与上下文（M4）")
app.add_typer(review_app, name="review")
app.add_typer(project_app, name="project")


def _hash_keyword(kw: str | None) -> tuple[bool, str]:
    if not kw:
        return False, ""
    import hashlib

    return True, hashlib.sha256(kw.encode("utf-8")).hexdigest()[:8]


def _filters_dict(**kwargs: object) -> dict[str, object]:
    return {k: v for k, v in kwargs.items() if v not in (None, (), [])}


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError as e:
        console.print(f"[red]日期解析失败：{s!r}: {e}[/red]")
        raise typer.Exit(code=2) from e


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

    cfg = _load_cfg(config)
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

    cfg = _load_cfg(config)
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

    cfg = _load_cfg(config)
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

    cfg = _load_cfg(config)
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

    cfg = _load_cfg(config)
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
    from .cards import filter_cards, iter_cards

    cfg = _load_cfg(config)
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    base = filter_cards(scan.cards, status="human_approved")
    now = datetime.now().astimezone()
    week_start = now - timedelta(days=7)
    next_week_end = now + timedelta(days=7)

    overdue: list = []
    due_this_week: list = []
    next_week_preview: list = []
    forgotten_or_partial: list = []
    reviewed_this_week: list = []
    track_counts: dict[str, int] = {}
    project_counts: dict[str, int] = {}

    for c in base:
        if c.review_after is not None:
            ra = c.review_after if c.review_after.tzinfo else c.review_after.replace(tzinfo=now.tzinfo)
            if ra <= now:
                overdue.append(c)
            elif ra <= now + timedelta(days=7):
                due_this_week.append(c)
            elif ra <= next_week_end + timedelta(days=7):
                next_week_preview.append(c)
        if c.reviewed_at is not None:
            ra2 = c.reviewed_at if c.reviewed_at.tzinfo else c.reviewed_at.replace(tzinfo=now.tzinfo)
            if ra2 >= week_start:
                reviewed_this_week.append(c)
        if c.last_review_result in ("partial", "forgotten"):
            forgotten_or_partial.append(c)
        if c.track:
            track_counts[c.track] = track_counts.get(c.track, 0) + 1
        for p in c.projects:
            project_counts[p] = project_counts.get(p, 0) + 1

    # suggested focus = backlog × forgotten 加权排序（纯计数，非 LLM）
    focus_score: dict[str, int] = {}
    for c in overdue + due_this_week:
        if c.track:
            focus_score[c.track] = focus_score.get(c.track, 0) + 1
    for c in forgotten_or_partial:
        if c.track:
            focus_score[c.track] = focus_score.get(c.track, 0) + 2
    suggested_focus = sorted(focus_score.items(), key=lambda kv: -kv[1])[:5]

    with RunLogger(cfg.state.runs_path, command="review-weekly") as logger:  # type: ignore[attr-defined]
        logger.emit(
            "review_due_listed",
            count=len(overdue) + len(due_this_week),
            output_format=output_format,
        )

    if output_format == "json":
        import json as _json
        payload = _json.dumps({
            "version": 1,
            "generated_at": now.isoformat(timespec="seconds"),
            "window": {"week_start": week_start.date().isoformat(),
                       "week_end": now.date().isoformat()},
            "overdue": [_card_to_safe_dict(c) for c in overdue],
            "due_this_week": [_card_to_safe_dict(c) for c in due_this_week],
            "reviewed_this_week_count": len(reviewed_this_week),
            "forgotten_or_partial": [_card_to_safe_dict(c) for c in forgotten_or_partial],
            "suggested_focus_tracks": [{"track": t, "score": s} for t, s in suggested_focus],
            "project_distribution": [
                {"project": p, "card_count": n}
                for p, n in sorted(project_counts.items(), key=lambda kv: -kv[1])
            ],
            "next_week_preview": [_card_to_safe_dict(c) for c in next_week_preview],
        }, ensure_ascii=False, indent=2)
        if output_path:
            output_path.write_text(payload + "\n", encoding="utf-8")
            console.print(f"[green]✓[/green] 已写入 {output_path}")
        else:
            print(payload)
        return

    def _list(items: list) -> str:
        if not items:
            return "_(none)_\n"
        return "\n".join(
            f"- [{c.id or c.path.stem}] {c.title or '(untitled)'}  "
            f"`track={c.track or '-'}` `last={c.last_review_result or '-'}` "
            f"`path={c.rel_path}`"
            for c in items
        ) + "\n"

    md = [
        f"# Weekly Review · {now.date().isoformat()}\n",
        f"_window: {week_start.date().isoformat()} → {now.date().isoformat()}_\n",
        f"\n## Overdue · {len(overdue)} 项\n",
        _list(overdue),
        f"\n## Due this week · {len(due_this_week)} 项\n",
        _list(due_this_week),
        f"\n## Reviewed this week · {len(reviewed_this_week)} 项\n",
        f"\n## Forgotten / partial · {len(forgotten_or_partial)} 项\n",
        _list(forgotten_or_partial),
        "\n## Suggested focus tracks\n",
        ("\n".join(f"- {t} (score={s})" for t, s in suggested_focus) + "\n") if suggested_focus else "_(none)_\n",
        "\n## Project distribution\n",
        ("\n".join(f"- {p}: {n}" for p, n in sorted(project_counts.items(), key=lambda kv: -kv[1])) + "\n") if project_counts else "_(none)_\n",
        f"\n## Next week preview · {len(next_week_preview)} 项\n",
        _list(next_week_preview),
        "\n_说明：本周报由 frontmatter 结构化汇总生成，**不**调用 LLM。_\n",
    ]
    out = "".join(md)
    if output_path:
        output_path.write_text(out, encoding="utf-8")
        console.print(f"[green]✓[/green] 已写入 {output_path}")
    else:
        print(out)


# ---------------------------------------------------------------------------
# recall
# ---------------------------------------------------------------------------


@app.command()
def recall(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    track: str | None = typer.Option(None, "--track"),
    project: str | None = typer.Option(None, "--project"),
    tag: list[str] = typer.Option([], "--tag", help="可重复，AND 语义"),
    keyword: str | None = typer.Option(
        None, "--keyword",
        help="多 token AND；ci-contains；仅匹配 frontmatter 白名单 + 文件名",
    ),
    source_type: str | None = typer.Option(None, "--source-type"),
    status: str = typer.Option(
        "human_approved", "--status", help="human_approved | ai_draft | all"
    ),
    include_drafts: bool = typer.Option(False, "--include-drafts"),
    since: str | None = typer.Option(None, "--since", help="YYYY-MM-DD"),
    until: str | None = typer.Option(None, "--until", help="YYYY-MM-DD"),
    limit: int = typer.Option(20, "--limit"),
    sort: str = typer.Option(
        "default", "--sort",
        help="default | review_after | updated_at | title | value_score",
    ),
    output_format: str = typer.Option(
        "compact", "--format",
        help="compact (默认) | table | markdown | json",
    ),
    query: str | None = typer.Option(
        None, "--query", "-q",
        help="BM25 词法检索（v0.3）。给定时走 BM25 路径，忽略 --keyword 与 --sort。",
    ),
    explain: bool = typer.Option(
        False, "--explain",
        help="仅 --query 路径生效：打印每条命中的字段贡献分。",
    ),
    ranking: str = typer.Option(
        "bm25", "--ranking",
        help="仅 --query 路径生效：bm25 (默认) | hybrid（bm25+value_score+review_due）",
    ),
    weight_bm25: float | None = typer.Option(
        None, "--weight-bm25",
        help="仅 --ranking hybrid：临时覆盖 bm25 权重（不改 yaml）",
    ),
    weight_value_score: float | None = typer.Option(
        None, "--weight-value-score",
        help="仅 --ranking hybrid：临时覆盖 value_score 权重（不改 yaml）",
    ),
    weight_review_due: float | None = typer.Option(
        None, "--weight-review-due",
        help="仅 --ranking hybrid：临时覆盖 review_due 权重（不改 yaml）",
    ),
) -> None:
    """检索 Knowledge Cards。

    两条互斥路径：
    - **不带 --query**：M4.1 规则检索（含 --keyword AND 过滤）；
    - **带 --query**：v0.3 BM25 词法检索，按相关度排序，可 --explain。

    无论哪条路径，都**只**读 frontmatter 白名单字段 + 卡片内 AI 已生成的安全
    section（``## AI Summary`` / ``## Action Items`` / ``## Principles`` /
    ``## Known Risks``）；**绝不**碰 source 原文、Source Excerpt、Human Note。
    """
    if query is not None:
        return _do_bm25_recall(
            config=config,
            query=query,
            track=track,
            project=project,
            tags=list(tag),
            source_type=source_type,
            status=status,
            include_drafts=include_drafts,
            since=since,
            until=until,
            limit=limit,
            output_format=output_format,
            explain=explain,
            ranking=ranking,
            weight_bm25=weight_bm25,
            weight_value_score=weight_value_score,
            weight_review_due=weight_review_due,
        )

    from .cards import filter_cards, iter_cards, sort_cards

    cfg = _load_cfg(config)
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    cards = filter_cards(
        scan.cards,
        track=track,
        project=project,
        tags=tag,
        source_type=source_type,
        status=status,
        keyword=keyword,
        since=_parse_date(since),
        until=_parse_date(until),
        include_drafts=include_drafts,
    )
    try:
        cards = sort_cards(cards, by=sort)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=2) from e
    cards = cards[:limit]

    kw_provided, kw_hash = _hash_keyword(keyword)
    with RunLogger(cfg.state.runs_path, command="recall") as logger:  # type: ignore[attr-defined]
        logger.emit(
            "recall_executed",
            count=len(cards),
            filters=_filters_dict(
                track=track,
                project=project,
                tags=list(tag),
                source_type=source_type,
                status=status,
                include_drafts=include_drafts,
                since=since,
                until=until,
                limit=limit,
                sort=sort,
            ),
            keyword_provided=kw_provided,
            keyword_hash=kw_hash,
            output_format=output_format,
        )

    if output_format == "json":
        import json as _json

        payload = {
            "version": 1,
            "query": {
                "track": track,
                "project": project,
                "tags": list(tag),
                "keyword_provided": kw_provided,
                "keyword_hash": kw_hash,
                "status_filter": status,
                "since": since,
                "until": until,
                "limit": limit,
                "sort": sort,
            },
            "count": len(cards),
            "items": [_card_to_safe_dict(c) for c in cards],
        }
        print(_json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if output_format == "markdown":
        # 直接 print 避免 rich 把 [id] 当 markup 吞掉
        print(f"# Recall · {len(cards)} 项 (sort={sort})\n")
        if not cards:
            print("_(no cards matched)_")
            return
        for c in cards:
            print(
                f"- **[{c.id or c.path.stem}]** {c.title or '(untitled)'}  "
                f"`status={c.status}` `track={c.track or '-'}` "
                f"`value_score={c.value_score if c.value_score is not None else '-'}`  "
                f"`path={c.rel_path}`"
            )
        return

    if output_format == "table":
        if not cards:
            console.print("[yellow]没有匹配的卡片。[/yellow]")
            return
        table = Table(title=f"Recall · {len(cards)} 项 (sort={sort})")
        table.add_column("id")
        table.add_column("title")
        table.add_column("status")
        table.add_column("track")
        table.add_column("score", justify="right")
        table.add_column("review_after")
        for c in cards:
            table.add_row(
                c.id or c.path.stem,
                c.title or "(untitled)",
                c.status,
                c.track or "-",
                str(c.value_score) if c.value_score is not None else "-",
                _safe_date(c.review_after),
            )
        console.print(table)
        return

    # compact (默认)
    if not cards:
        console.print("[yellow]没有匹配的卡片。[/yellow]")
        return
    console.print(f"[bold]Recall[/bold] · {len(cards)} 项 (sort={sort})")
    for c in cards:
        console.print(
            f"- {c.id or c.path.stem} · {c.title or '(untitled)'} · "
            f"status={c.status} · track={c.track or '-'} · "
            f"value_score={c.value_score if c.value_score is not None else '-'}"
        )




# ---------------------------------------------------------------------------
# v0.3 — BM25 lexical recall + index 子命令
# ---------------------------------------------------------------------------
# 设计契约（详见 docs/M5_4_LEXICAL_RECALL_PROTOCOL.md）：
# 1. BM25 是**纯本地词法检索**，不调用 LLM、不读 .env、不联网。
# 2. 索引只构建在 Knowledge Card 的安全字段上（frontmatter + 白名单 body
#    section），永远不索引 source 原文 / Source Excerpt / Human Note。
# 3. 索引产物落在 `.mindforge/index/bm25.json`，由 .gitignore 挡住。
# 4. recall 默认仍只查 human_approved；--include-drafts 显式打开。


index_app = typer.Typer(
    add_completion=False,
    help="BM25 本地索引子命令（v0.3，纯词法、不联网、不调 LLM）",
    no_args_is_help=True,
)
app.add_typer(index_app, name="index")


def _do_bm25_recall(
    *,
    config: Path,
    query: str,
    track: str | None,
    project: str | None,
    tags: list[str],
    source_type: str | None,
    status: str,
    include_drafts: bool,
    since: str | None,
    until: str | None,
    limit: int,
    output_format: str,
    explain: bool,
    ranking: str = "bm25",
    weight_bm25: float | None = None,
    weight_value_score: float | None = None,
    weight_review_due: float | None = None,
) -> None:
    """BM25 / hybrid 路径。

    - BM25 字段权重 / k1 / b 全部走 ``cfg.search.bm25``；
    - hybrid 路径在 BM25 之上叠加 value_score + review_due 两路本地信号；
    - 索引文件记录 ``config_hash``，与当前配置不一致 → 自动用内存重建（提示一次）。
    """
    from . import lexical_index as lx
    from .cards import iter_cards

    if ranking not in ("bm25", "hybrid"):
        console.print(f"[red]--ranking 仅支持 bm25 | hybrid，收到 {ranking!r}[/red]")
        raise typer.Exit(code=2)

    cfg = _load_cfg(config)
    workdir = cfg.state.workdir  # type: ignore[attr-defined]
    idx_path = lx.default_index_path(workdir)

    # 当前配置的字段权重（解析用户别名）+ k1 / b + config_hash
    fw = lx.resolve_field_weights(cfg.search.bm25.fields)
    cur_k1 = cfg.search.bm25.k1
    cur_b = cfg.search.bm25.b
    cur_hash = lx.compute_config_hash(field_weights=fw, k1=cur_k1, b=cur_b)

    index: lx.BM25Index
    used_disk = False
    index_stale = False
    if idx_path.exists():
        try:
            index = lx.BM25Index.load(idx_path)
            if index.config_hash and index.config_hash != cur_hash:
                # 配置漂移 → 旧索引按旧权重打分，结果不能信
                index_stale = True
                if output_format not in ("json",):
                    console.print(
                        "[yellow]提示：磁盘索引的 config_hash 与当前配置不一致；"
                        "本次内存即时重建。建议运行 `mindforge index rebuild`。[/yellow]"
                    )
                scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
                index = lx.build_index(scan.cards, field_weights=fw, k1=cur_k1, b=cur_b, config_hash=cur_hash)
            else:
                used_disk = True
        except (lx.IndexFormatError, OSError, ValueError) as e:
            console.print(f"[yellow]索引文件不可用（{e}）；改为内存即时构建。[/yellow]")
            scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
            index = lx.build_index(scan.cards, field_weights=fw, k1=cur_k1, b=cur_b, config_hash=cur_hash)
    else:
        if output_format not in ("json",):
            console.print(
                "[yellow]提示：尚无索引文件，本次内存即时构建。"
                "建议运行 `mindforge index rebuild` 以加速后续查询。[/yellow]"
            )
        scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
        index = lx.build_index(scan.cards, field_weights=fw, k1=cur_k1, b=cur_b, config_hash=cur_hash)

    if ranking == "hybrid":
        # v0.3.2 临时权重覆盖：仅作用于本次查询，绝不写回 yaml。
        # 任意一个 --weight-* 给出 → 进入 override 模式；其它分量回退到配置默认。
        cfg_w = dict(cfg.search.hybrid.weights)
        overrides_given = [w is not None for w in (weight_bm25, weight_value_score, weight_review_due)]
        weight_source = "cli_override" if any(overrides_given) else "config"
        if weight_bm25 is not None:
            cfg_w["bm25"] = weight_bm25
        if weight_value_score is not None:
            cfg_w["value_score"] = weight_value_score
        if weight_review_due is not None:
            cfg_w["review_due"] = weight_review_due
        # 校验：所有权重必须 >= 0，且至少一个 > 0；否则 fail-fast，不静默
        for k, v in cfg_w.items():
            if not isinstance(v, (int, float)) or v < 0:
                console.print(f"[red]非法 hybrid 权重 {k}={v!r}：必须是 >= 0 的数值[/red]")
                raise typer.Exit(code=2)
        if all(v == 0 for v in cfg_w.values()):
            console.print("[red]非法 hybrid 权重：三路权重不能同时为 0[/red]")
            raise typer.Exit(code=2)
        active_weights = cfg_w

        scan2 = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
        cards_for_hybrid = scan2.cards
        hybrid_hits = lx.hybrid_search(
            index, query,
            weights=active_weights,
            cards=cards_for_hybrid,
            status_filter=status,
            include_drafts=include_drafts,
            track=track, project=project, tags=tags, source_type=source_type,
            since=_parse_date(since), until=_parse_date(until),
            limit=limit,
        )
        hits = [hh.base for hh in hybrid_hits]
    else:
        hybrid_hits = None
        active_weights = None
        weight_source = "n/a"
        hits = lx.search(
            index, query,
            status_filter=status,
            include_drafts=include_drafts,
            track=track, project=project, tags=tags, source_type=source_type,
            since=_parse_date(since), until=_parse_date(until),
            limit=limit,
        )

    # 不把 query 原文写入 telemetry/runs；只记录是否提供 + hash 化指纹。
    kw_provided, kw_hash = _hash_keyword(query)
    with RunLogger(cfg.state.runs_path, command="recall_bm25") as logger:  # type: ignore[attr-defined]
        logger.emit(
            "recall_bm25_executed",
            count=len(hits),
            filters=_filters_dict(
                track=track,
                project=project,
                tags=list(tags),
                source_type=source_type,
                status=status,
                include_drafts=include_drafts,
                since=since,
                until=until,
                limit=limit,
                explain=explain,
                used_disk_index=used_disk,
                ranking_mode=ranking,
                index_stale=index_stale,
                weight_source=weight_source,
            ),
            keyword_provided=kw_provided,
            keyword_hash=kw_hash,
            output_format=output_format,
        )

    # —— hybrid 索引（既给非 JSON 输出，也给 JSON explain 用） ——
    hybrid_by_path: dict[str, "lx.HybridHit"] = {}
    if hybrid_hits is not None:
        hybrid_by_path = {hh.base.doc.rel_path: hh for hh in hybrid_hits}

    if output_format == "json":
        import json as _json

        items: list[dict]
        if hybrid_hits is not None:
            items = [_hybrid_hit_to_safe_dict(hh, explain=explain) for hh in hybrid_hits]
        else:
            items = [_hit_to_safe_dict(h, explain=explain) for h in hits]
        # v0.3.2: explain 模式追加 why_this_matched 简短规则解释（不含原文）
        if explain:
            for it, h in zip(items, hits):
                it["why_this_matched"] = _why_matched(h, hybrid_by_path or None)
                it["matched_terms"] = sorted({t for fh in h.field_hits for t in fh.term_counts})
                it["matched_fields"] = [fh.field for fh in h.field_hits]
                it["ranking_mode"] = ranking
                it["index_stale"] = index_stale
                it["weight_source"] = weight_source
        payload = {
            "version": 1,
            "engine": "bm25",
            "ranking": ranking,
            "weight_source": weight_source,
            "active_weights": active_weights,
            "index_stale": index_stale,
            "query": {
                "track": track,
                "project": project,
                "tags": list(tags),
                "query_provided": kw_provided,
                "query_hash": kw_hash,
                "status_filter": status,
                "include_drafts": include_drafts,
                "since": since,
                "until": until,
                "limit": limit,
            },
            "count": len(hits),
            "items": items,
        }
        print(_json.dumps(payload, ensure_ascii=False, indent=2))
        return

    # —— 非 JSON 路径：把 hybrid 的 final_score 与三路分量加到 explain 输出 ——
    label = "engine=bm25" + (
        f" ranking={ranking}" if ranking != "bm25" else ""
    ) + (f" weights={weight_source}" if ranking == "hybrid" else "")

    if output_format == "markdown":
        print(f"# Recall · {len(hits)} 项 ({label})\n")
        if not hits:
            print("_(no cards matched)_")
            return
        for h in hits:
            d = h.doc
            hh = hybrid_by_path.get(d.rel_path)
            score_str = f"score={(hh.final_score if hh else h.score):.3f}"
            print(
                f"- **[{d.id or Path(d.rel_path).stem}]** {d.title or '(untitled)'}  "
                f"`{score_str}` `status={d.status}` `track={d.track or '-'}` "
                f"`path={d.rel_path}`"
            )
            if explain and hh is not None:
                print(
                    f"    - hybrid: bm25={hh.bm25_norm:.3f}·{hh.bm25_score:.3f}, "
                    f"value={hh.value_norm:.3f}, review_due={hh.review_due_norm:.3f} "
                    f"→ final={hh.final_score:.3f}"
                )
            if explain:
                for fh in h.field_hits:
                    terms = ", ".join(f"{t}×{n}" for t, n in fh.term_counts.items())
                    print(f"    - {fh.field} (w={fh.weight}, +{fh.contribution:.3f}): {terms}")
        return

    if output_format == "table":
        if not hits:
            console.print("[yellow]没有匹配的卡片。[/yellow]")
            return
        table = Table(title=f"Recall · {len(hits)} 项 ({label})")
        table.add_column("score", justify="right")
        table.add_column("id")
        table.add_column("title")
        table.add_column("status")
        table.add_column("track")
        table.add_column("path")
        for h in hits:
            d = h.doc
            hh = hybrid_by_path.get(d.rel_path)
            score_val = hh.final_score if hh else h.score
            table.add_row(
                f"{score_val:.3f}",
                d.id or Path(d.rel_path).stem,
                d.title or "(untitled)",
                d.status,
                d.track or "-",
                d.rel_path,
            )
        console.print(table)
        return

    # compact（默认）
    if not hits:
        console.print("[yellow]没有匹配的卡片。[/yellow]")
        return
    console.print(f"[bold]Recall[/bold] · {len(hits)} 项 ({label})")
    for h in hits:
        d = h.doc
        hh = hybrid_by_path.get(d.rel_path)
        score_val = hh.final_score if hh else h.score
        console.print(
            f"- score={score_val:.3f} · {d.id or Path(d.rel_path).stem} · "
            f"{d.title or '(untitled)'} · status={d.status} · track={d.track or '-'}"
        )
        if explain:
            console.print(f"    [dim]why[/dim] {_why_matched(h, hybrid_by_path or None)}")
            if hh is not None:
                console.print(
                    f"    [dim]hybrid[/dim] bm25={hh.bm25_norm:.3f}·{hh.bm25_score:.3f} "
                    f"value={hh.value_norm:.3f} review_due={hh.review_due_norm:.3f} "
                    f"→ final={hh.final_score:.3f}"
                )
            for fh in h.field_hits:
                terms = ", ".join(f"{t}×{n}" for t, n in fh.term_counts.items())
                console.print(
                    f"    [dim]{fh.field}[/dim] w={fh.weight} +{fh.contribution:.3f}: {terms}"
                )


def _hybrid_hit_to_safe_dict(hh, *, explain: bool) -> dict:
    """HybridHit → JSON 安全 dict；包含 final_score 与三路分量。"""
    base = _hit_to_safe_dict(hh.base, explain=explain)
    base["bm25_score"] = round(hh.bm25_score, 6)
    base["bm25_norm"] = round(hh.bm25_norm, 6)
    base["value_norm"] = round(hh.value_norm, 6)
    base["review_due_norm"] = round(hh.review_due_norm, 6)
    base["final_score"] = round(hh.final_score, 6)
    base["score"] = base["final_score"]
    return base


def _why_matched(h, hybrid_by_path: dict | None) -> str:
    """v0.3.2 — 简短"为什么匹配"规则解释（**绝不**返回原文 / body）。

    设计：只用 SearchHit / HybridHit 已暴露的安全元数据组装一句话。
    输出长度 < 200 字符；只引用 field 名、weight、term 名、分量值。
    """
    if not h.field_hits:
        return "no field hits"
    top = max(h.field_hits, key=lambda fh: fh.contribution)
    terms = ",".join(top.term_counts.keys())
    parts = [f"top field={top.field}(w={top.weight}, +{top.contribution:.3f}) terms={terms}"]
    if hybrid_by_path:
        hh = hybrid_by_path.get(h.doc.rel_path)
        if hh is not None:
            parts.append(
                f"hybrid: bm25_norm={hh.bm25_norm:.2f}, "
                f"value={hh.value_norm:.2f}, review_due={hh.review_due_norm:.2f} "
                f"→ {hh.final_score:.3f}"
            )
    return "; ".join(parts)


def _hit_to_safe_dict(h, *, explain: bool) -> dict:
    """SearchHit → JSON 安全 dict；只暴露白名单字段。"""
    d = h.doc
    out: dict = {
        "score": round(h.score, 6),
        "id": d.id,
        "title": d.title,
        "rel_path": d.rel_path,
        "status": d.status,
        "track": d.track,
        "projects": list(d.projects),
        "tags": list(d.tags),
        "source_type": d.source_type,
        "created_at": d.created_at,
    }
    if explain:
        out["explain"] = [
            {
                "field": fh.field,
                "weight": fh.weight,
                "contribution": round(fh.contribution, 6),
                "terms": dict(fh.term_counts),
            }
            for fh in h.field_hits
        ]
    return out


@index_app.command("rebuild")
def index_rebuild(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """全量重建 BM25 本地索引到 ``<workdir>/index/bm25.json``。

    幂等：永远写整文件（先写 .tmp 再原子 rename）。索引内容只来自当前
    Knowledge Card 的安全字段；无网络、无 LLM。
    """
    from . import lexical_index as lx
    from .cards import iter_cards

    cfg = _load_cfg(config)
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    if scan.errors:
        console.print(f"[yellow]跳过 {len(scan.errors)} 张损坏卡片[/yellow]")
    fw = lx.resolve_field_weights(cfg.search.bm25.fields)
    cur_hash = lx.compute_config_hash(field_weights=fw, k1=cfg.search.bm25.k1, b=cfg.search.bm25.b)
    index = lx.build_index(
        scan.cards,
        field_weights=fw,
        k1=cfg.search.bm25.k1,
        b=cfg.search.bm25.b,
        config_hash=cur_hash,
    )
    idx_path = lx.default_index_path(cfg.state.workdir)  # type: ignore[attr-defined]
    index.save(idx_path)
    console.print(
        f"[green]✓ 索引已写入[/green] {idx_path} · "
        f"卡片={len(index.docs)} · avgdl={index.avgdl:.1f} · "
        f"config_hash={cur_hash} · 时间={index.built_at}"
    )


@index_app.command("status")
def index_status(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    output_format: str = typer.Option("compact", "--format", help="compact (默认) | json"),
    as_json: bool = typer.Option(False, "--json", help="等价于 --format json（v0.3.2 加）"),
) -> None:
    """打印索引存在性、字段权重、staleness 摘要。不读 query、不打印卡片正文。"""
    return _do_index_status(config=config, output_format="json" if as_json else output_format)


@index_app.command("info")
def index_info(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    output_format: str = typer.Option("compact", "--format", help="compact (默认) | json"),
    as_json: bool = typer.Option(False, "--json", help="等价于 --format json"),
) -> None:
    """v0.3.2：``index status`` 的别名，配合 ``--json`` 给机器可读的索引快照。

    JSON schema 稳定（version=1），字段：
      index_path / exists / stale / card_count / last_built_at /
      included_statuses / config_hash / current_config_hash /
      field_weights / k1 / b / ranking_defaults / hybrid_weights / tokenizer
    """
    return _do_index_status(config=config, output_format="json" if as_json else output_format)


def _do_index_status(*, config: Path, output_format: str) -> None:
    from . import lexical_index as lx
    from .cards import iter_cards

    cfg = _load_cfg(config)
    idx_path = lx.default_index_path(cfg.state.workdir)  # type: ignore[attr-defined]
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    fw_cur = lx.resolve_field_weights(cfg.search.bm25.fields)
    cur_hash = lx.compute_config_hash(field_weights=fw_cur, k1=cfg.search.bm25.k1, b=cfg.search.bm25.b)

    # ── 索引不存在分支 ──
    if not idx_path.exists():
        if output_format == "json":
            import json as _json
            print(_json.dumps({
                "version": 1,
                "index_path": str(idx_path),
                "exists": False,
                "stale": True,
                "card_count": len(scan.cards),
                "last_built_at": None,
                "included_statuses": ["human_approved", "ai_draft"],
                "config_hash": None,
                "current_config_hash": cur_hash,
                "field_weights": fw_cur,
                "k1": cfg.search.bm25.k1,
                "b": cfg.search.bm25.b,
                "ranking_defaults": "bm25",
                "hybrid_weights": dict(cfg.search.hybrid.weights),
                "tokenizer": "ascii_word_plus_cjk_char_v1",
            }, ensure_ascii=False, indent=2))
            return
        console.print("[yellow]索引文件不存在[/yellow]")
        console.print(f"  路径：{idx_path}")
        console.print(f"  当前 vault 卡片数：{len(scan.cards)}")
        console.print("  建议：[bold]mindforge index rebuild[/bold]")
        return

    try:
        index = lx.BM25Index.load(idx_path)
    except (lx.IndexFormatError, ValueError, OSError) as e:
        console.print(f"[red]索引读取失败：{e}[/red]")
        console.print("  建议：[bold]mindforge index rebuild[/bold]")
        raise typer.Exit(code=1) from e

    diff = lx.diff_index(index, scan.cards)
    config_drift = bool(index.config_hash) and index.config_hash != cur_hash
    fresh = diff.fresh and not config_drift

    if output_format == "json":
        import json as _json
        print(_json.dumps({
            "version": 1,
            "index_path": str(idx_path),
            "exists": True,
            "stale": not fresh,
            "config_drift": config_drift,
            "card_count": diff.indexed_count,
            "current_card_count": diff.current_count,
            "last_built_at": index.built_at,
            "included_statuses": ["human_approved", "ai_draft"],
            "config_hash": index.config_hash or None,
            "current_config_hash": cur_hash,
            "field_weights": index.field_weights,
            "k1": index.k1,
            "b": index.b,
            "avgdl": index.avgdl,
            "ranking_defaults": "bm25",
            "hybrid_weights": dict(cfg.search.hybrid.weights),
            "tokenizer": index.tokenizer_name,
            "added_count": len(diff.added),
            "removed_count": len(diff.removed),
            "changed_count": len(diff.changed),
        }, ensure_ascii=False, indent=2))
        return

    state_label = "[green]fresh[/green]" if fresh else "[yellow]stale[/yellow]"
    console.print(f"[bold]Index status[/bold] · {state_label}")
    console.print(f"  路径：{idx_path}")
    console.print(f"  built_at：{index.built_at}")
    console.print(f"  schema_version：{index.schema_version}")
    console.print(f"  tokenizer：{index.tokenizer_name}")
    console.print(f"  k1={index.k1} b={index.b} avgdl={index.avgdl:.1f}")
    console.print(f"  字段权重：{index.field_weights}")
    console.print(f"  config_hash（索引）：{index.config_hash or '(未记录)'}")
    console.print(f"  config_hash（当前）：{cur_hash}")
    if config_drift:
        console.print("  [yellow]⚠ 配置漂移[/yellow]：索引按旧 search 配置打分，结果不可信")
    console.print(f"  索引卡片数：{diff.indexed_count}  当前卡片数：{diff.current_count}")
    if diff.added:
        console.print(f"  [yellow]新增未索引[/yellow]：{len(diff.added)}（前 {min(5,len(diff.added))} 项）")
        for rp in diff.added[:5]:
            console.print(f"    + {rp}")
    if diff.removed:
        console.print(f"  [yellow]索引内已删除[/yellow]：{len(diff.removed)}")
        for rp in diff.removed[:5]:
            console.print(f"    - {rp}")
    if diff.changed:
        console.print(f"  [yellow]mtime 漂移[/yellow]：{len(diff.changed)}")
        for rp in diff.changed[:5]:
            console.print(f"    ~ {rp}")
    if not fresh:
        console.print("  建议：[bold]mindforge index rebuild[/bold]")


# ---------------------------------------------------------------------------
# project list / context
# ---------------------------------------------------------------------------


@project_app.command("list")
def project_list(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    output_format: str = typer.Option("markdown", "--format"),
) -> None:
    """列出所有卡片 frontmatter 中出现过的 project（并集去重，按字母序）。"""
    from .cards import iter_cards

    cfg = _load_cfg(config)
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    counts: dict[str, int] = {}
    for c in scan.cards:
        for p in c.projects:
            counts[p] = counts.get(p, 0) + 1
    items = sorted(counts.items())

    with RunLogger(cfg.state.runs_path, command="project-list") as logger:  # type: ignore[attr-defined]
        logger.emit(
            "project_list_emitted",
            count=len(items),
            output_format=output_format,
        )

    if output_format == "json":
        import json as _json

        print(_json.dumps(
            {"version": 1, "count": len(items), "items": [
                {"name": n, "card_count": k} for n, k in items
            ]},
            ensure_ascii=False, indent=2,
        ))
        return
    if not items:
        console.print("[yellow]当前没有任何卡片声明 project。[/yellow]")
        return
    console.print(f"[bold]Projects[/bold] · {len(items)} 项")
    for name, n in items:
        console.print(f"- {name} ({n} card{'s' if n != 1 else ''})")


@project_app.command("context")
def project_context(
    project_names: list[str] = typer.Argument(
        ...,
        help=(
            "一个或多个项目名（与卡片 frontmatter projects[] 比对，并匹配 "
            "30-Projects/<name>.md）。多于一个 → 启用多 project 联合模式。"
        ),
    ),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    limit: int = typer.Option(20, "--limit"),
    no_prompts: bool = typer.Option(False, "--no-prompts", help="不输出 Reusable Prompts 段"),
    include_drafts: bool = typer.Option(False, "--include-drafts"),
    include_actions: bool = typer.Option(
        True, "--include-actions/--no-actions", help="是否聚合 Action Items 段（默认开）"
    ),
    include_review_due: bool = typer.Option(
        True, "--include-review-due/--no-review-due", help="是否输出 Review Due 段（默认开）"
    ),
    include_next_step_prompt: bool = typer.Option(
        True, "--include-next-step-prompt/--no-next-step-prompt",
        help="是否附固定模板的下一步 prompt（**不调 LLM**，仅模板）",
    ),
    target: str | None = typer.Option(
        None, "--target",
        help="目标助手：claude-code | copilot | codex | generic（默认按 project profile.default_target，再退化为 generic）",
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o",
        help="把结果写到该文件而不是 stdout；安全：写入前不读 .env，不调 LLM",
    ),
    output_format: str = typer.Option("markdown", "--format"),
) -> None:
    """渲染一个或多个 project 的只读上下文包（markdown / json）。

    - 单 project：保持 v0.2.2 的固定 9 段结构（向后兼容）；
    - 多 project：使用 ``multi_project_context`` 渲染器；卡片去重、原则
      并列（不自动裁决）、suggested prompt 明确"multi-project context pack"。

    任何模式都**不**调 LLM、**不**读 .env、**不**读 raw source。
    """
    from .cards import filter_cards, iter_cards
    from .multi_project_context import (
        render_multi_project_context_json,
        render_multi_project_context_markdown,
    )
    from .project_context import (
        ProjectContextOptions,
        render_project_context_json,
        render_project_context_markdown,
        resolve_target,
    )
    from .project_profile import (
        ProjectProfile,
        ProjectProfileError,
        load_project_profile,
    )
    from .telemetry import measure

    cfg = _load_cfg(config)

    # 去重并保持用户顺序（"a a b" → ["a", "b"]）
    seen: set[str] = set()
    project_names = [n for n in project_names if not (n in seen or seen.add(n))]
    if not project_names:
        console.print("[red]至少需要一个 project_name[/red]")
        raise typer.Exit(code=2)

    is_multi = len(project_names) > 1

    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)

    profiles: dict[str, ProjectProfile] = {}
    cards_by_project: dict[str, list] = {}
    for name in project_names:
        try:
            profiles[name] = load_project_profile(
                cfg.vault.root, cfg.vault.projects_dir, name
            )
        except ProjectProfileError as e:
            console.print(f"[red]project_name 非法：{e}[/red]")
            raise typer.Exit(code=2) from e
        cards_by_project[name] = filter_cards(
            scan.cards,
            project=name,
            status="human_approved",
            include_drafts=include_drafts,
        )

    # 多项目模式下，target 解析仅看第一个 found=true 的 profile.default_target
    primary_profile = next(
        (profiles[n] for n in project_names if profiles[n].found),
        profiles[project_names[0]],
    )
    try:
        resolved_target = resolve_target(target, primary_profile)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=2) from e

    opts = ProjectContextOptions(
        include_prompts=not no_prompts,
        include_drafts=include_drafts,
        include_actions=include_actions,
        include_review_due=include_review_due,
        include_next_step_prompt=include_next_step_prompt,
        limit=limit,
        target=resolved_target,
    )

    if output_format not in {"markdown", "json"}:
        console.print(f"[red]--format 必须是 markdown 或 json，收到 {output_format!r}[/red]")
        raise typer.Exit(code=2)

    with measure(
        cfg.state.workdir, cfg.telemetry, "project-context",
        project_count=len(project_names),
    ) as th:
        if is_multi:
            if output_format == "json":
                out = render_multi_project_context_json(
                    project_names, cards_by_project, profiles, options=opts
                )
            else:
                out = render_multi_project_context_markdown(
                    project_names, cards_by_project, profiles, options=opts
                )
            total_cards = sum(min(len(c), limit) for c in cards_by_project.values())
        else:
            single_name = project_names[0]
            if output_format == "json":
                out = render_project_context_json(
                    single_name, cards_by_project[single_name],
                    options=opts, profile=profiles[single_name],
                )
            else:
                out = render_project_context_markdown(
                    single_name, cards_by_project[single_name],
                    options=opts, profile=profiles[single_name],
                )
            total_cards = min(len(cards_by_project[single_name]), limit)

        th.set_counts(card_count=total_cards, result_count=total_cards)

        with RunLogger(cfg.state.runs_path, command="project-context") as logger:  # type: ignore[attr-defined]
            # 多项目模式：runs jsonl 仅记 project_count + 第一个 project_name；
            # 不展开各项目名，避免日志结构每次随用户输入暴增。
            logger.emit(
                "project_context_emitted",
                project_name=project_names[0] if not is_multi else f"<{len(project_names)} projects>",
                count=total_cards,
                output_format=output_format,
                target=resolved_target,
                project_profile_found=primary_profile.found,
            )

        if output is not None:
            if not output.parent.exists():
                console.print(
                    f"[red]--output 父目录不存在：{output.parent}（请先 mkdir）[/red]"
                )
                raise typer.Exit(code=2)
            output.write_text(out, encoding="utf-8")
            console.print(f"[green]✔ project context 已写入[/green] {output}")
            return

        print(out)


# ---------------------------------------------------------------------------
# project update-evidence — 幂等写入 30-Projects/<name>.md 受控区块
# ---------------------------------------------------------------------------


@project_app.command("update-evidence")
def project_update_evidence(
    project_name: str = typer.Argument(..., help="项目名；必须已存在 30-Projects/<name>.md"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    include_drafts: bool = typer.Option(
        False, "--include-drafts", help="同时纳入 ai_draft 卡片（默认仅 human_approved）"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="只打印将要写入的内容，不落盘"
    ),
) -> None:
    """把当前项目已审核卡片的安全摘要，幂等写入项目笔记的受控区块。

    - 区块由 ``<!-- MINDFORGE:EVIDENCE:START -->`` 与 ``END`` 包围；
    - 多次运行同一参数时除时间戳外保持稳定，**不会重复追加**；
    - 不创建项目 profile；profile 文件不存在 → 退出 2 + 友好提示；
    - **永不**写 ai_summary / source_excerpt / 卡片正文 / prompt / completion。
    """
    from .cards import filter_cards, iter_cards
    from .evidence import EvidenceError, update_evidence_block, write_evidence_update
    from .project_profile import ProjectProfileError, _validate_project_name
    from .telemetry import measure

    cfg = _load_cfg(config)

    try:
        _validate_project_name(project_name)
    except ProjectProfileError as e:
        console.print(f"[red]project_name 非法：{e}[/red]")
        raise typer.Exit(code=2) from e

    profile_path = cfg.vault.projects_path / f"{project_name}.md"

    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    cards = filter_cards(
        scan.cards,
        project=project_name,
        status="human_approved",
        include_drafts=include_drafts,
    )

    with measure(
        cfg.state.workdir, cfg.telemetry, "project-update-evidence",
        project_count=1,
    ) as th:
        try:
            update = update_evidence_block(
                profile_path, project_name, cards,
                cards_dir_rel=cfg.vault.cards_dir,
            )
        except EvidenceError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(code=2) from e

        th.set_counts(card_count=update.card_count, result_count=update.card_count)

        with RunLogger(cfg.state.runs_path, command="project-update-evidence") as logger:  # type: ignore[attr-defined]
            logger.emit(
                "project_context_emitted",  # 复用 M5.3 事件类型，仅 metadata
                project_name=project_name,
                count=update.card_count,
                output_format="evidence-block",
                target="-",
                project_profile_found=True,
            )

        if dry_run:
            console.print(
                f"[bold]dry-run[/bold] · {profile_path} · "
                f"will_change={update.will_change} · existed={update.block_existed_before} · "
                f"cards={update.card_count}"
            )
            print(update.new_text)
            return

        if not update.will_change:
            console.print(
                f"[green]✔ evidence block 已是最新（{update.card_count} cards），未写盘[/green]"
            )
            return

        write_evidence_update(update)
        console.print(
            f"[green]✔ evidence block 已更新[/green] {profile_path} "
            f"· cards={update.card_count} · existed={update.block_existed_before}"
        )


# ---------------------------------------------------------------------------
# telemetry status / summary — 本地使用观察日志
# ---------------------------------------------------------------------------


telemetry_app = typer.Typer(
    add_completion=False,
    help="本地 telemetry（M5.7 / v0.2.3）— 仅元数据，永不上传",
)
app.add_typer(telemetry_app, name="telemetry")


@telemetry_app.command("status")
def telemetry_status(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """打印 telemetry 配置与本地文件位置（不读取事件内容）。"""
    from .telemetry import telemetry_path

    cfg = _load_cfg(config)
    p = telemetry_path(cfg.state.workdir)
    console.print("[bold]Telemetry status[/bold]")
    console.print(f"- enabled: {cfg.telemetry.enabled}")
    console.print(f"- local_only: {cfg.telemetry.local_only}")
    console.print(f"- file: {p}")
    console.print(f"- exists: {p.exists()}")
    if p.exists():
        try:
            line_count = sum(1 for _ in p.open("r", encoding="utf-8"))
        except OSError:
            line_count = 0
        console.print(f"- event_count: {line_count}")


@telemetry_app.command("summary")
def telemetry_summary_cmd(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    output_format: str = typer.Option("markdown", "--format"),
    recent_errors: int = typer.Option(5, "--recent-errors"),
) -> None:
    """聚合统计：总数 / 成功率 / 最常用命令 / 平均耗时 / 最近错误。

    所有数据仅来自本地 ``.mindforge/telemetry.jsonl``；不读取卡片正文。
    """
    from .telemetry import read_events, summarize

    cfg = _load_cfg(config)
    if output_format not in {"markdown", "json"}:
        console.print(f"[red]--format 必须是 markdown 或 json，收到 {output_format!r}[/red]")
        raise typer.Exit(code=2)

    events = read_events(cfg.state.workdir)
    summary = summarize(events, recent_errors=recent_errors)

    if output_format == "json":
        import json as _json

        print(_json.dumps(
            {
                "total": summary.total,
                "success": summary.success,
                "failure": summary.failure,
                "by_command": summary.by_command,
                "avg_duration_ms_by_command": summary.avg_duration_ms_by_command,
                "recent_errors": summary.recent_errors,
            },
            ensure_ascii=False, indent=2,
        ))
        return

    console.print("[bold]Telemetry summary[/bold]")
    console.print(f"- total: {summary.total}")
    console.print(f"- success: {summary.success}")
    console.print(f"- failure: {summary.failure}")
    if summary.by_command:
        console.print("[bold]Most used commands:[/bold]")
        for cmd, n in sorted(summary.by_command.items(), key=lambda kv: (-kv[1], kv[0])):
            avg = summary.avg_duration_ms_by_command.get(cmd)
            avg_part = f" · avg {avg}ms" if avg is not None else ""
            console.print(f"- {cmd}: {n}{avg_part}")
    if summary.recent_errors:
        console.print("[bold]Recent errors:[/bold]")
        for e in summary.recent_errors:
            console.print(
                f"- {e.get('timestamp')} · {e.get('command')} · "
                f"{e.get('error_code')} · {e.get('duration_ms')}ms"
            )


# ---------------------------------------------------------------------------
# 内部辅助 — 卡片摘要的安全字典 / 日期格式化
# ---------------------------------------------------------------------------


def _card_to_safe_dict(c) -> dict:  # type: ignore[no-untyped-def]
    return {
        "id": c.id,
        "title": c.title,
        "path": c.rel_path,
        "status": c.status,
        "track": c.track,
        "projects": list(c.projects),
        "tags": list(c.tags),
        "source_type": c.source_type,
        "source_url": c.source_url,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "reviewed_at": c.reviewed_at.isoformat() if c.reviewed_at else None,
        "review_after": c.review_after.isoformat() if c.review_after else None,
        "review_count": c.review_count,
        "last_review_result": c.last_review_result,
        "value_score": c.value_score,
    }


def _safe_date(dt) -> str:  # type: ignore[no-untyped-def]
    if dt is None:
        return "-"
    return dt.date().isoformat()


# ---------------------------------------------------------------------------
# vault subcommand — Obsidian 友好度（M5.5 / v0.2.5）
# 设计原则：只生成 _index.md / _link_candidates.md 两类**新文件**，
# 绝不改写已有 Knowledge Card 正文。如果同名文件已存在但缺 marker，
# 就写到 sibling 文件（_index.mindforge.md）避免覆盖人手内容。
# ---------------------------------------------------------------------------


vault_app = typer.Typer(
    add_completion=False,
    help="Obsidian 友好度（M5.5 / v0.2.5）：导航索引与双链候选，仅写新文件。",
)
app.add_typer(vault_app, name="vault")


@vault_app.command("index")
def vault_index(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    reviews_dir: str = typer.Option(
        "80-Reviews",
        "--reviews-dir",
        help="复习索引落盘的目录（相对 vault.root）；不存在则跳过。",
    ),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """生成或更新 cards / projects / reviews 三处的 _index.md。

    幂等：``_index.md`` 由 MindForge 维护，每次重写整个文件；首行的
    ``MINDFORGE:VAULT_INDEX`` marker 保证可识别 / 可覆盖。
    """
    from .vault import refresh_indexes

    cfg = _load_cfg(config)
    res = refresh_indexes(
        cfg.vault.root,
        cfg.vault.cards_dir,
        cfg.vault.projects_dir,
        reviews_dir,
        dry_run=dry_run,
    )
    if dry_run:
        console.print("[yellow]dry-run（未写文件）[/yellow]")
    for p in res.written:
        console.print(f"  → {p}")
    console.print(f"[green]✓ 完成：写入 {len(res.written)} 个 index 文件[/green]")


@vault_app.command("links")
def vault_links(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    top_k: int = typer.Option(5, "--top-k", min=1, max=20),
    min_score: int = typer.Option(3, "--min-score", min=1),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """基于安全字段（learning_track / projects / tags / source_type / title token）
    生成 ``_link_candidates.md``。**不**调 LLM、**不**做 embedding、**不**改卡片正文。
    """
    from .cards import iter_cards
    from .vault import build_link_candidates, write_link_candidates

    cfg = _load_cfg(config)
    res = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    cands = build_link_candidates(res.cards, top_k=top_k, min_score=min_score)
    p, _ = write_link_candidates(
        cfg.vault.root / cfg.vault.cards_dir, cands, dry_run=dry_run
    )
    if dry_run:
        console.print(f"[yellow]dry-run；预览路径 {p}[/yellow]")
    else:
        console.print(f"[green]✓ 写入 {p}[/green]")
    console.print(
        f"  cards={len(cands)}  with_candidates={sum(1 for c in cands if c.candidates)}"
    )


@vault_app.command("refresh")
def vault_refresh(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    reviews_dir: str = typer.Option("80-Reviews", "--reviews-dir"),
) -> None:
    """vault index + vault links 的组合糖；幂等。"""
    vault_index(config=config, reviews_dir=reviews_dir, dry_run=False)
    vault_links(config=config, top_k=5, min_score=3, dry_run=False)


# ---------------------------------------------------------------------------
# doctor — 只读诊断
# 设计：永远不读取 .env 内容、不打印 secret，只检查"风险面"和"可操作建议"。
# ---------------------------------------------------------------------------


@app.command()
def init(
    vault: Path | None = typer.Option(
        None,
        "--vault",
        help="目标 vault 根目录（默认：当前 mindforge.yaml 中 vault.root；"
        "若不存在则用 ./vault）",
    ),
    project_root: Path = typer.Option(
        Path("."),
        "--project-root",
        help="MindForge 工作目录（configs/ 与 .env.example 落在这里；默认当前目录）",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="覆写 MindForge 提供的模板配置文件（**不**会覆写用户数据目录）",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="只打印 plan，不写文件",
    ),
) -> None:
    """初始化最小可用的 vault 骨架与配置文件。

    幂等保证：多次运行不会重复创建已存在的目录或覆盖用户文件；只有 ``--force``
    才允许覆写 MindForge 自带的模板。
    """
    from .init_cmd import build_plan, execute_plan, next_steps_hint

    # repo_root：尽量找到本仓库 configs/ 与 vault_template/
    import mindforge as _pkg

    repo_root = Path(_pkg.__file__).resolve().parent.parent.parent

    # vault 路径优先级：CLI --vault > 当前 yaml vault.root > ./vault
    target_vault: Path
    if vault is not None:
        target_vault = vault.expanduser().resolve()
    else:
        cfg_path = project_root / "configs" / "mindforge.yaml"
        if cfg_path.exists():
            try:
                cfg = load_mindforge_config(cfg_path)
                target_vault = cfg.vault.root
            except ConfigError:
                target_vault = (project_root / "vault").resolve()
        else:
            target_vault = (project_root / "vault").resolve()

    plan = build_plan(
        target_vault, project_root=project_root.resolve(), repo_root=repo_root, force=force
    )

    console.print("[bold]MindForge init[/bold]")
    console.print(f"- vault.root  : {plan.vault_root}")
    console.print(f"- project root: {plan.project_root}")
    if force:
        console.print("- mode        : [yellow]--force (will overwrite templates)[/yellow]")
    if dry_run:
        console.print("- mode        : [yellow]--dry-run (no files written)[/yellow]")

    summary = plan.summary()
    console.print(
        f"- plan: create_dir={summary.get('create_dir', 0)} "
        f"copy_file={summary.get('copy_file', 0)} "
        f"overwrite_force={summary.get('overwrite_force', 0)} "
        f"skip_exists={summary.get('skip_exists', 0)}"
    )

    if dry_run:
        for it in plan.items:
            tag = {
                "create_dir": "[green]+ DIR [/green]",
                "copy_file": "[green]+ FILE[/green]",
                "overwrite_force": "[yellow]! OVR [/yellow]",
                "skip_exists": "[dim]= keep[/dim]",
            }.get(it.action, "?")
            console.print(f"  {tag} {it.target}  [dim]{it.note}[/dim]")
        console.print("[dim]--dry-run 完成；未写任何文件。[/dim]")
        return

    actions = execute_plan(plan)
    for line in actions:
        console.print(f"  {line}")

    # ── 关键：把刚拷过来的 mindforge.yaml 里的 vault.root 改成本次 --vault ──
    # 否则用户 init 完之后跑 doctor 会指向 repo 默认的 vault.root，体验割裂。
    cfg_dst = (project_root / "configs" / "mindforge.yaml").resolve()
    if cfg_dst.exists():
        try:
            import yaml as _yaml

            data = _yaml.safe_load(cfg_dst.read_text(encoding="utf-8")) or {}
            if isinstance(data, dict):
                vault_block = data.setdefault("vault", {})
                if isinstance(vault_block, dict):
                    if vault_block.get("root") != str(plan.vault_root):
                        vault_block["root"] = str(plan.vault_root)
                        cfg_dst.write_text(
                            _yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                            encoding="utf-8",
                        )
                        console.print(
                            f"  rewrote {cfg_dst}  vault.root → {plan.vault_root}"
                        )
        except Exception as e:  # noqa: BLE001
            console.print(f"[yellow]提示：未能改写 vault.root（{e}），请手工编辑 yaml。[/yellow]")

    console.print("\n[bold green]✓ MindForge initialized.[/bold green]")
    console.print("[bold]Next steps:[/bold]")
    for step in next_steps_hint():
        console.print(f"  {step}")
    console.print(
        "[dim]说明：init 不创建真实 .env、不读取 .env、不调用 LLM、不修改原始资料。[/dim]"
    )


@app.command()
def doctor(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """打印环境 + 配置 + 可选依赖 + .gitignore 风险快照。"""
    import importlib.util as _u
    import platform
    import shutil
    import subprocess
    import sys

    from . import __version__

    console.print(f"[bold]MindForge doctor[/bold]  v{__version__}")
    console.print(f"- Python            : {platform.python_version()} ({sys.executable})")
    console.print(f"- Platform          : {platform.platform()}")
    console.print(f"- config path       : {config}  ({'exists' if config.exists() else 'MISSING'})")

    if not config.exists():
        console.print("[yellow]提示：缺少 mindforge.yaml；其它检查跳过。[/yellow]")
        return

    cfg = _load_cfg(config)
    vault_root = cfg.vault.root
    inbox = vault_root / cfg.vault.inbox_root
    cards_dir = vault_root / cfg.vault.cards_dir
    projects_dir = vault_root / cfg.vault.projects_dir
    state_dir = Path(cfg.state.workdir)

    console.print(f"- vault.root        : {vault_root}  ({_ok_dir(vault_root)})")
    console.print(f"- inbox             : {inbox}  ({_ok_dir(inbox)})")
    console.print(f"- knowledge cards   : {cards_dir}  ({_ok_dir(cards_dir)})")
    console.print(f"- projects          : {projects_dir}  ({_ok_dir(projects_dir)})")
    console.print(f"- state workdir     : {state_dir}  ({_ok_dir(state_dir)})")
    console.print(f"- active_profile    : {cfg.llm.active_profile}")
    console.print(
        f"- telemetry.enabled : {cfg.telemetry.enabled} (local_only={cfg.telemetry.local_only})"
    )

    pdf_ok = _u.find_spec("pypdf") is not None
    docx_ok = _u.find_spec("docx") is not None
    pdf_msg = "✓" if pdf_ok else r"✗ (pip install mindforge\[pdf])"
    docx_msg = "✓" if docx_ok else r"✗ (pip install mindforge\[docx])"
    console.print(f"- optional dep pypdf       : {pdf_msg}")
    console.print(f"- optional dep python-docx : {docx_msg}")

    cwd = Path.cwd()
    env_file = cwd / ".env"
    gitignore = cwd / ".gitignore"
    if env_file.exists():
        ignored = False
        if gitignore.exists():
            try:
                ignored = ".env" in gitignore.read_text(encoding="utf-8").splitlines()
            except OSError:
                pass
        if ignored:
            console.print(
                "- .env             : present, [green]gitignored ✓[/green] (内容未被读取)"
            )
        else:
            console.print(
                "- .env             : [red]present BUT not in .gitignore![/red] "
                "立即把 .env 加入 .gitignore，避免误提交。"
            )
    else:
        console.print("- .env             : not present")

    if shutil.which("git"):
        try:
            out = subprocess.check_output(
                ["git", "status", "--porcelain"],
                cwd=cwd,
                stderr=subprocess.DEVNULL,
                timeout=5,
            ).decode("utf-8", "replace")
            risky = [
                line
                for line in out.splitlines()
                if any(
                    k in line
                    for k in (".mindforge", "telemetry.jsonl", "runs/", "state.json", ".env")
                )
            ]
            if risky:
                console.print(
                    "- [yellow]git status: 检测到运行时产物可能被加入暂存（请勿提交）：[/yellow]"
                )
                for r in risky[:5]:
                    console.print(f"    {r}")
            else:
                console.print("- git status       : 无敏感运行产物风险")
        except Exception:  # noqa: BLE001
            console.print("- git status       : (跳过)")

    # ── v0.2.6: actionable hints ──────────────────────────────────────
    hints: list[str] = []
    if not cards_dir.exists():
        hints.append("vault 目录缺失 → 运行: mindforge init --vault <path>")
    if cfg.llm.active_profile not in cfg.llm.profiles:
        hints.append(
            f"active_profile={cfg.llm.active_profile!r} 未在 llm.profiles 中定义 → 检查 mindforge.yaml"
        )
    elif cfg.llm.active_profile != "fake":
        hints.append(
            "active_profile 非 fake：真实跑 process 前请先 `mindforge llm ping` 校验环境变量"
        )
    if cards_dir.exists():
        try:
            from .cards import iter_cards as _iter
            from . import lexical_index as _lx

            res = _iter(cfg.vault.root, cfg.vault.cards_dir)
            n_drafts = sum(1 for c in res.cards if c.status == "ai_draft")
            n_approved = sum(1 for c in res.cards if c.status == "human_approved")
            if not res.cards:
                hints.append("尚无 Knowledge Cards → 运行: mindforge scan && mindforge process")
            elif n_drafts > 0:
                hints.append(
                    f"{n_drafts} 张 ai_draft 待人工审核 → 运行: mindforge approve list"
                )
            # v0.3.2: 没有 human_approved 但有 ai_draft → 提示 recall --include-drafts
            if res.cards and n_approved == 0 and n_drafts > 0:
                hints.append(
                    "暂无 human_approved 卡片 → 检索时加: mindforge recall --include-drafts"
                )
            # v0.4.1: 检测 overdue / due 复习并给出建议
            if n_approved > 0:
                _now_doc = datetime.now().astimezone()
                _overdue = 0
                _due_7 = 0
                for _c in res.cards:
                    if _c.status != "human_approved" or _c.review_after is None:
                        continue
                    _ra = _c.review_after if _c.review_after.tzinfo else _c.review_after.replace(tzinfo=_now_doc.tzinfo)
                    if _ra <= _now_doc:
                        _overdue += 1
                    elif _ra <= _now_doc + timedelta(days=7):
                        _due_7 += 1
                if _overdue:
                    hints.append(
                        f"{_overdue} 张卡片已 overdue → 运行: mindforge review backlog"
                    )
                elif _due_7:
                    hints.append(
                        f"{_due_7} 张卡片本周内到期 → 运行: mindforge review schedule --days 7"
                    )
            # v0.3.1: BM25 索引检查（缺失 / 配置漂移 / mtime 漂移）
            idx_path = _lx.default_index_path(cfg.state.workdir)  # type: ignore[attr-defined]
            if not idx_path.exists():
                if res.cards:
                    hints.append("BM25 索引缺失 → 运行: mindforge index rebuild")
            else:
                try:
                    idx = _lx.BM25Index.load(idx_path)
                    fw_cur = _lx.resolve_field_weights(cfg.search.bm25.fields)
                    cur_h = _lx.compute_config_hash(
                        field_weights=fw_cur, k1=cfg.search.bm25.k1, b=cfg.search.bm25.b,
                    )
                    if idx.config_hash and idx.config_hash != cur_h:
                        hints.append("BM25 索引与 search 配置不一致 → 运行: mindforge index rebuild")
                    else:
                        diff = _lx.diff_index(idx, res.cards)
                        if not diff.fresh:
                            hints.append("BM25 索引 stale（卡片有变更） → 运行: mindforge index rebuild")
                except Exception:  # noqa: BLE001
                    hints.append("BM25 索引读取失败 → 运行: mindforge index rebuild")
        except Exception:  # noqa: BLE001
            pass

    if hints:
        console.print("[bold]Action items:[/bold]")
        for h in hints:
            console.print(f"  • {h}")

    console.print(
        "[dim]说明：本命令不读 .env 内容、不发 HTTP、不打印 api_key / token。[/dim]"
    )


def _ok_dir(p: Path) -> str:
    if not p.exists():
        return "[red]missing[/red]"
    if not p.is_dir():
        return "[red]not a dir[/red]"
    return "[green]ok[/green]"


def main() -> None:
    """CLI 入口。``--debug`` 不传时静默 traceback，仅打印简短错误。

    设计动机：终端用户大多数时候只想看到"哪里坏了 + 怎么办"；完整 traceback
    属于开发者调试场景，按需开启。
    """
    import os
    import sys

    debug = os.environ.get("MINDFORGE_DEBUG") == "1" or "--debug" in sys.argv
    try:
        app()
    except typer.Exit:
        raise
    except Exception as e:  # noqa: BLE001 — 这里就是想兜底；debug 时再原样抛
        if debug:
            raise
        console.print(f"[red]✗ unexpected error: {type(e).__name__}: {e}[/red]")
        console.print("[dim]提示：加 --debug 查看完整 traceback。[/dim]")
        sys.exit(1)


# ---------------------------------------------------------------------------
# version — 打印版本与运行配置摘要（不含 secret）
# 设计意图：终端用户最常问的是"我装的哪个版本？现在用的哪个 vault / profile？"
# 输出严格仅元数据：不读 .env，不打印 api_key / model 名以外的敏感字段。
# ---------------------------------------------------------------------------


@app.command()
def version(
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="mindforge.yaml 路径（找不到也不报错，仅展示 MindForge 版本）",
    ),
) -> None:
    """打印 MindForge 版本与当前运行配置摘要。"""
    from . import __version__
    from .config import load_mindforge_config
    from .telemetry import telemetry_path

    console.print(f"[bold]MindForge[/bold] v{__version__}")
    console.print(f"- config: {config}")
    if not config.exists():
        console.print("  [yellow](config 文件不存在；以下字段省略)[/yellow]")
        console.print("[dim]提示：复制 configs/mindforge.yaml 到目标位置后重试。[/dim]")
        return
    try:
        cfg = load_mindforge_config(config)
    except ConfigError as e:
        console.print(f"  [red]config 解析失败：{e}[/red]")
        raise typer.Exit(code=2) from e

    # 兼容全局 --vault override（与 _load_cfg 行为一致）
    import os as _os
    from dataclasses import replace as _replace

    _ov = _os.environ.get("MINDFORGE_VAULT_OVERRIDE")
    if _ov:
        cfg = _replace(cfg, vault=_replace(cfg.vault, root=Path(_ov)))

    console.print(f"- vault.root        : {cfg.vault.root}")
    console.print(f"- vault.inbox_root  : {cfg.vault.inbox_root}")
    console.print(f"- vault.cards_dir   : {cfg.vault.cards_dir}")
    console.print(f"- vault.projects_dir: {cfg.vault.projects_dir}")
    console.print(f"- state.workdir     : {cfg.state.workdir}")
    console.print(f"- llm.active_profile: {cfg.llm.active_profile}")

    enabled_sources = sorted(cfg.sources.enabled)
    console.print(f"- sources.enabled   : {', '.join(enabled_sources) or '(none)'}")
    console.print(f"- telemetry.enabled : {cfg.telemetry.enabled}")
    console.print(f"- telemetry.local_only: {cfg.telemetry.local_only}")
    if cfg.telemetry.enabled:
        console.print(f"- telemetry.file    : {telemetry_path(cfg.state.workdir)}")
    console.print(
        "[dim]说明：本命令不读 .env、不发 HTTP、不打印任何 api_key 或 token。[/dim]"
    )


if __name__ == "__main__":  # pragma: no cover
    main()
