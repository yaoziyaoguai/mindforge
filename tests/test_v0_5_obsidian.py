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

from mindforge.cli import app, _obsidian_dogfood_command_snippets
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


def test_obsidian_scan_and_links_show_scope_and_next_steps(tmp_path: Path) -> None:
    """v0.7.7: dogfooding 输出要告诉用户 scope 生效情况和下一条命令。"""
    vault, _note, cfg = _make_obsidian_vault(tmp_path)

    scan = runner.invoke(app, ["obsidian", "scan", "--config", str(cfg), "--vault", str(vault), "--limit", "1"])
    links = runner.invoke(app, ["obsidian", "links", "--config", str(cfg), "--vault", str(vault)])

    assert scan.exit_code == 0, scan.output
    assert "scope: include=" in scan.output
    assert "Next: mindforge obsidian links" in scan.output
    assert "Then: mindforge obsidian stage" in scan.output
    assert links.exit_code == 0, links.output
    assert "scope: include=" in links.output
    assert "Next: mindforge obsidian stage" in links.output


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
    assert "source exists" in res.output
    assert "source in vault" in res.output
    assert "proposed path" in res.output
    assert "proposed title" in res.output
    assert "detected wikilinks" in res.output
    assert "frontmatter keys" in res.output
    assert "detected source type" in res.output
    assert "Agent Runtime" in res.output
    assert "Project Alpha" in res.output
    assert "would-create-staging-candidate" in res.output
    assert "risk warning" in res.output
    assert "next command" in res.output
    assert "--staged-export --diff --write --confirm" in res.output
    assert "manual check" in res.output
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
    assert "source exists" in res.output
    assert "dry-run" in res.output
    assert not (vault / "90-System" / "MindForge" / "Staging").exists()


def test_obsidian_stage_reports_missing_vault_without_write(tmp_path: Path) -> None:
    """v0.7.1: vault 路径错时也要给 dry-run preview，而不是 traceback。"""
    _vault, _note, cfg = _make_obsidian_vault(tmp_path)
    missing_vault = tmp_path / "missing-vault"
    res = runner.invoke(
        app,
        [
            "obsidian",
            "stage",
            "--config",
            str(cfg),
            "--vault",
            str(missing_vault),
            "--source",
            "note.md",
        ],
    )
    assert res.exit_code == 0, res.output
    assert "vault exists" in res.output
    assert "no" in res.output
    assert "Obsidian vault 不存在" in res.output
    assert not missing_vault.exists()


def test_obsidian_stage_reports_source_outside_vault_without_write(tmp_path: Path) -> None:
    """v0.7.1: 外部 source 必须只报告 skipped，避免误处理真实私人文件。"""
    vault, _note, cfg = _make_obsidian_vault(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("# Outside\n\nsecret body must not print\n", encoding="utf-8")
    before = outside.read_text(encoding="utf-8")

    res = runner.invoke(
        app,
        ["obsidian", "stage", "--config", str(cfg), "--vault", str(vault), "--source", str(outside)],
    )

    assert res.exit_code == 0, res.output
    assert "source in vault" in res.output
    assert "no" in res.output
    assert "必须位于 Obsidian vault 内" in res.output
    assert "secret body must not print" not in res.output
    assert outside.read_text(encoding="utf-8") == before
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


def test_obsidian_stage_bad_frontmatter_is_preview_skip_not_crash(tmp_path: Path) -> None:
    """坏 frontmatter 不能中断 dry-run，也不能输出 note 正文。"""
    vault, _note, cfg = _make_obsidian_vault(tmp_path)
    bad = vault / "02-Knowledge" / "Broken Stage.md"
    bad.write_text("---\ntitle: [unterminated\n---\n\nsecret body should stay hidden", encoding="utf-8")

    res = runner.invoke(
        app,
        ["obsidian", "stage", "--config", str(cfg), "--vault", str(vault), "--source", str(bad)],
    )

    assert res.exit_code == 0, res.output
    assert "source 解析失败" in res.output
    assert "skipped" in res.output
    assert "secret body should stay hidden" not in res.output


def test_obsidian_stage_from_non_repo_cwd_is_dry_run_only(tmp_path: Path, monkeypatch) -> None:
    """packaged-like smoke：显式 --config/--vault 时从 /tmp 也能 dry-run。"""
    vault, note, cfg = _make_obsidian_vault(tmp_path)
    before = note.read_text(encoding="utf-8")
    run_dir = tmp_path / "run dir with space"
    run_dir.mkdir()
    monkeypatch.chdir(run_dir)

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
            "--dry-run",
        ],
    )

    assert res.exit_code == 0, res.output
    assert "Obsidian stage preview" in res.output
    assert "dry-run：未写任何文件" in res.output
    assert note.read_text(encoding="utf-8") == before
    assert not (vault / "90-System" / "MindForge" / "Staging").exists()


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


