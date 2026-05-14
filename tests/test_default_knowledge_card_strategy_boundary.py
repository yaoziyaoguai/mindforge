"""DefaultKnowledgeCardStrategy boundary tests — v0.10 KnowledgeStrategy Slice 1.

为什么有这个文件
================

``tests/test_strategy_seam_boundary.py`` 已经覆盖整个 strategies/ 目录的
反向 import 边界。本文件**专门**针对 Slice 2 即将创建的
``strategies/default_knowledge_card.py`` 模块路径再加一层 AST 守护，
确保新模块从诞生那一刻起就遵守相同的边界规则。

为什么不合并到 ``test_strategy_seam_boundary.py``？
- 保持测试文件单一职责（一个文件 = 一种策略 module 的 boundary）；
- 让 Slice 1 Red 的失败原因明显是"新模块缺失"而不是"既有 boundary
  扫描漏了一个文件"；
- Slice 4 会把这两个文件 cross-reference 进 ARCHITECTURE_MAP.md。

设计期望
========

Slice 1 期望全部 **Red**（FileNotFoundError / 模块不存在）；
Slice 2 实现后转绿；Slice 4 把它们标为 permanent regression net。
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_SRC = _REPO / "src" / "mindforge"
_STRATEGY_FILE = _SRC / "strategies" / "default_knowledge_card.py"


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names.add(a.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


# 任何一项命中即违规（与 README 中的架构边界对齐）
_FORBIDDEN_FOR_DEFAULT_KCS: frozenset[str] = frozenset({
    # source domain（strategy 必须 source-agnostic）
    "mindforge.cubox_cli",
    "mindforge.cubox_dryrun_presenter",
    "mindforge.source_mux",
    "mindforge.scanner",
    "mindforge.sources.cubox_api",
    "mindforge.sources.cubox_markdown",
    "mindforge.sources.obsidian_vault",
    "mindforge.sources.pdf",
    "mindforge.sources.epub",
    "mindforge.sources.html_doc",
    "mindforge.sources.image_ocr",
    "mindforge.sources.plain_markdown",
    "mindforge.sources.chat_export",
    # vault / workspace
    "mindforge.vault_writer",
    "mindforge.workspace",
    "mindforge.obsidian",
    "mindforge.obsidian_cli",
    # approval / review / recall
    "mindforge.approver",
    "mindforge.approval_service",
    "mindforge.review_service",
    "mindforge.recall_service",
    # CLI / presenter / run logger
    "mindforge.cli",
    "mindforge.approve_presenter",
    "mindforge.review_presenter",
    "mindforge.recall_presenter",
    # 网络 / vector / embedding
    "requests",
    "httpx",
    "urllib3",
    "aiohttp",
    "openai",
    "anthropic",
    "transformers",
    "sentence_transformers",
    "faiss",
    "chromadb",
    "pinecone",
    "numpy",
    "torch",
    # dotenv
    "dotenv",
    "python_dotenv",
})


# ---------------------------------------------------------------------------
# 1. 模块文件存在 —— Slice 1 期望 Red
# ---------------------------------------------------------------------------


def test_strategy_module_file_exists() -> None:
    """``src/mindforge/strategies/default_knowledge_card.py`` 必须存在。"""
    assert _STRATEGY_FILE.is_file(), (
        f"模块文件未创建：{_STRATEGY_FILE}（Slice 2 的工作）"
    )


# ---------------------------------------------------------------------------
# 2. AST 反向 import 边界
# ---------------------------------------------------------------------------


def test_strategy_module_does_not_import_forbidden_modules() -> None:
    """default_knowledge_card.py 不得 import 任何 source / vault / approval /
    cli / 网络 / vector / dotenv 模块。
    """
    if not _STRATEGY_FILE.is_file():
        pytest.fail(
            "模块文件未创建（Slice 2 的工作）；本测试在 Slice 1 阶段期望 Red"
        )
    names = _imports(_STRATEGY_FILE)
    leaks = names & _FORBIDDEN_FOR_DEFAULT_KCS
    # 顶层根模块也要扫一遍（处理 ``import requests`` vs ``from requests import x``）
    top_roots = {n.split(".")[0] for n in names}
    forbidden_roots = {n.split(".")[0] for n in _FORBIDDEN_FOR_DEFAULT_KCS}
    leaks |= top_roots & forbidden_roots
    assert not leaks, (
        f"default_knowledge_card.py 反向 import 越界：{sorted(leaks)}"
    )


# ---------------------------------------------------------------------------
# 3. 模块只暴露 SourceDocument 一种输入面
# ---------------------------------------------------------------------------


def test_strategy_module_only_input_face_is_source_document() -> None:
    """模块对 source 层的依赖只允许是 ``mindforge.sources.base``（提供
    ``SourceDocument``）。
    """
    if not _STRATEGY_FILE.is_file():
        pytest.fail("模块文件未创建（Slice 2 的工作）；Slice 1 阶段期望 Red")
    names = _imports(_STRATEGY_FILE)
    source_imports = {n for n in names if n.startswith("mindforge.sources")
                       or n.startswith(".sources")
                       or n == "..sources.base"}
    # 允许 'mindforge.sources.base' / '..sources.base' / '.sources.base'
    allowed_suffixes = ("sources.base",)
    bad = [
        s for s in source_imports
        if not any(s.endswith(suf) for suf in allowed_suffixes)
    ]
    assert not bad, (
        f"default_knowledge_card.py 只能依赖 sources.base，越界：{bad}"
    )
