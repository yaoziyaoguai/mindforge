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

from .app_context import AppContextError, load_app_config
from .checkpoint import Checkpoint
from .config import ConfigError, MindForgeConfig, load_mindforge_config
from .next_suggestions import (
    NextSuggestion,
    compact_next_suggestions,
    next_suggestions,
)
from .env_loader import load_dotenv_silently
from .llm import LLMClient, build_providers
from .models import ItemState, StageRecord
from .obsidian_cli import obsidian_app
from .provider_cli import provider_app
from .processors import Pipeline  # noqa: F401  -- 保留向后兼容的 re-export，避免外部测试或脚本因 import 路径中断
from .strategies import (
    DEFAULT_STRATEGY_NAME,
    StrategyContext,
    StrategyMetadata,
    UnknownStrategyError,
    NotYetImplementedStrategyError,
    available_strategies,
    build_strategy,
    list_strategies,
)
from .recall_service import (
    RecallQuery,
    RecallServiceError,
    recall_hit_next_action,
    recall_no_result_next_action,
    run_bm25_recall,
)
from .recall_presenter import RecallRenderContext, render_recall_result
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
        "新用户先跑这条命令（零 secret / 零网络 / 零 vault 写入）：\n"
        "  mindforge demo               — 60 秒 fake/safe tour，零配置即可看到端到端效果\n\n"
        "常用命令：\n"
        "  mindforge demo               — 60 秒新用户 tour，无需 API key / 网络 / vault\n"
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
app.add_typer(obsidian_app, name="obsidian")
app.add_typer(provider_app, name="provider")
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
    try:
        return load_app_config(config_path, vault_override=_global_vault_override())
    except AppContextError as e:
        if e.kind == "missing_config":
            console.print(f"[red]✗ 配置文件不存在：{config_path}[/red]")
            console.print(
                "[dim]提示：可以从仓库中的 configs/mindforge.yaml 复制一份到目标位置，"
                "再用 --config 指定，或直接在仓库根运行命令。[/dim]"
            )
            raise typer.Exit(code=2) from e
        console.print(f"[red]✗ 配置错误：{e}[/red]")
        console.print(
            "[dim]提示：请检查 vault.root、sources.enabled、llm.active_profile "
            "三个字段是否合法。[/dim]"
        )
        raise typer.Exit(code=2) from e


