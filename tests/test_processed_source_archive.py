"""Processed source archive behavior tests.

产品语义：Source 是原始证据，Card 是加工结果。process/ai_draft 阶段不能移动
source；只有显式 approve 成功后，才把 vault inbox 内的原始 source 移到
``00-Inbox/_processed/<filename>``，并在 card frontmatter 保留 provenance。

v0.7.21 起归档路径扁平化：不再使用 adapter inbox_subdir 作为归档子目录。
"""

from __future__ import annotations

from pathlib import Path

import yaml

from mindforge.approval_service import approve_explicit_card
from mindforge.config import load_mindforge_config
from mindforge.scanner import Scanner


def _write_config(tmp_path: Path) -> tuple[Path, Path, Path]:
    vault = tmp_path / "vault"
    inbox = vault / "00-Inbox"
    for subdir in ("ManualNotes", "Cubox", "WebClips"):
        (inbox / subdir).mkdir(parents=True)
    cards = vault / "20-Knowledge-Cards"
    cards.mkdir(parents=True)

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
                },
                "sources": {
                    "enabled": ["plain_markdown", "cubox_markdown", "webclip_markdown"],
                    "registry": {
                        "plain_markdown": {
                            "adapter": "PlainMarkdownAdapter",
                            "inbox_subdir": "ManualNotes",
                            "file_glob": "*.md",
                            "enabled": True,
                        },
                        "cubox_markdown": {
                            "adapter": "CuboxMarkdownAdapter",
                            "inbox_subdir": "Cubox",
                            "file_glob": "*.md",
                            "enabled": True,
                        },
                        "webclip_markdown": {
                            "adapter": "WebClipMarkdownAdapter",
                            "inbox_subdir": "WebClips",
                            "file_glob": "*.md",
                            "enabled": True,
                        },
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
    return cfg_path, vault, cards


def _write_card(cards: Path, source: Path, *, source_type: str = "plain_markdown") -> Path:
    card = cards / f"{source.stem}.md"
    card.write_text(
        f"""---
id: card-{source.stem}
title: Source {source.stem}
status: ai_draft
track: agent-runtime
strategy_id: five_stage
strategy_version: 0.10.0
schema_version: "1"
source_id: source-{source.stem}
source_type: {source_type}
adapter_name: TestAdapter
source_path: "{source}"
source_title: "{source.stem}"
source_content_hash: sha256:test-source-hash
source_archive_path: ""
source_missing: false
prompt_versions:
  triage: v1
  distill: v1
  link_suggestion: v1
  review_questions: v1
  action_extraction: v1
profile: fake
stage_models:
  triage: {{ alias: fake, provider: fake, model: fake }}
run_id: run-test
---

## AI Summary

summary only
""",
        encoding="utf-8",
    )
    return card


def test_approve_moves_pending_source_to_processed_archive_and_updates_card(tmp_path: Path) -> None:
    cfg_path, vault, cards = _write_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    source = vault / "00-Inbox" / "ManualNotes" / "first-note.md"
    source.write_text("original evidence", encoding="utf-8")
    card = _write_card(cards, source)

    result = approve_explicit_card(cfg, card)

    assert result.error is None
    # v0.7.21 起归档路径扁平化：不再使用 ManualNotes bucket
    archived = vault / "00-Inbox" / "_processed" / "first-note.md"
    assert archived.exists()
    assert archived.read_text(encoding="utf-8") == "original evidence"
    assert not source.exists()
    card_text = card.read_text(encoding="utf-8")
    assert "status: human_approved" in card_text
    # 中文学习型说明：approve 只完成 ai_draft -> human_approved 的人工闸门
    # 和 source archive 回写，不能丢掉生成 provenance；这些字段是未来
    # Web/CLI 展示"这张卡如何生成"的依据。
    assert "strategy_id: five_stage" in card_text
    assert "source_content_hash: sha256:test-source-hash" in card_text
    assert "prompt_versions:" in card_text
    assert "action_extraction: v1" in card_text
    assert "stage_models:" in card_text
    assert "run_id: run-test" in card_text
    assert f'source_path: "{source}"' in card_text or f"source_path: {source}" in card_text
    assert "source_archive_path: 00-Inbox/_processed/first-note.md" in card_text
    assert "source_missing: false" in card_text


def test_scanner_skips_processed_archive_sources(tmp_path: Path) -> None:
    cfg_path, vault, _cards = _write_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    pending = vault / "00-Inbox" / "ManualNotes" / "pending.md"
    # v0.7.21：归档路径扁平化到 _processed/ 下
    processed = vault / "00-Inbox" / "_processed" / "done.md"
    pending.write_text("# pending\n", encoding="utf-8")
    processed.parent.mkdir(parents=True)
    processed.write_text("# processed\n", encoding="utf-8")

    results = list(Scanner(cfg).iter_results())

    assert [result.path.name for result in results] == ["pending.md"]


def test_archive_uses_conflict_safe_name_without_overwriting(tmp_path: Path) -> None:
    cfg_path, vault, cards = _write_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    source = vault / "00-Inbox" / "ManualNotes" / "first-note.md"
    source.write_text("new evidence", encoding="utf-8")
    # v0.7.21：归档路径扁平化
    existing = vault / "00-Inbox" / "_processed" / "first-note.md"
    existing.parent.mkdir(parents=True)
    existing.write_text("old evidence", encoding="utf-8")
    card = _write_card(cards, source)

    result = approve_explicit_card(cfg, card)

    assert result.error is None
    assert existing.read_text(encoding="utf-8") == "old evidence"
    archived = next(
        path
        for path in existing.parent.glob("first-note--*.md")
        if path.read_text(encoding="utf-8") == "new evidence"
    )
    assert f"source_archive_path: {archived.relative_to(vault).as_posix()}" in card.read_text(
        encoding="utf-8"
    )


def test_external_and_missing_sources_are_not_moved_but_provenance_is_visible(tmp_path: Path) -> None:
    cfg_path, _vault, cards = _write_config(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    external = tmp_path / "outside.md"
    external.write_text("external source", encoding="utf-8")
    external_card = _write_card(cards, external)
    missing = tmp_path / "missing.md"
    missing_card = _write_card(cards, missing)

    external_result = approve_explicit_card(cfg, external_card)
    missing_result = approve_explicit_card(cfg, missing_card)

    assert external_result.error is None
    assert missing_result.error is None
    assert external.exists()
    external_text = external_card.read_text(encoding="utf-8")
    missing_text = missing_card.read_text(encoding="utf-8")
    assert "source_external: true" in external_text
    assert "source_archive_path: ''" in external_text or "source_archive_path: \"\"" in external_text
    assert "source_missing: true" in missing_text
    assert "source_archive_path: ''" in missing_text or "source_archive_path: \"\"" in missing_text
