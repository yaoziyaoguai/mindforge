"""Architecture fitness functions — review_service AST 静态边界测试。

中文学习型说明
================

为什么要这一类测试？
--------------------
``tests/test_review_service.py`` 等行为层测试覆盖 ``build_weekly_review``
返回的 dataclass 字段、空状态语义、窗口计算等"运行时正确性"。

本文件不同。它把 ``review_service.py`` 的**架构意图**变成可回归验证的
fitness function：用 ``ast.parse`` 静态扫描 source，断言 import 图、
禁忌符号、public surface、模块体量。**不实例化任何对象，不运行业务路径**。

为什么 review_service 要被这样保护？
------------------------------------
- ``review_service`` 是 weekly review use-case 的唯一业务语义来源。
  它的存在前提是"业务聚合与 CLI / presenter / runtime 解耦"。
- weekly review 的核心边界是"只聚合 ``human_approved``、不自动 approve、
  不修改 card 状态、不写文件"——它是**纯读**服务。一旦它 import 了
  presenter / cli / typer / rich / openai / dotenv，或调用了 ``approve_*``
  / ``write_text``，weekly review 的安全语义就被打穿。
- 反向依赖（service → cli / presenter / obsidian_*）会立即引入循环
  导入与边界倒置。

防"小巨石化"机制
----------------
``__all__`` 快照锁 + 函数 / dataclass 数量上限。当前 review_service
有 7 个 public symbol、2 个顶层函数、5 个 dataclass。本测试设上限
8 / 3 / 6（各 +1 缓冲）。超过即 fail，强制评估"是否应该抽 sub-module
而不是继续往 review_service 里堆"。

允许的依赖白名单
----------------
正向断言：``review_service`` 的顶层 import 必须**完全等于**：

    {__future__, dataclasses, datetime,
     mindforge.cards, mindforge.config}

任何新依赖必须显式更新本测试，比开放 ban list 强度更高。

本文件与 v0.7.23 process_service boundary tests 的关系
--------------------------------------------------------
两个文件**结构同构**（同样的 5 个 AST helper、同样的 14 类断言），
但白名单 / 上限 / 禁忌不同。这种刻意的"模板复制"不是机械搬运——
它让每一个 service 的边界都独立、显式、可单独修改，避免共享 fixture
让边界声明被隐藏到一个抽象基类里。
"""

from __future__ import annotations

import ast
from pathlib import Path

# ---------------------------------------------------------------------------
# 模块级 fixture：一次解析，多次使用
# ---------------------------------------------------------------------------

REVIEW_SERVICE_PATH: Path = (
    Path(__file__).resolve().parents[1] / "src" / "mindforge" / "review_service.py"
)
SOURCE: str = REVIEW_SERVICE_PATH.read_text(encoding="utf-8")
TREE: ast.Module = ast.parse(SOURCE)


# ---------------------------------------------------------------------------
# AST helper（与 process_service_boundaries 同构，便于对照阅读）
# ---------------------------------------------------------------------------


def _toplevel_import_modules(tree: ast.Module) -> set[str]:
    """收集顶层 import 的模块名。

    ``from .x import y`` 还原为 ``mindforge.x``。
    """
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
    """收集所有 ``Call`` 节点的目标符号名。"""
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
    """把 ``a.b.c`` Attribute 链还原为字符串集合。"""
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


def _string_constants_assigned_or_returned(tree: ast.AST) -> set[str]:
    """收集 Assign/AnnAssign/Return/keyword value 中的字符串字面量。

    docstring 不会进入此集合（docstring 是裸 Expr，不是 Assign/Return）。
    """
    consts: set[str] = set()

    def _collect(value: ast.AST) -> None:
        for sub in ast.walk(value):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                consts.add(sub.value)

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            _collect(node.value)
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            _collect(node.value)
        elif isinstance(node, ast.Return) and node.value is not None:
            _collect(node.value)
        elif isinstance(node, ast.keyword) and node.value is not None:
            _collect(node.value)
    return consts