def _global_vault_override() -> Path | None:
    """读取 CLI 入口设置的 vault override；不读取 `.env` 文件。"""
    import os as _os

    override = _os.environ.get("MINDFORGE_VAULT_OVERRIDE")
    if not override:
        return None
    return Path(override)


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
def demo(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="输出机器可读 JSON (供 tests / CI 消费); 默认输出新用户可读文本。",
    ),
) -> None:
    """60 秒新用户 demo tour — 零 secret、零网络、零真实 vault 写入。

    中文学习型说明: 这是 MindForge 的 "1 分钟看到效果" 入口。它编排
    已有命令的 service 层 (CuboxApiAdapter / dogfood policy / vault
    probe), 把 SourceDocument → 路径分类 → vault 健康检查 → review
    packet 这条主链路跑给新用户看一眼。

    安全契约:
    - 不读取 ``.env`` 内容;
    - 不调用真实 Cubox HTTP API (使用仓库自带 fixture);
    - 不调用真实 LLM (走 fake-default 路径);
    - 不写任何 Obsidian vault (包括 ``.obsidian/``);
    - 不产生 ``human_approved`` 记录 (artifact_type=review_packet);
    - 不启用 RAG / embedding / semantic merge;
    - 不创建 tag, 不 release, 不 push。

    实现委托给 ``demo_tour.run_demo_tour``; CLI 只做 thin adapter
    (调用 + 渲染), 不持有业务规则。
    """
    from .demo_tour import render_demo_tour, run_demo_tour

    report = run_demo_tour()
    if json_output:
        import json as _json

        payload = {
            "all_ok": report.all_ok,
            "steps": [
                {
                    "name": s.name,
                    "title": s.title,
                    "ok": s.ok,
                    "summary": s.summary,
                    "detail": s.detail,
                }
                for s in report.steps
            ],
            "safety_invariants": list(report.safety_invariants),
            "next_actions": list(report.next_actions),
        }
        print(_json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_demo_tour(report))
    if not report.all_ok:
        raise typer.Exit(code=1)


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
            console.print("Next: mindforge process --profile fake --limit 1", markup=False)
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
    from .approval_service import approve_explicit_card
    from .approve_presenter import (
        render_execution_failure,
        render_execution_success,
    )

    with RunLogger(cfg.state.runs_path, command="approve") as logger:  # type: ignore[attr-defined]
        logger.emit("approval_started", card_path=str(card_path))
        result = approve_explicit_card(cfg, card_path)
        if result.error is not None:
            logger.emit(
                "approval_failed",
                card_path=str(card_path),
                error_message=result.error.message,
                prev_status=result.error.prev_status or "",
            )
            render_execution_failure(console, result.error)
            raise typer.Exit(code=result.error.exit_code)

        assert result.effect is not None
        effect = result.effect

        completed_fields: dict[str, object] = {
            "card_path": str(effect.card_path),
            "status": effect.new_status,
            "prev_status": effect.prev_status,
            "approval_method": effect.approval_method,
            "idempotent": effect.kind == "already_approved",
        }
        if effect.approved_at is not None:
            completed_fields["approved_at"] = effect.approved_at.isoformat()
        if effect.state_missing:
            completed_fields["state_missing"] = True
        logger.emit("approval_completed", **completed_fields)

    render_execution_success(console, result)


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
        from .approval_service import resolve_card_path_by_source_id
        from .approve_presenter import render_lookup_error

        lookup = resolve_card_path_by_source_id(cfg, source_id)
        if lookup.error is not None:
            render_lookup_error(console, lookup)
            raise typer.Exit(code=lookup.error.exit_code)
        assert lookup.card_path is not None
        _do_single_approve(lookup.card_path, cfg)
        return

    # ── --all 批量路径 ──────────────────────────────────────────
    if all_:
        _do_bulk_approve(cfg, dry_run=dry_run, confirm=confirm, limit=limit)
        return

    # 没给任何动作 → 友好提示
    from .approve_presenter import render_routing_hint

    render_routing_hint(console)
    raise typer.Exit(code=2)


def _do_bulk_approve(
    cfg: MindForgeConfig, *, dry_run: bool, confirm: bool, limit: int
) -> None:
    """--all 批量晋升执行体。

    为什么默认拒绝：批量批准是把"AI 草稿"一次性升级为"长期记忆"的危险动作，
    必须显式 ``--confirm`` 才能写入。``--dry-run`` 仅展示候选列表。
    """
    from .approval_service import build_bulk_approval_plan
    from .approve_presenter import (
        render_bulk_candidate_list,
        render_bulk_confirm_required,
        render_bulk_dry_run_footer,
        render_bulk_empty,
        render_bulk_summary,
    )

    plan = build_bulk_approval_plan(cfg, limit=limit)
    drafts = tuple(plan.candidates)

    if not drafts:
        render_bulk_empty(console)
        return

    render_bulk_candidate_list(console, drafts)

    if dry_run:
        render_bulk_dry_run_footer(console)
        return
    if not confirm:
        render_bulk_confirm_required(console)
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
    render_bulk_summary(console, ok=ok, fail=fail)


def _format_card_created_at(c) -> str:
    """已迁移到 approve_presenter.format_card_created_at；保留薄包装兼容。"""
    from .approve_presenter import format_card_created_at

    return format_card_created_at(c)


def _format_card_source_hint(c) -> str:
    """已迁移到 approve_presenter.format_card_source_hint；保留薄包装兼容。"""
    from .approve_presenter import format_card_source_hint

    return format_card_source_hint(c)


