"""Roadmap completion forbidden-implementation guard.

把 canonical roadmap / completion ledger 里的 future gates 固化为仓库级
源码扫描断言。

设计原则:
- 只扫 ``src/mindforge/`` 真实源码 (不扫 docs / tests, 那里允许出现
  描述性反例字面量);
- 反例匹配必须**精准**, 避免误伤合法用法 (``importlib.resources`` 是
  合法的 packaged asset 读取; ``subprocess`` 在 ``cli.doctor`` 里只
  用于固定 argv 的 ``git status`` safety 报告; 这些必须 allowlist);
- 扫描器本身不依赖任何外部工具 (只读 ``Path.read_text``)。

如果未来某个 gate 被 human authorizer 正式打开，必须同步更新
``docs/ROADMAP.md``、``docs/ROADMAP_COMPLETION_LEDGER.md`` 和本测试中的
显式 allowlist；靠删测试通过 gate 本身是 P0 违规。
"""

from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "mindforge"


def _all_source_files() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ---------- G1: real Cubox HTTP ingestion ----------

def test_no_real_cubox_http_ingestion():
    """G1 未开放: cubox 相关源码不得 import 任何 HTTP client。

    判据: 仅存在配置/凭证 skeleton (host 字面量) 是允许的; 真正
    fetch 行为要求 import ``httpx`` / ``requests`` / ``urllib.request``
    等, 这才是 G1 落地的真正信号。
    """
    http_client_imports = (
        "import httpx",
        "from httpx",
        "import requests",
        "from requests",
        "from urllib.request",
        "import urllib.request",
        "from http.client",
    )
    for f in _all_source_files():
        if "cubox" not in f.name:
            continue
        text = _read(f)
        for imp in http_client_imports:
            assert imp not in text, (
                f"{f.name}: imports HTTP client {imp!r}; "
                f"G1 (real Cubox ingestion) still future-gated"
            )


# ---------- G2: real Obsidian formal-note write ----------

def test_no_real_obsidian_formal_write():
    """G2 未开放: 源码不得直接对真实 Obsidian vault 做 formal-note
    写入。
    判据: 没有任何源码持有 ``--commit-write`` 行为 (该 flag 尚未实
    现); 也不允许出现 ``write_obsidian_note`` / ``commit_write_card``
    等 production-level 写函数名。
    """
    forbidden_names = (
        "commit_write_card(",
        "write_obsidian_note(",
        "write_formal_note(",
    )
    for f in _all_source_files():
        text = _read(f)
        for name in forbidden_names:
            assert name not in text, (
                f"{f.name}: defines forbidden formal-write helper {name!r}; "
                f"G2 still future-gated"
            )


# ---------- G3: human_approved auto-promotion ----------

# 已被 tests/test_review_approval_boundary.py 兜底; 这里只补一条
# repo-wide assertion: 不允许出现 ``human_approved = True`` 字面赋值
# (允许在 docstring / 测试 negatives 中出现)。
def test_no_runtime_human_approved_true_assignment():
    """G3 不变量: 不允许任何源码出现 ``human_approved = True`` 的
    runtime 赋值; 唯一晋升路径必须是 ``approver.approve_card``。
    """
    # 模式: human_approved 后跟 = 后跟 True, 但排除字符串 / 注释。
    pat = re.compile(r"^\s*human_approved\s*=\s*True\b", re.MULTILINE)
    for f in _all_source_files():
        text = _read(f)
        # 允许 docstring / 注释中描述这一禁令
        # 简单近似: 把三引号字符串与单行 # 注释剥掉再扫
        stripped = re.sub(r'""".*?"""', "", text, flags=re.DOTALL)
        stripped = re.sub(r"'''.*?'''", "", stripped, flags=re.DOTALL)
        stripped = re.sub(r"#.*", "", stripped)
        assert not pat.search(stripped), (
            f"{f.name}: contains runtime ``human_approved = True`` "
            f"assignment; only approver.approve_card may promote"
        )


# ---------- G4: custom executable strategy runtime ----------

# Custom strategy 当前只接受声明式 (StrategyDefinition); 不允许出现
# ``subprocess.run(<user-controlled>)`` / ``importlib.import_module(
# <user-input>)`` 模式。doctor 里固定 argv 的 ``git status`` 检测是
# allowlisted。

_SUBPROCESS_ALLOWLIST = {
    # cli.doctor 用 subprocess 调用固定 argv ['git','status',...]
    # 做 .gitignore safety 报告; 不接受用户输入。
    "cli.py",
}


def test_no_user_input_subprocess_in_strategy_layer():
    """G4 不变量: strategy / loader / registry 层不得 import 或
    调用 ``subprocess``。"""
    strategy_layer_hints = ("strategy", "loader", "registry", "custom")
    for f in _all_source_files():
        if not any(h in f.name for h in strategy_layer_hints):
            continue
        text = _read(f)
        # 允许 docstring 提及 subprocess (描述禁令), 但不允许 import
        assert "import subprocess" not in text, (
            f"{f.name}: imports subprocess in strategy layer; G4 forbids "
            f"executable strategy runtime"
        )


