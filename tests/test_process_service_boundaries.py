"""v0.7.23 — process_service AST 静态边界测试（架构护栏层）。

中文学习型说明
================

为什么要这一类测试？
--------------------
``tests/test_process_service.py``（v0.7.20 引入）覆盖的是 service 的
**行为契约**：``resolve_process_runtime`` 返回什么、错误码是什么、
``summarize_outcome`` 翻译三种 ``PipelineOutcome`` 的字段是否一致。
那些测试解决"代码运行时是否正确"。

本文件不同。它解决的是"代码本身写成什么样"——也就是**架构意图**：

1. ``process_service`` 是 MindForge 的 use-case service 层之一。它的
   存在前提是"业务语义和 CLI / presenter / provider / runtime 解耦"。
   一旦它悄悄 import 了 ``cli`` / ``rich`` / ``typer`` / ``openai`` /
   ``dotenv`` / ``recall_presenter`` ……，它就退化成"披着 service 名
   字的 CLI handler"。这种退化在普通行为测试里**不会失败**。
2. 因此本文件用 ``ast.parse`` 做**静态扫描**：直接读 source，看 import
   节点 / Call 节点 / Attribute 链 / Constant 字面量，**不实例化**任何
   对象、**不运行**任何业务路径。
3. 这与"普通单元测试"的根本区别：普通单元测试测"运行时行为"；本文件
   测"代码内的依赖图与禁忌符号"。两者互补。

为什么 process_service 要被这样保护？
-------------------------------------
- ``process`` 是 MindForge 唯一会触发"是否需要真实 LLM"的 use-case。
  fake provider 默认安全路径要求：在 ``active_profile == "fake"`` 时
  不读 ``.env`` / 不实例化真实 provider / 不联网。这条边界写在
  ``ProviderSelection.requires_real_env`` 里。如果 service 自己偷偷
  ``import openai`` 或 ``os.environ.get("OPENAI_API_KEY")``，整条边界
  就被打穿。AST 测试是这条边界的最后一道护栏。
- ``ai_draft`` / ``human_approved`` 是 MindForge 人工确认契约的核心：
  ``process`` 输出永远是 ``ai_draft``，**只有**用户显式 ``approve``
  才能进入 ``human_approved``。如果 service 中出现
  ``status="human_approved"`` 字面量赋值，就破坏了人工确认环节。
- 反向依赖（service → cli / presenter / obsidian_cli）会立即引入循环
  导入与边界倒置。一旦出现，未来抽其他 service 都会更困难。

这些测试如何防止 service "小巨石化"？
-------------------------------------
通过两类硬上限：

- ``__all__`` 快照锁：任何新增 public symbol 必须显式更新本测试，
  强制 PR 评审注意"是否真的应该塞进 process_service"。
- 函数 / dataclass 数量上限：当前 3 + 6；本测试设上限 4 + 7（各 +1
  缓冲）。超过即 fail，提示"先评估是否应该抽 ProcessExecutor 或拆出
  独立 sub-module，而不是在 process_service 里继续堆"。

允许的依赖白名单
----------------
正向断言：``process_service`` 的顶层 import 必须 **完全等于**：

    {__future__, dataclasses, pathlib, typing,
     mindforge.assets_runtime, mindforge.config,
     mindforge.processors.pipeline, mindforge.sources.base}

任何顶层 import 出现在白名单外都会 fail。这个机制比"逐个 ban 禁忌
模块"更强：白名单是封闭集合，新依赖必须显式获得评审。

本测试与 ``tests/test_process_service.py`` 的关系
--------------------------------------------------
本文件不重复旧测试已经覆盖的 typer / rich / dotenv / console / RunLogger
/ embedding / vector / rag 的 ban——那些是"开放 ban list"。本文件补的是：

1. 反向依赖 ban（cli / *_presenter / obsidian_*）；
2. 真实 LLM SDK ban（openai / anthropic / litellm / cohere / ollama）；
3. ``os.environ`` 直接访问 ban；
4. status mutation 函数 call ban；
5. ``human_approved`` 字面量赋值 ban；
6. ``__all__`` 快照锁与函数 / dataclass 数量上限；
7. 顶层 import 封闭白名单。
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# 模块级 fixture：一次解析，多次使用
# ---------------------------------------------------------------------------

PROCESS_SERVICE_PATH: Path = (
    Path(__file__).resolve().parents[1] / "src" / "mindforge" / "process_service.py"
)
SAFETY_POLICY_PATH: Path = (
    Path(__file__).resolve().parents[1] / "src" / "mindforge" / "safety_policy.py"
)
SOURCE: str = PROCESS_SERVICE_PATH.read_text(encoding="utf-8")
TREE: ast.Module = ast.parse(SOURCE)


# ---------------------------------------------------------------------------
# AST helper：所有断言都基于这些 helper，不做行级 grep
# ---------------------------------------------------------------------------


def _toplevel_import_modules(tree: ast.Module) -> set[str]:
    """收集顶层 import 的模块名。

    覆盖 ``import x`` 与 ``from x import y`` 两种形式。返回 ``x`` 的
    顶层段（``mindforge.config`` 也保留完整名，便于白名单匹配）。
    """
    mods: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            # 把相对 import ``from .x import y`` 还原成 ``mindforge.x``
            # 因为本文件位于 src/mindforge/process_service.py。
            if node.level == 1 and mod:
                mods.add(f"mindforge.{mod}")
            elif node.level == 0:
                mods.add(mod)
    return mods


def _all_imported_names(tree: ast.AST) -> set[str]:
    """收集所有 import 出现的模块名（含函数体内 import），用于反向
    依赖检查；函数体 import 在 process_service 里目前不存在，但保留
    完整覆盖避免规避。
    """
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
    """收集所有 ``Call`` 节点的目标符号（``func.id`` 或最后的 ``func.attr``）。

    用途：检查禁止调用的函数（如 ``approve_card``）。
    """
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
    """把 ``a.b.c`` 形式的 Attribute 链还原成 ``"a.b.c"`` 字符串集合。

    用途：检查 ``os.environ`` / ``Path.write_text`` 等链式访问。
    """
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
    """收集出现在 ``Assign``/``AnnAssign``/``Return`` 右侧或 ``keyword``
    参数 value 中的字符串字面量。

    docstring 里的字符串不会进入此集合——docstring 是模块/函数 body 的
    第一条 ``Expr(Constant(str))``，本函数只看赋值/返回/keyword，不看
    裸 Expr。
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
# 这是封闭集合，比"开放 ban list"强。
ALLOWED_TOPLEVEL_IMPORTS: frozenset[str] = frozenset({
    "__future__",
    "dataclasses",
    "pathlib",
    "typing",
    "mindforge.assets_runtime",
    "mindforge.config",
    "mindforge.processors.pipeline",
    "mindforge.sources.base",
})