def _approve_next_command(c) -> str:
    """已迁移到 approve_presenter.approve_next_command；保留薄包装兼容。"""
    from .approve_presenter import approve_next_command

    return approve_next_command(c)


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
    from .approval_service import ApprovalListQuery, list_approval_candidates
    from .approve_presenter import (
        render_approval_list,
        render_approval_list_json,
    )

    cfg = _load_cfg(config, read_env=False)
    wanted = {s.strip() for s in status.split(",") if s.strip()}
    res = list_approval_candidates(
        cfg,
        ApprovalListQuery(
            statuses=tuple(wanted),
            project=project,
            track=track,
            limit=limit,
        ),
    )

    if format_.lower() == "json":
        render_approval_list_json(console, res)
        return

    render_approval_list(console, res, wanted_statuses=wanted)


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
    from .approval_service import preview_approval_card
    from .approve_presenter import (
        render_approval_show,
        render_approval_show_error,
    )

    cfg = _load_cfg(config, read_env=False)
    preview = preview_approval_card(cfg, card)
    if preview.error is not None:
        render_approval_show_error(console, preview)
        raise typer.Exit(code=preview.error.exit_code)
    render_approval_show(console, preview, card)


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
    strategy: str = typer.Option(
        DEFAULT_STRATEGY_NAME,
        "--strategy",
        help=(
            "Knowledge strategy 名称（opt-in）。默认沿用 five_stage（LLM 驱动，"
            "通过 fake provider 离线可跑）。可选 default_knowledge_card 走"
            "离线确定性策略。策略选择只依赖此显式选项，绝不从 source/adapter "
            "反推。"
        ),
    ),
) -> None:
    """对 inbox 中已 scan 的文件跑 5 stage pipeline，落地 Knowledge Card。

    硬约束：原始 source 文件不被改写；卡片默认 ``status: ai_draft``，
    必须人工修改 frontmatter 才晋升 ``human_approved``。
    """
    cfg = _load_cfg(config, read_env=False)
    cfg = _override_active_profile(cfg, profile)

    # v0.7.20：把 fake-safety / 资源解析下沉到 process_service，CLI 只做
    # IO 副作用编排（dotenv / RunLogger / console / writer / checkpoint）。
    # service 不读 .env、不实例化真实 provider；CLI 根据 requires_real_env 决定。
    from .process_service import (
        ProcessError,
        ProcessRequest,
        resolve_process_runtime,
        summarize_outcome,
    )

    runtime_or_err = resolve_process_runtime(
        ProcessRequest(
            cfg=cfg,
            file=file,
            limit=limit,
            dry_run=dry_run,
            prompts_dir=prompts_dir,
            tracks=tracks,
            template=template,
        )
    )
    if isinstance(runtime_or_err, ProcessError):
        console.print(f"[red]✗ {runtime_or_err.message}[/red]")
        raise typer.Exit(code=2)
    runtime = runtime_or_err

    if runtime.provider.requires_real_env:
        # 中文学习型注释：v0.5.1 把本地 smoke 路径收紧为“不读 .env”。
        # 只有用户显式切到真实 provider 时，才加载 .env 以解析 base_url /
        # api_key 等环境变量；fake provider 必须保持完全离线、无 secret 依赖。
        # v0.7.20：fake-safety 判断已下沉到 process_service.requires_real_env，
        # CLI 只负责实际 IO（load_dotenv），保持 service 无副作用。
        load_dotenv_silently(Path.cwd())
    if dry_run:
        console.print("[yellow]--dry-run：不会写卡片、不会写 state.json[/yellow]")
    console.print(f"active_profile = [bold]{cfg.llm.active_profile}[/bold]")

    resolved_prompts_dir = runtime.assets.prompts_dir
    tracks_text = runtime.assets.tracks_text

    scanner = Scanner(cfg)
    cp = Checkpoint.load(cfg.state.state_path, backup=cfg.state.backup_state)

    providers = build_providers(cfg.llm)
    client = LLMClient(llm_config=cfg.llm, providers=providers)

    if runtime.assets.template_path is not None:
        writer = CardWriter(
            vault_root=cfg.vault.root,
            cards_dir=cfg.vault.cards_dir,
            template_path=runtime.assets.template_path,
        )
    else:
        writer = CardWriter(
            vault_root=cfg.vault.root,
            cards_dir=cfg.vault.cards_dir,
            template_text=runtime.assets.template_text,
        )

    strategy_ctx = StrategyContext(
        client=client,
        prompts_dir=resolved_prompts_dir,
        prompt_versions=cfg.prompts,
        triage_threshold=cfg.triage.value_score_threshold,
        learning_tracks_text=tracks_text,
        logger=None,
    )
    # v0.10 Slice 3：把 --strategy 作为 explicit opt-in seam 接入 build_strategy。
    # 未知名字时把 UnknownStrategyError 翻译成用户可读的退出（含已注册可选项），
    # 避免 stack trace 直接吐到终端。strategy 选择只依赖此 CLI flag；不从
    # source / adapter / SourcePlugin 反推。
    try:
        pipeline = build_strategy(strategy, strategy_ctx)
    except NotYetImplementedStrategyError as e:
        # planned strategy 与 unknown 严格区分：消息措辞不同，但都
        # 以非零退出码退出，避免上层流水线把它当成 success 继续。
        console.print(
            f"[yellow]✗ 策略 {strategy!r} 尚未实现（planned / not yet "
            f"implemented）；{e}[/yellow]"
        )
        raise typer.Exit(code=2) from None
    except UnknownStrategyError:
        console.print(
            f"[red]✗ 未知 strategy: {strategy!r}；可选：{available_strategies()}；"
            "运行 `mindforge strategies list` 查看所有策略。[/red]"
        )
        raise typer.Exit(code=2) from None

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

            # v0.7.20：把 outcome 三分流的字段提取下沉到 process_service.summarize_outcome
            # 这是纯函数；CLI 仍负责 RunLogger.emit / console.print / writer.write
            # / checkpoint 写回，保持时序耦合在 CLI 端。
            item_result = summarize_outcome(
                outcome, doc, result.adapter_name, dry_run=dry_run
            )

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
                item.track = item_result.track
                item.value_score = item_result.value_score
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
                item.track = item_result.track
                item.value_score = item_result.value_score
                source_dict = item_result.source_dict
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
                if item_result.would_write_only:
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
    if counts["processed"] > 0:
        console.print("Next: mindforge approve list", markup=False)
        console.print("Boundary: generated cards remain ai_draft until explicit human approval.", markup=False)
    elif counts["skipped"] > 0 and counts["processed"] == 0:
        console.print("Next: mindforge scan or mindforge approve list", markup=False)


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

