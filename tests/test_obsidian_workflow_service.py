"""v0.7.14 — Obsidian workflow / next-action service 测试。

学习要点：obsidian_workflow 只生成 staged workflow 导航 plan，不执行命令、不写
正式 notes。CLI 负责展示，stage/preflight service 负责各自业务边界。
"""

from __future__ import annotations

import socket
from pathlib import Path

from mindforge.obsidian_workflow import build_obsidian_next_plan, obsidian_workflow_command_snippets


def test_obsidian_workflow_empty_vault_recommends_stage_path(tmp_path: Path) -> None:
    """空 vault 仍只给 dry-run/staged-export/preflight 导航，不创建目录。"""
    vault = tmp_path / "vault"
    vault.mkdir()
    output_dir = tmp_path / "staged"

    plan = build_obsidian_next_plan(vault_root=vault, output_dir=output_dir)

    assert plan.vault_exists is True
    assert plan.source_hint == "<note.md>"
    assert plan.staged_export_count == 0
    assert plan.manifest_count == 0
    assert "stage --dry-run" in plan.recommended_next
    assert "formal note writes" in plan.safety_line
    assert not output_dir.exists()


def test_obsidian_workflow_manifest_recommends_preflight(tmp_path: Path) -> None:
    """存在 manifest 时 next action 指向 preflight，仍不写正式 vault note。"""
    vault = tmp_path / "vault"
    vault.mkdir()
    output_dir = tmp_path / "staged"
    output_dir.mkdir()
    (output_dir / "Candidate.md").write_text("staged only\n", encoding="utf-8")
    manifest = output_dir / "Candidate.manifest.json"
    manifest.write_text("{}\n", encoding="utf-8")
    before_notes = sorted(vault.rglob("*.md"))

    plan = build_obsidian_next_plan(vault_root=vault, output_dir=output_dir)

    assert plan.staged_export_count == 1
    assert plan.manifest_count == 1
    assert plan.latest_manifest == manifest
    assert "obsidian preflight" in plan.recommended_next
    assert sorted(vault.rglob("*.md")) == before_notes


def test_obsidian_workflow_demo_source_hint_and_checklist_order(tmp_path: Path) -> None:
    """source hint 与 checklist 顺序稳定，方便 CLI/docs/smoke 不漂移。"""
    vault = tmp_path / "vault"
    note = vault / "00-Inbox" / "demo.md"
    note.parent.mkdir(parents=True)
    note.write_text("# demo\n", encoding="utf-8")

    plan = build_obsidian_next_plan(vault_root=vault, output_dir=tmp_path / "staged")

    assert plan.source_hint == "00-Inbox/demo.md"
    assert [cmd.note for cmd in plan.commands][:3] == [
        "检查 vault 边界和 staged export 状态",
        "只读扫描 Markdown 安全摘要",
        "只读解析 [[wikilinks]]，不建 graph/RAG",
    ]
    assert plan.manual_inspection_steps == (
        "Inspect staged markdown and manifest by hand.",
        "Confirm backup expectations before any future write gate.",
        "Record unclear output in a local troubleshooting note; see README.md.",
    )


def test_obsidian_workflow_command_snippets_stop_at_preflight(tmp_path: Path) -> None:
    """workflow snippets 不包含 apply/write-back/plugin/RAG 已实现暗示。"""
    commands = obsidian_workflow_command_snippets(tmp_path / "vault", "note.md", tmp_path / "staged")
    joined = "\n".join(f"{item.command}\n{item.note}" for item in commands)

    assert "obsidian preflight" in joined
    assert "apply" not in joined
    assert "plugin" not in joined.lower()
    assert "embedding" not in joined.lower()


def test_obsidian_workflow_no_cli_env_llm_or_note_write_dependency(tmp_path: Path, monkeypatch) -> None:
    """workflow service 不依赖 Typer/Rich，不读 .env，不联网，也不写 vault notes。"""
    vault = tmp_path / "vault"
    vault.mkdir()
    (tmp_path / ".env").write_text("SECRET=value\n", encoding="utf-8")

    def _blocked(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("obsidian_workflow 不应触发外部边界")

    monkeypatch.setattr("mindforge.env_loader.load_dotenv_silently", _blocked)
    monkeypatch.setattr("mindforge.llm.build_providers", _blocked)
    monkeypatch.setattr(socket, "socket", _blocked)

    plan = build_obsidian_next_plan(vault_root=vault, output_dir=tmp_path / "staged")
    source = Path("src/mindforge/obsidian_workflow.py").read_text(encoding="utf-8")

    assert plan.vault_exists is True
    assert "import typer" not in source
    assert "from rich" not in source
    assert "write_text" not in source
    assert "read_text" not in source
    assert "build_providers" not in source
