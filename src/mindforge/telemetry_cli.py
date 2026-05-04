"""Local telemetry CLI adapter.

Telemetry 只读/汇总本地 metadata 文件，永不上传。
"""
from __future__ import annotations

from pathlib import Path

import typer

from .cli_runtime import console, load_cfg

# ---------------------------------------------------------------------------
# telemetry status / summary — 本地使用观察日志
# ---------------------------------------------------------------------------


telemetry_app = typer.Typer(
    add_completion=False,
    help="本地 telemetry（M5.7 / v0.2.3）— 仅元数据，永不上传",
)


@telemetry_app.command("status")
def telemetry_status(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """打印 telemetry 配置与本地文件位置（不读取事件内容）。"""
    from .telemetry import telemetry_path

    cfg = load_cfg(config, read_env=False)
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

    cfg = load_cfg(config, read_env=False)
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