def test_toplevel_imports_match_allowlist() -> None:
    """正向断言：顶层 import 必须**完全等于**白名单。

    任何新依赖必须显式更新此测试，强制 code review 注意"是否真的应该
    扩大 process_service 的依赖面"。
    """
    actual = _toplevel_import_modules(TREE)
    assert actual == ALLOWED_TOPLEVEL_IMPORTS, (
        f"process_service 顶层 import 与白名单不匹配。\n"
        f"  超出白名单（违规新增）: {sorted(actual - ALLOWED_TOPLEVEL_IMPORTS)}\n"
        f"  白名单未使用（应同步删除）: {sorted(ALLOWED_TOPLEVEL_IMPORTS - actual)}"
    )


def test_no_reverse_dep_on_cli() -> None:
    """禁止反向依赖 CLI 层。

    ``process_service`` 是被 CLI 调用的下层；如果它反过来 import cli，
    就形成边界倒置 + 循环导入风险。
    """
    forbidden = {"mindforge.cli"}
    hit = _all_imported_names(TREE) & forbidden
    assert not hit, f"process_service 不应 import CLI 层：{sorted(hit)}"


def test_no_reverse_dep_on_presenters() -> None:
    """禁止反向依赖 presenter 层。

    presenter 消费 service 的输出；service 反向依赖 presenter 会让
    "service 输出 dataclass，presenter 渲染" 这条单向流被破坏。
    """
    forbidden = {
        "mindforge.recall_presenter",
        "mindforge.approve_presenter",
        "mindforge.review_presenter",
    }
    hit = _all_imported_names(TREE) & forbidden
    assert not hit, f"process_service 不应 import presenter 层：{sorted(hit)}"


