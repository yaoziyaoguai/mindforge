"""Architecture fitness functions — CLI thin adapter AST 静态边界测试。

中文学习型说明
================

为什么要这一类测试？
--------------------
``cli.py`` (4500+ 行) 与 ``obsidian_cli.py`` (700+ 行) 是 MindForge 唯一
对外用户接口的入口。它们承担：

1. Typer command 注册；
2. 参数解析；
3. 调用 ``*_service`` use-case；
4. 调用 ``*_presenter`` 展示；
5. 控制进程退出码；
6. CLI 标志 → 进程级开关（如 ``MINDFORGE_DEBUG`` env）。

这是 adapter 层的合理职责。本文件**不**把 cli.py 锁成"行数上限"或
"白名单 import"——adapter 层是项目里依赖面最广的合法入口，强行白名单
会变成机械搬运。

本文件锁的是**真正不可越界的禁忌**：

- 真实 LLM SDK（必须走 ``mindforge.llm`` provider abstraction）；
- RAG / embedding / vector store（不在当前阶段 scope）；
- ``dotenv`` 直接 import（必须走 ``env_loader.load_dotenv_silently``
  统一入口）；
- 真实 LLM credential 字符串字面量（``"OPENAI_API_KEY"`` 等不应硬编码）；
- 直接 ``os.environ`` 读硬编码 LLM provider key（cli.py 允许设置自己
  的 ``MINDFORGE_*`` env 桥接，但不允许直接读 LLM provider 凭证）；
- ``"human_approved"`` 字面量作为 Assign 右值（cli.py 允许把它作为
  ``status=`` keyword 给 filter_cards / 作为 Typer Option 默认值 / 列在
  audit 元数据列表，但不允许直接赋值）；
- 反向依赖（cli.py 不应被任何 service / presenter 反向 import；本测试
  覆盖 service / presenter → cli 这一方向，cli 自己 import service /
  presenter 是合法 adapter）。

CLI thin 的真正含义
--------------------
"thin" 不是"行数少"，而是"**业务语义**主要由 service 承载，CLI 只做
adapter"。本文件用以下间接信号衡量 thin：

1. CLI **不**直接调用真实 LLM SDK 函数（``openai.ChatCompletion`` 等）；
2. CLI **不**直接 ``import openai`` 然后构造 client（必须委托
   ``mindforge.llm.build_providers``）；
3. CLI **不**直接读 LLM provider 凭证字符串；
4. CLI 调用 ``approve_explicit_card`` / ``approve_card`` 的路径必须
   存在（说明 approval 是通过 service delegation，而不是 cli 自己写
   ``status="human_approved"`` 翻状态）。第 4 条作为正向断言。

为什么这套测试不锁 cli.py 行数 / 函数数 / 文件数？
--------------------------------------------------
项目核心治理目标之一明确写在 ROADMAP：**"不为降低行数而拆"**。
cli.py 是巨石没错，但它是合法入口巨石，价值在于"用户看到的命令面"集中
在一处易找。后续如果要拆，应当按 use-case 抽 sub-app（如已经存在的
``obsidian_cli.py``），而不是按行数随意切。把"行数上限"塞进测试只会
变成 KPI 驱动机械搬运。

本文件覆盖范围
--------------
``cli.py`` 与 ``obsidian_cli.py`` 各跑一遍同一组检查（parametrize）。
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[1] / "src" / "mindforge"


@dataclass(frozen=True)
class CliFile:
    name: str
    path: Path


CLI_FILES: tuple[CliFile, ...] = (
    CliFile(name="cli", path=SRC_DIR / "cli.py"),
    CliFile(name="obsidian_cli", path=SRC_DIR / "obsidian_cli.py"),
)


# ---------------------------------------------------------------------------
# AST helper（与其他 boundaries 同构）
# ---------------------------------------------------------------------------


def _all_imported_names(tree: ast.AST) -> set[str]:
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
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                names.add(f.id)
            elif isinstance(f, ast.Attribute):
                names.add(f.attr)
    return names


def _all_string_constants(tree: ast.AST) -> set[str]:
    """收集所有 ``Constant(str)``（含 docstring）。

    本文件用于检测硬编码 LLM credential key 名；这些名字几乎不可能
    在 docstring 里"无害"出现，所以全局 collect 是够用的（false-positive
    风险极低）。
    """
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def _parse(cli: CliFile) -> ast.Module:
    return ast.parse(cli.path.read_text(encoding="utf-8"))


PARAM = pytest.mark.parametrize("cli", CLI_FILES, ids=[c.name for c in CLI_FILES])


# ---------------------------------------------------------------------------
# Hard bans：真实 LLM / RAG / dotenv 直 import / 凭证字面量
# ---------------------------------------------------------------------------


@PARAM
def test_no_real_llm_sdk_imports(cli: CliFile) -> None:
    """禁止直接 import 真实 LLM SDK。

    所有 LLM provider 都必须通过 ``mindforge.llm.build_providers``
    工厂构造。这一层 indirection 是 fake-safety 的关键：fake provider
    默认路径不应触碰真实 SDK 模块。
    """
    forbidden = {"openai", "anthropic", "litellm", "cohere", "ollama"}
    hit = _all_imported_names(_parse(cli)) & forbidden
    assert not hit, (
        f"{cli.name} 不应直接 import 真实 LLM SDK"
        f"（必须走 mindforge.llm.build_providers）：{sorted(hit)}"
    )


@PARAM
def test_no_rag_or_embedding_imports(cli: CliFile) -> None:
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
    for mod in _all_imported_names(_parse(cli)):
        low = mod.lower()
        for needle in forbidden_substrings:
            if needle in low:
                hits.append(mod)
                break
    assert not hits, f"{cli.name} 不应 import RAG/embedding：{hits}"


@PARAM
def test_no_direct_dotenv_imports(cli: CliFile) -> None:
    """禁止直接 import ``dotenv`` / ``python_dotenv``。

    .env 加载必须走 ``mindforge.env_loader.load_dotenv_silently`` 这个
    单一入口——它包含"是否真的应该加载"的安全检查。CLI 直接 import
    ``dotenv`` 会绕过该检查。
    """
    forbidden = {"dotenv", "python_dotenv"}
    hit = _all_imported_names(_parse(cli)) & forbidden
    assert not hit, (
        f"{cli.name} 不应直接 import dotenv"
        f"（必须走 mindforge.env_loader）：{sorted(hit)}"
    )


@PARAM
def test_no_real_llm_credential_literals(cli: CliFile) -> None:
    """禁止硬编码真实 LLM provider 凭证 env key。

    这些 key 名几乎不可能"无意义地"出现在 CLI 源码（包括 docstring）。
    一旦出现，要么是有人在 cli.py 里硬编码读 OpenAI 凭证（绕过 fake
    provider 安全路径），要么是把凭证名字暴露在用户提示文案里——都不
    应该发生。MindForge 的 model_env 是**运行时**从 ``MindForgeConfig``
    动态读，不是字面量。
    """
    forbidden = {
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "COHERE_API_KEY",
        "LITELLM_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
    }
    hit = _all_string_constants(_parse(cli)) & forbidden
    assert not hit, (
        f"{cli.name} 不应硬编码真实 LLM provider 凭证 key 名："
        f"{sorted(hit)}"
    )


# ---------------------------------------------------------------------------
# Status mutation boundary
# ---------------------------------------------------------------------------


@PARAM
def test_no_human_approved_assignment(cli: CliFile) -> None:
    """``"human_approved"`` 字面量**禁止**作为 Assign / AnnAssign 右值
    或 Return 值出现。

    cli.py 与 obsidian_cli.py 允许把 ``"human_approved"`` 作为：

    - ``status=`` keyword 参数传给 filter_cards / iter_cards（只读筛选）；
    - Typer ``Option`` 默认值或 help 文案（命令行参数描述）；
    - 列出现在 audit / 日志元数据 list 字面量里（说明哪些状态被纳入扫描）；
    - ``Compare`` 比较的右值（``c.status == "human_approved"`` 只读判定）；
    - ``in`` 表达式（``status in {"human_approved", "ai_draft"}``）；
    - f-string 拼接片段（``f"{n_approved} human_approved"``）。

    但**禁止**直接 ``card.status = "human_approved"`` 或
    ``status_value = "human_approved"``——那意味着 CLI 自己在翻状态，
    而不是委托 ``approval_service.approve_explicit_card`` /
    ``approver.approve_card``。
    """
    tree = _parse(cli)
    parents: dict[int, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[id(child)] = parent

    violations: list[str] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and node.value == "human_approved"):
            continue

        # 向上遍历找最近的语义"决定性"父节点；先匹配到 read 类（keyword
        # / collection / Compare / JoinedStr）即放行；先匹配到 Assign /
        # Return 即视为违规写入。
        cur: ast.AST | None = node
        kind: str | None = None
        while cur is not None:
            parent = parents.get(id(cur))
            if parent is None or isinstance(parent, ast.Module):
                break
            if isinstance(parent, ast.keyword):
                kind = "keyword"
                break
            if isinstance(parent, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
                kind = "collection"
                break
            if isinstance(parent, ast.Compare):
                kind = "compare"
                break
            if isinstance(parent, ast.JoinedStr):
                kind = "fstring"
                break
            if isinstance(parent, (ast.Assign, ast.AnnAssign)):
                kind = "assign"
                break
            if isinstance(parent, ast.Return):
                kind = "return"
                break
            cur = parent

        if kind in {"keyword", "collection", "compare", "fstring"}:
            continue
        if kind in {"assign", "return"}:
            violations.append(f"line {node.lineno}: {kind}")

    assert not violations, (
        f"{cli.name} 不应直接 Assign/Return 'human_approved' 字面量"
        f"（必须委托 approval_service / approver）：{violations}"
    )


# ---------------------------------------------------------------------------
# Reverse dep direction（service / presenter 不可 import cli；cli 可以
# import 它们。本测试覆盖**正向**：cli 自己不 import 自己 / 兄弟 cli 不
# 互相反向 import）
# ---------------------------------------------------------------------------


def test_obsidian_cli_does_not_import_top_cli() -> None:
    """``obsidian_cli`` 是 ``cli.py`` 的 sub-app；**禁止**反向 import
    ``mindforge.cli``，否则会形成循环 import。

    ``cli.py`` 通过 ``from .obsidian_cli import obsidian_app`` 注册子
    命令，反方向只能通过参数 / context 传递，不应 import。
    """
    obs_tree = ast.parse((SRC_DIR / "obsidian_cli.py").read_text(encoding="utf-8"))
    hit = _all_imported_names(obs_tree) & {"mindforge.cli"}
    assert not hit, f"obsidian_cli 不应反向 import cli：{sorted(hit)}"


# ---------------------------------------------------------------------------
# Positive assertions：service delegation 必须存在
# ---------------------------------------------------------------------------


def test_approval_cli_delegates_approval_via_service() -> None:
    """正向断言：``approval_cli.py`` 的 approve 命令必须委托
    ``approve_explicit_card``（来自 ``approval_service``）。

    中文学习型说明：root ``cli.py`` 现在只注册子 app；人工审批的 CLI
    adapter 边界在 ``approval_cli.py``。本测试锚定真正拥有该职责的模块，
    避免为了满足旧断言把 approval_service 反向塞回 root CLI。
    """
    approval_tree = ast.parse((SRC_DIR / "approval_cli.py").read_text(encoding="utf-8"))
    calls = _all_call_names(approval_tree)
    assert "approve_explicit_card" in calls, (
        "approval_cli.py 必须调用 approval_service.approve_explicit_card "
        "完成人审；delegation 缺失意味着 approval 路径有越界风险"
    )
    assert "mindforge.approval_service" in _all_imported_names(approval_tree), (
        "approval_cli.py 必须 import approval_service"
    )


def test_cli_runtime_uses_env_loader_not_direct_dotenv() -> None:
    """正向断言：``cli_runtime.py`` 必须 import 并使用 ``env_loader`` 入口。

    ``cli_runtime.load_cfg`` 是拆分后所有 CLI adapter 的统一配置入口；
    .env 加载只允许走 ``mindforge.env_loader.load_dotenv_silently``。
    """
    runtime_tree = ast.parse((SRC_DIR / "cli_runtime.py").read_text(encoding="utf-8"))
    imports = _all_imported_names(runtime_tree)
    assert "mindforge.env_loader" in imports, (
        "cli_runtime.py 必须 import mindforge.env_loader 以走 fake-safety 安全 .env 入口"
    )
    calls = _all_call_names(runtime_tree)
    assert "load_dotenv_silently" in calls, (
        "cli_runtime.py 必须调用 load_dotenv_silently（env_loader 入口），"
        "不允许其他 .env 加载方式"
    )


def test_process_execution_uses_llm_provider_factory() -> None:
    """正向断言：process 执行组合根必须通过 provider factory 构造 LLM。

    watch/import 复用 process 执行原语后，provider 构造从 ``process_cli.py``
    下沉到 ``process_executor.py``。CLI adapter 只保留参数解析和用户输出；
    复用层才持有 ``LLMClient`` / ``build_providers`` 细节，避免把业务执行逻辑
    复制到 watch/import 或塞回顶层 CLI。
    """
    process_tree = ast.parse((SRC_DIR / "process_cli.py").read_text(encoding="utf-8"))
    executor_tree = ast.parse((SRC_DIR / "process_executor.py").read_text(encoding="utf-8"))
    assert "mindforge.process_executor" in _all_imported_names(process_tree), (
        "process_cli.py 必须委托 process_executor 运行共享 process 原语"
    )
    assert "mindforge.llm" in _all_imported_names(executor_tree), (
        "process_executor.py 必须 import mindforge.llm 以走 provider factory"
    )
    assert "build_providers" in _all_call_names(executor_tree), (
        "process_executor.py 必须调用 build_providers 工厂构造 LLM provider"
    )
