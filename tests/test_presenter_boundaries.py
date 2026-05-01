"""Architecture fitness functions — presenter 层 AST 静态边界测试。

中文学习型说明
================

为什么要这一类测试？
--------------------
``approve_presenter`` / ``recall_presenter`` / ``review_presenter`` 是
MindForge 的展示层。它们的存在前提是"用户可见展示与 use-case 业务语义
解耦"——service 出 dataclass，presenter 把 dataclass 翻成 JSON / Markdown
/ Rich Table / 文本提示。

行为层测试覆盖"渲染输出格式是否正确"。本文件不同：它把 presenter 层的
**架构意图**变成静态可回归验证的 fitness function——用 ``ast.parse``
直接读 source，断言 import 图、禁忌符号、公开符号面、模块体量。
**不实例化任何对象，不运行业务路径**。

为什么 presenter 要被这样保护？
-------------------------------
- presenter 是 v0.7.21 / v0.7.22 通过抽取 ``cli.py`` 巨石得到的层。
  如果它悄悄 ``import .approver`` / 调 ``approve_card`` / 写 ``write_text``
  / 读 ``os.environ``，它就退化成"披着 presenter 名字的 controller"，
  抽取的意义被打穿。
- presenter 是**纯转换函数**：输入 dataclass，输出可见字符串/Rich 对象。
  它**不应**反过来 import CLI 层、不应跨 use-case 编排其他 service、
  不应承担 ``ai_draft → human_approved`` 状态翻转。
- presenter 是 console / file 输出的最外层；它**绝不**应 import 真实
  LLM SDK / dotenv / RAG / embedding。

三个 presenter 的允许依赖白名单（service-specific）
---------------------------------------------------
每个 presenter 只允许 import 自己对应的 ``*_service`` + cards data
shape + 必要 stdlib + 可选 ``rich``。本文件用 ``parametrize`` 让每个
presenter 各跑一遍同一组检查，便于对照定位违规来源。

allowed_per_presenter:
  approve_presenter:
    {__future__, json, typing, rich.console, rich.table,
     mindforge.approval_service, mindforge.cards}
  recall_presenter:
    {__future__, json, dataclasses, pathlib, typing,
     rich.console, rich.table, mindforge.recall_service}
  review_presenter:
    {__future__, typing, mindforge.cards, mindforge.review_service}

防"小巨石化"
-------------
顶层函数 / class 数量上限 + 公开符号面（top-level public name）快照。
``review_presenter`` / ``recall_presenter`` 当前没有显式 ``__all__``，
所以快照基于"顶层非 ``_`` 开头的 def/class 名"统一处理。新增公开符号
必须显式更新本测试，强制评审"是否真的应该塞进 presenter 层"。
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Presenter spec：每个 presenter 的白名单 / 上限 / 期望公开符号
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PresenterSpec:
    name: str
    path: Path
    allowed_imports: frozenset[str]
    func_cap: int
    class_cap: int
    expected_public: frozenset[str]


SRC_DIR = Path(__file__).resolve().parents[1] / "src" / "mindforge"


PRESENTERS: tuple[PresenterSpec, ...] = (
    PresenterSpec(
        name="approve_presenter",
        path=SRC_DIR / "approve_presenter.py",
        allowed_imports=frozenset({
            "__future__",
            "json",
            "typing",
            "rich.console",
            "rich.table",
            "mindforge.approval_service",
            "mindforge.cards",
        }),
        # 当前 17 公开 symbol（皆函数）；buffer +2
        func_cap=20,
        class_cap=2,
        expected_public=frozenset({
            "approve_next_command",
            "build_approval_list_json",
            "format_card_created_at",
            "format_card_source_hint",
            "render_approval_list",
            "render_approval_list_json",
            "render_approval_show",
            "render_approval_show_error",
            "render_bulk_candidate_list",
            "render_bulk_confirm_required",
            "render_bulk_dry_run_footer",
            "render_bulk_empty",
            "render_bulk_summary",
            "render_execution_failure",
            "render_execution_success",
            "render_lookup_error",
            "render_routing_hint",
        }),
    ),
    PresenterSpec(
        name="recall_presenter",
        path=SRC_DIR / "recall_presenter.py",
        allowed_imports=frozenset({
            "__future__",
            "json",
            "dataclasses",
            "pathlib",
            "typing",
            "rich.console",
            "rich.table",
            "mindforge.recall_service",
        }),
        func_cap=12,
        class_cap=4,
        # recall_presenter 无 __all__，本测试基于 AST 顶层 public name 快照
        expected_public=frozenset({
            "RecallRenderContext",
            "build_recall_json_payload",
            "format_recall_markdown",
            "render_recall_result",
        }),
    ),
    PresenterSpec(
        name="review_presenter",
        path=SRC_DIR / "review_presenter.py",
        allowed_imports=frozenset({
            "__future__",
            "typing",
            "mindforge.cards",
            "mindforge.review_service",
        }),
        func_cap=10,
        class_cap=2,
        expected_public=frozenset({
            "build_weekly_review_json",
            "render_weekly_learning_tasks",
            "render_weekly_next_actions",
            "render_weekly_review_markdown",
        }),
    ),
)


# ---------------------------------------------------------------------------
# AST helper（与 service boundaries 同构）
# ---------------------------------------------------------------------------


def _toplevel_import_modules(tree: ast.Module) -> set[str]:
    """收集顶层 import 模块名。``from .x import y`` 还原为 ``mindforge.x``。"""
    mods: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level == 1 and mod:
                mods.add(f"mindforge.{mod}")
            elif node.level == 0:
                mods.add(mod)
    return mods


def _all_imported_names(tree: ast.AST) -> set[str]:
    """收集所有 import（含函数体内 import），用于反向依赖检查。"""
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level >= 1 and mod:
                mods.add(f"mindforge.{mod}")
            elif node.level == 0 and mod:
                mods.add(mod)
    return mods


def _all_call_names(tree: ast.AST) -> set[str]:
    """收集所有 ``Call`` 节点目标符号名。"""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                names.add(f.id)
            elif isinstance(f, ast.Attribute):
                names.add(f.attr)
    return names


def _all_attribute_chains(tree: ast.AST) -> set[str]:
    chains: set[str] = set()

    def _flatten(n: ast.AST) -> str | None:
        if isinstance(n, ast.Name):
            return n.id
        if isinstance(n, ast.Attribute):
            base = _flatten(n.value)
            if base is None:
                return None
            return f"{base}.{n.attr}"
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            chain = _flatten(node)
            if chain:
                chains.add(chain)
    return chains


def _toplevel_public_names(tree: ast.Module) -> set[str]:
    """收集顶层非下划线开头的 def/class 名作为公开符号面。

    与 ``__all__`` 互补：当 presenter 没有 ``__all__`` 时，这是事实上
    可被外部 import 的公开符号集合。
    """
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                names.add(node.name)
    return names


def _parse(spec: PresenterSpec) -> ast.Module:
    return ast.parse(spec.path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Parametrized boundary tests
# ---------------------------------------------------------------------------

PARAM = pytest.mark.parametrize("spec", PRESENTERS, ids=[s.name for s in PRESENTERS])


@PARAM
def test_toplevel_imports_match_allowlist(spec: PresenterSpec) -> None:
    """正向断言：每个 presenter 的顶层 import 必须**完全等于**自己白名单。

    presenter 是窄输入窄输出的转换层，依赖应当极小；这条白名单封闭性
    把"潜入新依赖"变成显式 PR 评审决策。
    """
    actual = _toplevel_import_modules(_parse(spec))
    assert actual == spec.allowed_imports, (
        f"{spec.name} 顶层 import 与白名单不匹配。\n"
        f"  超出白名单（违规新增）: {sorted(actual - spec.allowed_imports)}\n"
        f"  白名单未使用（应同步删除）: {sorted(spec.allowed_imports - actual)}"
    )


@PARAM
def test_no_reverse_dep_on_cli(spec: PresenterSpec) -> None:
    """禁止反向依赖 CLI 层。

    presenter 是被 CLI 调用的下层；反向依赖会形成边界倒置 + 循环导入。
    """
    forbidden = {"mindforge.cli", "mindforge.obsidian_cli"}
    hit = _all_imported_names(_parse(spec)) & forbidden
    assert not hit, f"{spec.name} 不应 import CLI 层：{sorted(hit)}"


@PARAM
def test_no_cross_service_orchestration(spec: PresenterSpec) -> None:
    """禁止跨 use-case service 编排。

    每个 presenter 只允许 import 与自己**同名 use-case** 的 service
    （已在白名单里）。如果它再 import 其他 use-case service，就在
    presenter 层做 use-case orchestration——这是 controller / workflow
    的职责，不是展示。
    """
    forbidden = {
        "mindforge.process_service",
        "mindforge.review_service",
        "mindforge.approval_service",
        "mindforge.recall_service",
    } - spec.allowed_imports
    hit = _all_imported_names(_parse(spec)) & forbidden
    assert not hit, (
        f"{spec.name} 不应跨 use-case service 编排：{sorted(hit)}"
    )


@PARAM
def test_no_approver_or_status_mutation_imports(spec: PresenterSpec) -> None:
    """禁止 import approver / 状态翻转模块。

    presenter 永远不应承担 ``ai_draft → human_approved`` 状态翻转。
    那是 approval_service + approver 的独占职责。
    """
    forbidden = {"mindforge.approver", "mindforge.reviewer"}
    hit = _all_imported_names(_parse(spec)) & forbidden
    assert not hit, (
        f"{spec.name} 不应 import 状态翻转层（approver/reviewer）：{sorted(hit)}"
    )


@PARAM
def test_no_status_mutation_calls(spec: PresenterSpec) -> None:
    """禁止调用任何修改 card 状态的函数。"""
    forbidden = {
        "approve_card",
        "approve_explicit_card",
        "mark_review_outcome",
        "mark_card_status",
        "mark_card_review",
    }
    hit = _all_call_names(_parse(spec)) & forbidden
    assert not hit, f"{spec.name} 不应调用状态修改函数：{sorted(hit)}"


@PARAM
def test_no_real_llm_sdk_imports(spec: PresenterSpec) -> None:
    """禁止真实 LLM SDK。presenter 是纯展示，永远不应触发 LLM 调用。"""
    forbidden = {"openai", "anthropic", "litellm", "cohere", "ollama"}
    hit = _all_imported_names(_parse(spec)) & forbidden
    assert not hit, f"{spec.name} 不应 import 真实 LLM SDK：{sorted(hit)}"


@PARAM
def test_no_typer_or_click_imports(spec: PresenterSpec) -> None:
    """禁止 CLI 框架（typer/click）。

    presenter 不持有 Typer command / 不解析参数 / 不退出进程。
    Rich 是允许的（presenter 是渲染层），但 typer/click 属于 CLI adapter。
    """
    forbidden = {"typer", "click", "textual", "prompt_toolkit"}
    hit = _all_imported_names(_parse(spec)) & forbidden
    assert not hit, f"{spec.name} 不应 import CLI 框架：{sorted(hit)}"


@PARAM
def test_no_rag_or_embedding_imports(spec: PresenterSpec) -> None:
    """禁止 RAG / embedding / vector store。"""
    forbidden_substrings = (
        "embedding",
        "vector",
        "faiss",
        "chromadb",
        "qdrant",
        "pinecone",
        "weaviate",
    )
    hits: list[str] = []
    for mod in _all_imported_names(_parse(spec)):
        low = mod.lower()
        for needle in forbidden_substrings:
            if needle in low:
                hits.append(mod)
                break
    assert not hits, f"{spec.name} 不应 import RAG/embedding：{hits}"


@PARAM
def test_no_dotenv_imports(spec: PresenterSpec) -> None:
    """禁止 dotenv。presenter 不读 ``.env``。"""
    forbidden = {"dotenv", "python_dotenv", "mindforge.env_loader"}
    hit = _all_imported_names(_parse(spec)) & forbidden
    assert not hit, f"{spec.name} 不应 import dotenv 相关：{sorted(hit)}"


@PARAM
def test_no_os_environ_access(spec: PresenterSpec) -> None:
    """禁止访问 ``os.environ`` / ``os.getenv``。"""
    chains = _all_attribute_chains(_parse(spec))
    forbidden_chains = {"os.environ", "os.getenv", "environ.get"}
    hit = chains & forbidden_chains
    assert not hit, f"{spec.name} 不应访问 os.environ：{sorted(hit)}"


@PARAM
def test_no_file_write_calls(spec: PresenterSpec) -> None:
    """禁止任何写盘调用。

    presenter 是**纯转换函数**：输入 dataclass，输出 Rich/JSON/字符串。
    不写文件、不写 vault、不写 checkpoint。这是 presenter "纯函数化"
    边界的关键。
    """
    tree = _parse(spec)
    forbidden = {"write_text", "write_bytes"}
    hit = _all_call_names(tree) & forbidden
    assert not hit, f"{spec.name} 不应写文件：{sorted(hit)}"

    open_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "open"
    ]
    assert not open_calls, f"{spec.name} 不应调用 open() 写文件"


@PARAM
def test_no_human_approved_literal_assignment(spec: PresenterSpec) -> None:
    """``"human_approved"`` 字面量**只允许**作为 ``status=`` keyword 出现。

    presenter 偶尔需要把 ``human_approved`` 文案展示给用户（如
    "已审核 / human_approved" 标签），但**必须**作为 keyword 参数传给
    filter_cards 等只读函数；**不允许**作为 Assign 右侧值出现，否则
    意味着 presenter 在构造/翻转状态。
    """
    tree = _parse(spec)
    parents: dict[int, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[id(child)] = parent

    violations: list[str] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and node.value == "human_approved"):
            continue
        cur: ast.AST | None = node
        enclosing_keyword: ast.keyword | None = None
        while cur is not None:
            parent = parents.get(id(cur))
            if parent is None or isinstance(parent, ast.Module):
                break
            if isinstance(parent, ast.keyword):
                enclosing_keyword = parent
                break
            cur = parent
        if enclosing_keyword is not None and enclosing_keyword.arg == "status":
            continue
        violations.append(f"line {node.lineno}")
    assert not violations, (
        f"{spec.name} 不应在 status= keyword 之外出现 'human_approved' 字面量：{violations}"
    )


@PARAM
def test_public_surface_snapshot(spec: PresenterSpec) -> None:
    """公开符号面快照锁。

    若 presenter 定义了 ``__all__``，以 ``__all__`` 为准；否则以"顶层
    非 ``_`` 开头 def/class"为准。新增公开符号必须显式更新本测试，
    强制评审"是否真的应该塞进 presenter？还是应该抽 sub-module？"。
    """
    tree = _parse(spec)
    # 优先 __all__
    all_value: list[str] | None = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        all_value = [
                            elt.value
                            for elt in node.value.elts
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                        ]
    actual = frozenset(all_value) if all_value is not None else _toplevel_public_names(tree)
    assert actual == spec.expected_public, (
        f"{spec.name} 公开符号面快照不匹配。\n"
        f"  新增（请评审）: {sorted(actual - spec.expected_public)}\n"
        f"  缺失（请检查）: {sorted(spec.expected_public - actual)}"
    )


@PARAM
def test_function_count_cap(spec: PresenterSpec) -> None:
    """顶层函数数量上限。超过即提示"应该抽 sub-module 而不是继续堆"。"""
    tree = _parse(spec)
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) <= spec.func_cap, (
        f"{spec.name} 顶层函数数量 ({len(funcs)}) 超过上限 {spec.func_cap}。\n"
        f" 当前函数: {[f.name for f in funcs]}"
    )


@PARAM
def test_class_count_cap(spec: PresenterSpec) -> None:
    """顶层 class 数量上限（含 dataclass / Exception）。"""
    tree = _parse(spec)
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) <= spec.class_cap, (
        f"{spec.name} 顶层 class 数量 ({len(classes)}) 超过上限 {spec.class_cap}。\n"
        f" 当前 class: {[c.name for c in classes]}"
    )
