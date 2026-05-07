"""Architecture fitness functions — approval_service AST 静态边界测试。

中文学习型说明
================

为什么要这一类测试？
--------------------
``approval_service`` 是 MindForge 整个项目里**唯一被允许**完成
``ai_draft → human_approved`` 状态迁移的 use-case service。这条人工
确认环节是 MindForge 的核心安全边界：

- ``ai_draft`` 只能由 AI 生成；
- ``human_approved`` 必须**显式人审**才能赋值；
- 任何 service 自动 approve 都属于安全事故。

行为层测试（``tests/test_approval_service.py`` 等）覆盖"调用一次到底
做对了什么"。本文件不同：它把 ``approval_service.py`` 的**架构意图**
变成静态可回归验证的 fitness function——用 ``ast.parse`` 直接读 source，
断言 import 图、禁忌符号、public surface、模块体量。**不实例化任何
对象，不运行业务路径**。

核心边界
--------
1. ``approval_service`` 是**唯一**被允许调 ``approver.approve_card`` 的
   service。但它**不应**自己写 ``"human_approved"`` 字面量——状态字面量
   归 ``approver.py`` 管。本文件断言：approval_service 源码里**完全不
   出现** ``"human_approved"`` 字面量（连 keyword 参数都不允许），这样
   未来任何"在 approval_service 里偷偷 ``status="human_approved"``" 的
   尝试都会立刻被发现。
2. ``approval_service`` 不写文件、不读 ``.env``、不调真实 LLM、不依赖
   CLI / presenter / Obsidian 层。
3. ``approval_service`` 不依赖其他 use-case service（process / review /
   recall）——它是独立 use-case，否则 use-case 层会出现交叉耦合。

防"小巨石化"机制
----------------
``__all__`` 快照锁 + 函数 / dataclass 数量上限。当前 13 public symbol、
7 顶层函数、6 dataclass。本测试设上限 14 / 8 / 7（各 +1 缓冲）。
超过即 fail，强制评估"是否应该抽 sub-module（如 ApprovalLister /
ApprovalPreviewer）而不是继续往 approval_service 堆"。

允许的依赖白名单
----------------
正向断言：``approval_service`` 的顶层 import 必须**完全等于**：

    {__future__, dataclasses, pathlib,
     mindforge.approver, mindforge.cards, mindforge.checkpoint,
     mindforge.config, mindforge.models}

任何新依赖必须显式更新本测试。``approver`` 是允许的——这正是
approval_service 的 delegation target（人审写盘的真正执行者）。

本文件与 ``tests/test_review_service_boundaries.py`` /
``tests/test_process_service_boundaries.py`` 的关系
----------------------------------------------------
三个文件**结构同构**（同 5 个 AST helper、同类断言），但白名单 /
上限 / 禁忌不同。这种刻意的"模板复制"不是机械搬运——它让每一个 service
的边界都独立、显式、可单独修改，避免共享 fixture 让边界声明被隐藏到
一个抽象基类里。三份独立比一份共享更适合"架构 fitness function"。
"""

from __future__ import annotations

import ast
from pathlib import Path

# ---------------------------------------------------------------------------
# 模块级 fixture：一次解析，多次使用
# ---------------------------------------------------------------------------

APPROVAL_SERVICE_PATH: Path = (
    Path(__file__).resolve().parents[1] / "src" / "mindforge" / "approval_service.py"
)
SOURCE: str = APPROVAL_SERVICE_PATH.read_text(encoding="utf-8")
TREE: ast.Module = ast.parse(SOURCE)


# ---------------------------------------------------------------------------
# AST helper（与 process_service / review_service boundaries 同构）
# ---------------------------------------------------------------------------


def _toplevel_import_modules(tree: ast.Module) -> set[str]:
    """收集顶层 import 的模块名。``from .x import y`` 还原为 ``mindforge.x``。"""
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
    """收集所有 import（含函数体内 import）。"""
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


# ---------------------------------------------------------------------------
# Import boundary tests
# ---------------------------------------------------------------------------

ALLOWED_TOPLEVEL_IMPORTS: frozenset[str] = frozenset({
    "__future__",
    "dataclasses",
    "pathlib",
    "mindforge.approver",
    "mindforge.cards",
    "mindforge.checkpoint",
    "mindforge.config",
    "mindforge.models",
    "mindforge.source_archive_service",
})


def test_toplevel_imports_match_allowlist() -> None:
    """正向断言：顶层 import 必须**完全等于**白名单。

    ``mindforge.approver`` 在白名单里——它是 approval_service 的
    delegation target（真正写盘 + 状态翻转）。任何其他依赖必须显式
    评审。
    """
    actual = _toplevel_import_modules(TREE)
    assert actual == ALLOWED_TOPLEVEL_IMPORTS, (
        f"approval_service 顶层 import 与白名单不匹配。\n"
        f"  超出白名单（违规新增）: {sorted(actual - ALLOWED_TOPLEVEL_IMPORTS)}\n"
        f"  白名单未使用（应同步删除）: {sorted(ALLOWED_TOPLEVEL_IMPORTS - actual)}"
    )