# v0.11 Slice 1：strategies 子命令组只做"策略发现"。它纯查询 registry
# 元数据，不会触发 LLMClient 构造、不会读 .env、不会写 workspace、不会
# approve；这条边界让用户能在任何环境下安全运行 `mindforge strategies list`。
strategies_app = typer.Typer(
    add_completion=False,
    help="知识归纳策略发现（只读元数据：strategy_id / version / 描述）。",
)
app.add_typer(strategies_app, name="strategies")


@strategies_app.command("list")
def strategies_list(
    custom_path: Path | None = typer.Option(
        None,
        "--custom-path",
        help=(
            "可选的 custom strategy 目录（显式路径，必须由用户提供）。"
            "传入后会把该目录下的 declarative custom 定义并入展示，"
            "标记为 [custom]，仍标记为 not executable / preview / planned。"
            "discovery is not execution —— 不会触发任何 LLM / .env / vault 写入。"
        ),
    ),
) -> None:
    """列出所有内建知识归纳策略的元数据；可选地把 ``--custom-path`` 目录
    下的 custom declarative 定义并入展示。

    本命令是纯查询：不构造 LLMClient、不读 ``.env``、不写 vault、不
    approve、不调用 strategy 本身的 ``run()``。

    输出包含每个策略的 ``strategy_id`` / ``strategy_version`` /
    ``display_name`` / ``status`` / ``provider_mode`` / ``safety_policy`` /
    ``output_schema_id`` / ``description``；custom 定义额外标 ``[custom]``
    与 ``not executable``，built-in 标 ``[built-in]``。

    Custom 错误处理：每个 custom 文件**逐个**通过
    :func:`load_strategy_definition_from_file` 加载，**任一**文件校验
    失败时只对该文件输出一行可读的 ``validation error``（包含文件路径
    + 失败原因），不中断其它文件 + built-in 的展示，也不会把非法定义
    悄悄注册进 :func:`available_strategies` —— 校验失败的 custom 不会
    出现在元数据列表里。
    """

    for meta in list_strategies():
        _print_strategy_meta(meta, kind="built-in")

    if custom_path is None:
        return

    from mindforge.strategies.custom_loader import (
        StrategyDefinitionFileError,
        iter_strategy_definition_files,
        load_strategy_definition_from_file,
    )

    try:
        candidate_paths = iter_strategy_definition_files(custom_path)
    except StrategyDefinitionFileError as exc:
        # 中文学习型注释：目录本身不存在 / 不是目录 / symlink-escape
        # 等"目录级"错误，CLI 给一行可读输出后正常返回（exit 0），
        # 不裸抛栈 —— discovery UX 的硬约束。
        console.print(f"[red]validation error[/red] {exc}")
        return

    for path in candidate_paths:
        try:
            definition = load_strategy_definition_from_file(path)
        except StrategyDefinitionFileError as exc:
            # 中文学习型注释：单文件错误 → 单行友好展示，继续处理后续
            # 文件。绝不把 raw Traceback / Python repr 漏到终端，也
            # 绝不把非法定义注册成可执行 —— 后者由 discover_strategies
            # 完全不写入 registry 来保证。
            console.print(
                f"[red]validation error[/red] {path.name}: {exc}"
            )
            continue
        _print_strategy_meta(definition.to_metadata(), kind="custom")