def test_obsidian_staged_export_writes_export_dir_not_formal_notes(tmp_path: Path) -> None:
    """v0.7.2: staged export 是人工检查目录，不能写回正式 Obsidian notes。"""
    vault, note, cfg = _make_obsidian_vault(tmp_path)
    before = note.read_text(encoding="utf-8")
    export_dir = tmp_path / "exports"

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
            "--staged-export",
            "--output-dir",
            str(export_dir),
            "--write",
            "--confirm",
        ],
    )

    assert res.exit_code == 0, res.output
    exported = export_dir / "Agent-Runtime.md"
    manifest = export_dir / "Agent-Runtime.manifest.json"
    assert exported.exists()
    assert manifest.exists()
    assert note.read_text(encoding="utf-8") == before
    assert not (vault / "02-Knowledge" / "Agent-Runtime.md").exists()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["source_note"] == "02-Knowledge/Agent Runtime.md"
    assert payload["action"] == "staged-export-create"
    assert payload["safety"]["no_formal_obsidian_note_write"] is True
    assert payload["safety"]["no_real_llm"] is True
    assert payload["safety"]["no_env_read"] is True
    assert "Body secret should not be printed" not in exported.read_text(encoding="utf-8")
    assert "secret" not in manifest.read_text(encoding="utf-8").lower()


def test_obsidian_staged_export_does_not_overwrite_existing_file(tmp_path: Path) -> None:
    """同名 staged 文件应生成唯一文件名，避免覆盖用户已检查的 export。"""
    vault, note, cfg = _make_obsidian_vault(tmp_path)
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    existing = export_dir / "Agent-Runtime.md"
    existing.write_text("existing staged review\n", encoding="utf-8")

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
            "--staged-export",
            "--output-dir",
            str(export_dir),
            "--diff",
            "--write",
            "--confirm",
        ],
    )

    assert res.exit_code == 0, res.output
    assert "diff preview" in res.output
    assert "manual inspection" in res.output
    assert existing.read_text(encoding="utf-8") == "existing staged review\n"
    assert (export_dir / "Agent-Runtime-2.md").exists()
    assert (export_dir / "Agent-Runtime-2.manifest.json").exists()


def test_obsidian_staged_export_warns_formal_same_name_without_overwrite(tmp_path: Path) -> None:
    """正式 vault 同名文件只提示人工检查，不允许自动覆盖或 apply。"""
    vault, note, cfg = _make_obsidian_vault(tmp_path)
    formal_same_name = vault / "02-Knowledge" / "Agent-Runtime.md"
    formal_same_name.write_text("# Keep formal note\n", encoding="utf-8")
    before = formal_same_name.read_text(encoding="utf-8")

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
            "--staged-export",
            "--output-dir",
            str(tmp_path / "exports"),
            "--write",
            "--confirm",
        ],
    )

    assert res.exit_code == 0, res.output
    assert "可能存在正式 vault 同名 note" in res.output
    assert formal_same_name.read_text(encoding="utf-8") == before


def test_obsidian_staged_export_from_non_repo_cwd(tmp_path: Path, monkeypatch) -> None:
    """显式 --config/--vault/--output-dir 时，packaged-like cwd 不影响 export。"""
    vault, note, cfg = _make_obsidian_vault(tmp_path)
    before = note.read_text(encoding="utf-8")
    run_dir = tmp_path / "outside cwd"
    run_dir.mkdir()
    export_dir = tmp_path / "exports"
    monkeypatch.chdir(run_dir)

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
            "--staged-export",
            "--output-dir",
            str(export_dir),
            "--write",
            "--confirm",
        ],
    )

    assert res.exit_code == 0, res.output
    assert (export_dir / "Agent-Runtime.md").exists()
    assert note.read_text(encoding="utf-8") == before


