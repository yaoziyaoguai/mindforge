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
    assert "mindforge doctor --vault /tmp/project-vault --paths" in result.output
    assert (
        "mindforge dogfood preflight /tmp/project-vault --declare-non-sensitive"
        in result.output
    )
    assert "mindforge approve list --vault /tmp/project-vault" in result.output


def test_quickstart_mentions_three_required_command_paths() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["dogfood", "quickstart"])
    assert "mindforge dogfood readiness" in result.output
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
        # P2/P3 third-party-review remediation: explicit limit + rollback
        # + token guidance must surface in the runbook output itself, so
        # users who never read the doc still see the boundary reminders.
        "--limit 5",
        "--limit 20",
        "no full Cubox sync",
        "Rollback",
        "disposable",
        "Cubox API token is a secret",
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
    assert len(steps) == 11
    doc = Path("docs/REAL_DOGFOOD_QUICKSTART.md").read_text(encoding="utf-8")
    # 每条命令的核心动词必须出现在 doc 表格里 (粗匹配, 避免假阳性)。
    for command, _note in steps:
        head = command.split()[0:2]
        head_str = " ".join(head)
        assert head_str in doc, f"doc 表格缺少: {head_str!r}"


def test_quickstart_doc_covers_p2_p3_review_followups() -> None:
    """第三方 reviewer 的 P2/P3 必须在 doc 里有明确章节, 防止文档漂移。

    覆盖: explicit limit guidance / rollback & cleanup / token safety /
    boundary guarantees (no full sync / no formal vault write / no
    human_approved / no release/tag)。
    """
    doc = Path("docs/REAL_DOGFOOD_QUICKSTART.md").read_text(encoding="utf-8")
    for literal in (
        # explicit limit guidance
        "Explicit limit guidance",
        "`--limit 5`",
        "`--limit 20`",
        "does not support full Cubox account sync",
        "no `--all` flag",
        # rollback / cleanup
        "Rollback and cleanup guidance",
        "git restore",
        "disposable",
        "staging/",
        # token safety
        "Token safety guidance",
        "secret",
        "Never",
        "rotate it",
        # boundary guarantees
        "Boundary guidance",
        "No background indexing",
        "no PyPI publish",
        "no v1.0",
        # explicit re-statement that no human_approved is produced
        "human_approved",
    ):
        assert literal in doc, f"REAL_DOGFOOD_QUICKSTART.md 缺少: {literal!r}"
