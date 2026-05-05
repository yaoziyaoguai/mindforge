"""Source discovery tests for watch/import ingestion.

source_discovery 只负责安全枚举 file/folder 并把文件交给现有 adapter 解析，
不复制 source，不重写 Adapter 抽象，也不读取/展示 source 正文。
"""

from __future__ import annotations

from pathlib import Path

import yaml

from mindforge.app_context import load_app_config
from mindforge.source_discovery import discover_source_results


def _write_config(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    (vault / "00-Inbox" / "ManualNotes").mkdir(parents=True)
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
    return cfg


def test_discover_file_uses_existing_adapter_without_copying_to_inbox(tmp_path: Path) -> None:
    cfg = load_app_config(_write_config(tmp_path), cwd=tmp_path)
    external = tmp_path / "external.md"
    external.write_text("# External\n\nbody\n", encoding="utf-8")

    results = list(discover_source_results(cfg, external))

    assert len(results) == 1
    assert results[0].ok
    assert results[0].source_type == "plain_markdown"
    assert results[0].adapter_name == "PlainMarkdownAdapter"
    assert results[0].document is not None
    assert results[0].document.source_path == str(external.resolve())
    assert not (cfg.vault.inbox_path / "ManualNotes" / external.name).exists()


def test_discover_folder_skips_derived_and_hidden_dirs(tmp_path: Path) -> None:
    cfg = load_app_config(_write_config(tmp_path), cwd=tmp_path)
    root = tmp_path / "folder"
    keep = root / "keep.md"
    skip_paths = [
        root / ".git" / "ignored.md",
        root / ".hidden" / "ignored.md",
        root / ".mindforge" / "ignored.md",
        root / "_processed" / "ignored.md",
        root / "_ignored" / "ignored.md",
        root / "_rejected" / "ignored.md",
        root / "20-Knowledge-Cards" / "ignored.md",
        root / "runs" / "ignored.md",
        root / "index" / "ignored.md",
        root / "cache" / "ignored.md",
        root / "logs" / "ignored.md",
    ]
    keep.parent.mkdir(parents=True)
    keep.write_text("# keep\n", encoding="utf-8")
    for path in skip_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# ignored\n", encoding="utf-8")

    results = list(discover_source_results(cfg, root))

    assert [result.path.name for result in results] == ["keep.md"]


def test_discover_folder_dedupes_overlapping_paths(tmp_path: Path) -> None:
    cfg = load_app_config(_write_config(tmp_path), cwd=tmp_path)
    root = tmp_path / "folder"
    note = root / "nested" / "note.md"
    note.parent.mkdir(parents=True)
    note.write_text("# note\n", encoding="utf-8")

    results = list(discover_source_results(cfg, [root, note]))

    assert [result.path.resolve() for result in results] == [note.resolve()]