def _print_strategy_meta(meta: StrategyMetadata, *, kind: str) -> None:
    """统一的策略元数据展示（built-in / custom 共用）。

    custom 来源额外标 ``not executable``，让用户立刻分辨"我能否
    ``mindforge process --strategy <id>``"。
    """

    badge = "(built-in)" if kind == "built-in" else "(custom) not executable"
    console.print(
        f"[bold]{meta.strategy_id}[/bold]@{meta.strategy_version}  "
        f"[cyan]{meta.display_name}[/cyan]  "
        f"[magenta][{meta.status}][/magenta]  "
        f"[yellow]{badge}[/yellow]"
    )
    console.print(
        f"  status: {meta.status}  "
        f"provider_mode: {meta.provider_mode}  "
        f"safety_policy: {meta.safety_policy}  "
        f"output_schema_id: {meta.output_schema_id}"
    )
    console.print(f"  {meta.description}")


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
    from .review_presenter import (
        build_weekly_review_json,
        render_weekly_review_markdown,
    )
    from .review_service import build_weekly_review

    cfg = _load_cfg(config, read_env=False)
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
            print("\n" + recall_no_result_next_action())
            return
        for c in cards:
            print(
                f"- **[{c.id or c.path.stem}]** {c.title or '(untitled)'}  "
                f"`status={c.status}` `track={c.track or '-'}` "
                f"`value_score={c.value_score if c.value_score is not None else '-'}`  "
                f"`path={c.rel_path}`"
            )
        print("\n" + recall_hit_next_action())
        return

    if output_format == "table":
        if not cards:
            console.print("[yellow]没有匹配的卡片。[/yellow]")
            console.print(f"[dim]{recall_no_result_next_action()}[/dim]")
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
        console.print(f"[dim]{recall_hit_next_action()}[/dim]")
        return

    # compact (默认)
    if not cards:
        console.print("[yellow]没有匹配的卡片。[/yellow]")
        console.print(f"[dim]{recall_no_result_next_action()}[/dim]")
        return
    console.print(f"[bold]Recall[/bold] · {len(cards)} 项 (sort={sort})")
    for c in cards:
        console.print(
            f"- {c.id or c.path.stem} · {c.title or '(untitled)'} · "
            f"status={c.status} · track={c.track or '-'} · "
            f"value_score={c.value_score if c.value_score is not None else '-'}"
        )
    console.print(f"[dim]{recall_hit_next_action()}[/dim]")




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
    """BM25 / hybrid CLI wrapper；核心检索逻辑在 recall_service。"""
    cfg = _load_cfg(config, read_env=False)
    recall_query = RecallQuery(
        query=query,
        track=track,
        project=project,
        tags=tuple(tags),
        source_type=source_type,
        status=status,
        include_drafts=include_drafts,
        since=_parse_date(since),
        until=_parse_date(until),
        limit=limit,
        output_format=output_format,
        explain=explain,
        ranking=ranking,
        weight_bm25=weight_bm25,
        weight_value_score=weight_value_score,
        weight_review_due=weight_review_due,
    )
    try:
        result = run_bm25_recall(cfg, recall_query)
    except RecallServiceError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=2) from e

    for warning in result.warnings:
        console.print(f"[yellow]{warning}[/yellow]")

    # 不把 query 原文写入 telemetry/runs；只记录是否提供 + hash 化指纹。
    kw_provided, kw_hash = _hash_keyword(query)
    with RunLogger(cfg.state.runs_path, command="recall_bm25") as logger:  # type: ignore[attr-defined]
        logger.emit(
            "recall_bm25_executed",
            count=result.count,
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
                used_disk_index=result.index.used_disk,
                ranking_mode=ranking,
                index_stale=result.index.stale,
                weight_source=result.weight_source,
            ),
            keyword_provided=kw_provided,
            keyword_hash=kw_hash,
            output_format=output_format,
        )

    render_recall_result(
        console=console,
        result=result,
        output_format=output_format,
        context=RecallRenderContext(
            keyword_provided=kw_provided,
            keyword_hash=kw_hash,
            since=since,
            until=until,
        ),
    )


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


