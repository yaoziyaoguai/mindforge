"""v0.5 — Obsidian Binding MVP 测试。

学习要点：
- Obsidian 是 SourceAdapter 输入源，不是 output 目录别名；
- 默认只读，避免真实 vault 被 AI 草稿或机器状态污染；
- staging/review 与正式 notes 隔离；
- 这不是 Obsidian plugin，也不是 RAG/vector/graph。
"""

from __future__ import annotations

import json
import socket
from pathlib import Path

import yaml
from typer.testing import CliRunner

from mindforge.cli import app
from mindforge.config import load_mindforge_config
from mindforge.obsidian import ObsidianScanOptions, load_obsidian_documents
from mindforge.scanner import Scanner
from mindforge.sources.obsidian_vault import ObsidianVaultSourceAdapter
from mindforge.sources.registry import _BUILTIN_ADAPTERS, build_active_adapters

runner = CliRunner()


def _make_obsidian_vault(tmp_path: Path) -> tuple[Path, Path, Path]:
    vault = tmp_path / "obsidian-vault"
    (vault / ".obsidian").mkdir(parents=True)
    (vault / "02-Knowledge").mkdir(parents=True)
    (vault / "03-Projects").mkdir(parents=True)
    (vault / ".mindforge" / "runs").mkdir(parents=True)
    note = vault / "02-Knowledge" / "Agent Runtime.md"
    note.write_text(
        "---\n"
        "title: Agent Runtime\n"
        "tags: [agent, runtime]\n"
        "aliases: [Runtime Note]\n"
        "created: 2026-01-02\n"
        "updated: 2026-01-03\n"
        "---\n\n"
        "# Agent Runtime\n\n"
        "Links to [[Project Alpha]] and [[Runtime Note|alias]]. #pkm\n\n"
        "## Checkpoints\n\n"
        "Body secret should not be printed by CLI scan.\n",
        encoding="utf-8",
    )
    project = vault / "03-Projects" / "Project Alpha.md"
    project.write_text(
        "---\ntitle: Project Alpha\ntags: [project]\n---\n\n"
        "# Project Alpha\n\nBacklink to [[Agent Runtime]].\n",
        encoding="utf-8",
    )

    cfg = {
        "version": 0.5,
        "vault": {
            "root": str(tmp_path / "mindforge-vault"),
            "inbox_root": "00-Inbox",
            "cards_dir": "20-Knowledge-Cards",
            "archive_dir": "90-Archive/Skipped",
        },
        "sources": {
            "enabled": [],
            "registry": {
                "obsidian_note": {
                    "adapter": "ObsidianVaultSourceAdapter",
                    "inbox_subdir": ".",
                    "file_glob": "*.md",
                    "enabled": False,
                }
            },
        },
        "state": {
            "workdir": str(tmp_path / ".mindforge"),
            "state_file": "state.json",
            "runs_dir": "runs",
            "index_file": "index.jsonl",
            "backup_state": True,
        },
        "obsidian": {
            "vault_path": str(vault),
            "staging_dir": "90-System/MindForge/Staging",
            "review_dir": "90-System/MindForge/Review",
            "include_dirs": ["02-Knowledge", "03-Projects"],
            "exclude_dirs": [".obsidian", ".git", ".mindforge", "90-System/MindForge/Runtime"],
            "read_only": True,
        },
        "triage": {"value_score_threshold": 5, "default_track": "unrouted"},
        "llm": {
            "active_profile": "fake",
            "profiles": {
                "fake": {
                    "triage": "fake_alias",
                    "distill": "fake_alias",
                    "link_suggestion": "fake_alias",
                    "review_questions": "fake_alias",
                    "action_extraction": "fake_alias",
                }
            },
            "models": {"fake_alias": {"provider": "fake", "type": "fake", "model": "fake"}},
        },
        "prompts": {
            "triage_version": "v1",
            "distill_version": "v1",
            "link_suggestion_version": "v1",
            "review_questions_version": "v1",
            "action_extraction_version": "v1",
        },
        "logging": {"level": "INFO", "file": str(tmp_path / "mf.log")},
    }
    cfg_path = tmp_path / "mindforge.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return vault, note, cfg_path