def test_no_reverse_dep_on_obsidian_layer() -> None:
    """禁止反向依赖 Obsidian binding 层。

    Obsidian 写入路径与"是否写正式 vault notes"边界由 obsidian_workflow
    管理。process_service 不写文件、不接触 Obsidian vault。
    """
    forbidden = {
        "mindforge.obsidian_cli",
        "mindforge.obsidian_workflow",
        "mindforge.obsidian_stage",
    }
    hit = _all_imported_names(TREE) & forbidden
    assert not hit, (
        f"process_service 不应 import Obsidian binding 层：{sorted(hit)}"
    )


def test_no_real_llm_sdk_imports() -> None:
    """禁止真实 LLM SDK 直接 import。

    fake provider 默认安全路径要求 service 自身不知道任何具体 provider
    SDK；provider 装配是 CLI 端 LLMClient 的职责。
    """
    forbidden = {"openai", "anthropic", "litellm", "cohere", "ollama"}
    imported = _all_imported_names(TREE)
    hit = {m for m in imported if m.split(".")[0] in forbidden}
    assert not hit, f"process_service 不应 import 真实 LLM SDK：{sorted(hit)}"


def test_no_ui_framework_imports() -> None:
    """禁止任何 UI 框架直接 import。

    包括 ``click`` / ``textual`` 等可能未来被引入但同样越界的 UI 库。
    （``typer`` / ``rich`` 已被 ``test_process_service.py`` 覆盖；
    本测试加 ``click`` / ``textual`` / ``prompt_toolkit`` 强化。）
    """
    forbidden = {"click", "textual", "prompt_toolkit", "blessed", "urwid"}
    imported = _all_imported_names(TREE)
    hit = {m for m in imported if m.split(".")[0] in forbidden}
    assert not hit, f"process_service 不应 import UI 框架：{sorted(hit)}"


def test_no_rag_or_embedding_imports() -> None:
    """禁止 RAG / embedding / vector store 相关 import。

    MindForge 当前 roadmap 明确不做 RAG / embedding；service 层不能
    悄悄引入这条路径。
    """
    forbidden_substrings = ("embedding", "vector", "faiss", "chromadb", "qdrant")
    imported = _all_imported_names(TREE)
    hit = {
        m for m in imported
        if any(s in m.lower() for s in forbidden_substrings)
    }
    assert not hit, f"process_service 不应 import RAG/embedding：{sorted(hit)}"


# ---------------------------------------------------------------------------
# Forbidden call / attribute boundary tests
# ---------------------------------------------------------------------------


def test_no_os_environ_access() -> None:
    """禁止任何形式的 ``os.environ`` / ``os.getenv`` 访问。

    fake provider 默认安全路径要求 service 不读真实 .env。``dotenv``
    已被旧测试覆盖；本测试覆盖直接 stdlib 路径，避免规避。
    """
    chains = _all_attribute_chains(TREE)
    bad_chains = {
        c for c in chains
        if c.startswith("os.environ") or c == "os.getenv" or c.startswith("os.environ.")
    }
    calls = _all_call_names(TREE)
    bad_calls = calls & {"getenv"}
    assert not bad_chains, f"禁止 os.environ 访问，发现：{sorted(bad_chains)}"
    assert not bad_calls, f"禁止 getenv 调用，发现：{sorted(bad_calls)}"


def test_no_status_mutation_calls() -> None:
    """禁止调用任何会改变 card status 的函数。

    ai_draft / human_approved 边界要求只有显式 approve 才能改 status；
    process_service 永远只产 ai_draft，不能调 approve_card / mark_*。
    """
    forbidden = {
        "approve_card",
        "approve_explicit_card",
        "mark_review_outcome",
        "mark_card_status",
    }
    hit = _all_call_names(TREE) & forbidden
    assert not hit, (
        f"process_service 不应调用 status mutation 函数：{sorted(hit)}"
    )


def test_no_file_write_calls() -> None:
    """禁止任何形式的文件写入。

    service 是纯计算 + 错误码翻译；写盘由 CLI 端 CardWriter / RunLogger
    负责。``read_text`` 仍允许（``_resolve_assets`` 在用户显式传 tracks
    时读 user-known path），但 ``write_text`` / 写模式 ``open`` 必须 ban。
    """
    chains = _all_attribute_chains(TREE)
    bad_chains = {c for c in chains if c.endswith(".write_text") or c.endswith(".write_bytes")}
    assert not bad_chains, f"禁止 write_text/write_bytes：{sorted(bad_chains)}"
    # 检查 open(...) 调用 —— 当前不应出现任何 open 调用
    for node in ast.walk(TREE):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "open", (
                "process_service 不应直接调用 open()；写盘由 CLI 端负责"
            )


