"""Stage 6 — safe review/preview presentation family invariant.

设计意图
========

仓库里有 5 个 presenter 模块：

- ``approve_presenter.py``
- ``review_presenter.py``
- ``recall_presenter.py``
- ``cubox_dryrun_presenter.py``

它们都遵循同一组架构契约：**只做展示**。各自已有局部 boundary 测试
（``test_review_presenter.py`` 22 条、``test_approve_presenter.py`` 系列、
``test_cli_cubox_dry_run.py`` 守护 cubox presenter）。

Stage 6 在**家族级**统一断言所有 presenter 文件遵守同一组 forbidden
imports，避免未来新增 presenter 时再分别复制粘贴局部测试。

家族禁止导入：

1. CLI 框架：``typer`` / ``click``
2. 业务 service：``approver`` / ``approval_service`` / ``reviewer`` /
   ``review_service`` / ``recall_service`` / ``process_service``
3. processor / provider / pipeline：``processors`` / ``processor`` /
   ``providers`` / ``providers.factory`` / ``llm`` /
   ``llm.openai_compatible`` / ``llm.anthropic_compatible``
4. vault / writer / workspace：``vault_writer`` / ``writer`` /
   ``workspace`` / ``obsidian`` / ``obsidian_cli``
5. dotenv / env_loader：``dotenv`` / ``mindforge.env_loader``
6. 真实 LLM SDK：``openai`` / ``anthropic`` / ``httpx`` / ``requests``
7. RAG / embedding：``faiss`` / ``chromadb`` / ``sentence_transformers``
8. RunLogger：``mindforge.run_logger``

并断言 presenter 文件的源码不出现：

- ``open(`` 文件 IO 调用（presenter 是纯函数，输入是 dataclass，输出
  是字符串/JSON，不读写磁盘）
- ``approve_card(`` / ``mark_card_review(`` 业务动作调用
- 真实 ``socket.`` / ``requests.`` / ``httpx.`` 调用
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_SRC = _REPO / "src" / "mindforge"


_PRESENTER_FILES = [
    _SRC / "approve_presenter.py",
    _SRC / "review_presenter.py",
    _SRC / "recall_presenter.py",
    _SRC / "cubox_dryrun_presenter.py",
    # CLI Monolith Decomposition Pack 2 — process / init 命令的展示层
    # 已经从 cli.py 抽出。它们必须遵守家族契约：不依赖 service / processor /
    # provider / vault writer / dotenv / RunLogger / 网络。
    _SRC / "process_presenter.py",
    _SRC / "init_presenter.py",
    # Product Visibility milestone — library presenter 只展示 service 已计算的
    # inventory，不读取卡片/source 文件，不执行 approve。
    _SRC / "library_presenter.py",
    # Repo-Wide Monolith Decomposition Pack — obsidian 命令的展示层从
    # obsidian_cli.py 抽出。它必须遵守家族契约：不依赖 obsidian / obsidian_cli /
    # service / writer / RunLogger / Typer。允许使用 obsidian_stage 里的
    # 纯 path 工具 ``safe_relative_to``。
    _SRC / "obsidian_cli_presenter.py",
]


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


_FAMILY_FORBIDDEN = {
    # CLI 框架
    "typer",
    "click",
    # 业务 service
    "mindforge.approver",
    "mindforge.approval_service",
    "mindforge.reviewer",
    "mindforge.review_service",
    "mindforge.recall_service",
    "mindforge.process_service",
    # processor / pipeline / provider
    "mindforge.processors",
    "mindforge.processors.pipeline",
    "mindforge.processor",
    "mindforge.providers",
    "mindforge.providers.factory",
    "mindforge.llm",
    "mindforge.llm.client",
    "mindforge.llm.factory",
    "mindforge.llm.openai_compatible",
    "mindforge.llm.anthropic_compatible",
    # vault / writer / workspace
    "mindforge.vault_writer",
    "mindforge.writer",
    "mindforge.workspace",
    "mindforge.obsidian",
    "mindforge.obsidian_cli",
    # dotenv / env_loader
    "dotenv",
    "mindforge.env_loader",
    # real LLM SDK
    "openai",
    "anthropic",
    "httpx",
    "requests",
    # RAG / embedding
    "faiss",
    "chromadb",
    "sentence_transformers",
    # RunLogger
    "mindforge.run_logger",
}


@pytest.mark.parametrize(
    "presenter_path", _PRESENTER_FILES, ids=lambda p: p.name
)
def test_presenter_module_does_not_import_forbidden_targets(
    presenter_path: Path,
) -> None:
    assert presenter_path.exists(), f"presenter 文件缺失：{presenter_path}"
    leaked = _imports(presenter_path) & _FAMILY_FORBIDDEN
    assert not leaked, (
        f"{presenter_path.name} 不应 import：{leaked}（presenter 家族契约："
        f"只做展示，不触碰 service / processor / provider / vault / "
        f"dotenv / network / RAG / RunLogger）"
    )


_FORBIDDEN_SOURCE_PATTERNS = [
    # 文件读写
    (re.compile(r"\bopen\s*\("), "presenter 不允许直接 open() 文件"),
    (re.compile(r"\.write_text\s*\("), "presenter 不允许 .write_text()"),
    (re.compile(r"\.write_bytes\s*\("), "presenter 不允许 .write_bytes()"),
    (re.compile(r"\.read_text\s*\("), "presenter 不允许 .read_text()"),
    (re.compile(r"\.read_bytes\s*\("), "presenter 不允许 .read_bytes()"),
    # 业务动作
    (re.compile(r"\bapprove_card\s*\("), "presenter 不允许调 approve_card()"),
    (re.compile(r"\bapply_decision\s*\("), "presenter 不允许调 apply_decision()"),
    (re.compile(r"\bmark_card_review\s*\("), "presenter 不允许调 mark_card_review()"),
    # 网络 IO
    (re.compile(r"\bsocket\.socket\s*\("), "presenter 不允许直接用 socket"),
    (re.compile(r"\bhttpx\.\w+"), "presenter 不允许调 httpx"),
    (re.compile(r"\brequests\.\w+"), "presenter 不允许调 requests"),
    # env
    (re.compile(r"\bos\.environ\b"), "presenter 不允许读 os.environ"),
    (re.compile(r"\bload_dotenv\s*\("), "presenter 不允许 load_dotenv"),
]


@pytest.mark.parametrize(
    "presenter_path", _PRESENTER_FILES, ids=lambda p: p.name
)
def test_presenter_source_does_not_perform_io_or_business_actions(
    presenter_path: Path,
) -> None:
    text = presenter_path.read_text(encoding="utf-8")
    # 移除字符串字面量内的内容（例如 docstring 里出现的样例代码 / 函数名），
    # 避免误伤教学型注释。简化处理：只考虑非注释、非 docstring 的源码体。
    # 用 ast 提取所有非 docstring / 非注释的源代码 segment。
    tree = ast.parse(text)
    source_lines = text.splitlines()

    # 收集 docstring 行号区间
    docstring_line_ranges: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstring_line_ranges.append(
                    (body[0].lineno, body[0].end_lineno or body[0].lineno)
                )

    def in_docstring(lineno: int) -> bool:
        return any(s <= lineno <= e for s, e in docstring_line_ranges)

    code_only_lines: list[str] = []
    for i, line in enumerate(source_lines, start=1):
        stripped = line.split("#", 1)[0]
        if in_docstring(i):
            continue
        code_only_lines.append(stripped)
    code_only = "\n".join(code_only_lines)

    for pattern, msg in _FORBIDDEN_SOURCE_PATTERNS:
        m = pattern.search(code_only)
        assert m is None, (
            f"{presenter_path.name}: {msg}（命中：{m.group(0)!r}）"
        )


def test_all_presenter_files_are_covered_by_family_test() -> None:
    """防止漏网：仓库里所有 ``*_presenter.py`` 都必须在
    ``_PRESENTER_FILES`` 列表中（下次新增 presenter 时强制更新）。"""
    actual = sorted(p.name for p in _SRC.glob("*_presenter.py"))
    declared = sorted(p.name for p in _PRESENTER_FILES)
    assert actual == declared, (
        f"presenter 家族成员未对齐。仓库：{actual}；测试声明：{declared}。"
        f"新增 presenter 时请同时更新 _PRESENTER_FILES。"
    )