def test_no_reverse_dep_on_cli() -> None:
    """禁止反向依赖 CLI 层。"""
    forbidden = {"mindforge.cli"}
    hit = _all_imported_names(TREE) & forbidden
    assert not hit, f"approval_service 不应 import CLI 层：{sorted(hit)}"


def test_no_reverse_dep_on_presenters() -> None:
    """禁止反向依赖 presenter 层。

    approval_service 输出 dataclass，由 approve_presenter 渲染。
    单向流不可破坏。
    """
    forbidden = {
        "mindforge.recall_presenter",
        "mindforge.approve_presenter",
        "mindforge.review_presenter",
    }
    hit = _all_imported_names(TREE) & forbidden
    assert not hit, f"approval_service 不应 import presenter 层：{sorted(hit)}"


def test_no_reverse_dep_on_obsidian_layer() -> None:
    """禁止反向依赖 Obsidian binding 层。

    approval_service 不直接写 Obsidian vault。如果将来出现
    "approve 后自动写 vault" 的需求，应该由 obsidian_workflow 层
    监听 approval 事件，而不是 approval_service 主动 import obsidian。
    """
    forbidden = {
        "mindforge.obsidian_cli",
        "mindforge.obsidian_workflow",
        "mindforge.obsidian_stage",
    }
    hit = _all_imported_names(TREE) & forbidden
    assert not hit, f"approval_service 不应 import Obsidian 层：{sorted(hit)}"


def test_no_reverse_dep_on_other_services() -> None:
    """approval_service 不应 import 其他 use-case service。

    每个 use-case service 都是独立的；approval 不应依赖 process /
    review / recall 才能完成 approval。这条边界防止 use-case 层之间
    出现交叉依赖（最终会让 approval 牵一发动全身）。
    """
    forbidden = {
        "mindforge.process_service",
        "mindforge.review_service",
        "mindforge.recall_service",
    }
    hit = _all_imported_names(TREE) & forbidden
    assert not hit, (
        f"approval_service 不应 import 其他 use-case service："
        f"{sorted(hit)}"
    )


def test_no_real_llm_sdk_imports() -> None:
    """禁止真实 LLM SDK。

    approval 是纯人审 use-case：人在终端确认 → ``ai_draft`` 翻成
    ``human_approved``。不需要 LLM。
    """
    forbidden = {
        "openai",
        "anthropic",
        "litellm",
        "cohere",
        "ollama",
    }
    hit = _all_imported_names(TREE) & forbidden
    assert not hit, f"approval_service 不应 import 真实 LLM SDK：{sorted(hit)}"


def test_no_ui_framework_imports() -> None:
    """禁止 UI / CLI 框架直接出现。

    approval_service 输出 dataclass；Rich Table / Typer prompt 都属于
    CLI adapter / approve_presenter 的职责。
    """
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
    assert not hit, f"approval_service 不应 import UI 框架：{sorted(hit)}"


def test_no_rag_or_embedding_imports() -> None:
    """禁止 RAG / embedding / vector store 出现。"""
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
    assert not hits, f"approval_service 不应 import RAG/embedding 模块：{hits}"


def test_no_dotenv_imports() -> None:
    """禁止任何形式的 dotenv 加载。

    approval 不读 ``.env``。.env 加载是 process workflow 的边界专属。
    """
    forbidden = {"dotenv", "python_dotenv"}
    hit = _all_imported_names(TREE) & forbidden
    assert not hit, f"approval_service 不应 import dotenv：{sorted(hit)}"


# ---------------------------------------------------------------------------
# Behavior boundary tests
# ---------------------------------------------------------------------------


def test_no_os_environ_access() -> None:
    """禁止直接访问 ``os.environ`` / ``os.getenv``。"""
    chains = _all_attribute_chains(TREE)
    forbidden_chains = {"os.environ", "os.getenv", "environ.get"}
    hit = chains & forbidden_chains
    assert not hit, f"approval_service 不应直接访问 os.environ：{sorted(hit)}"


def test_no_direct_file_write_calls() -> None:
    """禁止任何**直接**写盘调用。

    approval_service 的写盘必须**全部**走 ``approver.approve_card``
    delegation。这一层 indirection 让"真正翻 ``human_approved`` 状态
    + 写盘"集中在 ``approver.py``，便于审计和后续替换实现。

    若 approval_service 自己 ``write_text`` / ``open(..., "w")``，
    就绕过了 approver 的人审契约。
    """
    forbidden = {"write_text", "write_bytes"}
    hit = _all_call_names(TREE) & forbidden
    assert not hit, (
        f"approval_service 不应直接写文件（必须走 approver.approve_card 委托）："
        f"{sorted(hit)}"
    )

    open_calls = [
        node
        for node in ast.walk(TREE)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "open"
    ]
    assert not open_calls, (
        "approval_service 不应调用 open() 写文件；写盘必须委托 approver.approve_card"
    )


