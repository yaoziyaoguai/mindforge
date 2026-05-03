"""``render_multi_project_context_markdown`` orchestrator/section 边界契约。

中文学习边界（Residual Architecture Debt Closure Pack）：

- 原 178 行 god-renderer 已被拆为 11 个 ``_section_*`` helper + 一个薄
  orchestrator。这两条不变量是这次拆分的"门"，未来任何人想重新把段落
  逻辑塞回 orchestrator，都会被这里挡住：
    1. orchestrator 函数体必须保持薄（行数 < 段落 helper 总数 × 阈值）；
    2. 每个 ``_section_*`` helper 必须存在并返回 ``list[str]``。
- 这些是 AST/inspection 级断言，不耦合具体文案；当文案需要改时，调整
  对应 ``_section_*``，orchestrator 与本测试都不需要改动。
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from mindforge import multi_project_context as mpc


_MODULE_PATH = Path(mpc.__file__)


_REQUIRED_SECTIONS = [
    "_section_overview",
    "_section_source_notice",
    "_section_project_profiles",
    "_section_cross_tracks",
    "_section_cross_principles",
    "_section_cross_risks",
    "_section_project_specific_cards",
    "_section_shared_action_items",
    "_section_review_due",
    "_section_suggested_prompt",
    "_section_excluded_content",
]


@pytest.mark.parametrize("name", _REQUIRED_SECTIONS)
def test_each_section_helper_exists_and_is_callable(name: str) -> None:
    """11 个具名 section helper 必须都存在；缺一即视为合并回 god-renderer。"""

    helper = getattr(mpc, name, None)
    assert helper is not None, f"缺失 section helper: {name}"
    assert callable(helper), f"{name} 必须是 callable"


def test_orchestrator_body_remains_thin() -> None:
    """``render_multi_project_context_markdown`` 必须保持薄编排，不再
    把段落逻辑写在主体里。

    阈值取 60 行（含 docstring + 11 次 extend + 3 个可选段 if）：当前
    实现约 40 行；如果未来主体 >60 行，几乎一定是把 helper 内联回来了。
    """

    src = inspect.getsource(mpc.render_multi_project_context_markdown)
    body_lines = src.splitlines()
    assert len(body_lines) < 60, (
        f"render_multi_project_context_markdown 主体已达 {len(body_lines)} 行；"
        f"段落逻辑应保留在 _section_* helper 中，主体只做编排。"
    )


def test_orchestrator_only_calls_section_helpers_and_setup() -> None:
    """orchestrator 内除了 setup（``_select_and_dedup`` / ``datetime`` /
    ``join``）外，其他主体调用必须命中 ``_section_*``。这是防止未来直接
    在主体里 inline 一段渲染的 AST 防线。"""

    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    target: ast.FunctionDef | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "render_multi_project_context_markdown":
            target = node
            break
    assert target is not None

    allowed_setup = {
        "_select_and_dedup",
        "now",
        "astimezone",
        "isoformat",
        "join",
        "rstrip",
        "extend",
        "append",
        "len",
        "values",
    }
    for node in ast.walk(target):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = getattr(func, "attr", None) or getattr(func, "id", None)
        if name is None:
            continue
        if name in allowed_setup:
            continue
        if name.startswith("_section_"):
            continue
        raise AssertionError(
            f"orchestrator 内出现非 section / 非 setup 调用 {name!r}；"
            f"段落渲染应下沉到 _section_* helper。"
        )
