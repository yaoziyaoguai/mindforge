"""Process 命令的展示层（Rich markup 字符串构造器）。

中文学习边界：
- 本模块只构造 Rich markup *字符串*；不打印（``console.print`` 留在 cli.py）、
  不写文件、不发 ``RunLogger.emit``、不调 LLM、不读 ``.env`` /
  ``os.environ`` / ``mindforge.run_logger`` / ``mindforge.process_service``。
- 这样做的原因：``mindforge process`` 的事件顺序（``card_written`` 必须先于
  ``source_processed``，dry-run 不能写卡片但仍要 ``source_processed``）是
  产品契约。CLI 持有 ``RunLogger`` / ``CardWriter`` / ``Checkpoint`` 的副作
  用编排权，presenter 只负责"用户看到的话"。
- presenter 故意 **不** import ``process_service``：保持 presenter 家族契约的
  零业务依赖。CLI 在调用 presenter 前从 ``ProcessItemResult`` 取出原始字段。
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping


def format_skipped(*, source_path: str, skip_reason: str | None) -> str:
    """渲染 ``skipped`` 行：黄色 tag + 路径 + skip_reason。"""

    return f"[yellow]skipped[/yellow] {source_path} :: {skip_reason or ''}"


def format_failed(
    *, source_path: str, error_stage: str | None, error_message: str | None
) -> str:
    """渲染 ``failed`` 行：红色 tag + 路径 + ``stage=`` + error message。"""

    return (
        f"[red]failed[/red] {source_path} @ stage={error_stage}: {error_message}"
    )


def format_processed_dry_run(*, source_path: str, target_dir: Path) -> str:
    """渲染 dry-run processed 行：``cyan`` ``would-write`` 标签 + 目标卡片目录。"""

    return f"[cyan]dry-run[/cyan] would-write {source_path} → {target_dir}"


def format_processed_real(
    *, source_path: str, output_path: Path, conflict: bool
) -> str:
    """渲染真实 processed 行：``conflict`` 时换 yellow，否则 green。"""

    tag = "[yellow]conflict[/yellow]" if conflict else "[green]processed[/green]"
    return f"{tag} {source_path} → {output_path}"


def format_summary(counts: Mapping[str, int]) -> str:
    """渲染 ``process 完成`` 汇总行：seen / processed / skipped / failed 四项。"""

    return (
        f"\n[bold]process 完成[/bold]：seen={counts.get('seen', 0)} "
        f"processed={counts.get('processed', 0)} "
        f"skipped={counts.get('skipped', 0)} "
        f"failed={counts.get('failed', 0)}"
    )


def format_next_hint(counts: Mapping[str, int], *, vault_root: Path | None = None) -> list[str]:
    """根据 counts 给出下一步建议（plain 字符串列表，CLI 决定是否打印）。

    安全契约：``processed > 0`` 时必须复述 ``ai_draft until explicit human
    approval`` 边界，避免用户把 fake provider 生成的卡片误当 production。
    """

    processed = counts.get("processed", 0)
    skipped = counts.get("skipped", 0)
    failed = counts.get("failed", 0)
    vault_suffix = f" --vault {vault_root}" if vault_root is not None else ""
    if processed > 0:
        return [
            f"Next: mindforge approve list{vault_suffix}",
            "Boundary: generated cards remain ai_draft until explicit human approval.",
            "Processing completed in this command.",
            "Check drafts with: mindforge approve list",
            "If processing failed, fix the error above and retry this command.",
        ]
    if skipped > 0:
        return [
            "Next: "
            f"mindforge scan{vault_suffix} or mindforge approve list{vault_suffix}",
            "Processing completed in this command.",
            "Check drafts with: mindforge approve list",
            "If processing failed, fix the error above and retry this command.",
        ]
    if failed > 0:
        return [
            "Processing completed in this command.",
            "If processing failed, fix the error above and retry this command.",
        ]
    return []


__all__ = [
    "format_failed",
    "format_next_hint",
    "format_processed_dry_run",
    "format_processed_real",
    "format_skipped",
    "format_summary",
]