def _obsidian_dogfood_command_snippets(
    vault: Path,
    source_hint: str,
    output_dir: Path,
) -> list[tuple[str, str]]:
    """兼容旧测试入口；Obsidian CLI adapter 实现已迁到 obsidian_cli.py。"""
    from .obsidian_cli import _obsidian_dogfood_command_snippets as _snippets

    return _snippets(vault, source_hint, output_dir)


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
        cfg = load_app_config(config, vault_override=_global_vault_override())
    except AppContextError as e:
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


@dogfood_app.command("preflight")
def dogfood_preflight(
    input_path: Path = typer.Argument(
        ...,
        help=(
            "要 dogfood 的输入路径; 不会被读取或遍历, 只做静态分类。"
            "推荐 examples/demo-vault 下的 synthetic 路径。"
        ),
    ),
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="MindForge 配置文件路径",
    ),
    declare_non_sensitive: bool = typer.Option(
        False,
        "--declare-non-sensitive",
        help=(
            "用户明确声明此路径为 non-sensitive local 数据 (非 home / "
            "非 Obsidian vault / 非真实 Cubox dump); 由用户为该声明负责。"
        ),
    ),
    allow_real: bool = typer.Option(
        False,
        "--allow-real",
        help="opt-in 校验真实 LLM 路径是否就绪 (不发起任何调用)",
    ),
) -> None:
    """v0.13 Stage 4 — 静态 dogfood preflight; 只做分类决策, 不读 input。

    中文学习型说明: 这是一个**纯静态**的安全闸门。它不会列举 input
    目录、不会读取任何文件、不会调用 LLM、不会写 vault。它只回答:
    "如果你现在以这条 path + 这组开关跑 dogfood, 是否安全。" 真正的
    执行仍由用户走 ``dogfood plan`` 中列出的命令逐条手动触发。
    """
    from .dogfood_safety import build_preflight_report, render_preflight_report
    from .env_loader import load_dotenv_silently

    load_dotenv_silently(Path.cwd())
    app_cfg = load_app_config(config)
    report = build_preflight_report(
        input_path,
        declared_non_sensitive=declare_non_sensitive,
        allow_real=allow_real,
        llm_config=app_cfg.llm,
    )
    print(render_preflight_report(report))
    if not report["decision"]["allowed"]:
        raise typer.Exit(code=2)


@dogfood_app.command("cubox-readiness")
def dogfood_cubox_readiness(
    token_env: str = typer.Option(
        "MINDFORGE_CUBOX_TOKEN",
        "--token-env",
        help=(
            "Cubox API token 环境变量名 (presence-only 检查; 永不打印 value)。"
            "默认 MINDFORGE_CUBOX_TOKEN; 用户可显式传任意名字。"
        ),
    ),
    allow_real: bool = typer.Option(
        False,
        "--allow-real",
        help=(
            "opt-in 校验未来 G1 真实 Cubox HTTP 路径解锁条件 (不发起任何调用)。"
            "G1 在本仓库内仍然 future-gated; 此命令永远不会真实拉取 Cubox。"
        ),
    ),
) -> None:
    """Cubox 真实路径 readiness 诊断 — presence-only, 不联网, 永不打印 token。

    中文学习型说明: 这是 readiness 报告, 不是真实拉取入口。它只回答:
    "如果你想用真实 Cubox 路径, 你的 env / 配置是否就绪。" 真实 dogfood
    数据路径 (今天就能跑) 是 ``mindforge cubox dry-run --export <file.json>``
    —— 用 Cubox web Settings → Export 导出的官方 JSON 文件做完全离线
    的预检 + ai_draft 生成, 不需要 token, 不联网。真实 HTTP API 路径
    被 future G1 gate 把守, 永远不会被本命令自动触发。
    """
    from .cubox_readiness import (
        classify_cubox_real_opt_in,
        inspect_cubox_config,
        render_cubox_readiness_report,
    )

    report = inspect_cubox_config(token_env_var=token_env)
    classification = classify_cubox_real_opt_in(report, allow_real=allow_real)
    print(render_cubox_readiness_report(report, classification))