# ---------------------------------------------------------------------------
# Import boundary tests
# ---------------------------------------------------------------------------

# 顶层依赖白名单：白名单之外的 import 都视为越界。
ALLOWED_TOPLEVEL_IMPORTS: frozenset[str] = frozenset({
    "__future__",
    "dataclasses",
    "datetime",
    "mindforge.cards",
    "mindforge.config",
})


def test_toplevel_imports_match_allowlist() -> None:
    """正向断言：顶层 import 必须**完全等于**白名单。

    任何新依赖必须显式更新本测试，强制 code review 注意"是否真的应该
    扩大 review_service 的依赖面"。review_service 是纯读聚合服务，
    依赖应当极小。
    """
    actual = _toplevel_import_modules(TREE)
    assert actual == ALLOWED_TOPLEVEL_IMPORTS, (
        f"review_service 顶层 import 与白名单不匹配。\n"
        f"  超出白名单（违规新增）: {sorted(actual - ALLOWED_TOPLEVEL_IMPORTS)}\n"
        f"  白名单未使用（应同步删除）: {sorted(ALLOWED_TOPLEVEL_IMPORTS - actual)}"
    )


def test_no_reverse_dep_on_cli() -> None:
    """禁止反向依赖 CLI 层。

    review_service 是被 CLI 调用的下层；反向依赖会形成边界倒置 +
    循环导入风险。
    """
    forbidden = {"mindforge.cli"}
    hit = _all_imported_names(TREE) & forbidden
    assert not hit, f"review_service 不应 import CLI 层：{sorted(hit)}"


def test_no_reverse_dep_on_presenters() -> None:
    """禁止反向依赖 presenter 层。

    review_service 输出 dataclass，由 review_presenter 渲染。
    反向依赖会破坏"service 出数据 → presenter 出展示"的单向流。
    """
    forbidden = {
        "mindforge.recall_presenter",
        "mindforge.approve_presenter",
        "mindforge.review_presenter",
    }
    hit = _all_imported_names(TREE) & forbidden
    assert not hit, f"review_service 不应 import presenter 层：{sorted(hit)}"


def test_no_reverse_dep_on_obsidian_layer() -> None:
    """禁止反向依赖 Obsidian binding 层。"""
    forbidden = {
        "mindforge.obsidian_cli",
        "mindforge.obsidian_workflow",
        "mindforge.obsidian_stage",
    }
    hit = _all_imported_names(TREE) & forbidden
    assert not hit, f"review_service 不应 import Obsidian 层：{sorted(hit)}"


def test_no_reverse_dep_on_other_services() -> None:
    """review_service 不应 import 其他 use-case service。

    每个 service 都是独立 use-case；review 不应依赖 process_service /
    approval_service / recall_service 才能完成 weekly 聚合。
    它只依赖 cards 数据访问层。
    """
    forbidden = {
        "mindforge.process_service",
        "mindforge.approval_service",
        "mindforge.recall_service",
    }
    hit = _all_imported_names(TREE) & forbidden
    assert not hit, (
        f"review_service 不应 import 其他 service 层（应只依赖 cards / config）："
        f"{sorted(hit)}"
    )


def test_no_real_llm_sdk_imports() -> None:
    """禁止真实 LLM SDK 出现。

    review 是纯统计/聚合 use-case，永远不应触发 LLM 调用。即使将来
    出现"AI 总结 weekly review"的设想，那也应该是独立的 reviewer
    service，不能让 review_service 直接吃 LLM SDK。
    """
    forbidden = {
        "openai",
        "anthropic",
        "litellm",
        "cohere",
        "ollama",
    }
    hit = _all_imported_names(TREE) & forbidden
    assert not hit, f"review_service 不应 import 真实 LLM SDK：{sorted(hit)}"


def test_no_ui_framework_imports() -> None:
    """禁止 UI / CLI 框架直接出现。"""
    forbidden = {
        "typer",
        "click",
        "rich",
        "rich.console",
        "rich.table",
        "textual",
        "prompt_toolkit",
        "blessed",
        "urwid",
    }
    hit = _all_imported_names(TREE) & forbidden
    assert not hit, f"review_service 不应 import UI 框架：{sorted(hit)}"


