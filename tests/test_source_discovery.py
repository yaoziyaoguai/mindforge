"""Source discovery tests for watch/import ingestion.

source_discovery 只负责安全枚举 file/folder 并把文件交给现有 adapter 解析，
不复制 source，不重写 Adapter 抽象，也不读取/展示 source 正文。
"""

from __future__ import annotations

from pathlib import Path

import yaml

from mindforge.app_context import load_app_config
from mindforge.source_discovery import (
    discover_source_results,
    enumerate_supported_source_files,
)


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


def test_enumerate_folder_recursively_finds_supported_files_with_explicit_policy(
    tmp_path: Path,
) -> None:
    cfg = load_app_config(_write_config(tmp_path), cwd=tmp_path)
    root = tmp_path / "folder"
    top = root / "top.md"
    nested = root / "nested" / "deep.md"
    top.parent.mkdir(parents=True)
    nested.parent.mkdir(parents=True)
    top.write_text("# top\n", encoding="utf-8")
    nested.write_text("# deep\n", encoding="utf-8")

    scan = enumerate_supported_source_files(cfg, root)

    assert scan.recursive is True
    assert [file.path for file in scan.candidates] == [nested.resolve(), top.resolve()]
    assert scan.skipped == ()


def test_enumerate_uses_same_policy_for_import_once_folder_targets(tmp_path: Path) -> None:
    cfg = load_app_config(_write_config(tmp_path), cwd=tmp_path)
    root = tmp_path / "folder"
    nested = root / "nested" / "import-once.md"
    nested.parent.mkdir(parents=True)
    nested.write_text("# import once\n", encoding="utf-8")

    results = list(discover_source_results(cfg, root))

    assert [result.path for result in results] == [nested.resolve()]


def test_enumerate_skips_runtime_hidden_temp_unsupported_and_generated_outputs(
    tmp_path: Path,
) -> None:
    cfg_path = _write_config(tmp_path)
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    raw["vault"]["cards_dir"] = "GeneratedCards"
    cfg_path.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")
    cfg = load_app_config(cfg_path, cwd=tmp_path)
    root = tmp_path / "folder"
    keep = root / "keep.md"
    skipped_paths = [
        root / ".git" / "ignored.md",
        root / "node_modules" / "ignored.md",
        root / ".venv" / "ignored.md",
        root / "GeneratedCards" / "ignored.md",
        root / ".hidden-dir" / "ignored.md",
        root / ".hidden.md",
        root / "~$draft.md",
        root / "swap.swp",
        root / "temp.tmp",
        root / "unsupported.csv",
    ]
    keep.parent.mkdir(parents=True)
    keep.write_text("# keep\n", encoding="utf-8")
    for path in skipped_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# ignored\n", encoding="utf-8")

    scan = enumerate_supported_source_files(cfg, root)
    reasons = {item.path.name: item.reason for item in scan.skipped if item.path.is_file()}
    dir_reasons = {item.path.name: item.reason for item in scan.skipped if item.path.is_dir()}

    assert [file.path for file in scan.candidates] == [keep.resolve()]
    assert dir_reasons[".git"] == "ignored_directory"
    assert dir_reasons["node_modules"] == "ignored_directory"
    assert dir_reasons[".venv"] == "ignored_directory"
    assert dir_reasons["GeneratedCards"] == "generated_output"
    assert dir_reasons[".hidden-dir"] == "ignored_directory"
    assert reasons[".hidden.md"] == "hidden_file"
    assert reasons["~$draft.md"] == "temp_file"
    assert reasons["swap.swp"] == "temp_file"
    assert reasons["temp.tmp"] == "temp_file"
    assert reasons["unsupported.csv"] == "unsupported_extension"


def test_enumerate_scanner_boundary_returns_candidates_not_source_documents(
    tmp_path: Path,
) -> None:
    """folder scanner 只发现文件，不越过 parser boundary 直接生成 SourceDocument。

    中文学习型说明：递归扫描只能回答“哪些文件可尝试解析、哪些被跳过以及原因”。
    SourceDocument 必须由 adapter/parser 负责生成，Knowledge Card 必须由后续
    process pipeline 负责生成，避免 folder watch 变成第二套 ingestion 逻辑。
    """

    cfg = load_app_config(_write_config(tmp_path), cwd=tmp_path)
    root = tmp_path / "folder"
    note = root / "note.md"
    note.parent.mkdir(parents=True)
    note.write_text("# note\n", encoding="utf-8")

    scan = enumerate_supported_source_files(cfg, root)

    assert scan.candidates[0].path == note.resolve()
    assert not hasattr(scan.candidates[0], "document")
    assert list(discover_source_results(cfg, root))[0].document is not None


def test_supported_status_matches_actual_active_parser_registry(tmp_path: Path) -> None:
    cfg = load_app_config(_write_config(tmp_path), cwd=tmp_path)
    root = tmp_path / "folder"
    markdown = root / "note.md"
    text = root / "note.txt"
    html = root / "note.html"
    json_file = root / "note.json"
    csv_file = root / "note.csv"
    for path in (markdown, text, html, json_file, csv_file):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("body\n", encoding="utf-8")

    scan = enumerate_supported_source_files(cfg, root)
    skipped_by_name = {item.path.name: item.reason for item in scan.skipped}

    assert [candidate.path.name for candidate in scan.candidates] == ["note.md"]
    assert skipped_by_name["note.txt"] == "unsupported_extension"
    assert skipped_by_name["note.html"] == "unsupported_extension"
    assert skipped_by_name["note.json"] == "unsupported_extension"
    assert skipped_by_name["note.csv"] == "unsupported_extension"
