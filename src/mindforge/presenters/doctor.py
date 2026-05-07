"""``mindforge doctor`` 的 Rich/markup 展示层。

中文学习型说明：
- 本模块只把 service 层返回的 ``state`` 字符串映射成带颜色的 markup。
- 不做任何业务判断（"该不该 init / 该不该 demo" 不在这里），不读 cfg，
  不发 IO。这样未来若 doctor 输出要切换为纯文本 / JSON / HTML，只需要替
  换 presenter，service 与 cli 完全不动。
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["doctor_icon", "ok_dir"]


def doctor_icon(state: str) -> str:
    """把 ``ok`` / ``warn`` / ``error`` / ``info`` 映射成带颜色的 markup 字符。

    未识别 state 一律退化成 ``info`` 风格的灰点，避免 KeyError 把 doctor
    渲染流程打断。
    """

    return {
        "ok": "[green]✓[/green]",
        "warn": "[yellow]⚠[/yellow]",
        "error": "[red]✗[/red]",
        "info": "[dim]·[/dim]",
    }.get(state, "[dim]·[/dim]")


def ok_dir(p: Path) -> str:
    """把目录存在性渲染成人类可读、带颜色的 markup 状态字符串。"""

    if not p.exists():
        return "[red]missing[/red]"
    if not p.is_dir():
        return "[red]not a dir[/red]"
    return "[green]ok[/green]"