def test_no_rag_or_embedding_imports() -> None:
    """禁止 RAG / embedding / vector store 出现。

    MindForge 当前阶段不引入向量检索。weekly review 用 frontmatter
    聚合即可，不需要 embedding。
    """
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
    for mod in _all_imported_names(TREE):
        low = mod.lower()
        for needle in forbidden_substrings:
            if needle in low:
                hits.append(mod)
                break
    assert not hits, f"review_service 不应 import RAG/embedding 模块：{hits}"


def test_no_dotenv_imports() -> None:
    """禁止任何形式的 dotenv 加载。

    .env 加载是 process workflow 的边界专属，且只在显式 opt-in 时启用。
    review_service 永远不应碰 .env。
    """
    forbidden = {"dotenv", "python_dotenv"}
    hit = _all_imported_names(TREE) & forbidden
    assert not hit, f"review_service 不应 import dotenv：{sorted(hit)}"


# ---------------------------------------------------------------------------
# Behavior boundary tests（基于 AST 的禁忌符号检查）
# ---------------------------------------------------------------------------


def test_no_os_environ_access() -> None:
    """禁止直接访问 ``os.environ`` / ``os.getenv``。

    review 不读环境变量。任何"weekly window 受 env 影响"的设计都
    应该走 ``MindForgeConfig``，由 config 层统一处理。
    """
    chains = _all_attribute_chains(TREE)
    forbidden_chains = {"os.environ", "os.getenv", "environ.get"}
    hit = chains & forbidden_chains
    assert not hit, f"review_service 不应直接访问 os.environ：{sorted(hit)}"


def test_no_status_mutation_calls() -> None:
    """禁止调用任何修改 card 状态的函数。

    review_service 是纯读：它聚合 ``human_approved`` 卡片做 weekly
    展示。即使 ``filter_cards(status="human_approved")`` 是允许的
    （只读筛选），任何 ``approve_*`` / ``mark_*`` 写入函数都属于
    approval / approver 层职责。
    """
    forbidden = {
        "approve_card",
        "approve_explicit_card",
        "mark_review_outcome",
        "mark_card_status",
    }
    hit = _all_call_names(TREE) & forbidden
    assert not hit, f"review_service 不应调用状态修改函数：{sorted(hit)}"


def test_no_file_write_calls() -> None:
    """禁止任何写盘调用。

    review 是纯读 use-case；它**绝不**写文件、写 vault、写 checkpoint。
    任何 ``write_text`` / ``write_bytes`` / ``open(...)`` 都属违规。
    （``read_text`` 仍然允许。）
    """
    forbidden = {"write_text", "write_bytes"}
    hit = _all_call_names(TREE) & forbidden
    assert not hit, f"review_service 不应写文件：{sorted(hit)}"

    # ``open`` 是内置函数，需要单独检查 Name(id="open") 形式
    open_calls = [
        node
        for node in ast.walk(TREE)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "open"
    ]
    assert not open_calls, "review_service 不应调用 open() 写文件"


