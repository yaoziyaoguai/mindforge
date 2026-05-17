"""Knowledge Health CLI entrypoint.

中文学习型说明：health 是只读维护报告。它读取 config/vault/state/wiki 的安全
摘要，输出 issue 与建议；不能修改卡片、不能 approve、不能调用 LLM/API。
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from .cli_runtime import console, load_cfg, render_active_vault_resolution_notice
from .health.health_service import KnowledgeHealthReport, build_knowledge_health_report


def health_cmd(
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="mindforge.yaml 路径",
    ),
    as_json: bool = typer.Option(False, "--json", help="输出机器可读 JSON。"),
) -> None:
    """生成只读 Knowledge Health Report。"""
    cfg = load_cfg(config, read_env=False)
    render_active_vault_resolution_notice(cfg)
    report = build_knowledge_health_report(cfg)
    if as_json:
        _print_json(report)
        return
    _print_report(report)


def _print_report(report: KnowledgeHealthReport) -> None:
    console.print("[bold]MindForge Knowledge Health[/bold]")
    console.print(report.summary, markup=False)
    if report.stats:
        stats = ", ".join(f"{key}={value}" for key, value in sorted(report.stats.items()))
        console.print(f"stats: {stats}", markup=False, soft_wrap=True)
    if not report.issues:
        return
    table = Table(title="Issues", show_lines=False)
    table.add_column("severity")
    table.add_column("code")
    table.add_column("reason", overflow="fold")
    table.add_column("suggested action", overflow="fold")
    for issue in report.issues:
        table.add_row(
            issue.severity.value,
            issue.code,
            issue.reason or issue.message,
            issue.suggested_action,
        )
    console.print(table)
    if report.maintenance_suggestions:
        console.print("[bold]Maintenance suggestions[/bold]")
        for item in report.maintenance_suggestions:
            console.print(f"- {item}", markup=False, soft_wrap=True)


def _print_json(report: KnowledgeHealthReport) -> None:
    import json

    payload = {
        "summary": report.summary,
        "stats": report.stats,
        "issues": [
            {
                "code": issue.code,
                "severity": issue.severity.value,
                "message": issue.message,
                "reason": issue.reason,
                "suggested_action": issue.suggested_action,
                "affected_card_ids": list(issue.affected_card_ids),
            }
            for issue in report.issues
        ],
        "maintenance_suggestions": list(report.maintenance_suggestions),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


__all__ = ["health_cmd"]