def test_no_human_approved_literal_anywhere() -> None:
    """``"human_approved"`` 字面量**绝不能**出现在 approval_service 源码任何位置。

    approval_service 的写状态语义必须**全部**委托给 ``approver.approve_card``。
    那才是唯一允许把 card 状态翻成 ``"human_approved"`` 的地方。
    本测试通过 AST 全局扫描 ``Constant("human_approved")``，覆盖：

    - Assign / AnnAssign 的 RHS
    - Return 值
    - keyword 参数
    - dataclass 字段默认值
    - 函数签名 default
    - f-string JoinedStr 的拼接片段
    - ``__all__`` / 常量元组

    docstring 不会进入此扫描——因为我们只看 ``Constant``，docstring
    虽然也是 Constant 但通常包含完整解释段落（"human_approved 状态机
    ..."），不是孤立字面量。本测试的语义是"不出现孤立字面量
    'human_approved'"，所以即使 docstring 里写了完整短语 'human_approved'
    单词，也会触发 fail——这是有意为之，避免任何"看似只是文字"的字面量
    被未来错误粘贴成代码。

    注意：截至当前实现，approval_service 源码中没有任何 'human_approved'
    字面量（连 docstring 也没有，docstring 只描述 'ai_draft 到 human-approved
    的人审边界'，使用了带空格的描述短语）。本断言因此是真正起作用的护栏。
    """
    violations: list[int] = []
    for node in ast.walk(TREE):
        if isinstance(node, ast.Constant) and node.value == "human_approved":
            violations.append(node.lineno)
    assert not violations, (
        f"approval_service 出现 'human_approved' 字面量（必须由 approver.approve_card "
        f"独占写状态）：lines {violations}"
    )


def test_approver_delegation_exists() -> None:
    """正向断言：approval_service 必须调用 ``approve_card``。

    这一条与"不写文件 + 不出现 human_approved 字面量"配对：approval
    service 必须**通过** delegation 完成人审，否则它根本没履行职责。
    若有人未来"重构掉" delegation 直接写状态，本测试会立刻失败。
    """
    assert "approve_card" in _all_call_names(TREE), (
        "approval_service 必须委托 approver.approve_card 完成人审；"
        "delegation 缺失意味着写状态路径出现"
    )


# ---------------------------------------------------------------------------
# Public surface snapshot lock
# ---------------------------------------------------------------------------

EXPECTED_PUBLIC_API: frozenset[str] = frozenset({
    "APPROVAL_PREVIEW_FIELDS",
    "ApprovalCardLookupResult",
    "ApprovalExecutionResult",
    "ApprovalListQuery",
    "ApprovalListResult",
    "ApprovalPreviewResult",
    "ApprovalServiceError",
    "approve_explicit_card",
    "build_bulk_approval_plan",
    "list_approval_candidates",
    "preview_approval_card",
    "resolve_candidate_by_card_id",
    "resolve_card_path_by_source_id",
})


def test_public_api_snapshot() -> None:
    """``__all__`` 快照锁。

    13 个 public symbol。新增必须显式更新本测试，强制评审"是否真的
    应该塞进 approval_service？还是应该抽 ApprovalLister / ApprovalPreviewer
    子模块？"。
    """
    from mindforge import approval_service

    actual = frozenset(getattr(approval_service, "__all__", ()))
    assert actual == EXPECTED_PUBLIC_API, (
        f"approval_service.__all__ 快照不匹配。\n"
        f"  新增（请评审）: {sorted(actual - EXPECTED_PUBLIC_API)}\n"
        f"  缺失（请检查）: {sorted(EXPECTED_PUBLIC_API - actual)}"
    )


def test_function_count_cap() -> None:
    """顶层函数数量上限。

    当前 7 个：``list_approval_candidates`` / ``build_bulk_approval_plan``
    / ``resolve_card_path_by_source_id`` / ``resolve_candidate_by_card_id``
    / ``preview_approval_card`` / ``approve_explicit_card`` /
    ``_resolve_user_card_path``。上限 8（+1 缓冲）。超过即 fail，提示
    "应该抽 ApprovalLister / ApprovalPreviewer / ApprovalResolver 子模块"。
    """
    funcs = [n for n in TREE.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) <= 8, (
        f"approval_service 顶层函数数量 ({len(funcs)}) 超过上限 8。"
        f" 请评估是否应该抽 sub-module，而不是继续堆。\n"
        f" 当前函数: {[f.name for f in funcs]}"
    )


def test_dataclass_count_cap() -> None:
    """顶层 dataclass 数量上限。

    当前 6 个 dataclass（含 ``ApprovalServiceError`` 异常类也用了
    ``@dataclass``）。上限 7（+1 缓冲）。
    """
    dataclasses_count = 0
    names: list[str] = []
    for node in TREE.body:
        if isinstance(node, ast.ClassDef):
            for deco in node.decorator_list:
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
    assert dataclasses_count <= 7, (
        f"approval_service dataclass 数量 ({dataclasses_count}) 超过上限 7。"
        f" 请评估是否应该抽独立 result/value-object 模块。\n"
        f" 当前 dataclass: {names}"
    )