def test_obsidian_adapter_parses_markdown_note(tmp_path: Path) -> None:
    vault, note, _cfg = _make_obsidian_vault(tmp_path)
    doc = ObsidianVaultSourceAdapter(vault).load(str(note))

    assert doc.source_type == "obsidian_note"
    assert doc.adapter_name == "obsidian_vault"
    assert doc.source_path == "02-Knowledge/Agent Runtime.md"
    assert doc.title == "Agent Runtime"
    assert {"agent", "runtime", "pkm"} <= set(doc.tags)
    assert doc.metadata["aliases"] == ["Runtime Note"]
    assert doc.created_at is not None
    assert doc.metadata["updated_at"] is not None
    assert doc.metadata["wikilinks"] == ["Project Alpha", "Runtime Note"]
    assert [h["text"] for h in doc.metadata["headings"]] == ["Agent Runtime", "Checkpoints"]
    assert doc.content_hash.startswith("sha256:")


def test_obsidian_adapter_hash_is_stable(tmp_path: Path) -> None:
    vault, note, _cfg = _make_obsidian_vault(tmp_path)
    adapter = ObsidianVaultSourceAdapter(vault)
    assert adapter.load(str(note)).content_hash == adapter.load(str(note)).content_hash


def test_obsidian_adapter_is_registered_but_not_active_by_default(tmp_path: Path) -> None:
    assert "ObsidianVaultSourceAdapter" in _BUILTIN_ADAPTERS
    _vault, _note, cfg_path = _make_obsidian_vault(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    assert build_active_adapters(cfg.sources) == {}
    assert Scanner(cfg).scan_all() == []


def test_processor_layer_has_no_obsidian_branch() -> None:
    text = Path("src/mindforge/processors/pipeline.py").read_text(encoding="utf-8").lower()
    assert "obsidian" not in text


def test_obsidian_scan_outputs_safe_summary_not_body(tmp_path: Path) -> None:
    vault, _note, cfg = _make_obsidian_vault(tmp_path)
    res = runner.invoke(app, ["obsidian", "scan", "--config", str(cfg), "--vault", str(vault), "--json"])
    assert res.exit_code == 0, res.output
    assert "Agent Runtime" in res.output
    assert "Body secret should not be printed" not in res.output
    assert "sha256:" in res.output


def test_obsidian_scan_json_is_stable(tmp_path: Path) -> None:
    vault, _note, cfg = _make_obsidian_vault(tmp_path)
    res = runner.invoke(
        app,
        ["obsidian", "scan", "--config", str(cfg), "--vault", str(vault), "--limit", "1", "--json"],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["version"] == 1
    assert len(data["notes"]) == 1
    assert set(data["notes"][0]) == {
        "title",
        "relative_path",
        "tags",
        "wikilink_count",
        "heading_count",
        "content_hash",
        "source_type",
    }


def test_obsidian_links_outputs_outgoing_and_incoming(tmp_path: Path) -> None:
    vault, _note, cfg = _make_obsidian_vault(tmp_path)
    res = runner.invoke(app, ["obsidian", "links", "--config", str(cfg), "--vault", str(vault), "--json"])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    rows = {row["note"]: row for row in data["links"]}
    assert rows["02-Knowledge/Agent Runtime.md"]["outgoing_links"] == ["Project Alpha", "Runtime Note"]
    assert rows["03-Projects/Project Alpha.md"]["incoming_count"] == 1


def test_obsidian_doctor_invalid_vault_is_actionable(tmp_path: Path) -> None:
    _vault, _note, cfg = _make_obsidian_vault(tmp_path)
    res = runner.invoke(app, ["obsidian", "doctor", "--config", str(cfg), "--vault", str(tmp_path / "missing")])
    assert res.exit_code == 2
    assert "vault path" in res.output
    assert "mindforge obsidian doctor --vault" in res.output


def test_obsidian_stage_dry_run_writes_nothing(tmp_path: Path) -> None:
    vault, note, cfg = _make_obsidian_vault(tmp_path)
    before = note.read_text(encoding="utf-8")
    res = runner.invoke(
        app,
        ["obsidian", "stage", "--config", str(cfg), "--vault", str(vault), "--source", str(note), "--dry-run"],
    )
    assert res.exit_code == 0, res.output
    assert "dry-run" in res.output
    assert "Obsidian stage preview" in res.output
    assert "source file" in res.output
    assert "proposed path" in res.output
    assert "would-create-staging-candidate" in res.output
    assert "next command" in res.output
    assert note.read_text(encoding="utf-8") == before
    assert not (vault / "90-System" / "MindForge" / "Staging").exists()


def test_obsidian_stage_dry_run_reports_skipped_directory_source(tmp_path: Path) -> None:
    """v0.5.3: dry-run 遇到目录 source 应给 preview，而不是写文件或崩溃。

    真实 dogfooding 时用户常把 vault 目录误传给 --source。dry-run 的产品边界是
    安全说明和下一步建议；真正写入仍要求单个 Markdown note。
    """
    vault, _note, cfg = _make_obsidian_vault(tmp_path)
    res = runner.invoke(
        app,
        ["obsidian", "stage", "--config", str(cfg), "--vault", str(vault), "--source", str(vault)],
    )
    assert res.exit_code == 0, res.output
    assert "Obsidian stage preview" in res.output
    assert "skipped" in res.output
    assert "stage 需要单个 Markdown note" in res.output
    assert not (vault / "90-System" / "MindForge" / "Staging").exists()


def test_obsidian_stage_dry_run_reports_missing_source_without_write(tmp_path: Path) -> None:
    """缺失路径在 dry-run 下应变成可读 skipped report，不触碰 vault。"""
    vault, _note, cfg = _make_obsidian_vault(tmp_path)
    res = runner.invoke(
        app,
        [
            "obsidian",
            "stage",
            "--config",
            str(cfg),
            "--vault",
            str(vault),
            "--source",
            "02-Knowledge/Missing.md",
        ],
    )
    assert res.exit_code == 0, res.output
    assert "source note 不存在" in res.output
    assert "dry-run" in res.output
    assert not (vault / "90-System" / "MindForge" / "Staging").exists()


def test_obsidian_stage_dry_run_reports_non_markdown_source(tmp_path: Path) -> None:
    """非 Markdown 文件只报告 skipped，避免用户误以为 MindForge 会处理任意文件。"""
    vault, _note, cfg = _make_obsidian_vault(tmp_path)
    txt = vault / "02-Knowledge" / "readme.txt"
    txt.write_text("not markdown", encoding="utf-8")
    res = runner.invoke(
        app,
        ["obsidian", "stage", "--config", str(cfg), "--vault", str(vault), "--source", str(txt)],
    )
    assert res.exit_code == 0, res.output
    assert "不是 Markdown 文件" in res.output
    assert "skipped" in res.output


def test_obsidian_stage_write_only_to_staging_and_preserves_source(tmp_path: Path) -> None:
    vault, note, cfg = _make_obsidian_vault(tmp_path)
    before = note.read_text(encoding="utf-8")
    res = runner.invoke(
        app,
        [
            "obsidian",
            "stage",
            "--config",
            str(cfg),
            "--vault",
            str(vault),
            "--source",
            "02-Knowledge/Agent Runtime.md",
            "--write",
            "--confirm",
        ],
    )
    assert res.exit_code == 0, res.output
    assert note.read_text(encoding="utf-8") == before
    staged = vault / "90-System" / "MindForge" / "Staging" / "Agent-Runtime.md"
    assert staged.exists()
    text = staged.read_text(encoding="utf-8")
    assert "source_type: obsidian_note" in text
    assert "obsidian_relative_path: 02-Knowledge/Agent Runtime.md" in text
    assert "status: ai_draft" in text
    assert "Body secret should not be printed" not in text


def test_obsidian_stage_rejects_formal_note_output_dir(tmp_path: Path) -> None:
    vault, note, cfg = _make_obsidian_vault(tmp_path)
    res = runner.invoke(
        app,
        [
            "obsidian",
            "stage",
            "--config",
            str(cfg),
            "--vault",
            str(vault),
            "--source",
            str(note),
            "--output-dir",
            "02-Knowledge",
            "--write",
            "--confirm",
        ],
    )
    assert res.exit_code == 2
    assert "staging/review" in res.output
    assert not (vault / "02-Knowledge" / "Agent-Runtime.md").exists()


def test_obsidian_commands_do_not_read_env_or_use_network(tmp_path: Path, monkeypatch) -> None:
    vault, _note, cfg = _make_obsidian_vault(tmp_path)
    (tmp_path / ".env").write_text("MINDFORGE_LLM_API_KEY=secret\n", encoding="utf-8")

    def _blocked_env(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("obsidian commands 不应读取 .env")

    def _blocked_socket(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("obsidian commands 不应联网")

    monkeypatch.setattr("mindforge.cli.load_dotenv_silently", _blocked_env)
    monkeypatch.setattr(socket, "socket", _blocked_socket)
    res = runner.invoke(app, ["obsidian", "scan", "--config", str(cfg), "--vault", str(vault)])
    assert res.exit_code == 0, res.output
    assert "secret" not in res.output

    stage_res = runner.invoke(
        app,
        ["obsidian", "stage", "--config", str(cfg), "--vault", str(vault), "--source", "02-Knowledge/Agent Runtime.md"],
    )
    assert stage_res.exit_code == 0, stage_res.output
    assert "secret" not in stage_res.output


def test_obsidian_scan_does_not_write_runtime_or_raw_text_state(tmp_path: Path) -> None:
    vault, _note, cfg = _make_obsidian_vault(tmp_path)
    res = runner.invoke(app, ["obsidian", "scan", "--config", str(cfg), "--vault", str(vault)])
    assert res.exit_code == 0, res.output
    assert not (tmp_path / ".mindforge" / "state.json").exists()
    assert not (tmp_path / ".mindforge" / "runs").exists()
    assert not (vault / "90-System" / "MindForge" / "Runtime").exists()
    docs = load_obsidian_documents(
        ObsidianScanOptions(vault, ("02-Knowledge",), (".obsidian", ".git", ".mindforge")),
    )
    assert docs and docs[0].raw_text


def test_obsidian_scan_empty_vault_is_actionable(tmp_path: Path) -> None:
    """空 vault 是 dogfooding 常见起点；scan/links 应提示下一步而不是只给空表。"""
    vault, _note, cfg = _make_obsidian_vault(tmp_path)
    for note in vault.rglob("*.md"):
        note.unlink()

    scan = runner.invoke(app, ["obsidian", "scan", "--config", str(cfg), "--vault", str(vault)])
    assert scan.exit_code == 0, scan.output
    assert "未发现 Markdown notes" in scan.output

    links = runner.invoke(app, ["obsidian", "links", "--config", str(cfg), "--vault", str(vault)])
    assert links.exit_code == 0, links.output
    assert "未发现可解析的 Markdown notes" in links.output


def test_obsidian_scan_bad_frontmatter_is_skipped_not_crash(tmp_path: Path) -> None:
    """坏 frontmatter 只能影响单个 note，不能中断整个只读 vault dry-run。"""
    vault, _note, cfg = _make_obsidian_vault(tmp_path)
    bad = vault / "02-Knowledge" / "Broken.md"
    bad.write_text("---\ntitle: [unterminated\n---\n\nbody secret should stay hidden", encoding="utf-8")

    res = runner.invoke(app, ["obsidian", "scan", "--config", str(cfg), "--vault", str(vault)])
    assert res.exit_code == 0, res.output
    assert "Skipped notes" in res.output
    assert "Broken.md" in res.output
    assert "body secret should stay hidden" not in res.output
