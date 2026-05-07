"""Init 命令的展示层（Rich markup 字符串构造器）。

中文学习边界：
- 本模块只构造字符串；不打印（``console.print`` 留在 cli.py）、不调
  ``typer.prompt`` / ``typer.confirm``、不写 ``configs/mindforge.yaml``、
  不读 ``.env``、不访问 ``os.environ``。
- 交互式 vault 路径 / telemetry / default_model 的 prompt 仍属于 cli.py 的
  ``init`` 命令体，因为它们与 Typer 的输入流强耦合，移出去会让 ``init_cmd``
  变成隐式 CLI adapter。
- 文件副作用（创建目录、复制 templates、覆写 mindforge.yaml）仍属于
  ``init_cmd.execute_plan`` 与 cli.py 内部的 ``_rewrite_init_config``。
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

from .init_cmd import InitPlan


def format_plan_header(plan: InitPlan) -> list[str]:
    """plan header：``MindForge init`` + vault.root + project root 两项路径。"""

    return [
        "[bold]MindForge init[/bold]",
        f"- vault.root  : {plan.vault_root}",
        f"- project root: {plan.project_root}",
    ]


def format_mode_lines(*, force: bool, dry_run: bool, interactive: bool) -> list[str]:
    """按需输出 mode 标签：仅出现激活的 mode，避免误导。"""

    lines: list[str] = []
    if force:
        lines.append("- mode        : [yellow]--force (will overwrite templates)[/yellow]")
    if dry_run:
        lines.append("- mode        : [yellow]--dry-run (no files written)[/yellow]")
    if interactive:
        lines.append("- mode        : [cyan]--interactive[/cyan]")
    return lines


def format_interactive_summary(
    *,
    interactive: bool,
    telemetry_enabled: bool | None,
    active_profile: str | None,
) -> list[str]:
    """interactive 模式下展示用户最终选定的 telemetry / default_model。"""

    if not interactive:
        return []
    return [
        f"- telemetry   : enabled={telemetry_enabled} (local_only=True)",
        f"- default_model: {active_profile}",
    ]


def format_plan_summary(summary: Mapping[str, int]) -> str:
    """渲染 plan 汇总：四种 action 的计数。"""

    return (
        f"- plan: create_dir={summary.get('create_dir', 0)} "
        f"copy_file={summary.get('copy_file', 0)} "
        f"overwrite_force={summary.get('overwrite_force', 0)} "
        f"skip_exists={summary.get('skip_exists', 0)}"
    )


_DRY_RUN_TAGS: dict[str, str] = {
    "create_dir": "[green]+ DIR [/green]",
    "copy_file": "[green]+ FILE[/green]",
    "overwrite_force": "[yellow]! OVR [/yellow]",
    "skip_exists": "[dim]= keep[/dim]",
}


def format_dry_run_item(action: str, *, target: Path, note: str) -> str:
    """单条 dry-run plan item：tag + target 路径 + dim 灰色 note。"""

    tag = _DRY_RUN_TAGS.get(action, "?")
    return f"  {tag} {target}  [dim]{note}[/dim]"


def format_dry_run_completion() -> str:
    """dry-run 完成提示：明确告知"未写任何文件"。"""

    return "[dim]--dry-run 完成；未写任何文件。[/dim]"


def format_execute_action(action_line: str) -> str:
    """单条 execute_plan 输出行：两空格缩进。"""

    return f"  {action_line}"


def format_next_steps(steps: Iterable[str]) -> list[str]:
    """Next steps 区块：bold 标题 + 缩进的 step 列表。"""

    lines = ["\n[bold green]✓ MindForge initialized.[/bold green]", "[bold]Next steps:[/bold]"]
    for step in steps:
        lines.append(f"  {step}")
    return lines


def format_safety_footer() -> str:
    """init 安全 footer：不创建 .env、不读 .env、不调 LLM、不动原始资料。"""

    return "[dim]说明：init 不创建真实 .env、不读取 .env、不调用 LLM、不修改原始资料。[/dim]"


__all__ = [
    "format_dry_run_completion",
    "format_dry_run_item",
    "format_execute_action",
    "format_interactive_summary",
    "format_mode_lines",
    "format_next_steps",
    "format_plan_header",
    "format_plan_summary",
    "format_safety_footer",
]