def _write_staged_export_for_preflight(
    tmp_path: Path,
    vault: Path,
    note: Path,
    cfg: Path,
    *,
    output_dir: Path | None = None,
) -> tuple[Path, Path]:
    export_dir = output_dir or (tmp_path / "exports")
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
            "--staged-export",
            "--output-dir",
            str(export_dir),
            "--write",
            "--confirm",
        ],
    )
    assert res.exit_code == 0, res.output
    return export_dir / "Agent-Runtime.md", export_dir / "Agent-Runtime.manifest.json"


def _patch_manifest(manifest: Path, **updates) -> None:
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    for key, value in updates.items():
        if key.startswith("write_gate__"):
            payload.setdefault("write_gate", {})[key.removeprefix("write_gate__")] = value
        elif value is None:
            payload.pop(key, None)
        else:
            payload[key] = value
    manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_obsidian_preflight_passes_complete_staged_manifest(tmp_path: Path) -> None:
    """v0.7.4: 完整 staged export 可进入未来 write-gate 人工检查，但不写正式 note。"""
    vault, note, cfg = _make_obsidian_vault(tmp_path)
    before = note.read_text(encoding="utf-8")
    exported, manifest = _write_staged_export_for_preflight(tmp_path, vault, note, cfg)

    res = runner.invoke(
        app,
        ["obsidian", "preflight", "--config", str(cfg), "--vault", str(vault), "--manifest", str(manifest)],
    )

    assert res.exit_code == 0, res.output
    assert "MindForge Obsidian preflight" in res.output
    assert "PASS" in res.output
    assert "staged export -> diff preview -> backup -> explicit confirmation" in res.output
    assert "本版本不会写正式 Obsidian notes" in res.output
    assert exported.exists()
    assert note.read_text(encoding="utf-8") == before
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    proposed_target = Path(payload["write_gate"]["proposed_target"])
    assert not proposed_target.exists()


def test_obsidian_preflight_blocks_missing_manifest_field(tmp_path: Path) -> None:
    """manifest 证据链不完整时必须 BLOCKED，避免未来 write gate 猜测用户意图。"""
    vault, note, cfg = _make_obsidian_vault(tmp_path)
    _exported, manifest = _write_staged_export_for_preflight(tmp_path, vault, note, cfg)
    _patch_manifest(manifest, action=None)

    res = runner.invoke(
        app,
        ["obsidian", "preflight", "--config", str(cfg), "--vault", str(vault), "--manifest", str(manifest)],
    )

    assert res.exit_code == 2, res.output
    assert "BLOCKED" in res.output
    assert "manifest 缺少 action" in res.output


def test_obsidian_preflight_blocks_missing_staged_markdown(tmp_path: Path) -> None:
    """staged markdown 消失时不能只凭 manifest 继续推进。"""
    vault, note, cfg = _make_obsidian_vault(tmp_path)
    exported, manifest = _write_staged_export_for_preflight(tmp_path, vault, note, cfg)
    exported.unlink()

    res = runner.invoke(
        app,
        ["obsidian", "preflight", "--config", str(cfg), "--vault", str(vault), "--manifest", str(manifest)],
    )

    assert res.exit_code == 2, res.output
    assert "staged markdown 不存在" in res.output


def test_obsidian_preflight_blocks_target_outside_vault(tmp_path: Path) -> None:
    """future proposed target 必须在 vault 内；preflight 仍然不会写任何文件。"""
    vault, note, cfg = _make_obsidian_vault(tmp_path)
    before = note.read_text(encoding="utf-8")
    _exported, manifest = _write_staged_export_for_preflight(tmp_path, vault, note, cfg)
    _patch_manifest(manifest, write_gate__proposed_target=str(tmp_path / "outside.md"))

    res = runner.invoke(
        app,
        ["obsidian", "preflight", "--config", str(cfg), "--vault", str(vault), "--manifest", str(manifest)],
    )

    assert res.exit_code == 2, res.output
    assert "proposed target 不在 Obsidian vault 内" in res.output
    assert note.read_text(encoding="utf-8") == before