def test_no_human_approved_literal_assignment() -> None:
    """``"human_approved"`` 字面量**只能**作为 ``status=`` keyword 参数出现。

    review_service 允许把 ``"human_approved"`` 作为 ``filter_cards`` 的
    keyword（``status="human_approved"``）——那是只读筛选条件。其他位置
    （Assign 右侧、Return 值、其他 keyword 参数）都属违规，因为那意味着
    review_service 在写状态、构造结果或承担非 review 的语义。

    实现：用 parent map 找到每个 ``Constant("human_approved")`` 最近
    enclosing 的 ``keyword`` 节点；若该 keyword 的 ``arg == "status"``
    则放行，否则 fail。这样既不会被嵌在 Assign RHS 里的 ``status=``
    keyword 误伤，也不会漏掉真正的违规位置。
    """
    parents: dict[int, ast.AST] = {}
    for parent in ast.walk(TREE):
        for child in ast.iter_child_nodes(parent):
            parents[id(child)] = parent

    violations: list[str] = []
    for node in ast.walk(TREE):
        if not (isinstance(node, ast.Constant) and node.value == "human_approved"):
            continue
        # 向上找最近的 keyword 或 Return / Assign / AnnAssign / FunctionDef
        cur: ast.AST | None = node
        enclosing_keyword: ast.keyword | None = None
        while cur is not None:
            parent = parents.get(id(cur))
            if parent is None:
                break
            if isinstance(parent, ast.keyword):
                enclosing_keyword = parent
                break
            # 越过 Module → 顶层裸 Constant 不太可能；直接停
            if isinstance(parent, ast.Module):
                break
            cur = parent
        if enclosing_keyword is not None and enclosing_keyword.arg == "status":
            continue  # 允许：filter_cards(status="human_approved")
        violations.append(f"line {node.lineno}: 'human_approved' 不在 status= keyword 中")
    assert not violations, (
        f"review_service 不应在 status= keyword 之外出现 'human_approved' "
        f"字面量：{violations}"
    )


# ---------------------------------------------------------------------------
# Public surface snapshot lock
# ---------------------------------------------------------------------------

EXPECTED_PUBLIC_API: frozenset[str] = frozenset({
    "FocusTrack",
    "ProjectCardCount",
    "WeeklyReviewEmptyState",
    "WeeklyReviewResult",
    "WeeklyReviewWindow",
    "build_weekly_review",
    "calculate_weekly_review_window",
})


def test_public_api_snapshot() -> None:
    """``__all__`` 快照锁。

    新增 public symbol 必须显式更新本测试，强制 PR 评审决定"是否真的
    应该塞进 review_service"。如果有更合适的归属（如新 reviewer 子
    模块），优先抽出去。
    """
    from mindforge import review_service  # 延迟 import，确保 src/ 已 path 化

    actual = frozenset(getattr(review_service, "__all__", ()))
    assert actual == EXPECTED_PUBLIC_API, (
        f"review_service.__all__ 快照不匹配。\n"
        f"  新增（请评审）: {sorted(actual - EXPECTED_PUBLIC_API)}\n"
        f"  缺失（请检查）: {sorted(EXPECTED_PUBLIC_API - actual)}"
    )


def test_function_count_cap() -> None:
    """顶层函数数量上限。

    当前 5 个：2 个 public（``calculate_weekly_review_window`` /
    ``build_weekly_review``）+ 3 个 private 助手（``_suggest_focus_tracks``
    / ``_build_empty_state`` / ``_align_tz``）。上限 6（+1 缓冲）。
    超过即 fail，提示"weekly review 之外是否真的应该塞进 review_service？
    还是该新建 review_xxx 子模块？"。
    """
    funcs = [n for n in TREE.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) <= 6, (
        f"review_service 顶层函数数量 ({len(funcs)}) 超过上限 6。"
        f" 请评估是否应该抽 sub-module，而不是继续往 review_service 堆。\n"
        f" 当前函数: {[f.name for f in funcs]}"
    )


def test_dataclass_count_cap() -> None:
    """顶层 dataclass 数量上限。

    当前 5 个 frozen dataclass。上限 6（+1 缓冲）。
    """
    dataclasses_count = 0
    names: list[str] = []
    for node in TREE.body:
        if isinstance(node, ast.ClassDef):
            for deco in node.decorator_list:
                # @dataclass 或 @dataclass(...)
                if (
                    (isinstance(deco, ast.Name) and deco.id == "dataclass")
                    or (
                        isinstance(deco, ast.Call)
                        and isinstance(deco.func, ast.Name)
                        and deco.func.id == "dataclass"
                    )
                ):
                    dataclasses_count += 1
                    names.append(node.name)
                    break
    assert dataclasses_count <= 6, (
        f"review_service dataclass 数量 ({dataclasses_count}) 超过上限 6。"
        f" 请评估是否应该抽独立 result/value-object 模块。\n"
        f" 当前 dataclass: {names}"
    )
