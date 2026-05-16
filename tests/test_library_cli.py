"""Library inventory CLI tests.

这些测试用临时 vault 验证知识库总览只展示安全 metadata。Library 入口回答
"我有哪些卡片"，但默认不读取 source 正文，也不展示 card body；正文必须由
用户显式 ``--show-content`` 才能看到。
"""

from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from mindforge.cli import app

runner = CliRunner()


def _write_config(tmp_path: Path) -> tuple[Path, Path, Path]:
    vault = tmp_path / "vault"
    inbox = vault / "00-Inbox" / "ManualNotes"
    cards = vault / "20-Knowledge-Cards" / "agent-runtime"
    inbox.mkdir(parents=True)
    cards.mkdir(parents=True)
    source = inbox / "first-note.md"
    source.write_text("SOURCE_BODY_MUST_NOT_LEAK\n", encoding="utf-8")

    cfg_path = tmp_path / "mindforge.yaml"
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "version": 0.7,
                "vault": {
                    "root": str(vault),
                    "inbox_root": "00-Inbox",
                    "cards_dir": "20-Knowledge-Cards",
                    "archive_dir": "90-Archive/Skipped",
                    "projects_dir": "30-Projects",
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
                    "workdir": str(tmp_path / ".mindforge"),
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
    return cfg_path, vault, source


def _write_card(
    cards_root: Path,
    name: str,
    *,
    status: str,
    source_path: Path,
    source_missing: bool = False,
) -> Path:
    card = cards_root / f"{name}.md"
    card.write_text(
        f"""---
id: {name}
title: {name.replace("-", " ").title()}
status: {status}
track: agent-runtime
projects:
  - local-dogfood
tags:
  - library
source_id: source-{name}
source_type: plain_markdown
adapter_name: PlainMarkdownAdapter
source_path: "{source_path}"
source_title: First Note
source_archive_path: ""
source_missing: {str(source_missing).lower()}
value_score: 8
created_at: 2026-05-05T10:00:00+08:00
profile: fake
stage_models:
  distill: {{ alias: fake_alias, provider: fake, model: fake }}
---

## AI Summary

CARD_BODY_SENTINEL_{name}
""",
        encoding="utf-8",
    )
    return card


def test_library_stats_counts_status_track_and_fake_provider(tmp_path: Path) -> None:
    cfg_path, vault, source = _write_config(tmp_path)
    cards_root = vault / "20-Knowledge-Cards" / "agent-runtime"
    _write_card(cards_root, "draft-one", status="ai_draft", source_path=source)
    _write_card(cards_root, "approved-one", status="human_approved", source_path=source)

    result = runner.invoke(app, ["library", "stats", "--config", str(cfg_path)])

    assert result.exit_code == 0, result.output
    assert str(vault) in result.output
    assert "total cards" in result.output
    assert "ai_draft=1" in result.output
    assert "human_approved=1" in result.output
    assert "agent-runtime=2" in result.output
    assert "fake=2" in result.output
    assert "SOURCE_BODY_MUST_NOT_LEAK" not in result.output


def test_library_list_and_show_default_are_metadata_only(tmp_path: Path) -> None:
    cfg_path, vault, source = _write_config(tmp_path)
    cards_root = vault / "20-Knowledge-Cards" / "agent-runtime"
    card = _write_card(cards_root, "draft-one", status="human_approved", source_path=source)

    listed = runner.invoke(app, ["library", "list", "--config", str(cfg_path)])
    shown = runner.invoke(
        app,
        ["library", "show", "20-Knowledge-Cards/agent-runtime/draft-one.md", "--config", str(cfg_path)],
    )
    shown_content = runner.invoke(
        app,
        ["library", "show", str(card), "--config", str(cfg_path), "--show-content"],
    )

    assert listed.exit_code == 0, listed.output
    assert "Draft One" in listed.output
    assert "plain_markdown" in listed.output
    assert "PlainMarkdownAdapter" in listed.output
    assert "source_missing=no" in listed.output
    assert "SOURCE_BODY_MUST_NOT_LEAK" not in listed.output
    assert "CARD_BODY_SENTINEL" not in listed.output

    assert shown.exit_code == 0, shown.output
    assert "human_approved：显式 approve 后进入正式知识库" in shown.output
    assert "offline LLM test double" in shown.output
    assert "CARD_BODY_SENTINEL" not in shown.output

    assert shown_content.exit_code == 0, shown_content.output
    assert "CARD_BODY_SENTINEL_draft-one" in shown_content.output


def test_library_show_reports_missing_source_without_reading_source_body(tmp_path: Path) -> None:
    cfg_path, vault, _source = _write_config(tmp_path)
    cards_root = vault / "20-Knowledge-Cards" / "agent-runtime"
    missing = vault / "00-Inbox" / "ManualNotes" / "missing.md"
    _write_card(
        cards_root,
        "missing-source",
        status="human_approved",
        source_path=missing,
        source_missing=True,
    )

    result = runner.invoke(
        app,
        ["library", "show", "missing-source", "--config", str(cfg_path)],
    )

    assert result.exit_code == 0, result.output
    assert "source_missing=yes" in result.output
    assert str(missing) in result.output
