"""prompt 文件加载 + 变量渲染（最小实现）。

为什么不用 jinja2
==================

prompts/<stage>/v1.md 中的占位符是 ``{{name}}`` 形式（与 jinja2 巧合），
但 v0.1 的 prompt 只做"按变量名替换"，**不**需要任何控制流 / 过滤器 /
转义规则。用一个 30 行的正则替换器更清晰、更可审计，不引入隐式行为。

LLM 看到的最终 prompt **必须**完全可由 ``(prompt_text, variables)`` 复现，
这是后续做 prompt A/B 与回放的基础。
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_VAR_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


@lru_cache(maxsize=64)
def load_prompt(prompts_dir: Path, stage: str, version: str) -> str:
    """读取 ``<prompts_dir>/<stage>/<version>.md`` 全文。"""
    path = prompts_dir / stage / f"{version}.md"
    return path.read_text("utf-8")


def render(prompt_text: str, variables: dict[str, Any]) -> str:
    """把 ``{{name}}`` 替换为 ``str(variables[name])``。

    缺失变量 → 留空字符串（v0.1 容错；缺失字段不致整体崩溃）。
    """

    def _sub(m: re.Match[str]) -> str:
        name = m.group(1)
        v = variables.get(name, "")
        if isinstance(v, str):
            return v
        return str(v)

    return _VAR_RE.sub(_sub, prompt_text)


__all__ = ["load_prompt", "render"]