@dogfood_app.command("quickstart")
def dogfood_quickstart(
    vault: Path | None = typer.Option(
        None,
        "--vault",
        help=(
            "项目专用 / demo vault 路径; 省略时使用 examples/demo-vault。"
            "新用户应**只**指定项目专用 vault, 永不指定真实 home Obsidian vault。"
        ),
    ),
    cubox_export: Path | None = typer.Option(
        None,
        "--cubox-export",
        help=(
            "可选: 本地 Cubox JSON export 文件路径 (Cubox web → Settings → "
            "Export 导出); 命令只渲染建议命令, 不读取该文件。"
        ),
    ),
) -> None:
    """新用户 10 分钟跑通 MindForge 的 quickstart 命令导航 (不执行命令)。

    中文学习型说明: 这是 **runbook 渲染器**, 不是自动化 runner。它列
    出新用户从安装 → fake provider smoke → Cubox JSON export 预检 →
    ai_draft → Obsidian 项目 vault dry-run 的完整路径, 让用户自己复制
    粘贴执行, 避免工具误改正式资料。永不调用真实 LLM / Cubox API /
    Obsidian write / human_approved 路径。
    """
    import os as _os

    chosen_vault = vault or Path(
        _os.environ.get("MINDFORGE_VAULT_OVERRIDE", "examples/demo-vault")
    )
    print("MindForge real dogfooding quickstart (read-only runbook)")
    print("=========================================================")
    print(f"vault: {chosen_vault}")
    if cubox_export:
        print(f"cubox export: {cubox_export}")
    print("")
    print("Safety: this command renders commands only; it does NOT execute")
    print("them. Commands below stay on the fake-default + dry-run path.")
    print("No .env content is read. No token is printed. No real LLM is")
    print("called. No formal Obsidian write. No human_approved is produced.")
    print("")
    print("Steps:")
    for idx, (command, note) in enumerate(
        _dogfood_quickstart_steps(chosen_vault, cubox_export), start=1
    ):
        print(f"  {idx:>2}. {command}")
        print(f"      {note}")
    print("")
    print("Limits: start with --limit 5; never exceed --limit 20 first run;")
    print("        no full Cubox sync exists — JSON export is opt-in per item.")
    print("Rollback: every step above is dry-run by default; obsidian stage")
    print("        --write only touches <vault>/staging/. Use a disposable")
    print("        project vault (cp -r examples/demo-vault /tmp/dogfood-vault).")
    print("Token: Cubox API token is a secret. Never paste, never commit,")
    print("        never print. cubox-readiness only ever returns a bool.")
    print("")
    print("Full guide: docs/REAL_DOGFOOD_QUICKSTART.md")


