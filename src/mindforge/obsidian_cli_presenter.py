"""Obsidian CLI 子命令的展示层。

中文学习边界：
- 本模块只构造 *字符串* 与 ``rich.table.Table`` 对象，不打印（``console.print``
  留在 ``obsidian_cli.py``）、不读 ``.env``、不调 LLM、不发 HTTP、不写 vault、
  不写 staged markdown、不写 manifest。
- 这样做的原因：``mindforge obsidian *`` 是 CLI adapter；adapter 既要保留
  Typer 入口与 IO 副作用编排（write 路径、退出码），又要避免业务/纯展示逻辑
  膨胀进 adapter 文件。把"用户看到的话/表"挪到 presenter 后，Typer 命令体
  专注挂载 service 调用与 IO 编排。
- presenter 故意 **不** import ``approval_service`` / ``review_service`` /
  ``recall_service``：这是 Obsidian adapter 已有的反向依赖禁令，必须延伸到它
  的 presenter 模块。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.table import Table

from .obsidian_stage import safe_relative_to


_DOCTOR_ICONS: dict[str, str] = {
    "ok": "[green]✓[/green]",
    "warn": "[yellow]⚠[/yellow]",
    "error": "[red]✗[/red]",
    "info": "[dim]·[/dim]",
}


def format_doctor_icon(state: str) -> str:
    """复用 doctor 图标映射，避免 obsidian_cli 反向依赖 cli.py 同名函数。"""

    return _DOCTOR_ICONS.get(state, "[dim]·[/dim]")


def format_copy_warning() -> str:
    """统一的"只对 vault 副本试跑"安全提示，方便测试与 i18n。"""

    return (
        "[yellow]安全提示：请只对可丢弃、非敏感的 Obsidian vault 副本做 dry-run；"
        "MindForge 不会自动整理正式 notes。[/yellow]"
    )


def format_dry_run_safety_footer() -> str:
    """stage dry-run 结束语：明确"未写任何文件"。"""

    return "[yellow]dry-run：未写任何文件，未移动 source note，未重写 wikilinks。[/yellow]"


def stage_preview_next_command(*, vault_root: Path, source_hint: str) -> str:
    """构造 stage preview 中"下一步建议命令"文本。"""

    return (
        f"mindforge obsidian stage --vault {vault_root} --source {source_hint}"
        " --staged-export --diff --write --confirm"
    )


def build_skipped_notes_table(vault_root: Path, issues: list[Any]) -> Table | None:
    """构造 skipped notes 表；issues 为空时返回 None，由调用方决定是否打印。"""

    if not issues:
        return None
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
    return table


def extract_stage_preview_fields(doc: Any) -> dict[str, object]:
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


def build_stage_preview_table(
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
) -> Table:
    """构造 stage dry-run preview 表；不写文件、不打印。"""

    if source_exists is None:
        source_exists = source.exists()
    if source_in_vault is None:
        source_in_vault = safe_relative_to(source, vault_root) is not None
    table = Table(title="Obsidian stage preview", show_lines=False)
    table.add_column("field", style="bold")
    table.add_column("value", overflow="fold")
    table.add_row("mode", "dry-run")
    table.add_row("vault", str(vault_root))
    table.add_row(
        "vault exists",
        "yes" if vault_root.exists() and vault_root.is_dir() else "no",
    )
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
    table.add_row(
        "risk warning",
        "只对可丢弃、非敏感 vault 副本试跑；不修改正式 notes。",
    )
    source_hint = safe_relative_to(source, vault_root) or str(source)
    table.add_row(
        "next command",
        stage_preview_next_command(vault_root=vault_root, source_hint=source_hint),
    )
    table.add_row(
        "manual check",
        "Use --diff, inspect staged markdown + manifest, then run obsidian preflight.",
    )
    return table


def diff_preview_missing_lines(manual_inspection_hint: str) -> list[str]:
    """staged target 不存在时的两条 dim 提示。"""

    return [
        "[dim]diff preview: staged target 不存在，将创建新文件。[/dim]",
        f"[dim]{manual_inspection_hint}[/dim]",
    ]


def diff_preview_header() -> str:
    """diff preview 标题行。"""

    return "[bold]diff preview[/bold] · staged directory only"


def diff_preview_no_changes() -> str:
    """无差异提示。"""

    return "[dim]无差异。[/dim]"


def diff_preview_truncated(more_lines: int) -> str:
    """diff 截断提示。"""

    return f"[dim]... diff truncated, {more_lines} more lines[/dim]"


def diff_preview_inspection_hint(manual_inspection_hint: str) -> str:
    """用户手工检查 staged markdown 的提示。"""

    return f"[dim]{manual_inspection_hint}[/dim]"


__all__ = [
    "build_skipped_notes_table",
    "build_stage_preview_table",
    "diff_preview_header",
    "diff_preview_inspection_hint",
    "diff_preview_missing_lines",
    "diff_preview_no_changes",
    "diff_preview_truncated",
    "extract_stage_preview_fields",
    "format_copy_warning",
    "format_doctor_icon",
    "format_dry_run_safety_footer",
    "stage_preview_next_command",
]
