"""v0.13 Stage 1 — ``mindforge provider`` CLI smoke + AST import-boundary.

CLI 表面:
- ``mindforge provider readiness --config <path>`` 可在不调网络的情况
  exit 0 并打印 readiness 报告; fake-default 状态被识别;
- ``mindforge provider smoke --config <path>`` 不传 ``--allow-real``
  时拒绝运行, exit 0, 输出含 blocker。

AST 边界: provider_readiness.py / real_smoke.py / provider_cli.py 不
反向 import CLI / approval / writer / cards / obsidian* / cubox* /
scanner / dotenv / requests / httpx / subprocess。
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mindforge.cli import app

runner = CliRunner()


def test_cli_provider_readiness_exits_clean():
    result = runner.invoke(
        app, ["provider", "readiness", "--config", "configs/mindforge.yaml"]
    )
    assert result.exit_code == 0, result.output
    assert "fake-default" in result.output
    assert "readiness report" in result.output.lower()


def test_cli_provider_smoke_refuses_without_allow_real():
    result = runner.invoke(
        app, ["provider", "smoke", "--config", "configs/mindforge.yaml"]
    )
    assert result.exit_code == 0, result.output
    assert "ran                   : False" in result.output
    assert "human_approved        : False" in result.output
    assert "blocker" in result.output.lower()


def test_cli_provider_smoke_does_not_print_secret(monkeypatch):
    # 即使 env 中存在 api_key, 默认 fake profile + 不传 allow-real 也不应触发
    monkeypatch.setenv("MF_FAKE_TEST_KEY_CLI_LEAK", "leaked-secret-1234567890")
    result = runner.invoke(
        app, ["provider", "smoke", "--config", "configs/mindforge.yaml"]
    )
    assert "leaked-secret-1234567890" not in result.output


_GUARDED = (
    Path("src/mindforge/provider_readiness.py"),
    Path("src/mindforge/real_smoke.py"),
    Path("src/mindforge/provider_cli.py"),
    Path("src/mindforge/dogfood_safety.py"),
)

# real_smoke 允许 import mindforge.llm.factory; provider_cli 允许 import
# mindforge.app_context + provider_readiness/real_smoke。
# 但都禁止 import 下列副作用模块。
_FORBIDDEN_PREFIXES = (
    "mindforge.cli",
    "mindforge.approval_service",
    "mindforge.approver",
    "mindforge.approve_presenter",
    "mindforge.writer",
    "mindforge.cards",
    "mindforge.process_service",
    "mindforge.review_service",
    "mindforge.review_presenter",
    "mindforge.recall_service",
    "mindforge.recall_presenter",
    "mindforge.obsidian",
    "mindforge.obsidian_cli",
    "mindforge.obsidian_stage",
    "mindforge.obsidian_workflow",
    "mindforge.cubox_cli",
    "mindforge.cubox_dryrun_presenter",
    "mindforge.cubox_preview_presenter",
    "mindforge.scanner",
    "mindforge.env_loader",
    "mindforge.processors",
    "dotenv",
    "requests",
    "httpx",
    "subprocess",
)


def _collect_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                # 相对 import: 规范化成 mindforge.<module> 以便 forbidden
                # 列表也能覆盖 (避免 'from .env_loader import X' 绕过守卫)。
                if node.module:
                    out.append(f"mindforge.{node.module}")
                continue
            if node.module:
                out.append(node.module)
    return out


# provider_cli 显式允许 env_loader (与 cli.py 的 .env 注入语义一致);
# real_smoke / provider_readiness 仍然禁止。
_PER_FILE_ALLOWLIST = {
    Path("src/mindforge/provider_cli.py"): {"mindforge.env_loader"},
}


@pytest.mark.parametrize("path", _GUARDED, ids=lambda p: p.name)
def test_provider_files_do_not_reverse_import_runtime(path: Path):
    assert path.exists(), path
    imports = _collect_imports(path)
    allow = _PER_FILE_ALLOWLIST.get(path, set())
    bad = sorted(
        {
            n
            for n in imports
            for prefix in _FORBIDDEN_PREFIXES
            if (n == prefix or n.startswith(prefix + ".")) and n not in allow
        }
    )
    assert not bad, (
        f"{path} reverse-imports forbidden runtime modules: {bad}; "
        "provider readiness/smoke/cli must stay decoupled from approval, "
        "writer, cards, obsidian, cubox, dotenv, network."
    )


def test_provider_readiness_imports_no_factory():
    """provider_readiness 不应 import llm.factory — 只 inspect, 不构造。"""
    imports = _collect_imports(Path("src/mindforge/provider_readiness.py"))
    bad = [n for n in imports if n.startswith("mindforge.llm")]
    assert not bad, f"provider_readiness must not import mindforge.llm.*; got {bad}"
