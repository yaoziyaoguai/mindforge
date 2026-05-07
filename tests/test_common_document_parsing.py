"""通用文档 parser registry 的契约测试。

中文学习型说明：folder scanner 只能发现候选文件；真正的格式解析必须停留在
parser/adapter 边界。这里用真实临时文件验证 P0 常见格式能产出统一
``SourceDocument``，P1 未实现格式则明确 unsupported / missing optional
dependency，不伪装成功。
"""

from __future__ import annotations

from pathlib import Path

import yaml

from mindforge.app_context import load_app_config
from mindforge.source_discovery import discover_source_results, enumerate_supported_source_files


def _write_config(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    (vault / "00-Inbox" / "Documents").mkdir(parents=True)
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
                    "enabled": ["common_document"],
                    "registry": {
                        "common_document": {
                            "adapter": "CommonDocumentAdapter",
                            "inbox_subdir": "Documents",
                            "file_glob": "*",
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


def test_p0_common_documents_parse_to_source_document(tmp_path: Path) -> None:
    cfg = load_app_config(_write_config(tmp_path), cwd=tmp_path)
    root = tmp_path / "docs"
    samples = {
        "note.md": "# Markdown Title\n\nbody",
        "note.markdown": "# Markdown Long\n\nbody",
        "note.txt": "Plain text title\n\nbody",
        "note.html": "<html><head><title>HTML Title</title></head><body><h1>Hello</h1><p>body</p></body></html>",
        "note.htm": "<h1>HTM Title</h1><p>body</p>",
        "note.json": '{"title": "JSON Title", "items": [{"body": "alpha"}]}',
        "note.csv": "title,body\nCSV Title,alpha\n",
    }
    for name, text in samples.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    results = list(discover_source_results(cfg, root))

    assert [result.path.name for result in results] == sorted(samples)
    assert all(result.ok for result in results)
    assert {result.document.source_type for result in results if result.document} == {
        "common_document"
    }
    assert all(result.document and result.document.content_hash.startswith("sha256:") for result in results)


def test_tsv_and_xml_are_lightweight_supported_p1_formats(tmp_path: Path) -> None:
    cfg = load_app_config(_write_config(tmp_path), cwd=tmp_path)
    root = tmp_path / "docs"
    (root / "table.tsv").parent.mkdir(parents=True)
    (root / "table.tsv").write_text("title\tbody\nTSV Title\talpha\n", encoding="utf-8")
    (root / "feed.xml").write_text("<root><title>XML Title</title><body>alpha</body></root>", encoding="utf-8")

    results = list(discover_source_results(cfg, root))

    assert [result.path.name for result in results] == ["feed.xml", "table.tsv"]
    assert all(result.ok for result in results)


def test_heavy_or_future_formats_are_explicitly_unsupported_or_optional(tmp_path: Path) -> None:
    cfg = load_app_config(_write_config(tmp_path), cwd=tmp_path)
    root = tmp_path / "docs"
    for name in ("slides.pptx", "sheet.xlsx", "book.epub", "note.rtf", "message.eml", "todo.org"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"not a real binary fixture")

    scan = enumerate_supported_source_files(cfg, root)
    skipped = {item.path.name: item.reason for item in scan.skipped}

    assert scan.candidates == ()
    assert skipped == {
        "book.epub": "missing_optional_dependency",
        "message.eml": "unsupported_extension",
        "note.rtf": "missing_optional_dependency",
        "sheet.xlsx": "missing_optional_dependency",
        "slides.pptx": "missing_optional_dependency",
        "todo.org": "unsupported_extension",
    }


def test_url_shortcut_files_do_not_fetch_network(tmp_path: Path) -> None:
    cfg = load_app_config(_write_config(tmp_path), cwd=tmp_path)
    root = tmp_path / "docs"
    (root / "remote.url").parent.mkdir(parents=True)
    (root / "remote.url").write_text("[InternetShortcut]\nURL=https://example.invalid/private\n", encoding="utf-8")
    (root / "remote.webloc").write_text(
        "<?xml version='1.0'?><plist><dict><key>URL</key><string>https://example.invalid/private</string></dict></plist>",
        encoding="utf-8",
    )

    results = list(discover_source_results(cfg, root))

    assert [result.path.name for result in results] == ["remote.url", "remote.webloc"]
    assert all(result.ok for result in results)
    assert all(result.document and "remote_fetch_enabled" not in result.document.metadata for result in results)
