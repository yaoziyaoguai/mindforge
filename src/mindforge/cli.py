"""MindForge root Typer entrypoint.

中文学习型说明：root ``cli.py`` 只负责全局参数、少量基础命令与命令族注册。
历史上 4500+ 行的 approve/process/review/recall/project/dogfood 等命令族已
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
)
from .cubox_cli import cubox_app
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
from .dogfood_cli import _dogfood_command_snippets, _dogfood_quickstart_steps, dogfood_app
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
from .llm_cli import llm_app
from .llm import build_providers
from .models import ItemState
from .next_suggestions import NextSuggestion, compact_next_suggestions, next_suggestions
from .obsidian_cli import _obsidian_dogfood_command_snippets, obsidian_app
from .env_loader import load_dotenv_silently
from .process_cli import _finalize_process_run, _process_one_result, process
from .processors import Pipeline  # noqa: F401 -- 保留向后兼容 re-export
from .project_cli import project_app
from .provider_cli import provider_app
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
from .scanner import Scanner
from .strategy_cli import strategies_app
from .telemetry_cli import telemetry_app
from .vault_cli import vault_app
from .web_cli import web

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
    "_dogfood_command_snippets",
    "_dogfood_quickstart_steps",
    "_obsidian_dogfood_command_snippets",
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
        help="临时覆盖配置中的 vault.root（不修改 yaml）。优先级：CLI > config > 默认。",
    ),
    obsidian_vault: Path | None = typer.Option(
        None,
        "--obsidian-vault",
        help="临时覆盖 obsidian.vault_path（仅 obsidian 子命令使用，不修改 yaml）。",
    ),
) -> None:
    """全局选项通过 env 透传，避免子命令与 Typer Context 紧耦合。"""
    import os

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
            console.print(
                f"Next: mindforge process --profile fake --limit 1 --vault {cfg.vault.root}",
                markup=False,
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

# Root command registration. We bind moved command callbacks directly so
# tests, shell completion, and external introspection see stable command names
# instead of Typer's anonymous flattened sub-app placeholders.
app.command()(process)
app.command()(recall)
app.command()(init)
app.command("setup")(setup_cmd)
app.command()(doctor)
app.command()(version)
app.command()(web)
app.command("commands")(commands_cmd)
app.command("start")(start_cmd)
app.command("today")(today_cmd)
app.command("next")(next_cmd)
app.add_typer(llm_app, name="llm")
app.add_typer(backup_app, name="backup")
app.add_typer(config_app, name="config")
app.add_typer(dogfood_app, name="dogfood")
app.add_typer(obsidian_app, name="obsidian")
app.add_typer(provider_app, name="provider")
app.add_typer(approve_app, name="approve")
app.add_typer(review_app, name="review")
app.add_typer(project_app, name="project")
app.add_typer(strategies_app, name="strategies")
app.add_typer(index_app, name="index")
app.add_typer(telemetry_app, name="telemetry")
app.add_typer(vault_app, name="vault")
app.add_typer(cubox_app, name="cubox")


def main() -> None:
    """CLI 入口。``--debug`` 不传时静默 traceback，仅打印简短错误。"""
    import os
    import sys

    sys.argv = _normalize_post_command_global_options(sys.argv)
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


if __name__ == "__main__":  # pragma: no cover
    main()