def test_obsidian_preflight_warns_existing_target_without_overwrite(tmp_path: Path) -> None:
    """target 已存在只能 WARNING，且 preflight 不覆盖正式或 review note。"""
    vault, note, cfg = _make_obsidian_vault(tmp_path)
    _exported, manifest = _write_staged_export_for_preflight(tmp_path, vault, note, cfg)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    proposed_target = Path(payload["write_gate"]["proposed_target"])
    proposed_target.parent.mkdir(parents=True)
    proposed_target.write_text("human review note stays\n", encoding="utf-8")

    res = runner.invoke(
        app,
        ["obsidian", "preflight", "--config", str(cfg), "--vault", str(vault), "--manifest", str(manifest)],
    )

    assert res.exit_code == 0, res.output
    assert "WARNING" in res.output
    assert "不会覆盖" in res.output
    assert proposed_target.read_text(encoding="utf-8") == "human review note stays\n"


def test_obsidian_preflight_blocks_runtime_cache_index_paths(tmp_path: Path) -> None:
    """staged output 若落到 runtime/cache/index/logs/vector/graph 这类机器层，必须阻断。"""
    vault, note, cfg = _make_obsidian_vault(tmp_path)
    _exported, manifest = _write_staged_export_for_preflight(
        tmp_path,
        vault,
        note,
        cfg,
        output_dir=tmp_path / "runtime" / "exports",
    )

    res = runner.invoke(
        app,
        ["obsidian", "preflight", "--config", str(cfg), "--vault", str(vault), "--manifest", str(manifest)],
    )

    assert res.exit_code == 2, res.output
    assert "禁止的机器派生层路径" in res.output
    assert "runtime" in res.output