def test_no_dynamic_import_module_of_user_input():
    """G4 不变量: 不允许 ``importlib.import_module(<variable>)``
    模式 (会变成 arbitrary plugin runtime)。``importlib.resources``
    与 ``importlib.util.find_spec`` 是合法的 packaged asset / 可选依
    赖检测, 不在禁令内。
    """
    pat = re.compile(r"importlib\.import_module\s*\(")
    for f in _all_source_files():
        text = _read(f)
        assert not pat.search(text), (
            f"{f.name}: uses importlib.import_module(...); G4 forbids "
            f"arbitrary plugin runtime"
        )


# ---------- G5: RAG / embedding / semantic merge ----------

def test_no_rag_embedding_semantic_merge_implementation():
    """G5 未开放: 不允许真正的 RAG / embedding / semantic merge
    实现入口。允许 docstring / 测试反例中描述这些禁令。
    """
    forbidden_impl_names = (
        "def embed_text(",
        "def build_vector_index(",
        "def semantic_merge(",
        "def rag_retrieve(",
    )
    for f in _all_source_files():
        text = _read(f)
        for name in forbidden_impl_names:
            assert name not in text, (
                f"{f.name}: defines {name!r}; G5 still future-gated"
            )


# ---------- G6: release / git tag automation ----------

def test_no_automated_git_tag_or_release_in_source():
    """G6 release-gated: 源码不得包含 ``git tag`` / ``git push --tags``
    / ``git push --force`` 的自动化命令。
    """
    forbidden_substrings = (
        '"tag"',  # ['git','tag', ...] argv pattern
        "'tag'",
        "--tags",
        "--force",
    )
    # 仅扫描 cli/ 与 release/ 相关的文件; 其他模块不应碰 git 命令。
    for f in _all_source_files():
        text = _read(f)
        if "subprocess" not in text and "git " not in text:
            continue
        # 允许 docstring 描述 (如 cli.doctor 注释提到 git 命令)
        if "git tag" in text or "git push --tags" in text or "git push --force" in text:
            # 必须是文档 / 注释而非实际命令; 简化判断: 整份文件中
            # 不允许 'git tag' / 'git push --tags' 出现在非 docstring /
            # 非注释行 (比如 subprocess.run([..., 'tag', ...]))。
            stripped = re.sub(r'""".*?"""', "", text, flags=re.DOTALL)
            stripped = re.sub(r"'''.*?'''", "", stripped, flags=re.DOTALL)
            stripped = re.sub(r"#.*", "", stripped)
            for s in ("git tag", "git push --tags", "git push --force"):
                assert s not in stripped, (
                    f"{f.name}: source code contains {s!r} outside "
                    f"docstring/comment; G6 forbids release automation"
                )
        for sub in forbidden_substrings:
            # 不要 false-positive 击中 docstring 字面量; 只扫 subprocess 调用上下文
            if sub in text and "subprocess" in text:
                # 简化: 拒绝 subprocess.run/check_output 中带 'tag'/'--tags'/'--force'
                pat = re.compile(
                    r"subprocess\.\w+\s*\(\s*\[[^\]]*"
                    + re.escape(sub.strip("'\""))
                    + r"[^\]]*\]"
                )
                assert not pat.search(text), (
                    f"{f.name}: subprocess invocation containing {sub!r}; "
                    f"G6 forbids release automation"
                )


# ---------- consolidated invariant ----------

def test_default_active_profile_remains_fake_in_shipped_config():
    """v0.13 closure invariant: shipped ``configs/mindforge.yaml`` 默认
    ``active_profile: fake``。让用户开箱不付费。"""
    cfg = (Path(__file__).resolve().parents[1] / "configs" / "mindforge.yaml").read_text(
        encoding="utf-8"
    )
    assert "active_profile: fake" in cfg, (
        "default config must ship with active_profile: fake; "
        "real provider stays explicit opt-in"
    )


def test_completion_ledger_doc_exists_with_required_buckets():
    """ROADMAP_COMPLETION_LEDGER.md 必须存在并列出全部 5 个 status
    bucket。"""
    p = Path(__file__).resolve().parents[1] / "docs" / "ROADMAP_COMPLETION_LEDGER.md"
    assert p.exists(), "missing ROADMAP_COMPLETION_LEDGER.md"
    text = p.read_text(encoding="utf-8")
    for bucket in (
        "`pushed`",
        "`local-complete`",
        "`future-gated`",
        "`release-gated`",
        "`forbidden`",
    ):
        assert bucket in text, f"completion ledger missing bucket: {bucket}"
    for gate in ("Real Cubox ingestion", "Real Obsidian", "RAG / embedding", "Public release"):
        assert gate in text
