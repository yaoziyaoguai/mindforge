"""MindForge root Typer entrypoint.

中文学习型说明：root ``cli.py`` 只负责全局参数、少量基础命令与命令族注册。
历史上 4500+ 行的 approve/process/review/recall/project 等命令族已
拆入各自 ``*_cli.py`` adapter；service / presenter / policy / source / strategy
边界不再反向依赖 root CLI。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import typer
from rich.table import Table

from .approval_cli import approve_app
from .backup_cli import backup_app
from .checkpoint import Checkpoint
from .cli_cards import card_to_safe_dict as _card_to_safe_dict
from .cli_cards import filters_dict as _filters_dict
from .cli_cards import hash_keyword as _hash_keyword
from .cli_cards import parse_date as _parse_date
from .cli_cards import safe_date as _safe_date
from .cli_runtime import (
    console,
    global_vault_override as _global_vault_override,
    load_cfg as _load_cfg,
    normalize_post_command_global_options as _normalize_post_command_global_options,
    override_active_profile as _override_active_profile,
    render_active_vault_resolution_notice,
)
from .daily_cli import (
    DailySnapshot,
    _compact_next_suggestions,
    _daily_snapshot,
    _next_suggestions,
    _snapshot_to_dict,
    commands_cmd,
    next_cmd,
    start_cmd,
    today_cmd,
    version,
)
from .doctor_cli import (
    _dir_state,
    _doctor_icon,
    _doctor_paths,
    _doctor_recovery_checks,
    _ok_dir,
    doctor,
)
from .init_config_cli import (
    _available_profile_names,
    _build_config_init_plan,
    _config_doctor_rows,
    _config_ux_payload,
    _print_config_init_plan,
    _print_config_ux_payload,
    _rewrite_init_config,
    _validate_interactive_vault_target,
    config_app,
    init,
    setup_cmd,
)
from .import_cli import import_cmd
from .llm import build_providers
from .library_cli import library_app
from .models import ItemState
from .next_suggestions import NextSuggestion, compact_next_suggestions, next_suggestions
from .obsidian_cli import _obsidian_workflow_command_snippets, obsidian_app
from .env_loader import load_dotenv_silently
from .process_cli import _finalize_process_run, process
from .processors import Pipeline  # noqa: F401 -- 保留向后兼容 re-export
from .process_executor import process_one_result as _process_one_result
from .project_cli import project_app
from .prompt_cli import prompts_app
from .recall_index_cli import (
    _do_bm25_recall,
    _do_index_status,
    _do_rule_recall,
    index_app,
    recall,
)
from .review_cli import (
    _bucket_review,
    _ics_escape,
    _render_ics,
    _review_learning_tasks,
    _review_next_actions,
    review_app,
)
from .run_logger import (
    EVENT_SOURCE_ERROR,
    EVENT_SOURCE_SEEN,
    EVENT_SOURCE_SKIPPED_OR_UNCHANGED,
    EVENT_STATE_WRITTEN,
    EVENT_STATUS_REPORTED,
    RunLogger,
    summarize_latest_run,
)
from .runs_cli import runs_app
from .scanner import Scanner
from .strategy_cli import strategies_app
from .telemetry_cli import telemetry_app
from .trash_cli import trash_app
from .vault_cli import vault_app
from .web_cli import web
from .wiki_cli import wiki_app
from .watch_cli import watch_app
from .workspace_cli import workspace_app

__all__ = [
    "app",
    "main",
    "Pipeline",
    "NextSuggestion",
    "compact_next_suggestions",
    "next_suggestions",
    "DailySnapshot",
    "_card_to_safe_dict",
    "_filters_dict",
    "_hash_keyword",
    "_parse_date",
    "_safe_date",
    "_load_cfg",
    "_global_vault_override",
    "_override_active_profile",
    "_normalize_post_command_global_options",
    "_daily_snapshot",
    "_snapshot_to_dict",
    "_next_suggestions",
    "_compact_next_suggestions",
    "_doctor_recovery_checks",
    "_doctor_paths",
    "_doctor_icon",
    "_dir_state",
    "_ok_dir",
    "_obsidian_workflow_command_snippets",
    "_available_profile_names",
    "_validate_interactive_vault_target",
    "_rewrite_init_config",
    "_config_ux_payload",
    "_print_config_ux_payload",
    "_config_doctor_rows",
    "_build_config_init_plan",
    "_print_config_init_plan",
    "_process_one_result",
    "_finalize_process_run",
    "_do_rule_recall",
    "_do_bm25_recall",
    "_do_index_status",
    "_bucket_review",
    "_ics_escape",
    "_render_ics",
    "_review_learning_tasks",
    "_review_next_actions",
    "load_dotenv_silently",
    "build_providers",
]

app = typer.Typer(
    add_completion=True,
    invoke_without_command=True,
    help=(
        "MindForge — 多源接入的本地 AI 知识加工管线。\n\n"
        "第一阶段主路径：真实模型配置 → 本地文件/文件夹 Source → 后台 Process → "
        "AI Draft → Human Review → Explicit Approve → Library / Wiki。\n\n"
        "常用命令：\n"
        "  mindforge web                — 打开本地 Web 控制台并配置真实模型\n"
        "  mindforge status             — 查看本地 workspace / draft / library 状态\n"
        "  mindforge doctor             — 做本地安装与路径健康检查\n"
        "  watch add <path>             — 注册 watched source，并启动后台 Process\n"
        "  import <path>                — 一次性导入文件/文件夹，并启动后台 Process\n"
        "  runs show <run_id>           — 查看后台 processing 进度或失败原因\n"
        "  approve list / approve 1     — 查看并显式确认 AI Draft\n"
        "  library list / show          — 浏览已审批知识\n"
        "  trash list / move / restore  — 管理回收站\n"
        "  wiki status / rebuild / show — 管理从 approved cards 派生的 Wiki\n"
        "  prompts list / show          — 只读查看内置 prompt\n"
        "  recall --query <text>        — 搜索已审批知识\n"
        "  version                      — 打印版本与运行配置摘要（不含 secret）\n"
    ),
    pretty_exceptions_enable=False,
)


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
        help=(
            "临时覆盖 active vault（不修改 yaml）。优先级：explicit --vault > "
            "cwd/ancestor vault > project root configs/mindforge.yaml 的 vault.root > "
            "configured/bundled fallback。"
        ),
    ),
    obsidian_vault: Path | None = typer.Option(
        None,
        "--obsidian-vault",
        help="临时覆盖 obsidian.vault_path（仅 obsidian 子命令使用，不修改 yaml）。",
    ),
    version_flag: bool = typer.Option(
        False,
        "--version",
        help="打印 MindForge 版本并退出。",
        is_eager=True,
    ),
) -> None:
    """全局选项通过 env 透传，避免子命令与 Typer Context 紧耦合。"""
    import os

    if version_flag:
        from . import __version__

        console.print(f"MindForge v{__version__}", markup=False)
        raise typer.Exit()
    if debug:
        os.environ["MINDFORGE_DEBUG"] = "1"
    else:
        os.environ.pop("MINDFORGE_DEBUG", None)
    if vault is not None:
        os.environ["MINDFORGE_VAULT_OVERRIDE"] = str(vault.expanduser().resolve())
    else:
        os.environ.pop("MINDFORGE_VAULT_OVERRIDE", None)
    if obsidian_vault is not None:
        os.environ["MINDFORGE_OBSIDIAN_VAULT_OVERRIDE"] = str(
            obsidian_vault.expanduser().resolve()
        )
    else:
        os.environ.pop("MINDFORGE_OBSIDIAN_VAULT_OVERRIDE", None)


@app.command(hidden=True, add_help_option=False)
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
    """[Advanced] 扫描 inbox 目录并登记到 state.json。用户主路径请用 mindforge watch add 或 mindforge import。"""
    cfg = _load_cfg(config, read_env=False)
    console.print(f"active vault: {cfg.vault.root}", markup=False, soft_wrap=True)
    console.print(f"state path  : {cfg.state.state_path}", markup=False, soft_wrap=True)
    render_active_vault_resolution_notice(cfg)
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
            console.print(f"scanned: {doc.source_path}", markup=False, soft_wrap=True)
            table.add_row(doc.source_type, doc.source_path, label, doc.content_hash[:18] + "...")

        console.print(table)
        console.print(
            f"扫描完成：共 [bold]{seen}[/bold] 个文件，"
            f"新增/变更 [green]{new_or_changed}[/green]，失败 [red]{failed}[/red]"
        )

        if write_state:
            cp.save(active_profile=cfg.llm.active_profile)  # type: ignore[attr-defined]
            console.print(f"已写入 state.json → {cfg.state.state_path}", soft_wrap=True)  # type: ignore[attr-defined]
            console.print(
                f"Next: mindforge web  # open Sources to process {cfg.vault.root}",
                markup=False,
                soft_wrap=True,
            )
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
    as_json: bool = typer.Option(False, "--json", help="输出机器可读 JSON。"),
) -> None:
    """打印真实本地 workspace / vault / draft / recall 状态汇总。"""
    from .app_context import AppContextError
    from .presenters.local_status import (
        render_friendly_error,
        render_local_status,
        render_status_json,
    )
    from .services.local_status import build_local_status_snapshot, friendly_config_error

    try:
        snapshot = build_local_status_snapshot(
            config,
            vault_override=_global_vault_override(),
            cwd=Path.cwd(),
        )
    except AppContextError as exc:
        render_friendly_error(console, friendly_config_error(config, str(exc)))
        raise typer.Exit(code=2) from exc
    if as_json:
        render_status_json(snapshot)
        return
    # 中文学习型说明：status 是 read/query path，不能创建 RunLogger，也不能让
    # “最近一次 processing/run”被查询命令污染。运行事件只能由 scan/process/
    # background worker 这类 command path 写入。
    render_local_status(console, snapshot)


def _legacy_status(
    config: Path = Path("configs/mindforge.yaml"),
) -> None:
    """历史 state.json 摘要实现；保留给内部兼容，不再作为用户主入口。"""
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

# Root command registration. We bind moved command callbacks directly so
# tests, shell completion, and external introspection see stable command names
# instead of Typer's anonymous flattened sub-app placeholders.
app.command(hidden=True, add_help_option=False)(process)
app.command("import")(import_cmd)
app.command()(recall)
app.command()(init)
app.command("setup", hidden=True, add_help_option=False)(setup_cmd)
app.command()(doctor)
app.command()(version)
app.command()(web)
app.command("commands")(commands_cmd)
app.command("start")(start_cmd)
app.command("today")(today_cmd)
app.command("next")(next_cmd)
app.add_typer(library_app, name="library")
app.add_typer(backup_app, name="backup", hidden=True)
app.add_typer(config_app, name="config", hidden=True)
app.add_typer(obsidian_app, name="obsidian", hidden=True)
app.add_typer(approve_app, name="approve")
app.add_typer(review_app, name="review")
app.add_typer(project_app, name="project", hidden=True)
app.add_typer(strategies_app, name="strategies", hidden=True)
app.add_typer(prompts_app, name="prompts")
app.add_typer(index_app, name="index")
app.add_typer(telemetry_app, name="telemetry", hidden=True)
app.add_typer(vault_app, name="vault", hidden=True)
app.add_typer(workspace_app, name="workspace", hidden=True)
app.add_typer(trash_app, name="trash")
app.add_typer(wiki_app, name="wiki")
app.add_typer(watch_app, name="watch")
app.add_typer(runs_app, name="runs")


def main() -> None:
    """CLI 入口。``--debug`` 不传时静默 traceback，仅打印简短错误。"""
    import os
    import sys

    sys.argv = _normalize_post_command_global_options(sys.argv)
    if _render_legacy_command_redirect(sys.argv):
        sys.exit(2)
    debug = os.environ.get("MINDFORGE_DEBUG") == "1" or "--debug" in sys.argv
    try:
        app()
    except typer.Exit:
        raise
    except Exception as e:  # noqa: BLE001
        if debug:
            raise
        console.print(f"[red]✗ unexpected error: {type(e).__name__}: {e}[/red]")
        console.print("[dim]提示：加 --debug 查看完整 traceback。[/dim]")
        sys.exit(1)


def _render_legacy_command_redirect(argv: list[str]) -> bool:
    """把旧命令变成迁移提示，而不是继续暴露一套隐藏产品面。

    中文学习型说明：这里刻意放在 ``main`` 的 argv 边界，而不是注册 Typer
    hidden command。原因是 Typer hidden command 仍可通过 ``cmd --help`` 直达，
    会把 demo/fake/Cubox/profile 等历史语义继续变成第二套用户手册。
    """
    if len(argv) < 2:
        return False
    command = argv[1]
    redirects = {
        "demo": "mindforge web",
        "dogfood": "mindforge web",
        "cubox": "mindforge watch add <local-file-or-folder>",
        "provider": "mindforge web",
        "llm": "mindforge web",
    }
    replacement = redirects.get(command)
    if replacement is None:
        return False
    console.print("[yellow]This legacy command has been removed.[/yellow]")
    console.print(
        "MindForge now uses real model setup, local sources, background "
        "processing, review, approve, library, and wiki."
    )
    console.print(f"Use: [bold]{replacement}[/bold]")
    return True


if __name__ == "__main__":  # pragma: no cover
    main()
