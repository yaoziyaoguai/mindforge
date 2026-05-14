"""Source Plugin Slice 5 — Source ingestion consumption boundary 契约 (TDD)。

为什么有这个文件
================

Slice 1–4 守住了 source 层内部（contract / capability / mux / cubox
opt-in）。Slice 5 守住的是 **下游消费者**：strategy / processor /
{approval,review,recall}_service 必须**只看 SourceDocument**，永远不
直接 import 任何具体 adapter 类（CuboxApiAdapter / CuboxMarkdownAdapter
/ ObsidianVaultSourceAdapter / PdfSourceAdapter / …）。

任何反向依赖都意味着：
- "下游业务在 if isinstance(adapter, CuboxApiAdapter)" 偷偷做特殊分支；
- "review/approval 直接读 cubox 字段" 让 source 层换实现就崩；
- 真实 LLM / 真实 API 路径绕过 SourceMux 的 audit_trail 直接被业务层
  调起。

CLI 是 source 的 adapter 层，自己 import concrete adapter 是合法的
（``cubox_cli.py`` 与 ``obsidian_cli.py`` 即如此）。Slice 5 不限制
CLI；只限制 strategy / processor / 三个 service。

设计边界
========

- 本文件**只动 tests**，不动 production code（当前下游已合规，Slice
  5 是把现状钉成不可回退的边界）。
- 用 AST 静态扫 import 表，避免运行时副作用。
- 限定可扫范围为顶层模块（不递归子模块），把规则写得显式。

Red / Green 期望
================

全部 **Green**。Slice 5 的 Red 来自未来回归——任何想让下游业务直接持
有具体 adapter 类的 PR 都会被这一组测试钉住。
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import mindforge


# 已知的所有具体 adapter 模块（不允许下游 import）
_CONCRETE_ADAPTER_MODULES = frozenset({
    "cubox_api",
    "cubox_markdown",
    "obsidian_vault",
    "plain_markdown",
    "pdf",
    "epub",
    "html_doc",
    "image_ocr",
})


# 受约束的下游模块；下游业务只能消费 sources.base 中的 SourceDocument /
# SourceAdapter 抽象，不能 import 任何 _CONCRETE_ADAPTER_MODULES。
#
# **不**包含 cli.py / cubox_cli.py / obsidian_cli.py：CLI 子模块本身就是
# adapter 集成层，可以拿具体类（这是 Hexagonal Architecture 的"adapters"
# 那一侧）。
_CONSTRAINED_DOWNSTREAM = (
    "strategies/base.py",
    "strategies/five_stage.py",
    "strategies/registry.py",
    "processors/base.py",
    "processors/pipeline.py",
    "approval_service.py",
    "review_service.py",
    "recall_service.py",
    "process_service.py",
    "source_mux.py",  # mux 自身也不能感知具体 adapter
)


def _module_path(rel: str) -> Path:
    pkg_dir = Path(mindforge.__file__).parent
    return pkg_dir / rel


def _from_imports(path: Path) -> set[tuple[str, ...]]:
    """返回所有 ``from X.Y import Z`` 的 ``(X, Y, ...)`` 元组集合。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: set[tuple[str, ...]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            out.add(tuple(node.module.split(".")))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                out.add(tuple(alias.name.split(".")))
    return out


# ---------------------------------------------------------------------------
# 1. 下游模块不得 import 任何具体 adapter
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rel_path", _CONSTRAINED_DOWNSTREAM)
def test_downstream_module_does_not_import_concrete_adapter(rel_path: str) -> None:
    """downstream 业务层只能消费 SourceDocument / SourceAdapter 抽象。

    具体 adapter 类（CuboxApiAdapter / ObsidianVaultSourceAdapter / …）
    只允许由 sources.registry / scanner / 各个 *_cli.py 引用。

    这是 Hexagonal Architecture 的核心：业务层与 adapter 实现解耦。
    """
    path = _module_path(rel_path)
    leaks: list[str] = []
    for parts in _from_imports(path):
        # 形如 ('mindforge', 'sources', 'cubox_api') 或 ('.', 'sources', 'cubox_api')
        # AST 已剥离前导 '.'，但 module 可能从 sources 开头。
        for i, seg in enumerate(parts):
            if seg == "sources" and i + 1 < len(parts):
                child = parts[i + 1]
                if child in _CONCRETE_ADAPTER_MODULES:
                    leaks.append(".".join(parts))
                    break
    assert not leaks, (
        f"{rel_path} 不得 import 具体 adapter 模块：{leaks}；"
        f"只能 import sources.base 抽象"
    )


# ---------------------------------------------------------------------------
# 2. 下游模块不得 import 任何 LLM provider
# ---------------------------------------------------------------------------


_FORBIDDEN_DOWNSTREAM_LIBS = frozenset({
    "openai",
    "anthropic",
    "cohere",
    "google",  # google.generativeai
    "transformers",
    "sentence_transformers",
    "faiss",
    "chromadb",
    "pinecone",
})


@pytest.mark.parametrize("rel_path", _CONSTRAINED_DOWNSTREAM)
def test_downstream_module_does_not_import_llm_provider(rel_path: str) -> None:
    path = _module_path(rel_path)
    top_imports: set[str] = set()
    for parts in _from_imports(path):
        if parts:
            top_imports.add(parts[0])
    leaked = top_imports & _FORBIDDEN_DOWNSTREAM_LIBS
    assert not leaked, (
        f"{rel_path} 不得 import LLM provider / vector / embedding 库：{leaked}"
    )


# ---------------------------------------------------------------------------
# 3. CLI 自己持具体 adapter 是合法的（钉住边界，避免误改）
# ---------------------------------------------------------------------------


def test_source_specific_legacy_cli_is_removed_but_obsidian_adapter_layer_remains() -> None:
    """source adapter 仍可存在，但 Cubox-first CLI surface 已迁移删除。

    中文学习型说明：过去的反向 contract 允许 ``cubox_cli.py`` 持有具体
    Cubox adapter。产品语义迁移后，Cubox 不能再作为用户主命令层存在；
    这里改守新边界：root/CLI 不再依赖 Cubox adapter，但现有 Obsidian
    adapter CLI 仍是隐藏的内部集成层。
    """
    cubox_cli = _module_path("cubox_cli.py")
    obsidian_cli = _module_path("obsidian_cli.py")
    assert not cubox_cli.exists()
    assert obsidian_cli.exists()
    obsidian_imports = {".".join(p) for p in _from_imports(obsidian_cli)}
    assert any("sources.obsidian_vault" in s for s in obsidian_imports), (
        "obsidian_cli.py 应直接 import ObsidianVaultSourceAdapter"
    )


# ---------------------------------------------------------------------------
# 4. SourceDocument 是 sources.base 的导出符号 —— 下游消费的唯一入口
# ---------------------------------------------------------------------------


def test_source_document_is_only_exported_from_base() -> None:
    """SourceDocument 必须只在 sources.base 定义；其他 source 模块只能 import
    它，不能重新定义同名符号——避免下游被多处 SourceDocument 污染。
    """
    from mindforge.sources import base as base_mod
    pkg_dir = Path(mindforge.__file__).parent / "sources"
    offenders: list[str] = []
    for py in pkg_dir.glob("*.py"):
        if py.name in {"base.py", "__init__.py"}:
            continue
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "SourceDocument":
                offenders.append(py.name)
    assert not offenders, (
        f"SourceDocument 必须只在 sources/base.py 定义；以下文件重复定义：{offenders}"
    )
    # 同时确认 base_mod 自身导出
    assert hasattr(base_mod, "SourceDocument")