def _dogfood_quickstart_steps(
    vault: Path, cubox_export: Path | None
) -> list[tuple[str, str]]:
    """集中维护 quickstart 命令, 供 CLI 与测试共同使用, 减少文档漂移。

    Cubox 步骤分两条路径:
    - 用户提供 ``--cubox-export`` 时, 给出针对该文件的具体命令;
    - 否则给出"如何从 Cubox web 导出"的提示 + 通用占位命令。
    """
    v = str(vault)
    cubox_path = str(cubox_export) if cubox_export else "<file.json>"
    cubox_hint = (
        "替换 <file.json> 为 Cubox web → Settings → Export 导出的 JSON 文件"
        if cubox_export is None
        else "已使用你提供的 Cubox export 文件"
    )
    return [
        (
            "mindforge doctor --paths",
            "确认本地路径与安全边界 (确认 active_profile=fake)",
        ),
        (
            "mindforge provider readiness --config configs/mindforge.yaml",
            "确认 LLM provider 是 fake-default; api_key value 永不打印",
        ),
        (
            "mindforge dogfood cubox-readiness --token-env MINDFORGE_CUBOX_TOKEN",
            "确认 Cubox 真实路径 readiness; 不联网, 不打印 token",
        ),
        (
            f"mindforge cubox dry-run --export {cubox_path}",
            f"Cubox JSON export 离线预检 (真实数据, 零网络)。{cubox_hint}",
        ),
        (
            f"mindforge cubox preview-ai-draft --export {cubox_path} --limit 5",
            "对前 5 条用 fake provider 生成 ai_draft (review-only; 永远不要 --limit > 20 第一次跑)",
        ),
        (
            "mindforge dogfood preflight examples/demo-vault --declare-non-sensitive",
            "静态 dogfood 路径分类; 不读输入, 不调 LLM, 不写 vault",
        ),
        (
            f"mindforge obsidian doctor --vault {v}",
            "确认项目 vault 安全 (only the path you pass, no home scan)",
        ),
        (
            f"mindforge obsidian scan --vault {v} --limit 5",
            "扫描项目 vault 中的非敏感 Markdown",
        ),
        (
            f"mindforge obsidian stage --vault {v} --source <note.md> --dry-run",
            "项目 vault staging dry-run (默认 --dry-run; --write 才真写)",
        ),
        (
            "mindforge approve list",
            "查看待人工 approve 的 ai_draft (永远只能由 approver.approve_card 晋升)",
        ),
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
        hints.sort(key=lambda item: {"try_first": -1, "critical": 0, "recommended": 1, "info": 2}.get(item[0], 9))
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
        # 用户友好性 polish：在要求 init 之前先告诉新用户有零配置 demo 可选；
        # 这是 ``mindforge demo`` 60 秒 tour 的入口提示，不替换 init 的 critical 性。
        # UX completion: 用 try_first 优先级保证 demo 在 doctor Action items 列表
        # 第一行出现，让新用户在被多条 critical 提示劝退之前先看到安全演示路径。
        actions.append((
            "try_first",
            "想先跑零配置 tour（无需 vault / API key / 网络）→ 运行: mindforge demo",
        ))

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
    from .telemetry import telemetry_path

    console.print(f"[bold]MindForge[/bold] v{__version__}")
    console.print(f"- config: {config}")
    if not config.exists():
        console.print("  [yellow](config 文件不存在；以下字段省略)[/yellow]")
        console.print("[dim]提示：复制 configs/mindforge.yaml 到目标位置后重试。[/dim]")
        return
    try:
        cfg = load_app_config(config, vault_override=_global_vault_override())
    except AppContextError as e:
        console.print(f"  [red]config 解析失败：{e}[/red]")
        raise typer.Exit(code=2) from e

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
            ("mindforge obsidian next --vault PATH", "查看 dogfooding 状态、staged export 和下一步"),
            ("mindforge obsidian doctor --vault PATH", "检查只读 Obsidian 绑定边界"),
            ("mindforge obsidian scan --vault PATH", "只读扫描 Markdown note 安全摘要"),
            ("mindforge obsidian links --vault PATH", "只读解析 [[wikilinks]]"),
            ("mindforge obsidian stage --source NOTE --dry-run", "预览 staging 候选，不写正式 notes"),
            (
                "mindforge obsidian stage --source NOTE --staged-export --diff --write --confirm",
                "写 staged export + manifest，不写正式 notes",
            ),
            ("mindforge obsidian preflight --manifest PATH", "校验 future write-gate 证据链"),
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


# Historical _next_suggestions / _compact_next_suggestions extracted to
# the next_suggestions module. cli.py keeps thin private aliases so
# existing call sites stay unchanged. See next_suggestions.py module
# docstring for the architecture boundary (no console / no Typer).
def _next_suggestions(cfg):
    return next_suggestions(cfg)


def _compact_next_suggestions(suggestions):
    return compact_next_suggestions(suggestions)


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


# ---------------------------------------------------------------------------
# `mindforge cubox` — Cubox export 本地预检入口（dry-run）
#
# adapter 实现位于 ``cubox_cli.py``，独立成文件以保持本模块对
# source-specific adapter 与跨源 mux 模块的零静态依赖（由既有 AST
# 边界测试守护）。
# ---------------------------------------------------------------------------
from .cubox_cli import cubox_app  # noqa: E402

app.add_typer(cubox_app, name="cubox")


if __name__ == "__main__":  # pragma: no cover
    main()
