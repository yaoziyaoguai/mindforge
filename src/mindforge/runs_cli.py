"""Processing run CLI read surface."""

from __future__ import annotations

from pathlib import Path

import typer

from .cli_runtime import console, load_cfg, render_active_vault_resolution_notice
from mindforge.processing.run_store import get_processing_run, list_processing_runs

runs_app = typer.Typer(
    add_completion=False,
    help="查看后台 processing run 状态；只读，不启动处理。",
)


@runs_app.command("show")
def runs_show(
    run_id: str = typer.Argument(..., help="processing run_id"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """展示单个后台 processing run。"""

    cfg = load_cfg(config, read_env=False)
    render_active_vault_resolution_notice(cfg)
    record = get_processing_run(cfg, run_id)
    if record is None:
        console.print(f"processing run not found: {run_id}", markup=False)
        raise typer.Exit(code=2)
    _print_record(record)


@runs_app.command("list")
def runs_list(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    limit: int = typer.Option(10, "--limit", min=1, max=100),
) -> None:
    """列出最近的后台 processing runs。"""

    cfg = load_cfg(config, read_env=False)
    render_active_vault_resolution_notice(cfg)
    records = list_processing_runs(cfg)[:limit]
    if not records:
        console.print("No background processing runs yet.", markup=False)
        console.print(
            "Start one with: mindforge watch add <file-or-folder> or mindforge import <file-or-folder>",
            markup=False,
            soft_wrap=True,
        )
        return
    console.print("[bold]Background processing runs[/bold]")
    for record in records:
        console.print(
            f"- run_id={record.run_id} · status={record.status} · "
            f"source={record.source_path or record.source_ref} · started={record.started_at}",
            markup=False,
            soft_wrap=True,
        )


def _print_record(record) -> None:
    """只读展示 run；不 repair、不创建新的 processing state。"""

    console.print("[bold]Processing run[/bold]")
    console.print(f"run_id: {record.run_id}", markup=False)
    console.print(f"status: {record.status}", markup=False)
    console.print(f"mode: {record.mode}", markup=False)
    console.print(f"source: {record.source_path or record.source_ref}", markup=False, soft_wrap=True)
    console.print(f"started_at: {record.started_at}", markup=False)
    console.print(f"current_step: {record.current_step or '-'}", markup=False)
    console.print(f"last_heartbeat_at: {record.last_heartbeat_at or '-'}", markup=False)
    console.print(f"finished_at: {record.finished_at or '-'}", markup=False)
    console.print(f"message: {record.message}", markup=False, soft_wrap=True)
    if record.error_message:
        console.print(f"error: {record.error_message}", markup=False, soft_wrap=True)
    if record.skip_reasons:
        console.print("[bold]Skipped reasons[/bold]")
        for reason in record.skip_reasons:
            console.print(f"- {reason}", markup=False, soft_wrap=True)
    console.print(
        "summary: discovered={discovered} drafts={drafts} skipped={skipped} errors={errors}".format(
            discovered=record.summary.get("discovered", 0),
            drafts=record.summary.get("drafts", 0),
            skipped=record.summary.get("skipped", 0),
            errors=record.summary.get("errors", 0),
        ),
        markup=False,
    )
    if record.status in {"failed", "partial_failed"}:
        if _looks_like_model_setup_error(record.error_message or record.message):
            console.print(
                "Next: complete model setup in Web Setup or local secret store, then retry after setup with mindforge import <path> or Process now.",
                markup=False,
                soft_wrap=True,
            )
        else:
            console.print(
                "Next: fix the issue above, then retry with mindforge import <path> or Process now from Sources.",
                markup=False,
                soft_wrap=True,
            )
    elif record.status in {"queued", "running"}:
        console.print(
            "Background processing is active. Current step and heartbeat show the worker is still making progress.",
            markup=False,
            soft_wrap=True,
        )
    elif record.summary.get("drafts", 0):
        console.print("Drafts appear in: mindforge approve list", markup=False)


def _looks_like_model_setup_error(message: str) -> bool:
    """识别 model setup blocker，只用于展示下一步，不读取 secret。"""

    lowered = message.lower()
    return (
        "model setup" in lowered
        or "add a model in web setup" in lowered
        or "provider api key" in lowered
        or "no model configured" in lowered
    )


__all__ = ["runs_app"]
