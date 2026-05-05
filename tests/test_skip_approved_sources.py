"""P0 regression tests for stale approved sources still left in Inbox."""

from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from mindforge.cli import app

runner = CliRunner()


def _write_config(tmp_path: Path) -> tuple[Path, Path]:
    vault = tmp_path / "vault"
    (vault / "00-Inbox" / "ManualNotes").mkdir(parents=True)
    (vault / "20-Knowledge-Cards" / "agent-runtime").mkdir(parents=True)
    cfg = tmp_path / "mindforge.yaml"
    cfg.write_text(
        yaml.safe_dump(
            {
                "version": 0.7,
                "vault": {
                    "root": str(vault),
                    "inbox_root": "00-Inbox",
                    "cards_dir": "20-Knowledge-Cards",
                    "archive_dir": "90-Archive/Skipped",
                },
                "sources": {
                    "enabled": ["plain_markdown"],
                    "registry": {
                        "plain_markdown": {
                            "adapter": "PlainMarkdownAdapter",
                            "inbox_subdir": "ManualNotes",
                            "file_glob": "*.md",
                            "enabled": True,
                        }
                    },
                },
                "state": {
                    "workdir": ".mindforge",
                    "state_file": "state.json",
                    "runs_dir": "runs",
                    "index_file": "index.jsonl",
                    "backup_state": True,
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
                    "models": {
                        "fake_alias": {
                            "provider": "fake",
                            "type": "fake",
                            "base_url": "fake://",
                            "model": "fake",
                            "timeout_seconds": 5,
                            "max_retries": 0,
                        }
                    },
                },
                "prompts": {
                    "triage_version": "v1",
                    "distill_version": "v1",
                    "link_suggestion_version": "v1",
                    "review_questions_version": "v1",
                    "action_extraction_version": "v1",
                },
                "logging": {"level": "INFO", "file": str(tmp_path / "mf.log")},
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return cfg, vault


def _write_source(vault: Path, name: str) -> Path:
    path = vault / "00-Inbox" / "ManualNotes" / name
    path.write_text(f"# {name}\n\nbody\n", encoding="utf-8")
    return path


def _write_approved_card(vault: Path, source: Path) -> Path:
    card = vault / "20-Knowledge-Cards" / "agent-runtime" / "20260505--first-note.md"
    card.write_text(
        f"""---
id: first-note
title: first-note
status: human_approved
track: agent-runtime
source_id: source-first
source_type: plain_markdown
adapter_name: PlainMarkdownAdapter
source_path: "{source}"
source_title: first-note
source_archive_path: ""
source_missing: false
profile: fake
---

## AI Summary

approved old card
""",
        encoding="utf-8",
    )
    return card


def _write_approved_card_with_vault_relative_source(vault: Path, source: Path) -> Path:
    card = vault / "20-Knowledge-Cards" / "agent-runtime" / "20260505--relative.md"
    card.write_text(
        f"""---
id: relative-note
title: relative-note
status: human_approved
track: agent-runtime
source_type: plain_markdown
adapter_name: PlainMarkdownAdapter
source_path: "{source.relative_to(vault).as_posix()}"
source_title: relative-note
profile: fake
---

## AI Summary

approved card with vault-relative provenance
""",
        encoding="utf-8",
    )
    return card


def test_process_skips_inbox_source_already_referenced_by_human_approved_card(
    tmp_path: Path,
) -> None:
    cfg, vault = _write_config(tmp_path)
    old_source = _write_source(vault, "first-note.md")
    _write_approved_card(vault, old_source)
    _write_source(vault, "third-note.md")

    result = runner.invoke(app, ["process", "--config", str(cfg), "--profile", "fake", "--limit", "1"])

    assert result.exit_code == 0, result.output
    assert "already_approved" in result.output
    assert "third-note.md" in result.output
    assert not list((vault / "20-Knowledge-Cards").rglob("*.conflict.md"))
    cards = list((vault / "20-Knowledge-Cards").rglob("*.md"))
    assert len(cards) == 2
    assert old_source.exists(), "历史 source 只能被跳过，不能默认移动或删除"


def test_process_skips_approved_source_when_card_kept_vault_relative_path(
    tmp_path: Path,
) -> None:
    cfg, vault = _write_config(tmp_path)
    old_source = _write_source(vault, "first-note.md")
    _write_approved_card_with_vault_relative_source(vault, old_source)
    _write_source(vault, "third-note.md")

    result = runner.invoke(app, ["process", "--config", str(cfg), "--profile", "fake", "--limit", "1"])

    assert result.exit_code == 0, result.output
    assert "already_approved" in result.output
    assert "third-note.md" in result.output
    assert not list((vault / "20-Knowledge-Cards").rglob("*.conflict.md"))