def test_obsidian_preflight_does_not_read_env_llm_or_telemetry(tmp_path: Path, monkeypatch) -> None:
    """preflight 是本地 manifest 校验，不应碰 .env、真实 LLM provider 或 telemetry 上传。"""
    vault, note, cfg = _make_obsidian_vault(tmp_path)
    _exported, manifest = _write_staged_export_for_preflight(tmp_path, vault, note, cfg)
    (tmp_path / ".env").write_text("MINDFORGE_LLM_API_KEY=secret\n", encoding="utf-8")

    def _blocked(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("preflight 不应触发这个外部边界")

    monkeypatch.setattr("mindforge.cli.load_dotenv_silently", _blocked)
    monkeypatch.setattr("mindforge.cli.build_providers", _blocked)
    monkeypatch.setattr(socket, "socket", _blocked)

    res = runner.invoke(
        app,
        ["obsidian", "preflight", "--config", str(cfg), "--vault", str(vault), "--manifest", str(manifest)],
    )

    assert res.exit_code == 0, res.output
    assert "secret" not in res.output
    assert "不会调用真实 LLM" in res.output


def test_obsidian_preflight_from_non_repo_cwd(tmp_path: Path, monkeypatch) -> None:
    """显式 --config/--vault/--manifest 时，从 /tmp 类 cwd 也能完成 write-gate prep。"""
    vault, note, cfg = _make_obsidian_vault(tmp_path)
    _exported, manifest = _write_staged_export_for_preflight(tmp_path, vault, note, cfg)
    run_dir = tmp_path / "tmp cwd"
    run_dir.mkdir()
    monkeypatch.chdir(run_dir)

    res = runner.invoke(
        app,
        ["obsidian", "preflight", "--config", str(cfg), "--vault", str(vault), "--manifest", str(manifest)],
    )

    assert res.exit_code == 0, res.output
    assert "PASS" in res.output


def test_obsidian_next_outputs_dogfooding_flow(tmp_path: Path) -> None:
    """v0.7.5: Obsidian 专用 next 只输出人工 dogfooding 路径，不执行写入。"""
    vault, note, cfg = _make_obsidian_vault(tmp_path)
    before = note.read_text(encoding="utf-8")

    res = runner.invoke(app, ["obsidian", "next", "--config", str(cfg), "--vault", str(vault)])

    assert res.exit_code == 0, res.output
    assert "MindForge Obsidian dogfooding flow" in res.output
    assert "obsidian doctor" in res.output
    assert "obsidian scan" in res.output
    assert "obsidian links" in res.output
    assert "--dry-run" in res.output
    assert "--staged-export" in res.output
    assert "--diff" in res.output
    assert "obsidian preflight" in res.output
    assert "manual inspection" in res.output.lower()
    assert "no .env, no real LLM, no formal note writes" in res.output
    assert "apply command" in res.output
    assert note.read_text(encoding="utf-8") == before
    assert not (vault / "90-System" / "MindForge" / "Review").exists()


def test_obsidian_next_reports_staged_manifest_status(tmp_path: Path) -> None:
    """obsidian next 应展示 staged export / manifest 状态并建议 preflight。"""
    vault, note, cfg = _make_obsidian_vault(tmp_path)
    export_dir = tmp_path / "staged"
    _exported, manifest = _write_staged_export_for_preflight(
        tmp_path,
        vault,
        note,
        cfg,
        output_dir=export_dir,
    )

    res = runner.invoke(
        app,
        [
            "obsidian",
            "next",
            "--config",
            str(cfg),
            "--vault",
            str(vault),
            "--output-dir",
            str(export_dir),
        ],
    )

    assert res.exit_code == 0, res.output
    assert "Current status" in res.output
    assert "staged exports: 1" in res.output
    assert "manifests: 1" in res.output
    assert str(manifest) in res.output
    assert "recommended next: mindforge obsidian preflight" in res.output


def test_obsidian_dogfood_snippets_match_next_output(tmp_path: Path) -> None:
    """CLI 输出和 helper 共享 snippets，避免文档化命令逐步漂移。"""
    vault, _note, cfg = _make_obsidian_vault(tmp_path)
    source_hint = "02-Knowledge/Agent Runtime.md"
    output_dir = Path("/tmp/mindforge-obsidian-staged")
    res = runner.invoke(app, ["obsidian", "next", "--config", str(cfg), "--vault", str(vault)])

    assert res.exit_code == 0, res.output
    for command, _note_text in _obsidian_dogfood_command_snippets(vault.resolve(), source_hint, output_dir):
        assert command in res.output


def test_obsidian_dogfooding_checklist_exists_and_sets_boundaries() -> None:
    checklist = Path("docs/templates/OBSIDIAN_DOGFOODING_CHECKLIST.md")
    text = checklist.read_text(encoding="utf-8")

    assert checklist.exists()
    assert "disposable, non-sensitive vault copy" in text
    assert "real `.env`" in text
    assert "real LLM" in text
    assert "formal Obsidian notes" in text
    assert "staged export path" in text
    assert "manifest path" in text
    assert "Diff preview" in text
    assert "include/exclude" in text
    assert "v0.7 patch" in text
    assert "v0.8 backlog" in text
    assert "No RAG / embedding" in text
    assert "No Obsidian plugin" in text


def test_obsidian_dogfooding_docs_do_not_claim_forbidden_capabilities() -> None:
    """v0.7.5 docs 可以说 non-goals，但不能把 plugin/RAG/real LLM 写成已实现。"""
    doc = Path("docs/V0_7_5_OBSIDIAN_DOGFOODING_FLOW.md").read_text(encoding="utf-8")
    checklist = Path("docs/templates/OBSIDIAN_DOGFOODING_CHECKLIST.md").read_text(encoding="utf-8")
    combined = f"{doc}\n{checklist}".lower()

    forbidden_claims = [
        "rag is implemented",
        "embedding is implemented",
        "plugin is implemented",
        "real llm is enabled",
        "can write formal obsidian notes",
        "automatic vault cleanup is implemented",
        "does automatic vault cleanup",
    ]
    for claim in forbidden_claims:
        assert claim not in combined
    assert "no formal obsidian notes are written" in combined


def test_obsidian_dogfooding_flow_demo_vault_hash_unchanged(tmp_path: Path) -> None:
    """真实 CLI 行为：dry-run -> staged export -> preflight 后，正式 note hash 不变。"""
    vault, note, cfg = _make_obsidian_vault(tmp_path)
    before = note.read_text(encoding="utf-8")

    dry_run = runner.invoke(
        app,
        ["obsidian", "stage", "--config", str(cfg), "--vault", str(vault), "--source", str(note), "--dry-run"],
    )
    exported, manifest = _write_staged_export_for_preflight(tmp_path, vault, note, cfg)
    preflight = runner.invoke(
        app,
        ["obsidian", "preflight", "--config", str(cfg), "--vault", str(vault), "--manifest", str(manifest)],
    )

    assert dry_run.exit_code == 0, dry_run.output
    assert "dry-run：未写任何文件" in dry_run.output
    assert exported.exists()
    assert preflight.exit_code == 0, preflight.output
    assert "PASS" in preflight.output
    assert note.read_text(encoding="utf-8") == before
    assert not (vault / "02-Knowledge" / "Agent-Runtime.md").exists()


def test_obsidian_dogfooding_flow_from_tmp_disposable_vault(tmp_path: Path, monkeypatch) -> None:
    """从 /tmp 类 cwd 走完整 Obsidian dogfooding 主路径，证明不依赖 repo cwd。"""
    vault, note, cfg = _make_obsidian_vault(tmp_path)
    run_dir = tmp_path / "tmp-run"
    run_dir.mkdir()
    output_dir = tmp_path / "staged"
    monkeypatch.chdir(run_dir)

    next_res = runner.invoke(app, ["obsidian", "next", "--config", str(cfg), "--vault", str(vault)])
    dry_run = runner.invoke(
        app,
        ["obsidian", "stage", "--config", str(cfg), "--vault", str(vault), "--source", str(note), "--dry-run"],
    )
    exported, manifest = _write_staged_export_for_preflight(tmp_path, vault, note, cfg, output_dir=output_dir)
    preflight = runner.invoke(
        app,
        ["obsidian", "preflight", "--config", str(cfg), "--vault", str(vault), "--manifest", str(manifest)],
    )

    assert next_res.exit_code == 0, next_res.output
    assert dry_run.exit_code == 0, dry_run.output
    assert exported.exists()
    assert preflight.exit_code == 0, preflight.output
    assert "PASS" in preflight.output


def test_obsidian_readiness_doc_exists_and_preserves_boundaries() -> None:
    """v0.7.6: readiness 只能总结 dry-run 能力，不能提前宣称 write/apply/plugin/RAG。"""
    doc_path = Path("docs/V0_7_X_OBSIDIAN_INTEGRATION_READINESS.md")
    text = doc_path.read_text(encoding="utf-8")
    lowered = text.lower()

    assert doc_path.exists()
    assert "v0.7.1" in text
    assert "v0.7.5" in text
    assert "No formal Obsidian note writes" in text
    assert "No Obsidian plugin" in text
    assert "No RAG / embedding" in text
    assert "No default real LLM path" in text
    assert "No telemetry upload" in text
    forbidden_claims = [
        "apply is implemented",
        "write gate is enabled",
        "plugin is implemented",
        "rag is implemented",
        "real llm is enabled",
    ]
    for claim in forbidden_claims:
        assert claim not in lowered


def test_obsidian_readiness_doc_command_examples_are_covered() -> None:
    """readiness 文档中的关键命令必须是已有 CLI 入口或明确的人工占位示例。"""
    text = Path("docs/V0_7_X_OBSIDIAN_INTEGRATION_READINESS.md").read_text(encoding="utf-8")
    required_commands = [
        "mindforge obsidian next --vault <disposable-vault-copy>",
        "mindforge obsidian doctor --vault <copy>",
        "mindforge obsidian scan --vault <copy> --limit 20",
        "mindforge obsidian links --vault <copy>",
        "mindforge obsidian stage --vault <copy> --source <note.md> --dry-run",
        "mindforge obsidian preflight --vault <copy> --manifest",
    ]
    for command in required_commands:
        assert command in text
    assert "<note.md>" in text
    assert "<export>.manifest.json" in text


def test_v0_7_7_friction_doc_keeps_no_write_boundaries() -> None:
    doc = Path("docs/V0_7_7_DOGFOODING_FRICTION_FIXES.md")
    text = doc.read_text(encoding="utf-8")
    lowered = text.lower()

    assert doc.exists()
    assert "Dogfooding path" in text
    assert "Friction fixed" in text
    assert "No formal Obsidian notes are written" in text
    assert "No `.env`, real LLM" in text
    for claim in ["rag is implemented", "plugin is implemented", "real llm is enabled"]:
        assert claim not in lowered


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


def test_obsidian_scan_include_exclude_scope_rules(tmp_path: Path) -> None:
    """v0.7.3: include/exclude 是 dry-run 范围边界，不应靠用户肉眼过滤输出。"""
    vault, _note, cfg = _make_obsidian_vault(tmp_path)

    include_res = runner.invoke(
        app,
        ["obsidian", "scan", "--config", str(cfg), "--vault", str(vault), "--include", "03-Projects", "--json"],
    )
    assert include_res.exit_code == 0, include_res.output
    include_titles = [item["title"] for item in json.loads(include_res.output)["notes"]]
    assert include_titles == ["Project Alpha"]

    exclude_res = runner.invoke(
        app,
        ["obsidian", "scan", "--config", str(cfg), "--vault", str(vault), "--exclude", "03-Projects", "--json"],
    )
    assert exclude_res.exit_code == 0, exclude_res.output
    exclude_titles = [item["title"] for item in json.loads(exclude_res.output)["notes"]]
    assert "Agent Runtime" in exclude_titles
    assert "Project Alpha" not in exclude_titles


def test_obsidian_default_excludes_runtime_dirs(tmp_path: Path) -> None:
    """默认排除 .obsidian/.git/.mindforge，避免把机器目录当用户知识扫描。"""
    vault, _note, cfg = _make_obsidian_vault(tmp_path)
    (vault / ".obsidian" / "Plugin Note.md").write_text("# Plugin Note\n", encoding="utf-8")
    (vault / ".git").mkdir()
    (vault / ".git" / "Git Note.md").write_text("# Git Note\n", encoding="utf-8")
    (vault / ".mindforge" / "Runtime Note.md").write_text("# Runtime Note\n", encoding="utf-8")

    res = runner.invoke(app, ["obsidian", "scan", "--config", str(cfg), "--vault", str(vault), "--json"])

    assert res.exit_code == 0, res.output
    titles = [item["title"] for item in json.loads(res.output)["notes"]]
    assert "Plugin Note" not in titles
    assert "Git Note" not in titles
    assert "Runtime Note" not in titles
    assert "Agent Runtime" in titles


def test_obsidian_scope_handles_chinese_and_space_paths(tmp_path: Path) -> None:
    """中文和空格路径是个人 vault 常态，scope 规则不能只适配 demo 英文路径。"""
    vault, _note, cfg = _make_obsidian_vault(tmp_path)
    folder = vault / "02-Knowledge" / "中文 资料"
    folder.mkdir()
    note = folder / "学习 笔记.md"
    note.write_text("---\ntitle: 学习 笔记\n---\n\n# 学习\n", encoding="utf-8")

    res = runner.invoke(
        app,
        ["obsidian", "scan", "--config", str(cfg), "--vault", str(vault), "--include", "02-Knowledge/中文 资料"],
    )

    assert res.exit_code == 0, res.output
    assert "学习 笔记" in res.output


def test_obsidian_stage_respects_scope_without_write(tmp_path: Path) -> None:
    """stage 必须复用 scan scope；排除的 source 只能 skipped，不能写 export。"""
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
            str(note),
            "--exclude",
            "02-Knowledge",
        ],
    )

    assert res.exit_code == 0, res.output
    assert "include/exclude scope" in res.output
    assert "skipped" in res.output
    assert note.read_text(encoding="utf-8") == before
    assert not (vault / "90-System" / "MindForge" / "Staging").exists()


def test_obsidian_doctor_reports_scope_and_staged_safety(tmp_path: Path) -> None:
    """doctor plus 要说明 scope、安全写入边界，并识别 staged export 目录。"""
    vault, _note, cfg = _make_obsidian_vault(tmp_path)
    staged = tmp_path / ".mindforge" / "staged" / "obsidian"
    staged.mkdir(parents=True)
    (staged / "candidate.md").write_text("# staged\n", encoding="utf-8")

    res = runner.invoke(app, ["obsidian", "doctor", "--config", str(cfg), "--vault", str(vault)])

    assert res.exit_code == 0, res.output
    assert "formal note writes" in res.output
    assert "include rules" in res.output
    assert "exclude rules" in res.output
    assert "staged export dir" in res.output
    assert "files=1" in res.output
    assert "RAG" not in res.output
    assert "plugin" not in res.output.lower()


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
