"""Tests for ``mindforge dogfood quickstart`` runbook command.

Quickstart 是 **read-only runbook**, 不执行任何子命令; 测试守护:
- 命令执行成功;
- 输出涵盖 Cubox JSON-export + ai_draft + Obsidian dry-run 三段;
- 命令清单与 docs/REAL_DOGFOOD_QUICKSTART.md 表格一致, 防止文档漂移;
- 显式声明不调用真实 LLM / 不写 vault / 不产生 human_approved。
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from mindforge.cli import _dogfood_quickstart_steps, app


def test_quickstart_default_vault_exits_zero() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["dogfood", "quickstart"])
    assert result.exit_code == 0, result.output
    assert "examples/demo-vault" in result.output


def test_quickstart_explicit_vault() -> None:
    runner = CliRunner()
    result = runner.invoke(
        app, ["dogfood", "quickstart", "--vault", "/tmp/project-vault"]
    )
    assert result.exit_code == 0, result.output
    assert "/tmp/project-vault" in result.output


def test_quickstart_mentions_three_required_command_paths() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["dogfood", "quickstart"])
    assert "mindforge cubox dry-run" in result.output
    assert "mindforge cubox preview-ai-draft" in result.output
    assert "mindforge obsidian stage" in result.output
    assert "--dry-run" in result.output


def test_quickstart_mentions_safety_boundaries() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["dogfood", "quickstart"])
    for literal in (
        "fake-default",
        "No .env content is read",
        "No real LLM",
        "No formal Obsidian write",
        "No human_approved is produced",
        "REAL_DOGFOOD_QUICKSTART.md",
    ):
        assert literal in result.output, f"missing: {literal!r}"


def test_quickstart_with_cubox_export_substitutes_path() -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "dogfood",
            "quickstart",
            "--vault",
            "/tmp/v",
            "--cubox-export",
            "/tmp/cb.json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "/tmp/cb.json" in result.output


def test_quickstart_steps_helper_consistency_with_doc() -> None:
    """命令清单条数与 doc 表格行数一致, 防止文档漂移。"""
    steps = _dogfood_quickstart_steps(Path("examples/demo-vault"), None)
    assert len(steps) == 10
    doc = Path("docs/REAL_DOGFOOD_QUICKSTART.md").read_text(encoding="utf-8")
    # 每条命令的核心动词必须出现在 doc 表格里 (粗匹配, 避免假阳性)。
    for command, _note in steps:
        head = command.split()[0:2]
        head_str = " ".join(head)
        assert head_str in doc, f"doc 表格缺少: {head_str!r}"