def test_no_human_approved_literal_assignment() -> None:
    """禁止 ``human_approved`` 字符串字面量出现在赋值 / 返回 / keyword。

    docstring 里写 "human_approved" 是合法的（用于解释边界）；本测试
    专门检查赋值/返回/构造 dict 时的字面量，避免漏。
    """
    consts = _string_constants_assigned_or_returned(TREE)
    assert "human_approved" not in consts, (
        "process_service 不能直接产 human_approved；"
        "ai_draft → human_approved 必须经过用户显式 approve。"
    )


# ---------------------------------------------------------------------------
# Interface lock boundary tests
# ---------------------------------------------------------------------------

# v0.7.20 抽出后冻结的 public 接口快照。
# 任何新增 public symbol 必须显式更新此快照，强制 code review。
EXPECTED_PUBLIC_API: frozenset[str] = frozenset({
    "FAKE_PROFILE",
    "ProcessAssets",
    "ProcessError",
    "ProcessItemResult",
    "ProcessRequest",
    "ProcessRuntime",
    "ProviderSelection",
    "PROCESS_ERROR_MALFORMED_INPUT",
    "PROCESS_ERROR_MISSING_SOURCE",
    "PROCESS_ERROR_UNSUPPORTED_PROVIDER",
    "resolve_process_runtime",
    "summarize_outcome",
})


def test_public_api_snapshot() -> None:
    """``__all__`` 快照锁：防止悄悄扩张 public 接口。

    任何新增 public symbol 都必须显式更新本测试。这迫使 code review
    思考"这个 symbol 真的应该是 process_service 的 public API 吗？"
    """
    from mindforge import process_service as svc
    actual = frozenset(svc.__all__)
    assert actual == EXPECTED_PUBLIC_API, (
        f"process_service.__all__ 与快照不匹配。\n"
        f"  新增（需评审）: {sorted(actual - EXPECTED_PUBLIC_API)}\n"
        f"  删除（需评审）: {sorted(EXPECTED_PUBLIC_API - actual)}"
    )


def test_function_count_cap() -> None:
    """函数数量上限：防止悄悄塞业务函数 → service 小巨石化。

    当前 3 个：``resolve_process_runtime`` / ``_resolve_assets`` /
    ``summarize_outcome``。上限 4（+1 缓冲）。超过即 fail，提示"先
    评估是否应该抽 ProcessExecutor 或独立 sub-module"。
    """
    funcs = [
        n for n in TREE.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert len(funcs) <= 4, (
        f"process_service 顶层函数数量超过上限 4（当前 {len(funcs)}：{[f.name for f in funcs]}）。"
        " 考虑是否应该抽 ProcessExecutor 或独立 sub-module，"
        "而不是继续在 process_service 里堆函数。"
    )


def test_dataclass_count_cap() -> None:
    """dataclass 数量上限：防止悄悄塞 result 类型 → 接口蔓延。

    当前 6 个 frozen dataclass。上限 7（+1 缓冲）。超过即 fail。
    """
    classes = [n for n in TREE.body if isinstance(n, ast.ClassDef)]
    assert len(classes) <= 7, (
        f"process_service 顶层 class 数量超过上限 7（当前 {len(classes)}：{[c.name for c in classes]}）。"
        " 考虑是否应该把 result 类型移到独立模块。"
    )


# ---------------------------------------------------------------------------
# Policy alignment boundary
# ---------------------------------------------------------------------------


def test_safety_policy_declares_relevant_boundaries() -> None:
    """断言 ``safety_policy`` 模块声明了与 process_service 相关的边界。

    本测试不强制 process_service 直接 import safety_policy（当前不
    需要），但要求 safety_policy 至少声明 ``fake_provider_default`` /
    ``no_real_llm`` / ``no_env_read`` 三条边界，这样 process_service
    的边界与全局 policy 是对齐的。
    """
    pytest.importorskip("mindforge.safety_policy")
    from mindforge import safety_policy as sp
    assert hasattr(sp, "boundary_statement"), (
        "safety_policy 应提供 boundary_statement(...) 函数"
    )
    for boundary in ("fake_provider_default", "no_real_llm", "no_env_read"):
        try:
            text = sp.boundary_statement(boundary)
        except Exception as e:
            pytest.fail(f"boundary_statement({boundary!r}) 不可调用：{e}")
        assert isinstance(text, str) and text, (
            f"boundary_statement({boundary!r}) 应返回非空字符串"
        )
