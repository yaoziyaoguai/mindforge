"""mindforge — 命令行入口（typer）。

v0.1 当前命令：
- ``mindforge scan``    — 扫描 inbox，派发到 adapter，更新 state.json；不调 LLM。
- ``mindforge process`` — 跑 5 stage pipeline，写入 Knowledge Card。
- ``mindforge status``  — 打印 state.json 的状态汇总（按 status / source_type）。
- ``mindforge llm ping``— 只校验 active_profile 涉及的模型 env 是否齐全，不发 HTTP。
"""

from __future__ import annotations

from dataclasses import dataclass
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
backup_app = typer.Typer(add_completion=False, help="本地备份 / 导出 / 恢复检查（不上传、不读 .env）")
app.add_typer(backup_app, name="backup")
config_app = typer.Typer(add_completion=False, help="本地配置 / setup 诊断（safe-by-default）")
app.add_typer(config_app, name="config")
dogfood_app = typer.Typer(add_completion=False, help="非敏感本地 dogfooding 计划与 checklist")
app.add_typer(dogfood_app, name="dogfood")
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
    obsidian_vault: Path | None = typer.Option(
        None,
        "--obsidian-vault",
        help="临时覆盖 obsidian.vault_path（仅 obsidian 子命令使用，不修改 yaml）。",
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
    if obsidian_vault is not None:
        os.environ["MINDFORGE_OBSIDIAN_VAULT_OVERRIDE"] = str(
            obsidian_vault.expanduser().resolve()
        )
    else:
        os.environ.pop("MINDFORGE_OBSIDIAN_VAULT_OVERRIDE", None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_cfg(config_path: Path, *, read_env: bool = True) -> MindForgeConfig:
    # 入口处加载 .env（静默，不打印 value，env > dotfile）
    if read_env:
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
    return _apply_global_vault_override(cfg)


def _apply_global_vault_override(cfg: MindForgeConfig) -> MindForgeConfig:
    """应用全局 --vault 覆盖；只改 vault.root，不碰 yaml 文件。"""
    import os as _os
    from dataclasses import replace as _replace

    override = _os.environ.get("MINDFORGE_VAULT_OVERRIDE")
    if not override:
        return cfg
    new_vault = _replace(cfg.vault, root=Path(override))
    return _replace(cfg, vault=new_vault)


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
    cfg = _load_cfg(config, read_env=False)
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
    cfg = _load_cfg(config, read_env=False)
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
        console.print(
            "[dim]边界：这是一次显式人工 approve；MindForge 不会让 AI 自动写入 "
            "human_approved。下一步可运行 `mindforge recall --query ...` 或 "
            "`mindforge review weekly` 使用这张卡片。[/dim]"
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
    cfg = _load_cfg(config, read_env=False)

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


def _format_card_created_at(c) -> str:
    """把卡片创建时间压成 CLI 友好字符串；只读 frontmatter 安全字段。"""
    return c.created_at.isoformat(timespec="minutes") if c.created_at else "-"


def _format_card_source_hint(c) -> str:
    """生成 approve 待办里的 source 摘要，避免读取 source 原文。

    v0.6.2 的边界是“让人更容易判断是否批准”，但不能为了展示更丰富而回读
    原始资料正文；这里仅使用 CardSummary 已白名单化的 source_* frontmatter。
    """
    if c.source_title:
        return c.source_title
    if c.source_url:
        return c.source_url
    return c.source_type or "-"


def _approve_next_command(c) -> str:
    """为单张草稿给出最短下一步命令，不自动 approve。"""
    return f"mindforge approve --card {c.rel_path}"


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

    cfg = _load_cfg(config, read_env=False)
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
        console.print("[yellow]没有待 approve 的卡片。[/yellow]")
        console.print(
            "[dim]下一步：如果 inbox 有新资料，先运行 `mindforge scan`，再运行 "
            "`mindforge process --profile fake --limit 1` 生成 ai_draft；"
            "MindForge 不会自动 approve。[/dim]"
        )
        return
    table = Table(title=f"Approve Todo · {len(rows)} pending (status in {sorted(wanted)})")
    for col in (
        "title",
        "source",
        "created",
        "track",
        "risk / safety",
        "next command",
    ):
        table.add_column(col, overflow="fold")
    for c in rows:
        table.add_row(
            c.title or "?",
            _format_card_source_hint(c),
            _format_card_created_at(c),
            c.track or "-",
            "ai_draft，需要人工确认；不会自动 approve",
            _approve_next_command(c),
        )
    console.print(table)
    console.print("[bold]Todo commands[/bold]")
    for c in rows:
        console.print(
            f"- {c.title or '?'} · source={_format_card_source_hint(c)} · "
            f"created={_format_card_created_at(c)} · next=`{_approve_next_command(c)}`",
            markup=False,
        )
    console.print(
        "[dim]说明：approve 会把 ai_draft 晋升为 human_approved，之后才进入 "
        "recall / review / project context 的默认结果；MindForge 不会自动 approve。[/dim]"
    )


@approve_app.command("show")
def approve_show(
    card: Path = typer.Option(..., "--card", help="要查看的 ai_draft / card 路径"),
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"), "--config", "-c", help="mindforge.yaml 路径"
    ),
) -> None:
    """查看待 approve 卡片的安全摘要；不读取正文、不改变状态。

    v0.6.5 dogfooding 需要用户在 approve 前多看一步，但这里仍守住边界：
    只读 frontmatter 白名单字段，不打印 source raw text，也不把 ai_draft 自动晋升。
    """
    from .cards import read_card_frontmatter

    cfg = _load_cfg(config, read_env=False)
    card_path = card.expanduser()
    if not card_path.is_absolute():
        card_path = cfg.vault.root / card_path
    if not card_path.exists():
        console.print(f"[red]✗ card 不存在：{card_path}[/red]")
        console.print("Next: mindforge approve list", markup=False)
        raise typer.Exit(code=2)
    try:
        fm = read_card_frontmatter(card_path)
    except Exception as e:  # noqa: BLE001 - 只打印解析错误摘要，不输出正文
        console.print(f"[red]✗ card frontmatter 无法读取：{type(e).__name__}: {e}[/red]")
        raise typer.Exit(code=2) from e
    console.print("[bold]Approve preview[/bold]")
    for key in ("id", "title", "status", "track", "source_type", "source_title", "created_at", "value_score"):
        console.print(f"{key:<12}: {fm.get(key, '-')}")
    console.print(f"path        : {card_path}")
    console.print(
        "Boundary: preview only; no auto approve, no .env, no LLM, no source body.",
        markup=False,
    )
    console.print(f"Next: mindforge approve --card {card_path}", markup=False)


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
    prompts_dir: Path | None = typer.Option(
        None,
        "--prompts-dir",
        help="prompts 根目录；未传时使用 package 内置 prompts。",
    ),
    tracks: Path | None = typer.Option(
        None,
        "--tracks",
        help="learning_tracks.yaml 路径；未传时使用 package 内置 learning tracks。",
    ),
    template: Path | None = typer.Option(
        None,
        "--template",
        help="Knowledge Card 模板路径；未传时使用 package 内置模板。",
    ),
) -> None:
    """对 inbox 中已 scan 的文件跑 5 stage pipeline，落地 Knowledge Card。

    硬约束：原始 source 文件不被改写；卡片默认 ``status: ai_draft``，
    必须人工修改 frontmatter 才晋升 ``human_approved``。
    """
    cfg = _load_cfg(config, read_env=False)
    cfg = _override_active_profile(cfg, profile)
    if cfg.llm.active_profile != "fake":
        # 中文学习型注释：v0.5.1 把本地 smoke 路径收紧为“不读 .env”。
        # 只有用户显式切到真实 provider 时，才加载 .env 以解析 base_url /
        # api_key 等环境变量；fake provider 必须保持完全离线、无 secret 依赖。
        load_dotenv_silently(Path.cwd())
    if dry_run:
        console.print("[yellow]--dry-run：不会写卡片、不会写 state.json[/yellow]")
    console.print(f"active_profile = [bold]{cfg.llm.active_profile}[/bold]")

    from .assets_runtime import asset_root, bundled_text

    # 中文学习型说明：v0.5.2 起默认 prompts/tracks/template 来自 package
    # resources，而不是当前工作目录或仓库根。用户显式传入路径时仍然优先，
    # 这保证了自定义 prompt 实验不受影响，同时让 wheel 安装后可运行。
    resolved_prompts_dir = (
        prompts_dir.expanduser() if prompts_dir is not None else asset_root().joinpath("prompts")
    )
    tracks_text = (
        tracks.expanduser().read_text("utf-8")
        if tracks is not None
        else bundled_text("configs", "learning_tracks.yaml")
    )

    scanner = Scanner(cfg)
    cp = Checkpoint.load(cfg.state.state_path, backup=cfg.state.backup_state)

    providers = build_providers(cfg.llm)
    client = LLMClient(llm_config=cfg.llm, providers=providers)

    if template is not None:
        writer = CardWriter(
            vault_root=cfg.vault.root,
            cards_dir=cfg.vault.cards_dir,
            template_path=template.expanduser(),
        )
    else:
        writer = CardWriter(
            vault_root=cfg.vault.root,
            cards_dir=cfg.vault.cards_dir,
            template_text=bundled_text("templates", "knowledge_card.md.j2"),
        )

    pipeline = Pipeline(
        client=client,
        logger=None,  # type: ignore[arg-type]
        prompts_dir=resolved_prompts_dir,
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

    cfg = _load_cfg(config, read_env=False)
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

    cfg = _load_cfg(config, read_env=False)
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

    cfg = _load_cfg(config, read_env=False)
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

    cfg = _load_cfg(config, read_env=False)
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

    cfg = _load_cfg(config, read_env=False)
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

    cfg = _load_cfg(config, read_env=False)
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
    has_weekly_work = bool(overdue or due_this_week or reviewed_this_week or forgotten_or_partial or next_week_preview)

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
            "next_actions": _review_next_actions(has_weekly_work),
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
        "\n## Learning tasks\n",
        _review_learning_tasks(overdue, due_this_week, forgotten_or_partial),
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
        (
            "\n## Next action\n"
            + "\n".join(f"- {a}" for a in _review_next_actions(has_weekly_work))
            + "\n"
            if not has_weekly_work
            else ""
        ),
        "\n## Workflow bridge\n",
        "- review 只使用 human_approved 卡片；新资料先 process 成 ai_draft，"
        "再由你显式 approve。\n"
        "- 找不到复习方向时，先运行 `mindforge recall --query <keyword>` 定位卡片，"
        "再回到 `mindforge review weekly`。\n",
        "\n_说明：本周报由 frontmatter 结构化汇总生成，**不**调用 LLM。_\n",
    ]
    out = "".join(md)
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
    """把 review 数据压成个人学习任务，不改变 review 调度。

    这里不新增调度算法，只把已有 frontmatter 汇总转成“今天该做什么”的语言，
    避免 v0.6.2 越界成智能推荐或 LLM 复习教练。
    """
    tasks: list[str] = []
    if overdue:
        tasks.append(f"- 先处理 {len(overdue)} 张 overdue 卡片。")
    if due_this_week:
        tasks.append(f"- 本周安排 {len(due_this_week)} 张 due card。")
    if forgotten_or_partial:
        tasks.append(f"- 优先回看 {len(forgotten_or_partial)} 张 forgotten/partial 卡片。")
    if not tasks:
        tasks.append("- 当前没有明确复习任务；先 approve 新草稿或用 recall 找主题。")
    return "\n".join(tasks) + "\n"


def _review_next_actions(has_weekly_work: bool) -> list[str]:
    """review 空状态的下一步建议；只返回静态命令，不触发任何写操作。"""
    if has_weekly_work:
        return ["运行 `mindforge review due` 聚焦今天到期项。"]
    return [
        "运行 `mindforge approve list` 查看是否有 ai_draft 待人工批准。",
        "运行 `mindforge process --profile fake --limit 1` 从 inbox 生成新的 ai_draft。",
        "运行 `mindforge recall --query <keyword>` 从已批准卡片里找学习主题。",
    ]


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

    cfg = _load_cfg(config, read_env=False)
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
            print("\n" + _recall_no_result_next_action())
            return
        for c in cards:
            print(
                f"- **[{c.id or c.path.stem}]** {c.title or '(untitled)'}  "
                f"`status={c.status}` `track={c.track or '-'}` "
                f"`value_score={c.value_score if c.value_score is not None else '-'}`  "
                f"`path={c.rel_path}`"
            )
        print("\n" + _recall_hit_next_action())
        return

    if output_format == "table":
        if not cards:
            console.print("[yellow]没有匹配的卡片。[/yellow]")
            console.print(f"[dim]{_recall_no_result_next_action()}[/dim]")
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
        console.print(f"[dim]{_recall_hit_next_action()}[/dim]")
        return

    # compact (默认)
    if not cards:
        console.print("[yellow]没有匹配的卡片。[/yellow]")
        console.print(f"[dim]{_recall_no_result_next_action()}[/dim]")
        return
    console.print(f"[bold]Recall[/bold] · {len(cards)} 项 (sort={sort})")
    for c in cards:
        console.print(
            f"- {c.id or c.path.stem} · {c.title or '(untitled)'} · "
            f"status={c.status} · track={c.track or '-'} · "
            f"value_score={c.value_score if c.value_score is not None else '-'}"
        )
    console.print(f"[dim]{_recall_hit_next_action()}[/dim]")




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

    cfg = _load_cfg(config, read_env=False)
    workdir = cfg.state.workdir  # type: ignore[attr-defined]
    idx_path = lx.default_index_path(workdir)
    card_scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    recall_stats = _recall_local_stats(card_scan.cards)

    # 当前配置的字段权重（解析用户别名）+ k1 / b + config_hash
    fw = lx.resolve_field_weights(cfg.search.bm25.fields)
    cur_k1 = cfg.search.bm25.k1
    cur_b = cfg.search.bm25.b
    cur_hash = lx.compute_config_hash(field_weights=fw, k1=cur_k1, b=cur_b)

    index: lx.BM25Index
    used_disk = False
    index_stale = False
    index_source = "memory-temp"
    if idx_path.exists():
        try:
            index = lx.BM25Index.load(idx_path)
            if index.config_hash and index.config_hash != cur_hash:
                # 配置漂移 → 旧索引按旧权重打分，结果不能信
                index_stale = True
                index_source = "memory-rebuilt-stale"
                if output_format not in ("json",):
                    console.print(
                        "[yellow]提示：磁盘索引的 config_hash 与当前配置不一致；"
                        "本次内存即时重建。建议运行 `mindforge index rebuild`。[/yellow]"
                    )
                index = lx.build_index(card_scan.cards, field_weights=fw, k1=cur_k1, b=cur_b, config_hash=cur_hash)
            else:
                used_disk = True
                index_source = "disk"
        except (lx.IndexFormatError, OSError, ValueError) as e:
            index_source = "memory-rebuilt-error"
            console.print(f"[yellow]索引文件不可用（{e}）；改为内存即时构建。[/yellow]")
            index = lx.build_index(card_scan.cards, field_weights=fw, k1=cur_k1, b=cur_b, config_hash=cur_hash)
    else:
        if output_format not in ("json",):
            console.print(
                "[yellow]提示：尚无索引文件，本次内存即时构建。"
                "建议运行 `mindforge index rebuild` 以加速后续查询。[/yellow]"
            )
        index = lx.build_index(card_scan.cards, field_weights=fw, k1=cur_k1, b=cur_b, config_hash=cur_hash)

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

        cards_for_hybrid = card_scan.cards
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
            "index": {
                "source": index_source,
                "used_disk": used_disk,
                "path": str(idx_path),
                "suggest_rebuild": _recall_should_suggest_rebuild(index_source, index_stale),
                "card_counts": recall_stats,
            },
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
        print(_recall_search_summary(
            query=query,
            index_source=index_source,
            index_path=idx_path,
            used_disk=used_disk,
            index_stale=index_stale,
            stats=recall_stats,
        ))
        if not hits:
            print("_(no cards matched)_")
            print("\n" + _recall_no_result_next_action(recall_stats))
            return
        for rank, h in enumerate(hits, start=1):
            d = h.doc
            hh = hybrid_by_path.get(d.rel_path)
            score_str = f"score={(hh.final_score if hh else h.score):.3f}"
            print(
                f"- **#{rank} [{d.id or Path(d.rel_path).stem}]** {d.title or '(untitled)'}  "
                f"`{score_str}` `source={d.source_type or '-'}` "
                f"`status={_recall_status_label(d.status)}` `track={d.track or '-'}` "
                f"`terms={_hit_terms(h)}` `path={d.rel_path}`"
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
        print("\n" + _recall_hit_next_action())
        return

    if output_format == "table":
        _print_recall_search_summary(
            query=query,
            index_source=index_source,
            index_path=idx_path,
            used_disk=used_disk,
            index_stale=index_stale,
            stats=recall_stats,
        )
        if not hits:
            console.print("[yellow]没有匹配的卡片。[/yellow]")
            console.print(f"[dim]{_recall_no_result_next_action(recall_stats)}[/dim]")
            return
        table = Table(title=f"Recall · {len(hits)} 项 ({label})")
        table.add_column("rank", justify="right")
        table.add_column("score", justify="right")
        table.add_column("title")
        table.add_column("source")
        table.add_column("status")
        table.add_column("matched terms")
        table.add_column("next")
        for rank, h in enumerate(hits, start=1):
            d = h.doc
            hh = hybrid_by_path.get(d.rel_path)
            score_val = hh.final_score if hh else h.score
            table.add_row(
                str(rank),
                f"{score_val:.3f}",
                d.title or "(untitled)",
                d.source_type or "-",
                _recall_status_label(d.status),
                _hit_terms(h),
                "review weekly",
            )
        console.print(table)
        console.print(f"[dim]{_recall_hit_next_action()}[/dim]")
        return

    # compact（默认）
    _print_recall_search_summary(
        query=query,
        index_source=index_source,
        index_path=idx_path,
        used_disk=used_disk,
        index_stale=index_stale,
        stats=recall_stats,
    )
    if not hits:
        console.print("[yellow]没有匹配的卡片。[/yellow]")
        print(_recall_no_result_next_action(recall_stats))
        return
    console.print(f"[bold]Recall[/bold] · {len(hits)} 项 ({label})")
    for rank, h in enumerate(hits, start=1):
        d = h.doc
        hh = hybrid_by_path.get(d.rel_path)
        score_val = hh.final_score if hh else h.score
        console.print(
            f"- score={score_val:.3f} · rank=#{rank} · {d.id or Path(d.rel_path).stem} · "
            f"{d.title or '(untitled)'} · source={d.source_type or '-'} · "
            f"status={_recall_status_label(d.status)} · terms={_hit_terms(h)}"
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
    console.print(f"[dim]{_recall_hit_next_action()}[/dim]")


def _recall_local_stats(cards) -> dict[str, int]:
    """汇总 recall 空状态需要的本地计数；只读 CardSummary 安全字段。

    这里不用 state.json，也不读 source 原文，避免 search UX 越界成诊断全仓库的
    重流程。计数只帮助用户判断下一步是 approve、process 还是 rebuild。
    """
    stats = {"total": 0, "human_approved": 0, "ai_draft": 0, "other": 0}
    for c in cards:
        stats["total"] += 1
        if c.status == "human_approved":
            stats["human_approved"] += 1
        elif c.status == "ai_draft":
            stats["ai_draft"] += 1
        else:
            stats["other"] += 1
    return stats


def _recall_should_suggest_rebuild(index_source: str, index_stale: bool) -> bool:
    """判断是否建议 rebuild；不把临时内存索引误说成失败。"""
    return index_stale or index_source != "disk"


def _recall_search_summary(
    *,
    query: str,
    index_source: str,
    index_path: Path,
    used_disk: bool,
    index_stale: bool,
    stats: dict[str, int],
) -> str:
    """生成 recall 搜索摘要；stdout 可显示 query，但 telemetry 仍只写 hash。"""
    suggest = "yes" if _recall_should_suggest_rebuild(index_source, index_stale) else "no"
    index_label = (
        "disk index" if used_disk else "temporary in-memory index"
    )
    return (
        f"Search query: {query}\n"
        f"Index: {index_label} (source={index_source}, suggest_rebuild={suggest}, path={index_path})\n"
        f"Cards: approved={stats['human_approved']} ai_draft={stats['ai_draft']} total={stats['total']}\n"
        "Boundary: local lexical recall only; no RAG, no embedding, no LLM, no .env, no upload.\n"
    )


def _print_recall_search_summary(
    *,
    query: str,
    index_source: str,
    index_path: Path,
    used_disk: bool,
    index_stale: bool,
    stats: dict[str, int],
) -> None:
    """用普通文本打印搜索摘要，避免 Rich markup 吞掉 query 中的方括号。"""
    print(
        _recall_search_summary(
            query=query,
            index_source=index_source,
            index_path=index_path,
            used_disk=used_disk,
            index_stale=index_stale,
            stats=stats,
        ).rstrip()
    )


def _hit_terms(h) -> str:
    """从 SearchHit 提取匹配 term 摘要；不返回任何原文片段。"""
    terms: list[str] = []
    for fh in h.field_hits:
        for term in fh.term_counts:
            if term not in terms:
                terms.append(term)
    return ",".join(terms[:6]) or "-"


def _recall_status_label(status: str) -> str:
    """把状态翻译成搜索风险提示，明确 draft 不是正式长期记忆。"""
    if status == "human_approved":
        return "human_approved/approved knowledge"
    if status == "ai_draft":
        return "ai_draft/risky draft"
    return status


def _recall_hit_next_action() -> str:
    """recall 命中后的学习流桥接提示；不改变检索结果本身。

    recall 的职责仍是只读检索 human_approved 卡片。v0.6.2 只在 CLI 末尾补
    下一步建议，避免把 search UX 误扩展成自动 review 或自动 approve。
    """
    return (
        "下一步：用 `mindforge review weekly` 安排复习；需要更多材料时运行 "
        "`mindforge process --profile fake --limit 1`，再手动 approve。"
    )


def _recall_no_result_next_action(stats: dict[str, int] | None = None) -> str:
    """recall 无结果时的恢复建议；保持纯本地、不调用 LLM。"""
    counts = ""
    if stats is not None:
        counts = (
            f"当前 approved cards={stats['human_approved']}，"
            f"ai_draft={stats['ai_draft']}。"
        )
    return (
        f"{counts}下一步：运行 `mindforge index rebuild`；如只有草稿，先运行 "
        "`mindforge approve list`；如资料不足，继续 process。也可以缩短 query、"
        "换同义词，或改用更具体的 title/track 关键词。"
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

    cfg = _load_cfg(config, read_env=False)
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

    cfg = _load_cfg(config, read_env=False)
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
# backup — v0.5.5 local export / recovery safety
# ---------------------------------------------------------------------------


@backup_app.command("export")
def backup_export(
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="备份输出目录；默认 .mindforge/backups/<timestamp>。",
    ),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """导出本地安全备份：已审核卡片摘要、state summary、review schedule。

    中文学习型说明：v0.5.5 的 backup/export 是恢复辅助，不是云同步。它只导出
    Knowledge Card frontmatter 白名单摘要和本地状态计数，不读取 `.env`，不复制
    source 原文、不上传 telemetry，也不会覆盖已存在备份目录。
    """
    from .cards import filter_cards, iter_cards

    cfg = _load_cfg(config, read_env=False)
    now = datetime.now().astimezone()
    if output_dir is None:
        safe_ts = now.isoformat(timespec="seconds").replace(":", "-")
        target = cfg.state.workdir / "backups" / f"mindforge-backup-{safe_ts}"
    else:
        target = output_dir.expanduser()
        if not target.is_absolute():
            target = Path.cwd() / target
    target = target.resolve()
    if target.exists():
        console.print(f"[red]✗ 备份目录已存在，拒绝覆盖：{target}[/red]")
        console.print("[dim]下一步：换一个 --output-dir，或先人工检查旧备份。[/dim]")
        raise typer.Exit(code=2)
    target.mkdir(parents=True)

    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    approved = filter_cards(scan.cards, status="human_approved")
    cards_payload = [_card_to_safe_dict(card) for card in approved]

    state_payload: dict[str, object]
    if cfg.state.state_path.exists():
        try:
            cp = Checkpoint.load(cfg.state.state_path, backup=False)
            state_payload = {
                "state_path": str(cfg.state.state_path),
                "exists": True,
                "count_by_status": cp.count_by_status(),
                "count_by_source_type": cp.count_by_source_type(),
            }
        except Exception as e:  # noqa: BLE001 - 只导出错误类别，不输出原始 state 内容
            state_payload = {
                "state_path": str(cfg.state.state_path),
                "exists": True,
                "error": f"{type(e).__name__}: {e}",
            }
    else:
        state_payload = {"state_path": str(cfg.state.state_path), "exists": False}

    schedule_payload = _build_review_schedule_export(approved, generated_at=now, days=7)
    manifest = {
        "version": 1,
        "generated_at": now.isoformat(timespec="seconds"),
        "vault_root": str(cfg.vault.root),
        "files": {
            "human_approved_cards": "human_approved_cards.json",
            "state_summary": "state_summary.json",
            "review_schedule": "review_schedule.json",
        },
        "safety": {
            "contains_env": False,
            "contains_source_raw_text": False,
            "contains_prompt_or_completion": False,
            "uploads_telemetry": False,
        },
    }

    _write_json(target / "manifest.json", manifest)
    _write_json(target / "human_approved_cards.json", {"count": len(cards_payload), "items": cards_payload})
    _write_json(target / "state_summary.json", state_payload)
    _write_json(target / "review_schedule.json", schedule_payload)
    (target / "README.md").write_text(
        "# MindForge Local Backup\n\n"
        "This backup contains safe summaries only: human_approved card metadata, "
        "state counters, and a local review schedule. It does not contain `.env`, "
        "source raw text, prompt/completion logs, telemetry upload data, or Obsidian formal-note writes.\n",
        encoding="utf-8",
    )

    console.print(f"[green]✓ backup exported[/green] {target}")
    console.print(f"  human_approved cards: {len(cards_payload)}")
    console.print("  files: manifest.json, human_approved_cards.json, state_summary.json, review_schedule.json")
    console.print("[dim]说明：未读取 .env，未上传 telemetry，未修改 Obsidian notes。[/dim]")


def _write_json(path: Path, payload: object) -> None:
    import json as _json

    path.write_text(_json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _build_review_schedule_export(cards: list, *, generated_at: datetime, days: int) -> dict[str, object]:
    """构建安全 review schedule 导出，不写系统日历、不读取正文。"""
    horizon = generated_at + timedelta(days=days)
    by_day: dict[str, list[dict[str, object]]] = {}
    for card in cards:
        if card.review_after is None:
            continue
        due_at = card.review_after if card.review_after.tzinfo else card.review_after.replace(tzinfo=generated_at.tzinfo)
        if due_at <= generated_at:
            key = generated_at.date().isoformat()
        elif due_at <= horizon:
            key = due_at.date().isoformat()
        else:
            continue
        by_day.setdefault(key, []).append(_card_to_safe_dict(card))
    return {
        "version": 1,
        "generated_at": generated_at.isoformat(timespec="seconds"),
        "horizon_days": days,
        "total": sum(len(items) for items in by_day.values()),
        "days": [{"date": day, "count": len(items), "items": items} for day, items in sorted(by_day.items())],
    }


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

    cfg = _load_cfg(config, read_env=False)
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

    cfg = _load_cfg(config, read_env=False)

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

    cfg = _load_cfg(config, read_env=False)

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

    cfg = _load_cfg(config, read_env=False)
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

    cfg = _load_cfg(config, read_env=False)
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

obsidian_app = typer.Typer(
    add_completion=False,
    help="v0.5 Obsidian Binding：只读扫描真实 Obsidian vault，候选输出只进 staging/review。",
)
app.add_typer(obsidian_app, name="obsidian")


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

    cfg = _load_cfg(config, read_env=False)
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

    cfg = _load_cfg(config, read_env=False)
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
# obsidian — v0.5 read-only binding / staging bridge
# ---------------------------------------------------------------------------


def _obsidian_vault_override(arg: Path | None) -> Path | None:
    import os

    if arg is not None:
        return arg.expanduser().resolve()
    env = os.environ.get("MINDFORGE_OBSIDIAN_VAULT_OVERRIDE")
    return Path(env).expanduser().resolve() if env else None


def _obsidian_options(
    cfg: MindForgeConfig,
    vault_override: Path | None,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> tuple[Path, object]:
    from .obsidian import ObsidianScanOptions, resolve_obsidian_vault

    vault_root = resolve_obsidian_vault(
        cfg.obsidian,
        cfg.vault.root,
        override=_obsidian_vault_override(vault_override),
    )
    return vault_root, ObsidianScanOptions(
        vault_root=vault_root,
        include_dirs=tuple(include) if include else cfg.obsidian.include_dirs,
        exclude_dirs=(*cfg.obsidian.exclude_dirs, *(exclude or [])),
    )


def _obsidian_copy_warning() -> None:
    console.print(
        "[yellow]安全提示：请只对可丢弃、非敏感的 Obsidian vault 副本做 dry-run；"
        "MindForge 不会自动整理正式 notes。[/yellow]"
    )


def _print_obsidian_issues(vault_root: Path, issues: list[object]) -> None:
    """打印单文件跳过原因，不输出 note 正文。

    中文学习型说明：真实 vault 副本可能含坏 frontmatter 或工具生成的异常
    Markdown。这里输出路径和错误类别，足够定位摩擦点，但不泄漏正文内容。
    """
    if not issues:
        return
    table = Table(title="Skipped notes", show_lines=False)
    table.add_column("path", overflow="fold")
    table.add_column("reason", overflow="fold")
    for issue in issues:
        path = getattr(issue, "path")
        reason = getattr(issue, "reason")
        try:
            rel = Path(path).resolve().relative_to(vault_root).as_posix()
        except ValueError:
            rel = str(path)
        table.add_row(rel, str(reason))
    console.print(table)


def _resolve_obsidian_source_for_preview(source: Path, vault_root: Path) -> Path:
    """解析 stage source，兼容 cwd 路径和 vault 内相对路径。

    中文学习型说明：用户 dry-run 时常写 ``--vault demo --source demo`` 或从
    不同 cwd 传路径。解析顺序先尊重当前 cwd 中真实存在的路径，再回退到 vault
    内相对路径；后续仍要求 source 位于 vault 内，避免误处理外部资料。
    """
    raw = source.expanduser()
    if raw.is_absolute():
        return raw.resolve()
    cwd_candidate = raw.resolve()
    if cwd_candidate.exists():
        return cwd_candidate
    return (vault_root / raw).resolve()


def _first_markdown_hint(vault_root: Path) -> str:
    for path in sorted(vault_root.rglob("*.md")):
        if path.is_file():
            try:
                return path.relative_to(vault_root).as_posix()
            except ValueError:
                return str(path)
    return "<note.md>"


def _print_stage_preview(
    *,
    vault_root: Path,
    source: Path,
    target: Path | None,
    action: str,
    skipped_reason: str,
    content_hash: str = "-",
    title: str = "-",
    wikilinks: list[str] | None = None,
    frontmatter_keys: list[str] | None = None,
    source_type: str = "-",
    source_exists: bool | None = None,
    source_in_vault: bool | None = None,
) -> None:
    """输出 Obsidian stage dry-run preview，且不写文件。

    dry-run report 是 v0.5.3 的产品边界：它告诉用户将会发生什么、为什么
    可能跳过、下一步怎么确认，但不会修改正式 notes 或 staging 文件。
    v0.7.1 增加 note 结构摘要，但仍只来自 SourceDocument 安全元数据，不打印
    note 正文或 source raw_text。
    """
    if source_exists is None:
        source_exists = source.exists()
    if source_in_vault is None:
        source_in_vault = _safe_relative_to(source, vault_root) is not None
    table = Table(title="Obsidian stage preview", show_lines=False)
    table.add_column("field", style="bold")
    table.add_column("value", overflow="fold")
    table.add_row("mode", "dry-run")
    table.add_row("vault", str(vault_root))
    table.add_row("vault exists", "yes" if vault_root.exists() and vault_root.is_dir() else "no")
    table.add_row("source file", str(source))
    table.add_row("source exists", "yes" if source_exists else "no")
    table.add_row("source in vault", "yes" if source_in_vault else "no")
    table.add_row("proposed path", str(target) if target is not None else "-")
    table.add_row("proposed title", title or "-")
    table.add_row("detected wikilinks", ", ".join(wikilinks or []) or "-")
    table.add_row("frontmatter keys", ", ".join(frontmatter_keys or []) or "-")
    table.add_row("detected source type", source_type or "-")
    table.add_row("action type", action)
    table.add_row("skipped reason", skipped_reason or "-")
    table.add_row("source hash", content_hash)
    table.add_row("risk warning", "只对可丢弃、非敏感 vault 副本试跑；不修改正式 notes。")
    hint = _first_markdown_hint(vault_root)
    table.add_row(
        "next command",
        f"mindforge obsidian stage --vault {vault_root} --source {hint} --dry-run",
    )
    console.print(table)
    if skipped_reason:
        print(f"skipped reason: {skipped_reason}")
    console.print("[yellow]dry-run：未写任何文件，未移动 source note，未重写 wikilinks。[/yellow]")


def _safe_relative_to(path: Path, root: Path) -> str | None:
    """返回 path 相对 vault 的路径；失败返回 None 而不是抛错。

    Obsidian preview 经常处理用户手输路径。这里用显式 helper 避免在错误路径
    场景下泄漏 traceback，同时不吞掉后续真正写入分支的安全判断。
    """
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def _stage_preview_fields(doc) -> dict[str, object]:
    """提取 stage preview 可展示的 note 结构摘要，不读取/打印正文。"""
    frontmatter = doc.metadata.get("frontmatter") if isinstance(doc.metadata, dict) else {}
    if not isinstance(frontmatter, dict):
        frontmatter = {}
    return {
        "title": doc.title or Path(doc.source_path).stem,
        "wikilinks": list(doc.metadata.get("wikilinks") or []),
        "frontmatter_keys": sorted(str(k) for k in frontmatter.keys()),
        "source_type": doc.source_type,
    }


def _obsidian_export_filename(doc) -> str:
    """生成 staged export 文件名，避免依赖 obsidian.py 内部私有 slug helper。"""
    import re

    title = doc.title or Path(doc.source_path).stem
    slug = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]+", "-", title).strip("-")
    return (slug or "obsidian-candidate") + ".md"


def _unique_export_path(path: Path) -> Path:
    """返回不会覆盖已有文件的 staged export 路径。

    中文学习型说明：staged export 是人工检查目录，不是正式 vault 写入通道。
    因此遇到同名文件时生成唯一文件名，而不是覆盖或尝试自动合并，避免用户
    误以为 MindForge 已经替他们完成了 Obsidian note 决策。
    """
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for idx in range(2, 10_000):
        candidate = path.with_name(f"{stem}-{idx}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"无法生成唯一 staged export 文件名：{path}")


def _staged_export_dir(cfg: MindForgeConfig, output_dir: Path | None) -> Path:
    """解析 staged export 目录；用户显式路径优先，否则走 state.workdir。"""
    if output_dir is not None:
        return output_dir.expanduser().resolve()
    return (cfg.state.workdir / "staged" / "obsidian").expanduser().resolve()


def _formal_note_conflict_paths(vault_root: Path, filename: str) -> list[Path]:
    """只报告正式 vault 中可能冲突的同名 note，不自动覆盖、不自动迁移。"""
    conflicts: list[Path] = []
    for path in vault_root.rglob(filename):
        if not path.is_file():
            continue
        rel = _safe_relative_to(path, vault_root)
        if rel is None:
            continue
        if rel.startswith(".mindforge/") or rel.startswith("90-System/MindForge/"):
            continue
        conflicts.append(path)
    return sorted(conflicts)


def _print_staged_diff_preview(existing: Path, proposed_content: str) -> None:
    """打印 staged export 的轻量 diff；只比较 staged 目录，不写正式 notes。"""
    import difflib

    if not existing.exists():
        console.print("[dim]diff preview: staged target 不存在，将创建新文件。[/dim]")
        return
    old_lines = existing.read_text(encoding="utf-8").splitlines(keepends=True)
    new_lines = proposed_content.splitlines(keepends=True)
    diff = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=str(existing),
            tofile="proposed",
            n=3,
        )
    )
    console.print("[bold]diff preview[/bold] · staged directory only")
    if not diff:
        console.print("[dim]无差异。[/dim]")
        return
    for line in diff[:80]:
        console.print(line.rstrip("\n"), markup=False)
    if len(diff) > 80:
        console.print(f"[dim]... diff truncated, {len(diff) - 80} more lines[/dim]")


def _write_obsidian_staged_export(
    *,
    cfg: MindForgeConfig,
    vault_root: Path,
    source_path: Path,
    doc,
    content: str,
    output_dir: Path | None,
    diff_preview: bool,
) -> Path:
    """写 staged export markdown + manifest，明确不写正式 Obsidian notes。"""
    import json as _json

    export_dir = _staged_export_dir(cfg, output_dir)
    filename = _obsidian_export_filename(doc)
    proposed = export_dir / filename
    if diff_preview:
        _print_staged_diff_preview(proposed, content)
    target = _unique_export_path(proposed)
    manifest = target.with_suffix(".manifest.json")
    proposed_target = (vault_root / cfg.obsidian.review_dir / target.name).resolve()
    backup_path = (cfg.state.workdir / "backups" / "obsidian" / target.name).expanduser().resolve()
    export_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    payload = {
        "version": 1,
        "source_note": doc.source_path,
        "source_file": str(source_path),
        "staged_markdown": str(target),
        "proposed_file": str(target),
        "action": "staged-export-create" if target == proposed else "staged-export-create-unique",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "staged_export",
        "dry_run": False,
        "staged_export_dir": str(export_dir),
        "staged_output_policy": "explicit-output-dir" if output_dir is not None else "default-state-workdir",
        "safety": {
            "no_formal_obsidian_note_write": True,
            "no_real_llm": True,
            "no_env_read": True,
            "no_telemetry_upload": True,
            "no_runtime_logs_or_index_in_export": True,
        },
        "write_gate": {
            "proposed_target": str(proposed_target),
            "backup_path": str(backup_path),
            "recovery_plan": "restore backup_path, keep staged_markdown unchanged, then rerun preflight",
            "explicit_confirmation_required": True,
            "diff_preview_required": True,
            "writes_formal_notes_now": False,
        },
    }
    manifest.write_text(_json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    conflicts = _formal_note_conflict_paths(vault_root, target.name)
    console.print(f"[green]✓ staged export written[/green] {target}")
    console.print(f"[green]✓ manifest written[/green] {manifest}")
    if conflicts:
        console.print("[yellow]可能存在正式 vault 同名 note；仅提示人工检查，未覆盖：[/yellow]")
        for item in conflicts[:10]:
            console.print(f"  - {_safe_relative_to(item, vault_root) or item}")
    console.print("[dim]说明：未写正式 Obsidian notes；未移动 source；未读取 .env；未调用 LLM。[/dim]")
    return target


@obsidian_app.command("scan")
def obsidian_scan(
    vault: Path | None = typer.Option(
        None,
        "--vault",
        "--obsidian-vault",
        help="Obsidian vault 路径；覆盖 obsidian.vault_path。",
    ),
    include: list[str] | None = typer.Option(None, "--include", help="本次 scan 的 include pattern，可重复"),
    exclude: list[str] | None = typer.Option(None, "--exclude", help="本次 scan 的 exclude pattern，可重复"),
    limit: int = typer.Option(0, "--limit", min=0, help="最多展示多少条（0=全部）"),
    json_output: bool = typer.Option(False, "--json", help="输出 JSON 安全摘要"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """只读扫描 Obsidian Markdown note，输出安全摘要，不输出正文。"""
    from .obsidian import load_obsidian_documents_with_issues, summarize_doc

    cfg = _load_cfg(config, read_env=False)
    vault_root, options = _obsidian_options(cfg, vault, include=include, exclude=exclude)
    try:
        docs, issues = load_obsidian_documents_with_issues(options, limit=limit)
    except (FileNotFoundError, NotADirectoryError) as e:
        console.print(f"[red]✗ {e}[/red]")
        console.print("[dim]提示：传 --vault <ObsidianVault>，或配置 obsidian.vault_path。[/dim]")
        raise typer.Exit(code=2) from e

    rows = [summarize_doc(doc) for doc in docs]
    if json_output:
        import json as _json

        print(_json.dumps({"version": 1, "vault": str(vault_root), "notes": rows}, ensure_ascii=False))
        return

    _obsidian_copy_warning()
    console.print(
        f"[dim]scope: include={', '.join(options.include_dirs) or '<all markdown>'}; "
        f"exclude={', '.join(options.exclude_dirs) or '<default runtime dirs>'}[/dim]"
    )
    table = Table(title=f"Obsidian scan · {vault_root}", show_lines=False)
    for col in ("title", "relative_path", "tags", "wikilinks", "headings", "hash"):
        table.add_column(col, overflow="fold")
    for row in rows:
        table.add_row(
            str(row["title"] or ""),
            str(row["relative_path"]),
            ", ".join(row["tags"]) or "-",
            str(row["wikilink_count"]),
            str(row["heading_count"]),
            str(row["content_hash"])[:18] + "...",
        )
    console.print(table)
    console.print(
        f"[green]✓ scanned {len(rows)} Obsidian notes[/green] "
        "[dim](只读；未输出 note 全文；未写正式 notes)[/dim]"
    )
    if not rows:
        console.print(
            "[yellow]未发现 Markdown notes。请检查 --vault、include_dirs，或先复制一个"
            "非敏感 Obsidian vault 副本再 dry-run。[/yellow]"
        )
    _print_obsidian_issues(vault_root, issues)
    if (vault_root / ".obsidian").is_dir():
        console.print("[dim]检测到 .obsidian/；仅确认存在，未读取其配置内容。[/dim]")


@obsidian_app.command("links")
def obsidian_links(
    vault: Path | None = typer.Option(None, "--vault", "--obsidian-vault"),
    include: list[str] | None = typer.Option(None, "--include", help="本次 links 的 include pattern，可重复"),
    exclude: list[str] | None = typer.Option(None, "--exclude", help="本次 links 的 exclude pattern，可重复"),
    json_output: bool = typer.Option(False, "--json", help="输出 JSON"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """只读解析 Obsidian [[wikilinks]]，不建 graph DB、不改 note。"""
    from .obsidian import build_link_entries, load_obsidian_documents_with_issues

    cfg = _load_cfg(config, read_env=False)
    vault_root, options = _obsidian_options(cfg, vault, include=include, exclude=exclude)
    try:
        docs, issues = load_obsidian_documents_with_issues(options)
    except (FileNotFoundError, NotADirectoryError) as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(code=2) from e
    entries = build_link_entries(docs)
    if json_output:
        import json as _json

        print(_json.dumps({"version": 1, "vault": str(vault_root), "links": entries}, ensure_ascii=False))
        return

    _obsidian_copy_warning()
    table = Table(title=f"Obsidian links · {vault_root}", show_lines=False)
    table.add_column("note", overflow="fold")
    table.add_column("outgoing_links", overflow="fold")
    table.add_column("incoming", justify="right")
    for item in entries:
        table.add_row(
            item["note"],
            ", ".join(item["outgoing_links"]) or "-",
            str(item["incoming_count"]),
        )
    console.print(table)
    if not entries:
        console.print("[yellow]未发现可解析的 Markdown notes；未建立链接报告。[/yellow]")
    _print_obsidian_issues(vault_root, issues)
    console.print("说明：只读解析 [[wikilinks]]；不做 graph DB / RAG / embedding。", markup=False)


@obsidian_app.command("stage")
def obsidian_stage(
    source: Path = typer.Option(..., "--source", help="要生成 staging 候选的 Obsidian note"),
    vault: Path | None = typer.Option(None, "--vault", "--obsidian-vault"),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        help="输出目录；普通 staging 限定在 vault staging/review，--staged-export 时可为任意 staged export 目录。",
    ),
    staged_export: bool = typer.Option(False, "--staged-export", help="写入 staged export directory，不写正式 Obsidian notes"),
    diff_preview: bool = typer.Option(False, "--diff", help="显示 proposed markdown 与已有 staged file 的轻量 diff"),
    include: list[str] | None = typer.Option(None, "--include", help="本次 stage 的 include pattern，可重复"),
    exclude: list[str] | None = typer.Option(None, "--exclude", help="本次 stage 的 exclude pattern，可重复"),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--write",
        help="默认 dry-run；真正写入需 --write --confirm。",
    ),
    confirm: bool = typer.Option(False, "--confirm", help="搭配 --write 才允许落盘"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """把 Obsidian note 的候选加工结果写入 staging/review，而不是修改原 note。"""
    from .obsidian import build_stage_markdown, obsidian_path_in_scope, stage_output_path
    from .sources.obsidian_vault import ObsidianVaultSourceAdapter

    cfg = _load_cfg(config, read_env=False)
    vault_root, options = _obsidian_options(cfg, vault, include=include, exclude=exclude)
    _obsidian_copy_warning()
    source_path = _resolve_obsidian_source_for_preview(source, vault_root)
    if not vault_root.exists() or not vault_root.is_dir():
        _print_stage_preview(
            vault_root=vault_root,
            source=source_path,
            target=None,
            action="skipped",
            skipped_reason="Obsidian vault 不存在或不是目录；请检查 --vault。",
            source_exists=source_path.exists(),
            source_in_vault=_safe_relative_to(source_path, vault_root) is not None,
        )
        return
    if _safe_relative_to(source_path, vault_root) is None:
        if dry_run:
            _print_stage_preview(
                vault_root=vault_root,
                source=source_path,
                target=None,
                action="skipped",
                skipped_reason="--source 必须位于 Obsidian vault 内，避免误处理外部资料。",
                source_exists=source_path.exists(),
                source_in_vault=False,
            )
            return
        console.print("[red]✗ --source 必须位于 Obsidian vault 内，避免误处理真实外部资料。[/red]")
        raise typer.Exit(code=2) from None
    if not source_path.exists():
        if dry_run:
            _print_stage_preview(
                vault_root=vault_root,
                source=source_path,
                target=None,
                action="skipped",
                skipped_reason="source note 不存在。",
                source_exists=False,
                source_in_vault=True,
            )
            return
        console.print(f"[red]✗ source note 不存在：{source_path}[/red]")
        raise typer.Exit(code=2)
    if source_path.is_dir():
        if dry_run:
            _print_stage_preview(
                vault_root=vault_root,
                source=source_path,
                target=None,
                action="skipped",
                skipped_reason="--source 是目录；stage 需要单个 Markdown note。",
                source_exists=True,
                source_in_vault=True,
            )
            return
        console.print(f"[red]✗ --source 是目录；请传单个 Markdown note：{source_path}[/red]")
        raise typer.Exit(code=2)
    if source_path.suffix.lower() != ".md":
        if dry_run:
            _print_stage_preview(
                vault_root=vault_root,
                source=source_path,
                target=None,
                action="skipped",
                skipped_reason="--source 不是 Markdown 文件。",
                source_exists=True,
                source_in_vault=True,
            )
            return
        console.print(f"[red]✗ --source 不是 Markdown 文件：{source_path}[/red]")
        raise typer.Exit(code=2)
    in_scope, scope_reason = obsidian_path_in_scope(source_path, options)  # type: ignore[arg-type]
    if not in_scope:
        if dry_run:
            _print_stage_preview(
                vault_root=vault_root,
                source=source_path,
                target=None,
                action="skipped",
                skipped_reason=f"source 不在当前 include/exclude scope：{scope_reason}。",
                source_exists=True,
                source_in_vault=True,
            )
            return
        console.print(f"[red]✗ source 不在当前 include/exclude scope：{scope_reason}。[/red]")
        raise typer.Exit(code=2)

    adapter = ObsidianVaultSourceAdapter(vault_root)
    try:
        doc = adapter.load(str(source_path))
    except Exception as e:  # noqa: BLE001 - 只打印安全错误摘要，不输出 note 正文
        if dry_run:
            _print_stage_preview(
                vault_root=vault_root,
                source=source_path,
                target=None,
                action="skipped",
                skipped_reason=f"source 解析失败：{type(e).__name__}: {e}",
                source_exists=True,
                source_in_vault=True,
            )
            return
        console.print(f"[red]✗ source 解析失败：{type(e).__name__}: {e}[/red]")
        raise typer.Exit(code=2) from e
    if staged_export:
        target = _staged_export_dir(cfg, output_dir) / _obsidian_export_filename(doc)
    else:
        try:
            target = stage_output_path(vault_root, cfg.obsidian, doc, output_dir)
        except ValueError as e:
            console.print(f"[red]✗ {e}[/red]")
            raise typer.Exit(code=2) from e
    content = build_stage_markdown(doc)

    if dry_run:
        preview_fields = _stage_preview_fields(doc)
        _print_stage_preview(
            vault_root=vault_root,
            source=source_path,
            target=target,
            action=(
                "would-create-staged-export"
                if staged_export and not target.exists()
                else "would-update-staged-export"
                if staged_export
                else "would-create-staging-candidate"
                if not target.exists()
                else "would-update-staging-candidate"
            ),
            skipped_reason="",
            content_hash=doc.content_hash,
            title=str(preview_fields["title"]),
            wikilinks=list(preview_fields["wikilinks"]),  # type: ignore[arg-type]
            frontmatter_keys=list(preview_fields["frontmatter_keys"]),  # type: ignore[arg-type]
            source_type=str(preview_fields["source_type"]),
            source_exists=True,
            source_in_vault=True,
        )
        return
    if not confirm:
        console.print("[red]✗ 写入 staging 需要显式 --write --confirm。[/red]")
        raise typer.Exit(code=2)

    if staged_export:
        _write_obsidian_staged_export(
            cfg=cfg,
            vault_root=vault_root,
            source_path=source_path,
            doc=doc,
            content=content,
            output_dir=output_dir,
            diff_preview=diff_preview,
        )
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    console.print(f"[green]✓ staged[/green] {target}")
    console.print("[dim]说明：未修改 source note、未移动文件、未重写 wikilinks、未 auto approve。[/dim]")


@obsidian_app.command("preflight")
def obsidian_preflight_cmd(
    manifest: Path = typer.Option(..., "--manifest", help="staged export manifest JSON 路径"),
    vault: Path | None = typer.Option(None, "--vault", "--obsidian-vault"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """只读检查 staged export 是否具备未来 write-gate 条件；本版本不写正式 notes。"""
    from .obsidian import obsidian_preflight, resolve_obsidian_vault

    cfg = _load_cfg(config, read_env=False)
    vault_root = resolve_obsidian_vault(
        cfg.obsidian,
        cfg.vault.root,
        override=_obsidian_vault_override(vault),
    )
    result = obsidian_preflight(
        vault_root=vault_root,
        manifest_path=manifest,
        default_staged_root=cfg.state.workdir / "staged" / "obsidian",
    )

    _obsidian_copy_warning()
    console.print(f"[bold]MindForge Obsidian preflight[/bold] · {result.status}")
    table = Table(title="Write-gate prep", show_lines=False)
    table.add_column("field", style="bold")
    table.add_column("value", overflow="fold")
    table.add_row("status", result.status)
    table.add_row("manifest", str(result.manifest_path))
    table.add_row("staged markdown", str(result.staged_markdown or "-"))
    table.add_row("proposed target", str(result.proposed_target or "-"))
    table.add_row("backup path", str(result.backup_path or "-"))
    table.add_row("recovery plan", result.recovery_plan or "-")
    table.add_row("formal note writes", "NO - v0.7.4 only validates write-gate readiness")
    table.add_row("future gate", "staged export -> diff preview -> backup -> explicit confirmation")
    console.print(table)

    if result.blocked:
        console.print("[red]BLOCKED reasons[/red]")
        for reason in result.blocked:
            console.print(f"  - {reason}", markup=False)
            print(f"BLOCKED reason: {reason}")
    if result.warnings:
        console.print("[yellow]WARNING reasons[/yellow]")
        for reason in result.warnings:
            console.print(f"  - {reason}", markup=False)
            print(f"WARNING reason: {reason}")
    if result.status == "PASS":
        console.print("[green]PASS: staged export is ready for manual inspection.[/green]")
    elif result.status == "WARNING":
        console.print("[yellow]WARNING: inspect conflicts manually before any future confirmation.[/yellow]")
    else:
        console.print("[red]BLOCKED: staged export is not ready for any future write gate.[/red]")
    console.print(
        "Next: manually inspect the staged markdown and diff; future write requires explicit confirmation.",
        markup=False,
    )
    print("future gate: staged export -> diff preview -> backup -> explicit confirmation")
    console.print("说明：本版本不会写正式 Obsidian notes，不会读取 .env，不会调用真实 LLM。", markup=False)
    if result.status == "BLOCKED":
        raise typer.Exit(code=2)


@obsidian_app.command("doctor")
def obsidian_doctor(
    vault: Path | None = typer.Option(None, "--vault", "--obsidian-vault"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """检查 Obsidian binding 安全边界。"""
    from .obsidian import obsidian_doctor_rows, resolve_obsidian_vault

    cfg = _load_cfg(config, read_env=False)
    vault_root = resolve_obsidian_vault(
        cfg.obsidian,
        cfg.vault.root,
        override=_obsidian_vault_override(vault),
    )
    rows = obsidian_doctor_rows(vault_root, cfg.obsidian)
    console.print(f"[bold]MindForge Obsidian doctor[/bold] · {vault_root}")
    _obsidian_copy_warning()
    for state, label, detail in rows:
        console.print(f"  {_doctor_icon(state)} {label:<20}: {detail}")
    staged_dir = (cfg.state.workdir / "staged" / "obsidian").expanduser().resolve()
    staged_count = len(list(staged_dir.glob("*"))) if staged_dir.exists() else 0
    console.print(
        f"  {_doctor_icon('warn' if staged_count else 'ok')} {'staged export dir':<20}: "
        f"{staged_dir} · files={staged_count}"
    )
    if not vault_root.exists():
        console.print("[critical] 设置 Obsidian vault：mindforge obsidian doctor --vault <path>", markup=False)
        raise typer.Exit(code=2)
    console.print("[bold]Next steps[/bold]")
    console.print("  [recommended] mindforge obsidian scan --vault <path> --limit 20", markup=False)
    console.print("  [recommended] mindforge obsidian links --vault <path>", markup=False)
    console.print(
        "  [info] mindforge obsidian stage --vault <path> --source <note.md> --dry-run",
        markup=False,
    )
    console.print(
        "  [info] mindforge obsidian stage --vault <path> --source <note.md> --staged-export --write --confirm",
        markup=False,
    )
    console.print("[dim]不建议、也不会直接修改正式 Obsidian notes。[/dim]")


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
    interactive: bool = typer.Option(
        False,
        "--interactive",
        help="交互式初始化：选择 vault 路径、telemetry、本次 active_profile",
    ),
) -> None:
    """初始化最小可用的 vault 骨架与配置文件。

    幂等保证：多次运行不会重复创建已存在的目录或覆盖用户文件；只有 ``--force``
    才允许覆写 MindForge 自带的模板。
    """
    from .init_cmd import VAULT_DIRS, build_plan, execute_plan, next_steps_hint

    # v0.5.2：init 的默认 configs 来自 package assets，而不是仓库根。
    # 这让 wheel 安装后的 `mindforge init` 仍可复制 mindforge.yaml /
    # learning_tracks.yaml / llm.example.yaml。vault 目录骨架仍由 VAULT_DIRS
    # 显式创建，不依赖 repo-root vault_template。
    from .assets_runtime import bundled_asset_path_for_process

    repo_root = bundled_asset_path_for_process()
    project_root = project_root.resolve()

    interactive_telemetry_enabled: bool | None = None
    interactive_active_profile: str | None = None

    if interactive:
        default_vault = Path("~/MindForgeVault").expanduser()
        profile_names = _available_profile_names(project_root, repo_root)
        default_profile = "fake" if "fake" in profile_names else (profile_names[0] if profile_names else "fake")
        console.print("[bold]MindForge init --interactive[/bold]")
        console.print("[dim]说明：telemetry 只写本地文件，不上传；init 不读取 .env、不调用 LLM。[/dim]")
        console.print(
            f"[dim]已注册 profile：{', '.join(profile_names) if profile_names else '(未能读取，默认 fake)'}[/dim]"
        )
        try:
            vault_text = typer.prompt("vault 路径", default=str(default_vault)).strip()
            if not vault_text:
                console.print("[red]✗ vault 路径不能为空。请重新运行 init --interactive。[/red]")
                raise typer.Exit(code=2)
            target_vault = Path(vault_text).expanduser().resolve()
            _validate_interactive_vault_target(target_vault, VAULT_DIRS)

            interactive_telemetry_enabled = typer.confirm(
                "启用本地 telemetry？（仅写 .mindforge/telemetry.jsonl，不上传）",
                default=True,
            )
            console.print(
                "[yellow]提示：真实 provider 需要单独配置 .env；MindForge init 不会读取 .env。[/yellow]"
            )
            profile_text = typer.prompt(
                "active_profile",
                default=default_profile,
            ).strip()
            if not profile_text:
                console.print("[red]✗ active_profile 不能为空。[/red]")
                raise typer.Exit(code=2)
            if profile_names and profile_text not in profile_names:
                console.print(
                    f"[red]✗ active_profile={profile_text!r} 不在已注册 profile 中：{profile_names}[/red]"
                )
                raise typer.Exit(code=2)
            interactive_active_profile = profile_text
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]已中断；尚未写入任何文件。[/yellow]")
            raise typer.Exit(code=130) from None
        except typer.Abort:
            console.print("\n[yellow]已中断；尚未写入任何文件。[/yellow]")
            raise typer.Exit(code=130) from None
    elif vault is not None:
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
        target_vault, project_root=project_root, repo_root=repo_root, force=force
    )

    console.print("[bold]MindForge init[/bold]")
    console.print(f"- vault.root  : {plan.vault_root}")
    console.print(f"- project root: {plan.project_root}")
    if force:
        console.print("- mode        : [yellow]--force (will overwrite templates)[/yellow]")
    if dry_run:
        console.print("- mode        : [yellow]--dry-run (no files written)[/yellow]")
    if interactive:
        console.print("- mode        : [cyan]--interactive[/cyan]")
        console.print(
            f"- telemetry   : enabled={interactive_telemetry_enabled} (local_only=True)"
        )
        console.print(f"- profile     : {interactive_active_profile}")

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

    cfg_dst = (project_root / "configs" / "mindforge.yaml").resolve()
    _rewrite_init_config(
        cfg_dst,
        vault_root=plan.vault_root,
        telemetry_enabled=interactive_telemetry_enabled,
        active_profile=interactive_active_profile,
    )

    console.print("\n[bold green]✓ MindForge initialized.[/bold green]")
    console.print("[bold]Next steps:[/bold]")
    for step in next_steps_hint():
        console.print(f"  {step}")
    console.print(
        "[dim]说明：init 不创建真实 .env、不读取 .env、不调用 LLM、不修改原始资料。[/dim]"
    )


def _available_profile_names(project_root: Path, repo_root: Path) -> list[str]:
    """只读 yaml profile 名，不读取 .env、不解析 provider 环境变量。"""
    import yaml as _yaml

    for cfg_path in (
        project_root / "configs" / "mindforge.yaml",
        repo_root / "configs" / "mindforge.yaml",
    ):
        if not cfg_path.exists():
            continue
        try:
            data = _yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            llm = data.get("llm") if isinstance(data, dict) else None
            profiles = llm.get("profiles") if isinstance(llm, dict) else None
            if isinstance(profiles, dict):
                return sorted(str(k) for k in profiles)
        except Exception:  # noqa: BLE001
            continue
    return ["fake"]


def _validate_interactive_vault_target(target_vault: Path, vault_dirs: tuple[str, ...]) -> None:
    if target_vault.exists() and not target_vault.is_dir():
        console.print(f"[red]✗ vault 路径不是目录：{target_vault}[/red]")
        raise typer.Exit(code=2)
    if not target_vault.exists():
        return
    visible = [p for p in target_vault.iterdir() if not p.name.startswith(".")]
    if not visible:
        return
    required = {"00-Inbox", "20-Knowledge-Cards", "30-Projects"}
    if required <= {p.name for p in target_vault.iterdir()}:
        return
    allowed = {Path(d).parts[0] for d in vault_dirs}
    unknown = [p.name for p in visible if p.name not in allowed]
    if unknown:
        console.print(
            f"[red]✗ 目标目录已存在且不是 MindForge vault：{target_vault}[/red]"
        )
        console.print(
            "[dim]请选择空目录，或指向已有 MindForge vault。检测到的非 vault 内容："
            f"{', '.join(sorted(unknown)[:5])}[/dim]"
        )
        raise typer.Exit(code=2)


def _rewrite_init_config(
    cfg_dst: Path,
    *,
    vault_root: Path,
    telemetry_enabled: bool | None,
    active_profile: str | None,
) -> None:
    # 把刚拷过来的 mindforge.yaml 改成本次 init 选择；否则 doctor 会指向模板路径。
    if not cfg_dst.exists():
        return
    try:
        import yaml as _yaml

        data = _yaml.safe_load(cfg_dst.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            return
        changed: list[str] = []
        vault_block = data.setdefault("vault", {})
        if isinstance(vault_block, dict) and vault_block.get("root") != str(vault_root):
            vault_block["root"] = str(vault_root)
            changed.append(f"vault.root → {vault_root}")
        if telemetry_enabled is not None:
            telemetry = data.setdefault("telemetry", {})
            if isinstance(telemetry, dict):
                if telemetry.get("enabled") != telemetry_enabled:
                    telemetry["enabled"] = telemetry_enabled
                    changed.append(f"telemetry.enabled → {telemetry_enabled}")
                if telemetry.get("local_only") is not True:
                    telemetry["local_only"] = True
                    changed.append("telemetry.local_only → True")
        if active_profile:
            llm = data.setdefault("llm", {})
            if isinstance(llm, dict) and llm.get("active_profile") != active_profile:
                llm["active_profile"] = active_profile
                changed.append(f"llm.active_profile → {active_profile}")
        if changed:
            cfg_dst.write_text(
                _yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            console.print(f"  rewrote {cfg_dst}  " + "；".join(changed))
    except Exception as e:  # noqa: BLE001
        console.print(f"[yellow]提示：未能改写 mindforge.yaml（{e}），请手工编辑 yaml。[/yellow]")


@config_app.command("show")
def config_show(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    output_format: str = typer.Option("text", "--format", help="text | json"),
) -> None:
    """展示当前本地配置视图；只读 yaml，不读 .env、不解析真实 provider。"""
    cfg = _load_cfg(config, read_env=False)
    payload = _config_ux_payload(config, cfg)
    if output_format == "json":
        import json as _json

        print(_json.dumps(payload, ensure_ascii=False, indent=2))
        return
    _print_config_ux_payload("MindForge config show", payload)


@config_app.command("doctor")
def config_doctor(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """诊断 setup/config 风险，并给出下一步命令。"""
    console.print(f"[bold]MindForge config doctor[/bold] · {config}")
    if not config.exists():
        console.print("[red]✗ config missing[/red]")
        console.print("Next: mindforge config init --output <path> --vault <vault>", markup=False)
        console.print("Safe defaults: fake provider, no .env, no real LLM, no Obsidian writes.", markup=False)
        raise typer.Exit(code=2)
    try:
        cfg = _apply_global_vault_override(load_mindforge_config(config))
    except ConfigError as e:
        console.print(f"[red]✗ config invalid[/red] {e}")
        console.print("Next: fix YAML, or run `mindforge config init --dry-run` to inspect a safe template.")
        raise typer.Exit(code=2) from e

    payload = _config_ux_payload(config, cfg)
    _print_config_ux_payload("Config status", payload)
    rows = _config_doctor_rows(cfg)
    console.print("[bold]Validation[/bold]")
    for state, label, detail, next_action in rows:
        console.print(f"  {_doctor_icon(state)} {label:<18}: {detail}")
        if next_action:
            console.print(f"    next: {next_action}", markup=False)
    if all(state != "error" for state, *_rest in rows):
        console.print("[green]✓ config looks safe for local fake-provider use[/green]")


@config_app.command("init")
def config_init(
    output: Path = typer.Option(Path("configs/mindforge.yaml"), "--output", "-o"),
    vault: Path = typer.Option(Path("vault"), "--vault", help="写入配置中的 vault.root"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只打印计划，不写文件"),
    force: bool = typer.Option(False, "--force", help="允许覆盖已有 config 文件"),
) -> None:
    """生成最小本地配置文件；默认 fake provider 且拒绝覆盖。

    中文学习型说明：这是 setup UX 的轻量入口，不替代 `mindforge init` 的 vault
    骨架创建；它只从 package asset 复制一份安全默认 yaml，并改写少量字段。
    """
    plan = _build_config_init_plan(output=output, vault=vault, force=force)
    _print_config_init_plan(plan, dry_run=dry_run)
    if dry_run:
        return
    if output.exists() and not force:
        console.print("[red]✗ config 已存在，拒绝覆盖。使用 --force 才会覆盖。[/red]")
        raise typer.Exit(code=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(plan["content"], encoding="utf-8")
    console.print(f"[green]✓ wrote config[/green] {output}")
    console.print("Next: mindforge config doctor --config <path>", markup=False)


@app.command("setup")
def setup_cmd(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    vault: Path = typer.Option(Path("vault"), "--vault"),
    dry_run: bool = typer.Option(True, "--dry-run/--write", help="默认 dry-run；--write 才落盘 config"),
    force: bool = typer.Option(False, "--force", help="搭配 --write 才允许覆盖 config"),
) -> None:
    """第一天 setup plan：CLI-first、默认 dry-run、默认 fake provider。"""
    console.print("[bold]MindForge setup[/bold]")
    console.print("Mode: dry-run" if dry_run else "Mode: write config", markup=False)
    console.print("Safety: fake provider, no .env, no real LLM, no Obsidian formal-note writes.", markup=False)
    plan = _build_config_init_plan(output=config, vault=vault, force=force)
    _print_config_init_plan(plan, dry_run=dry_run)
    console.print("Next after setup: mindforge start --config <path>", markup=False)
    if not dry_run:
        if config.exists() and not force:
            console.print("[red]✗ config 已存在，拒绝覆盖。使用 --force 才会覆盖。[/red]")
            raise typer.Exit(code=2)
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(plan["content"], encoding="utf-8")
        console.print(f"[green]✓ wrote config[/green] {config}")


def _config_ux_payload(config_path: Path, cfg: MindForgeConfig) -> dict[str, object]:
    """把 MindForgeConfig 压成 setup UX 摘要；不包含 secret 或 provider env 值。"""
    return {
        "config_path": str(config_path),
        "vault_root": str(cfg.vault.root),
        "paths": {
            "inbox": str(cfg.vault.inbox_path),
            "cards": str(cfg.vault.cards_path),
            "projects": str(cfg.vault.projects_path),
            "state": str(cfg.state.state_path),
            "runs": str(cfg.state.runs_path),
            "index": str(cfg.state.workdir / "index" / "bm25.json"),
            "review": "frontmatter review_after fields",
            "backups": str(cfg.state.workdir / "backups"),
        },
        "active_profile": cfg.llm.active_profile,
        "safe_by_default": {
            "fake_provider": cfg.llm.active_profile == "fake",
            "reads_env": False,
            "calls_real_llm": False,
            "writes_formal_obsidian_notes": False,
            "telemetry_upload": False,
        },
        "next": "mindforge doctor --paths",
    }


def _print_config_ux_payload(title: str, payload: dict[str, object]) -> None:
    """打印短配置摘要；保持 CLI 可扫读，不展开完整 yaml。"""
    console.print(f"[bold]{title}[/bold]")
    console.print(f"config        : {payload['config_path']}")
    console.print(f"vault.root    : {payload['vault_root']}")
    console.print(f"active_profile: {payload['active_profile']}")
    paths = payload["paths"]
    if isinstance(paths, dict):
        console.print("[bold]Paths[/bold]")
        for key, value in paths.items():
            console.print(f"  {key:<8}: {value}")
    safety = payload["safe_by_default"]
    if isinstance(safety, dict):
        console.print("[bold]Safety[/bold]")
        for key, value in safety.items():
            console.print(f"  {key:<28}: {value}")
    console.print(f"Next: {payload['next']}", markup=False)


def _config_doctor_rows(cfg: MindForgeConfig) -> list[tuple[str, str, str, str]]:
    """配置诊断行；只做路径和 package asset 可读性检查。

    这些检查不会创建目录，不会读取 `.env`，也不会调用 provider。路径可写性用
    父目录检查表示“setup 是否可恢复”，避免为了诊断而写探针文件。
    """
    rows: list[tuple[str, str, str, str]] = []
    rows.append((
        "ok" if cfg.vault.root.exists() else "warn",
        "vault.root",
        str(cfg.vault.root),
        "mindforge init --vault <path>" if not cfg.vault.root.exists() else "",
    ))
    for label, path in (
        ("cards dir", cfg.vault.cards_path),
        ("state parent", cfg.state.state_path.parent),
        ("index parent", (cfg.state.workdir / "index")),
        ("backup parent", (cfg.state.workdir / "backups")),
    ):
        parent = path if path.exists() else path.parent
        rows.append((
            "ok" if parent.exists() else "warn",
            label,
            str(path),
            "mindforge init --interactive" if not parent.exists() else "",
        ))
    profile_ok = cfg.llm.active_profile in cfg.llm.profiles
    rows.append((
        "ok" if profile_ok else "error",
        "active_profile",
        cfg.llm.active_profile,
        "edit mindforge.yaml llm.active_profile" if not profile_ok else "",
    ))
    try:
        from .assets_runtime import bundled_text

        bundled_text("configs", "mindforge.yaml")
        bundled_text("templates", "knowledge_card.md.j2")
        rows.append(("ok", "package assets", "configs/templates readable", ""))
    except Exception as e:  # noqa: BLE001
        rows.append(("error", "package assets", f"{type(e).__name__}: {e}", "reinstall MindForge"))
    rows.append(("ok", "env policy", "config UX does not read .env", ""))
    rows.append(("ok", "llm policy", "setup defaults to fake / no real LLM call", ""))
    return rows


def _build_config_init_plan(*, output: Path, vault: Path, force: bool) -> dict[str, object]:
    """从 package asset 生成安全 config 内容，保留用户显式路径优先。"""
    from .assets_runtime import bundled_text
    import yaml as _yaml

    raw = bundled_text("configs", "mindforge.yaml")
    data = _yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        raise typer.Exit(code=2)
    vault_block = data.setdefault("vault", {})
    if isinstance(vault_block, dict):
        vault_block["root"] = str(vault.expanduser().resolve())
    llm = data.setdefault("llm", {})
    if isinstance(llm, dict):
        llm["active_profile"] = "fake"
    telemetry = data.setdefault("telemetry", {})
    if isinstance(telemetry, dict):
        telemetry["local_only"] = True
    content = _yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    return {
        "output": output,
        "vault": vault.expanduser().resolve(),
        "exists": output.exists(),
        "force": force,
        "content": content,
    }


def _print_config_init_plan(plan: dict[str, object], *, dry_run: bool) -> None:
    console.print("[bold]Config init plan[/bold]")
    console.print(f"output : {plan['output']}")
    console.print(f"vault  : {plan['vault']}")
    console.print(f"exists : {plan['exists']}  force={plan['force']}")
    console.print("defaults: active_profile=fake, no .env read, no real LLM, no Obsidian writes", markup=False)
    if dry_run:
        console.print("[dim]dry-run: no files written[/dim]")


@dogfood_app.command("plan")
def dogfood_plan(
    vault: Path | None = typer.Option(
        None,
        "--vault",
        help="非敏感 disposable vault 副本路径；省略时使用全局 --vault 或 examples/demo-vault",
    ),
) -> None:
    """输出非敏感 dogfooding 命令路径；不执行、不读 .env、不写 vault。

    中文学习型说明：这是 checklist/命令导航层，不是自动化 runner。真实
    dogfooding 必须由用户拿可丢弃副本逐条执行，避免工具误改正式资料。
    """
    import os as _os

    chosen = vault or Path(_os.environ.get("MINDFORGE_VAULT_OVERRIDE", "examples/demo-vault"))
    console.print("[bold]MindForge non-sensitive dogfooding plan[/bold]")
    console.print(f"vault copy: {chosen}")
    print("Safety: disposable non-sensitive copy only; no .env, no real LLM, no Obsidian formal-note writes.")
    console.print("[bold]Commands[/bold]")
    for command, note in _dogfood_command_snippets(chosen):
        print(f"- {command}")
        print(f"  {note}")
    console.print("Checklist: docs/templates/NON_SENSITIVE_DOGFOODING_CHECKLIST.md", markup=False)


def _dogfood_command_snippets(vault: Path) -> list[tuple[str, str]]:
    """集中维护 dogfooding 命令，供 CLI 与测试共同使用，减少文档漂移。"""
    v = str(vault)
    return [
        (f"mindforge doctor --vault {v} --paths", "确认本地路径和安全边界"),
        (f"mindforge scan --vault {v}", "扫描非敏感 inbox"),
        (f"mindforge process --profile fake --limit 1 --vault {v}", "只用 fake provider 生成 ai_draft"),
        (f"mindforge approve list --vault {v}", "查看待人工批准草稿"),
        (f"mindforge approve show --card <card-path> --vault {v}", "预览单张草稿安全摘要"),
        (f"mindforge recall --query \"agent\" --vault {v}", "检索 human_approved knowledge"),
        (f"mindforge review weekly --vault {v}", "生成本周学习任务"),
        (f"mindforge backup export --vault {v} --output-dir /tmp/mindforge-backup", "导出安全备份"),
        (f"mindforge obsidian stage --vault {v} --source <note.md> --dry-run", "只预览 staging，不写正式 notes"),
        (f"mindforge today --vault {v}", "回到每日入口检查下一步"),
    ]


@app.command()
def doctor(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    vault: Path | None = typer.Option(
        None,
        "--vault",
        help="临时覆盖配置中的 vault.root（兼容 `mindforge doctor --vault PATH`）。",
    ),
    paths: bool = typer.Option(False, "--paths", help="展示本地会读/会写/不会写的目录边界"),
) -> None:
    """打印环境 + 配置 + 可选依赖 + .gitignore 风险快照。"""
    import importlib.util as _u
    import platform
    import shutil
    import subprocess
    import sys

    from . import __version__

    console.print(f"[bold]MindForge doctor[/bold]  v{__version__}")
    console.print("[dim]" + "─" * 72 + "[/dim]")
    console.print("[bold]Runtime[/bold]")
    console.print(f"  {_doctor_icon('ok')} Python            : {platform.python_version()} ({sys.executable})")
    console.print(f"  {_doctor_icon('info')} Platform          : {platform.platform()}")
    config_status = "ok" if config.exists() else "error"
    config_text = "exists" if config.exists() else "MISSING"
    console.print(f"  {_doctor_icon(config_status)} config path       : {config}  ({config_text})")

    if not config.exists():
        console.print("[dim]" + "─" * 72 + "[/dim]")
        console.print("[bold]Action items[/bold]")
        console.print(
            "  [critical] 缺少 mindforge.yaml → 运行: mindforge init --interactive",
            markup=False,
        )
        return

    cfg = _load_cfg(config, read_env=False)
    if vault is not None:
        from dataclasses import replace as _replace

        cfg = _replace(cfg, vault=_replace(cfg.vault, root=vault.expanduser().resolve()))
    vault_root = cfg.vault.root
    inbox = vault_root / cfg.vault.inbox_root
    cards_dir = vault_root / cfg.vault.cards_dir
    projects_dir = vault_root / cfg.vault.projects_dir
    state_dir = Path(cfg.state.workdir)

    console.print("[dim]" + "─" * 72 + "[/dim]")
    console.print("[bold]Vault[/bold]")
    for label, path in (
        ("vault.root", vault_root),
        ("inbox", inbox),
        ("knowledge cards", cards_dir),
        ("projects", projects_dir),
        ("state workdir", state_dir),
    ):
        console.print(f"  {_doctor_icon(_dir_state(path))} {label:<17}: {path}  ({_ok_dir(path)})")
    profile_state = "ok" if cfg.llm.active_profile in cfg.llm.profiles else "error"
    console.print(f"  {_doctor_icon(profile_state)} active_profile    : {cfg.llm.active_profile}")
    console.print(
        f"  {_doctor_icon('ok' if cfg.telemetry.local_only else 'warn')} telemetry.enabled : "
        f"{cfg.telemetry.enabled} (local_only={cfg.telemetry.local_only})"
    )

    pdf_ok = _u.find_spec("pypdf") is not None
    docx_ok = _u.find_spec("docx") is not None
    console.print("[dim]" + "─" * 72 + "[/dim]")
    console.print("[bold]Optional installs[/bold]")
    pdf_msg = "installed" if pdf_ok else r"missing (pip install mindforge\[pdf])"
    docx_msg = "installed" if docx_ok else r"missing (pip install mindforge\[docx])"
    console.print(f"  {_doctor_icon('ok' if pdf_ok else 'info')} pypdf       : {pdf_msg}")
    console.print(f"  {_doctor_icon('ok' if docx_ok else 'info')} python-docx : {docx_msg}")

    cwd = Path.cwd()
    env_file = cwd / ".env"
    gitignore = cwd / ".gitignore"
    console.print("[dim]" + "─" * 72 + "[/dim]")
    console.print("[bold]Safety[/bold]")
    if env_file.exists():
        ignored = False
        if gitignore.exists():
            try:
                ignored = ".env" in gitignore.read_text(encoding="utf-8").splitlines()
            except OSError:
                pass
        if ignored:
            console.print(
                f"  {_doctor_icon('ok')} .env             : present, gitignored (内容未被读取)"
            )
        else:
            console.print(
                f"  {_doctor_icon('error')} .env             : present BUT not in .gitignore；"
                "立即把 .env 加入 .gitignore，避免误提交。"
            )
    else:
        console.print(f"  {_doctor_icon('info')} .env             : not present")

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
                    f"  {_doctor_icon('warn')} git status       : 检测到运行时产物可能被加入暂存（请勿提交）："
                )
                for r in risky[:5]:
                    console.print(f"    {r}")
            else:
                console.print(f"  {_doctor_icon('ok')} git status       : 无敏感运行产物风险")
        except Exception:  # noqa: BLE001
            console.print(f"  {_doctor_icon('info')} git status       : (跳过)")

    console.print("[dim]" + "─" * 72 + "[/dim]")
    console.print("[bold]Recovery checks[/bold]")
    recovery_hints = _doctor_recovery_checks(cfg)
    for state, label, detail in recovery_hints["rows"]:
        console.print(f"  {_doctor_icon(state)} {label:<22}: {detail}")
    if paths:
        console.print("[dim]" + "─" * 72 + "[/dim]")
        console.print("[bold]Data safety paths[/bold]")
        for label, value in _doctor_paths(cfg):
            console.print(f"  {label:<18}: {value}")

    # ── v0.2.6: actionable hints ──────────────────────────────────────
    hints: list[tuple[str, str]] = []
    hints.extend(recovery_hints["actions"])
    if not cards_dir.exists():
        hints.append(("critical", "vault 目录缺失 → 运行: mindforge init --interactive"))
    if cfg.llm.active_profile not in cfg.llm.profiles:
        hints.append(
            ("critical", f"active_profile={cfg.llm.active_profile!r} 未在 llm.profiles 中定义 → 检查 mindforge.yaml")
        )
    elif cfg.llm.active_profile != "fake":
        hints.append(
            ("critical", "active_profile 非 fake：真实跑 process 前请先 `mindforge llm ping` 校验环境变量")
        )
    if cards_dir.exists():
        try:
            from .cards import iter_cards as _iter
            from . import lexical_index as _lx

            res = _iter(cfg.vault.root, cfg.vault.cards_dir)
            n_drafts = sum(1 for c in res.cards if c.status == "ai_draft")
            n_approved = sum(1 for c in res.cards if c.status == "human_approved")
            if not res.cards:
                hints.append(("recommended", "尚无 Knowledge Cards → 运行: mindforge scan && mindforge process"))
            elif n_drafts > 0:
                hints.append(
                    ("recommended", f"{n_drafts} 张 ai_draft 待人工审核 → 运行: mindforge approve list")
                )
            # v0.3.2: 没有 human_approved 但有 ai_draft → 提示 recall --include-drafts
            if res.cards and n_approved == 0 and n_drafts > 0:
                hints.append(
                    ("info", "暂无 human_approved 卡片 → 检索时加: mindforge recall --include-drafts")
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
                        ("recommended", f"{_overdue} 张卡片已 overdue → 运行: mindforge review backlog")
                    )
                elif _due_7:
                    hints.append(
                        ("recommended", f"{_due_7} 张卡片本周内到期 → 运行: mindforge review schedule --days 7")
                    )
            # v0.3.1: BM25 索引检查（缺失 / 配置漂移 / mtime 漂移）
            idx_path = _lx.default_index_path(cfg.state.workdir)  # type: ignore[attr-defined]
            if not idx_path.exists():
                if res.cards:
                    hints.append(("recommended", "BM25 索引缺失 → 运行: mindforge index rebuild"))
            else:
                try:
                    idx = _lx.BM25Index.load(idx_path)
                    fw_cur = _lx.resolve_field_weights(cfg.search.bm25.fields)
                    cur_h = _lx.compute_config_hash(
                        field_weights=fw_cur, k1=cfg.search.bm25.k1, b=cfg.search.bm25.b,
                    )
                    if idx.config_hash and idx.config_hash != cur_h:
                        hints.append(("recommended", "BM25 索引与 search 配置不一致 → 运行: mindforge index rebuild"))
                    else:
                        diff = _lx.diff_index(idx, res.cards)
                        if not diff.fresh:
                            hints.append(("recommended", "BM25 索引 stale（卡片有变更） → 运行: mindforge index rebuild"))
                except Exception:  # noqa: BLE001
                    hints.append(("recommended", "BM25 索引读取失败 → 运行: mindforge index rebuild"))
        except Exception:  # noqa: BLE001
            pass

    if hints:
        hints = list(dict.fromkeys(hints))
        hints.sort(key=lambda item: {"critical": 0, "recommended": 1, "info": 2}.get(item[0], 9))
        console.print("[dim]" + "─" * 72 + "[/dim]")
        console.print("[bold]Action items:[/bold]")
        for priority, h in hints:
            console.print(f"  [{priority}] {h}", markup=False)

    console.print(
        "[dim]说明：本命令不读 .env 内容、不发 HTTP、不打印 api_key / token。[/dim]"
    )


def _doctor_recovery_checks(cfg: MindForgeConfig) -> dict[str, list[tuple[str, str, str]]]:
    """doctor plus 的本地恢复检查。

    中文学习型说明：这些检查只读路径存在性、JSON/YAML 可读性和 package asset
    可访问性；不会读取 `.env`，不会调用 LLM，也不会写 vault 或 Obsidian notes。
    """
    rows: list[tuple[str, str, str]] = []
    actions: list[tuple[str, str]] = []

    state_path = cfg.state.state_path
    if state_path.exists():
        try:
            Checkpoint.load(state_path, backup=False)
            rows.append(("ok", "state.json", f"readable · {state_path}"))
        except Exception as e:  # noqa: BLE001
            rows.append(("error", "state.json", f"unreadable · {type(e).__name__}: {e}"))
            actions.append(("critical", "state.json 读取失败 → 先备份 .mindforge，再检查 JSON 或从 state.json.bak 恢复"))
    else:
        rows.append(("warn", "state.json", f"missing · {state_path}"))
        actions.append(("recommended", "state.json 缺失 → 运行: mindforge scan"))

    cards_dir = cfg.vault.cards_path
    rows.append(("ok" if cards_dir.is_dir() else "error", "cards dir", str(cards_dir)))
    if not cards_dir.is_dir():
        actions.append(("critical", "Knowledge Cards 目录缺失 → 运行: mindforge init --interactive"))

    index_path = cfg.state.workdir / "index" / "bm25.json"
    rows.append(("ok" if index_path.exists() else "warn", "bm25 index", str(index_path) if index_path.exists() else "missing"))
    if not index_path.exists():
        actions.append(("recommended", "BM25 索引缺失 → 运行: mindforge index rebuild"))

    try:
        from .assets_runtime import bundled_text

        bundled_text("configs", "mindforge.yaml")
        bundled_text("templates", "knowledge_card.md.j2")
        rows.append(("ok", "package assets", "configs/templates readable"))
    except Exception as e:  # noqa: BLE001
        rows.append(("error", "package assets", f"unreadable · {type(e).__name__}: {e}"))
        actions.append(("critical", "package assets 不可读 → 检查安装包或重新安装 MindForge"))

    demo = Path("examples/demo-vault")
    rows.append(("ok" if demo.is_dir() else "info", "demo vault", str(demo) if demo.is_dir() else "not in current cwd"))
    try:
        from .cards import filter_cards, iter_cards

        approved = filter_cards(iter_cards(cfg.vault.root, cfg.vault.cards_dir).cards, status="human_approved")
        schedule = _build_review_schedule_export(list(approved), generated_at=datetime.now().astimezone(), days=7)
        rows.append(("ok" if schedule["total"] else "info", "review schedule", f"{schedule['total']} item(s) in next 7 days"))
        if not schedule["total"]:
            actions.append(("info", "未来 7 天无复习任务 → 运行: mindforge review weekly 查看整体状态"))
    except Exception as e:  # noqa: BLE001
        rows.append(("warn", "review schedule", f"unavailable · {type(e).__name__}: {e}"))
    return {"rows": rows, "actions": actions}


def _doctor_paths(cfg: MindForgeConfig) -> list[tuple[str, str]]:
    return [
        ("reads inbox", str(cfg.vault.inbox_path)),
        ("reads cards", str(cfg.vault.cards_path)),
        ("reads state", str(cfg.state.state_path)),
        ("writes state", str(cfg.state.state_path)),
        ("writes runs", str(cfg.state.runs_path)),
        ("writes index", str(cfg.state.workdir / "index" / "bm25.json")),
        ("writes backups", str(cfg.state.workdir / "backups")),
        ("dry-run only", "obsidian stage defaults to --dry-run"),
        ("never writes", "formal Obsidian notes unless user explicitly writes staging/review"),
    ]


def _doctor_icon(state: str) -> str:
    return {
        "ok": "[green]✓[/green]",
        "warn": "[yellow]⚠[/yellow]",
        "error": "[red]✗[/red]",
        "info": "[dim]·[/dim]",
    }.get(state, "[dim]·[/dim]")


def _dir_state(p: Path) -> str:
    if not p.exists() or not p.is_dir():
        return "error"
    return "ok"


def _ok_dir(p: Path) -> str:
    if not p.exists():
        return "[red]missing[/red]"
    if not p.is_dir():
        return "[red]not a dir[/red]"
    return "[green]ok[/green]"


_COMMANDS_WITH_LOCAL_VAULT_OPTION = {"init", "obsidian", "setup"}


def _normalize_post_command_global_options(argv: list[str]) -> list[str]:
    """把后置 ``--vault`` 归一化为 Typer 全局参数位置。

    中文学习型说明：Typer 的全局 option 按规范应写成
    ``mindforge --vault PATH next``，但真实用户更自然地写
    ``mindforge next --vault PATH``。v0.5.1 在入口层做一个很小的 argv
    归一化，只移动非 ``init`` / ``obsidian`` 命令后面的 ``--vault``：

    - ``init --vault`` 是 init 自己的目标 vault 参数，不能搬动；
    - ``obsidian ... --vault`` 是 Obsidian 子命令自己的 vault 参数，不能搬动；
    - 其他命令的 ``--vault`` 表示覆盖 MindForge ``vault.root``，可以安全
      提前到全局位置。

    这避免给每个子命令重复加一遍 ``vault`` 参数，也不改变 Typer 原本
    合法的 ``mindforge --vault PATH <command>`` 写法。
    """
    if len(argv) < 3:
        return argv

    option_takes_value = {"--config", "-c", "--vault", "--obsidian-vault"}
    command_idx: int | None = None
    i = 1
    while i < len(argv):
        token = argv[i]
        if token == "--":
            return argv
        if token.startswith("-"):
            if token in option_takes_value and i + 1 < len(argv):
                i += 2
                continue
            i += 1
            continue
        command_idx = i
        break

    if command_idx is None:
        return argv
    nested_command = next(
        (a for a in argv[command_idx + 1:] if not a.startswith("-")),
        "",
    )
    if (
        argv[command_idx] in _COMMANDS_WITH_LOCAL_VAULT_OPTION
        or (argv[command_idx] == "config" and nested_command == "init")
    ):
        return argv

    moved: list[str] = []
    rest: list[str] = []
    i = 1
    while i < len(argv):
        token = argv[i]
        if i > command_idx and token == "--vault" and i + 1 < len(argv):
            moved.extend([token, argv[i + 1]])
            i += 2
            continue
        if i > command_idx and token.startswith("--vault="):
            moved.extend(["--vault", token.split("=", 1)[1]])
            i += 1
            continue
        rest.append(token)
        i += 1

    if not moved:
        return argv
    return [argv[0], *moved, *rest]


def main() -> None:
    """CLI 入口。``--debug`` 不传时静默 traceback，仅打印简短错误。

    设计动机：终端用户大多数时候只想看到"哪里坏了 + 怎么办"；完整 traceback
    属于开发者调试场景，按需开启。
    """
    import os
    import sys

    sys.argv = _normalize_post_command_global_options(sys.argv)
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


# ---------------------------------------------------------------------------
# v0.4.2: 产品体验闭环 — `mindforge commands` 与 `mindforge next`
# ---------------------------------------------------------------------------
# 设计意图（学习要点）
# --------------------
# 1. CLI 变多以后，`mindforge --help` 会按字母序铺平展示，新用户根本不知道
#    "下一步该敲哪一条"。这两条命令解决"命令发现"和"工作流引导"两个问题：
#    - `commands` 按"任务场景"分组，给每条命令一句中文"什么时候用"。
#    - `next` 读取当前 vault / state 的健康指标，给出"现在最该做的下一步"。
# 2. 这两条命令必须遵守 v0.x 安全核心：
#    - **不读 .env 内容**（仅检查文件是否存在）；
#    - **不调 LLM**（纯字符串模板 + 文件系统统计）；
#    - **不联网**；
#    - **不输出 raw_text / 卡片正文 / prompt / completion / api_key**。
# 3. `next` 的判定基于"显式可观察事实"：vault 是否存在、inbox 是否有文件、
#    state.json 是否有 raw / triaged 残留、卡片目录是否有 ai_draft、
#    .mindforge/index/ 是否存在、review backlog 是否非空 …… 都是文件系统能
#    答的问题，不需要任何 AI 推断。
# ---------------------------------------------------------------------------

# `commands` 的固定脚本：(group, command, "什么时候用")
_COMMAND_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "第一次开始",
        [
            ("mindforge start", "第一天入口：看状态、安全边界和下一条命令"),
            ("mindforge setup --dry-run", "预览本地 safe-by-default setup"),
            ("mindforge config show", "查看当前 config / vault / state 路径"),
            ("mindforge dogfood plan --vault PATH", "非敏感副本 dogfooding 命令路径"),
            ("mindforge init --vault PATH", "创建 vault 骨架与默认 configs"),
            ("mindforge doctor --paths", "健康检查 + 本地读写边界"),
        ],
    ),
    (
        "导入 / 处理资料",
        [
            ("mindforge scan", "扫 inbox，建 SourceDocument，刷 state.json"),
            ("mindforge process --profile fake --limit N", "离线 fake provider 生成 ai_draft"),
            ("mindforge status", "查看 state.json 中的处理进度"),
        ],
    ),
    (
        "审批 ai_draft",
        [
            ("mindforge approve list", "查看待人工批准的草稿"),
            ("mindforge approve show --card PATH", "预览单张草稿安全摘要"),
            ("mindforge approve --card PATH", "把单张卡片晋升为 human_approved"),
            ("mindforge approve --all --dry-run", "批量预览；不会自动 approve"),
        ],
    ),
    (
        "Recall",
        [
            ("mindforge index rebuild", "本地 BM25 索引重建（不联网）"),
            ("mindforge recall --query \"...\"", "本地词法检索"),
            ("mindforge recall --ranking hybrid --explain", "三路融合 + 评分解释"),
        ],
    ),
    (
        "Review",
        [
            ("mindforge review backlog", "overdue / today / upcoming / missing 四桶"),
            ("mindforge review schedule --days 7", "未来 N 天复习计划"),
            ("mindforge review weekly", "周报（不调 LLM）"),
            ("mindforge review mark --card PATH --result remembered", "标记复习结果"),
        ],
    ),
    (
        "Obsidian dry-run",
        [
            ("mindforge obsidian doctor --vault PATH", "检查只读 Obsidian 绑定边界"),
            ("mindforge obsidian scan --vault PATH", "只读扫描 Markdown note 安全摘要"),
            ("mindforge obsidian links --vault PATH", "只读解析 [[wikilinks]]"),
            ("mindforge obsidian stage --source NOTE --dry-run", "预览 staging 候选，不写正式 notes"),
        ],
    ),
    (
        "Backup / Doctor",
        [
            ("mindforge backup export", "导出本地安全备份（不含 .env / source 原文）"),
            ("mindforge doctor --paths", "检查恢复状态和本地读写边界"),
            ("mindforge vault index", "维护 _index.md 导航文件"),
            ("mindforge vault links", "维护 _link_candidates.md 双链建议"),
        ],
    ),
    (
        "Debug / Safety",
        [
            ("mindforge commands", "按目标查看命令导航"),
            ("mindforge config doctor", "诊断配置、package assets 和安全默认值"),
            ("mindforge next", "根据当前状态推荐下一步"),
            ("mindforge today", "每日待办 / review / index 状态"),
            ("mindforge version", "版本与运行配置摘要（不含 secret）"),
            ("mindforge telemetry status", "查看本地 telemetry 开关与文件路径"),
        ],
    ),
]


@app.command("commands")
def commands_cmd() -> None:
    """按"任务场景"列出 MindForge 所有命令 + 一句话用途说明。

    设计原则：
    - 仅从静态脚本生成，不读 vault、不读 .env、不发 HTTP；
    - 不调 LLM；
    - 不输出任何卡片正文 / raw_text / prompt / completion / api_key。
    """
    from . import __version__
    from rich.markup import escape

    console.print(f"[bold]MindForge[/bold] v{__version__} — 命令地图（按场景）\n")
    for group, items in _COMMAND_GROUPS:
        console.print(f"[bold cyan]{group}[/bold cyan]")
        for cmd, desc in items:
            console.print(f"  [green]{escape(cmd)}[/green]")
            console.print(f"    {escape(desc)}")
        console.print("")
    console.print(
        "[dim]说明：完整使用手册见 docs/USER_GUIDE.md，新手上路见 docs/GETTING_STARTED.md。"
        "本命令不读 .env、不发 HTTP、不调用 LLM。[/dim]"
    )


@dataclass(frozen=True)
class NextSuggestion:
    command: str
    reason: str
    priority: str


@dataclass(frozen=True)
class DailySnapshot:
    """个人每日入口的只读状态快照。

    中文学习型说明：v0.5.4 的 daily loop 只汇总可观察状态，不读取 source
    正文、不调用 LLM、不自动 approve，也不修改 Obsidian notes。它是产品引导层，
    不是 SourceAdapter / processor / recall 架构的一部分。
    """

    vault_root: str
    vault_exists: bool
    inbox_files: int
    state_exists: bool
    state_counts: dict[str, int]
    recent_sources: tuple[str, ...]
    card_counts: dict[str, int]
    review_overdue: int
    review_due_week: int
    index_exists: bool
    latest_run: str | None


def _daily_snapshot(cfg: MindForgeConfig) -> DailySnapshot:
    """读取本地 daily loop 所需的安全摘要。

    所有信息来自文件名、state.json 状态字段和 Knowledge Card frontmatter
    白名单字段；不会读取 `.env`、prompt、completion、source raw_text 或
    Obsidian 正式 note 正文。
    """
    from .cards import iter_cards

    vault_root = cfg.vault.root
    inbox_files = 0
    if cfg.vault.inbox_path.exists():
        inbox_files = sum(
            1 for p in cfg.vault.inbox_path.rglob("*") if p.is_file() and not p.name.startswith(".")
        )

    state_counts: dict[str, int] = {}
    recent_items: list[ItemState] = []
    if cfg.state.state_path.exists():
        try:
            cp = Checkpoint.load(cfg.state.state_path, backup=False)
            state_counts = cp.count_by_status()
            recent_items = sorted(
                (item for item in cp.all_items() if _state_source_belongs_to_vault(item, cfg.vault.root)),
                key=lambda it: it.processed_at or it.first_seen_at or datetime.min,
                reverse=True,
            )[:3]
        except Exception:
            state_counts = {"unreadable": 1}

    scan = iter_cards(vault_root, cfg.vault.cards_dir)
    card_counts: dict[str, int] = {}
    review_overdue = 0
    review_due_week = 0
    now = datetime.now().astimezone()
    for card in scan.cards:
        card_counts[card.status] = card_counts.get(card.status, 0) + 1
        if card.status != "human_approved" or card.review_after is None:
            continue
        due_at = card.review_after if card.review_after.tzinfo else card.review_after.replace(tzinfo=now.tzinfo)
        if due_at <= now:
            review_overdue += 1
        elif due_at <= now + timedelta(days=7):
            review_due_week += 1

    runs_dir = cfg.state.runs_path
    latest_run = None
    if runs_dir.exists():
        files = sorted((p for p in runs_dir.glob("*.jsonl") if p.is_file()), key=lambda p: p.stat().st_mtime)
        if files:
            latest_run = files[-1].name

    return DailySnapshot(
        vault_root=str(vault_root),
        vault_exists=vault_root.exists(),
        inbox_files=inbox_files,
        state_exists=cfg.state.state_path.exists(),
        state_counts=state_counts,
        recent_sources=tuple(item.source_path for item in recent_items),
        card_counts=card_counts,
        review_overdue=review_overdue,
        review_due_week=review_due_week,
        index_exists=(cfg.state.workdir / "index" / "bm25.json").exists(),
        latest_run=latest_run,
    )


def _state_source_belongs_to_vault(item: ItemState, vault_root: Path) -> bool:
    """判断 state 记录是否属于当前 vault。

    中文学习型说明：开发/packaged smoke 可能共用同一个 `.mindforge/state.json`，
    里面混有不同临时 vault 的历史 source。daily loop 不能把别的 vault 的路径
    显示成当前用户今天的进度，所以只展示当前 vault 内的绝对路径或普通相对路径。
    """
    p = Path(item.source_path)
    if not p.is_absolute():
        return True
    try:
        p.resolve().relative_to(vault_root.resolve())
        return True
    except ValueError:
        return False


def _snapshot_to_dict(snapshot: DailySnapshot) -> dict[str, object]:
    return {
        "vault_root": snapshot.vault_root,
        "vault_exists": snapshot.vault_exists,
        "inbox_files": snapshot.inbox_files,
        "state_exists": snapshot.state_exists,
        "state_counts": snapshot.state_counts,
        "recent_sources": list(snapshot.recent_sources),
        "card_counts": snapshot.card_counts,
        "review": {
            "overdue": snapshot.review_overdue,
            "due_this_week": snapshot.review_due_week,
        },
        "index_exists": snapshot.index_exists,
        "latest_run": snapshot.latest_run,
    }


def _print_daily_snapshot(snapshot: DailySnapshot) -> None:
    console.print("[bold]Daily status[/bold]")
    console.print(f"  vault        : {snapshot.vault_root}")
    console.print(f"  inbox files  : {snapshot.inbox_files}")
    console.print(
        "  cards        : "
        f"ai_draft={snapshot.card_counts.get('ai_draft', 0)} · "
        f"human_approved={snapshot.card_counts.get('human_approved', 0)}"
    )
    console.print(
        f"  review       : overdue={snapshot.review_overdue} · "
        f"due_this_week={snapshot.review_due_week}"
    )
    console.print(f"  index        : {'ready' if snapshot.index_exists else 'missing'}")
    console.print(f"  latest run   : {snapshot.latest_run or '-'}")
    if snapshot.recent_sources:
        console.print("  recent source:")
        for src in snapshot.recent_sources:
            console.print(f"    - {src}")
    else:
        console.print("  recent source: -")


def _print_next_actions(suggestions: list[NextSuggestion]) -> None:
    console.print("\n[bold]Next actions[/bold]")
    for item in suggestions:
        console.print(f"  [{item.priority}] → {item.command}", markup=False)
        console.print(f"    {item.reason}")


def _print_start_guidance(snapshot: DailySnapshot, suggestions: list[NextSuggestion]) -> None:
    """打印第一天 onboarding 状态，不触发任何写操作。

    中文学习型说明：`start` 是 CLI 产品入口，不是新的业务管线。它只把
    doctor/today/next 的只读信号组合成用户能理解的步骤，避免把 onboarding
    做成 Web UI/TUI 或隐藏式自动流程。
    """
    console.print("[bold]Onboarding status[/bold]")
    console.print(f"  vault exists        : {'yes' if snapshot.vault_exists else 'no'}")
    console.print(f"  initialized         : {'yes' if snapshot.state_exists else 'not yet / state missing'}")
    console.print(f"  sources in inbox    : {snapshot.inbox_files}")
    console.print(f"  ai_draft cards      : {snapshot.card_counts.get('ai_draft', 0)}")
    console.print(f"  human_approved      : {snapshot.card_counts.get('human_approved', 0)}")
    console.print(f"  bm25 index          : {'ready' if snapshot.index_exists else 'missing'}")
    console.print(
        f"  review schedule     : overdue={snapshot.review_overdue} · "
        f"due_this_week={snapshot.review_due_week}"
    )
    _print_next_actions(suggestions[:3])
    console.print(
        "\n[dim]安全默认：fake provider；start 不读 .env、不调 LLM、不发 HTTP、"
        "不写正式 Obsidian notes。[/dim]"
    )


def _next_suggestions(cfg: MindForgeConfig) -> list[NextSuggestion]:
    """根据 vault / state 当前状态，推断"下一步该做什么"。

    返回带 priority 的建议；JSON 仍保留 v0.4.2 的 command / reason 字段。

    判定来源全部是文件系统可观察事实，不做任何 AI 推断；
    每一条都对应一条用户能直接执行的命令。
    """
    suggestions: list[NextSuggestion] = []
    vault_root = cfg.vault.root
    inbox = cfg.vault.inbox_path
    cards = cfg.vault.cards_path
    projects_dir = cfg.vault.projects_path
    workdir = cfg.state.workdir

    # 1. vault 是否完整
    if not vault_root.exists():
        suggestions.append(
            NextSuggestion(
                f"mindforge init --vault {vault_root}",
                "vault 根目录不存在，先一键铺骨架",
                "critical",
            )
        )
        return suggestions
    if not inbox.exists() or not cards.exists():
        suggestions.append(
            NextSuggestion(
                "mindforge init",
                "vault 子目录缺失（00-Inbox/ 或 20-Knowledge-Cards/）",
                "critical",
            )
        )

    # 2. inbox 是否有原料（统计文件数即可，**不读内容**）
    inbox_files = 0
    if inbox.exists():
        for p in inbox.rglob("*"):
            if p.is_file() and not p.name.startswith("."):
                inbox_files += 1
    if inbox_files == 0:
        suggestions.append(
            NextSuggestion(
                f"# 把 markdown 放到 {inbox}/ManualNotes/ 或 Cubox/ 等子目录",
                "inbox 当前为空，没有可加工的原料",
                "info",
            )
        )

    # 3. state.json 是否有未处理（raw/triaged）
    state_path = workdir / "state.json"
    raw_or_triaged = 0
    drafts_in_state = 0
    if state_path.exists():
        try:
            import json as _json

            data = _json.loads(state_path.read_text(encoding="utf-8"))
            for entry in data.get("documents", {}).values():
                st = entry.get("status", "")
                if st in {"raw", "triaged"}:
                    raw_or_triaged += 1
        except Exception:
            pass
    if inbox_files > 0 and raw_or_triaged == 0 and not state_path.exists():
        suggestions.append(NextSuggestion("mindforge scan", "inbox 有文件但 state.json 还没建立", "critical"))
    elif raw_or_triaged > 0:
        suggestions.append(
            NextSuggestion(
                "mindforge process --limit 10",
                f"state 中有 {raw_or_triaged} 条未跑完 pipeline",
                "critical",
            )
        )

    # 4. ai_draft 待审核（**只**统计 frontmatter 的 status 字段）
    draft_count = 0
    if cards.exists():
        try:
            import yaml as _yaml

            for p in cards.rglob("*.md"):
                if p.name.startswith("_"):
                    continue
                try:
                    text = p.read_text(encoding="utf-8")
                    if not text.startswith("---"):
                        continue
                    end = text.find("\n---", 3)
                    if end < 0:
                        continue
                    fm = _yaml.safe_load(text[3:end]) or {}
                    if fm.get("status") == "ai_draft":
                        draft_count += 1
                except Exception:
                    continue
        except Exception:
            pass
    drafts_in_state = draft_count
    if draft_count > 0:
        suggestions.append(
            NextSuggestion(
                "mindforge approve list",
                f"有 {draft_count} 张 ai_draft 卡片等待审核（不会自动 approve）",
                "recommended",
            )
        )

    # 5. 索引是否存在
    index_path = workdir / "index" / "bm25.json"
    card_file_count = 0
    if cards.exists():
        card_file_count = sum(
            1
            for p in cards.rglob("*.md")
            if p.is_file() and not p.name.startswith("_")
        )
    if cards.exists() and not index_path.exists() and card_file_count > 0:
        # 即使全部 ai_draft，也给一次 rebuild 提示（recall --include-drafts 仍能用）。
        suggestions.append(
            NextSuggestion(
                "mindforge index rebuild",
                "BM25 索引尚未建立（recall 需要它）",
                "recommended",
            )
        )

    # 6. 复习 backlog
    overdue = 0
    if cards.exists():
        try:
            from datetime import datetime as _dt
            import yaml as _yaml

            now = _dt.now().astimezone()
            for p in cards.rglob("*.md"):
                if p.name.startswith("_"):
                    continue
                try:
                    text = p.read_text(encoding="utf-8")
                    if not text.startswith("---"):
                        continue
                    end = text.find("\n---", 3)
                    if end < 0:
                        continue
                    fm = _yaml.safe_load(text[3:end]) or {}
                    if fm.get("status") != "human_approved":
                        continue
                    ra = fm.get("review_after")
                    if not ra:
                        continue
                    if isinstance(ra, str):
                        try:
                            ra = _dt.fromisoformat(ra.replace("Z", "+00:00"))
                        except Exception:
                            continue
                    if hasattr(ra, "tzinfo") and ra.tzinfo is None:
                        ra = ra.replace(tzinfo=now.tzinfo)
                    if ra <= now:
                        overdue += 1
                except Exception:
                    continue
        except Exception:
            pass
    if overdue > 0:
        suggestions.append(
            NextSuggestion(
                "mindforge review backlog",
                f"有 {overdue} 张复习卡片已 overdue",
                "recommended",
            )
        )

    # 7. 项目上下文（有 30-Projects 文件即提示）
    project_count = 0
    if projects_dir.exists():
        project_count = sum(
            1
            for p in projects_dir.glob("*.md")
            if not p.name.startswith("_") and p.is_file()
        )
    if project_count > 0 and drafts_in_state >= 0:
        suggestions.append(
            NextSuggestion(
                "mindforge project list",
                f"vault 中有 {project_count} 个项目笔记，可生成 context pack",
                "info",
            )
        )

    # 8. 兜底：什么都没建议时给一条 doctor
    if not suggestions:
        suggestions.append(NextSuggestion("mindforge doctor", "看起来一切就绪；定期跑 doctor 自检", "info"))
    return _compact_next_suggestions(suggestions)


def _compact_next_suggestions(suggestions: list[NextSuggestion]) -> list[NextSuggestion]:
    suggestions = sorted(
        suggestions,
        key=lambda s: {"critical": 0, "recommended": 1, "info": 2}.get(s.priority, 9),
    )
    if len(suggestions) <= 5:
        return suggestions
    shown = suggestions[:4]
    hidden = len(suggestions) - len(shown)
    shown.append(
        NextSuggestion(
            "mindforge doctor",
            f"还有 {hidden} 条低优先级建议；运行 doctor 查看完整自检",
            "info",
        )
    )
    return shown


@app.command("start")
def start_cmd(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    output_format: str = typer.Option("text", "--format", "-f", help="text | json"),
) -> None:
    """第一天入口：展示当前状态、安全边界和下一条推荐命令。

    该命令只读本地文件系统和卡片 frontmatter，不会 init、scan、process、
    approve 或写 Obsidian notes。真正动作仍由用户显式执行。
    """
    if not config.exists():
        if output_format == "json":
            import json as _json

            print(
                _json.dumps(
                    {
                        "version": 1,
                        "error": "config_missing",
                        "next_command": "mindforge init --interactive",
                        "safety": _start_safety_dict(),
                    },
                    ensure_ascii=False,
                )
            )
        else:
            console.print("[bold]MindForge start[/bold]\n")
            console.print("[yellow]尚未找到配置。[/yellow]")
            console.print("  下一步：mindforge init --interactive", markup=False)
            console.print("[dim]安全默认：初始化不会调用真实 LLM；后续 process 默认 fake。[/dim]")
        return

    cfg = _load_cfg(config, read_env=False)
    snapshot = _daily_snapshot(cfg)
    suggestions = _next_suggestions(cfg)
    if output_format == "json":
        import json as _json

        print(
            _json.dumps(
                {
                    "version": 1,
                    "status": _snapshot_to_dict(snapshot),
                    "suggestions": [
                        {"command": s.command, "reason": s.reason, "priority": s.priority}
                        for s in suggestions
                    ],
                    "safety": _start_safety_dict(),
                },
                ensure_ascii=False,
            )
        )
        return

    console.print(f"[bold]MindForge start[/bold]  — vault: {cfg.vault.root}\n")
    _print_start_guidance(snapshot, suggestions)


def _start_safety_dict() -> dict[str, bool]:
    return {
        "default_fake_provider": True,
        "reads_env": False,
        "calls_real_llm": False,
        "writes_formal_obsidian_notes": False,
        "uploads_telemetry": False,
    }


@app.command("today")
def today_cmd(
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="mindforge.yaml 路径",
    ),
    output_format: str = typer.Option("text", "--format", "-f", help="text | json"),
) -> None:
    """每日入口：只读汇总待办、复习、索引和下一条命令。

    中文学习型说明：`today` 是 v0.5.4 的个人日常使用入口。它只读取本地状态
    与卡片 frontmatter 安全字段，不触发 process、不自动 approve、不读取
    `.env`、不调用真实 LLM，也不修改 Obsidian notes。
    """
    if not config.exists():
        if output_format == "json":
            import json as _json

            print(_json.dumps({"version": 1, "error": "config_missing"}, ensure_ascii=False))
        else:
            console.print("[yellow]配置不存在，先跑：mindforge init --interactive[/yellow]")
        return
    cfg = _load_cfg(config, read_env=False)
    snapshot = _daily_snapshot(cfg)
    suggestions = _next_suggestions(cfg)

    if output_format == "json":
        import json as _json

        print(
            _json.dumps(
                {
                    "version": 1,
                    "status": _snapshot_to_dict(snapshot),
                    "suggestions": [
                        {"command": s.command, "reason": s.reason, "priority": s.priority}
                        for s in suggestions
                    ],
                },
                ensure_ascii=False,
            )
        )
        return

    console.print(f"[bold]MindForge today[/bold]  — vault: {cfg.vault.root}\n")
    _print_daily_snapshot(snapshot)
    _print_next_actions(suggestions)
    console.print(
        "\n[dim]说明：today 只读本地状态和卡片 frontmatter；不读 .env、不调 LLM、"
        "不发 HTTP、不自动 approve。[/dim]"
    )


@app.command("next")
def next_cmd(
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="mindforge.yaml 路径",
    ),
    output_format: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="text | json",
    ),
) -> None:
    """根据 vault 当前状态，推荐"下一步该做什么"。

    安全契约（与 doctor 一致）：
    - 不读 .env 内容；
    - 不调 LLM；
    - 不发 HTTP；
    - 不输出卡片正文 / raw_text / prompt / completion；
    - 输出仅含命令字符串与中文原因，不含 secret。
    """
    if not config.exists():
        if output_format == "json":
            import json as _json

            print(_json.dumps({
                "version": 2,
                "error": "config_missing",
                "suggestions": [
                    {
                        "command": "mindforge init",
                        "reason": "configs/mindforge.yaml 不存在",
                        "priority": "critical",
                    }
                ],
            }, ensure_ascii=False))
        else:
            console.print("[yellow]配置不存在，先跑：[/yellow]")
            console.print("  [critical] mindforge init --interactive", markup=False)
        return
    try:
        cfg = _load_cfg(config, read_env=False)
    except typer.Exit:
        return

    suggestions = _next_suggestions(cfg)

    if output_format == "json":
        import json as _json

        print(
            _json.dumps(
                {
                    "version": 2,
                    "vault_root": str(cfg.vault.root),
                    "status": _snapshot_to_dict(_daily_snapshot(cfg)),
                    "suggestions": [
                        {
                            "command": item.command,
                            "reason": item.reason,
                            "priority": item.priority,
                        }
                        for item in suggestions
                    ],
                },
                ensure_ascii=False,
            )
        )
        return

    console.print(f"[bold]MindForge next[/bold]  — vault: {cfg.vault.root}\n")
    _print_daily_snapshot(_daily_snapshot(cfg))
    _print_next_actions(suggestions)
    console.print(
        "\n[dim]说明：本命令不读 .env、不调 LLM、不发 HTTP；"
        "建议来自文件系统可观察事实（state.json / 卡片 frontmatter / 索引文件）。[/dim]"
    )


if __name__ == "__main__":  # pragma: no cover
    main()
