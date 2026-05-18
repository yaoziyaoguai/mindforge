"""Readable document source pipeline regression tests.

中文学习型说明：这些测试覆盖 fresh-clone 风格的最小用户配置，而不是手写
完整 ``sources`` 段。目标是守住产品承诺：用户从 Web/CLI import 本地可读文档
时，source discovery 必须走默认 readable adapter registry，后续 pipeline 只生成
``ai_draft``，不会自动 approve，也不会调用真实 LLM/API。
"""

from __future__ import annotations

from pathlib import Path

import yaml

from mindforge.app_context import load_app_config
from mindforge.cards import read_card_frontmatter
from mindforge.ingestion_service import import_sources
from mindforge.source_discovery import discover_source_results, enumerate_supported_source_files
from mindforge.sources.adapter_result import AdapterResult
from mindforge.sources.base import SourceDocument, compute_content_hash


def _write_fresh_clone_config(tmp_path: Path) -> tuple[Path, Path]:
    """写入 fresh clone 风格最小配置；sources 由 internal defaults 提供。"""
    vault = tmp_path / "vault"
    (vault / "00-Inbox").mkdir(parents=True)
    cfg = tmp_path / "configs" / "mindforge.yaml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(
        yaml.safe_dump(
            {
                "version": 0.7,
                "vault": {"root": "vault"},
                "llm": {
                    "active": "fake",
                    "providers": {
                        "fake": {
                            "type": "fake",
                            "purpose": "offline_demo_ci_deterministic_tests",
                        }
                    },
                },
                "telemetry": {"enabled": True, "local_only": True},
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return cfg, vault


def _card_paths(vault: Path) -> list[Path]:
    return sorted((vault / "20-Knowledge-Cards").rglob("*.md"))


def _document(path: Path, *, source_type: str, adapter_name: str, raw_text: str) -> SourceDocument:
    return SourceDocument(
        source_id=f"sha1:{path.stem}-{source_type}",
        source_type=source_type,  # type: ignore[arg-type]
        source_path=str(path.resolve()),
        title=path.stem,
        raw_text=raw_text,
        metadata={"synthetic": True},
        content_hash=compute_content_hash(raw_text, {"source_type": source_type, "path": str(path)}),
        adapter_name=adapter_name,
    )


def test_fresh_clone_defaults_include_readable_document_sources(tmp_path: Path) -> None:
    """默认运行配置必须包含 readable document source registry。"""
    cfg_path, _vault = _write_fresh_clone_config(tmp_path)
    cfg = load_app_config(cfg_path, cwd=tmp_path)

    entries = {entry.source_type: entry for entry in cfg.sources.active_entries()}

    assert entries["plain_markdown"].adapter == "PlainMarkdownAdapter"
    assert entries["txt"].adapter == "TxtAdapter"
    assert entries["html"].adapter == "HtmlAdapter"
    assert entries["pdf"].adapter == "PdfTextAdapter"
    assert entries["docx"].adapter == "DocxTextAdapter"


def test_fresh_clone_imports_txt_and_html_as_ai_drafts(tmp_path: Path) -> None:
    """TXT / local HTML 走真实 import/process pipeline，并只生成 ai_draft。"""
    cfg_path, vault = _write_fresh_clone_config(tmp_path)
    cfg = load_app_config(cfg_path, cwd=tmp_path)
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "note.txt").write_text("TXT Source Title\n\nUseful body.", encoding="utf-8")
    (sources / "page.html").write_text(
        "<html><head><title>HTML Source</title></head><body><h1>HTML Source</h1><p>Useful body.</p></body></html>",
        encoding="utf-8",
    )

    summary = import_sources(cfg, sources)

    assert summary.counts["processed"] == 2
    cards = _card_paths(vault)
    assert len(cards) == 2
    frontmatters = [read_card_frontmatter(path) for path in cards]
    assert {fm["status"] for fm in frontmatters} == {"ai_draft"}
    assert {fm["source_type"] for fm in frontmatters} == {"txt", "html"}
    assert {fm["adapter_name"] for fm in frontmatters} == {"TxtAdapter", "HtmlAdapter"}


def test_pdf_docx_adapter_result_dispatch_reaches_import_pipeline(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """PDF/DOCX 的 v0.2 AdapterResult 能进入主 import pipeline。

    中文学习型说明：这里 mock 的是 adapter 输出，而不是 processor。这样测试的
    重点落在 source registry → AdapterResult → ScanResult → process pipeline 的
    架构边界；PDF/DOCX 真实解析能力由 adapters/ 下的单元与 optional smoke 守护。
    """
    cfg_path, vault = _write_fresh_clone_config(tmp_path)
    cfg = load_app_config(cfg_path, cwd=tmp_path)
    sources = tmp_path / "sources"
    sources.mkdir()
    pdf = sources / "paper.pdf"
    docx = sources / "brief.docx"
    pdf.write_bytes(b"%PDF-1.4 synthetic")
    docx.write_bytes(b"synthetic docx placeholder")

    from mindforge.sources.docx_adapter import DocxTextAdapter
    from mindforge.sources.pdf_adapter import PdfTextAdapter

    def fake_pdf_load(self: PdfTextAdapter, path: str) -> AdapterResult:
        source = Path(path)
        return AdapterResult(
            status="loaded",
            document=_document(
                source,
                source_type="pdf",
                adapter_name=self.name,
                raw_text="Synthetic PDF body.",
            ),
        )

    def fake_docx_load(self: DocxTextAdapter, path: str) -> AdapterResult:
        source = Path(path)
        return AdapterResult(
            status="loaded",
            document=_document(
                source,
                source_type="docx",
                adapter_name=self.name,
                raw_text="Synthetic DOCX body.",
            ),
        )

    monkeypatch.setattr(PdfTextAdapter, "load", fake_pdf_load)
    monkeypatch.setattr(DocxTextAdapter, "load", fake_docx_load)

    summary = import_sources(cfg, sources)

    assert summary.counts["processed"] == 2
    frontmatters = [read_card_frontmatter(path) for path in _card_paths(vault)]
    assert {fm["source_type"] for fm in frontmatters} == {"pdf", "docx"}
    assert {fm["adapter_name"] for fm in frontmatters} == {"PdfTextAdapter", "DocxTextAdapter"}


def test_legacy_doc_is_friendly_unsupported_without_processing(tmp_path: Path) -> None:
    """Legacy .doc 友好 unsupported，不执行本地文件、不生成 card。"""
    cfg_path, vault = _write_fresh_clone_config(tmp_path)
    cfg = load_app_config(cfg_path, cwd=tmp_path)
    legacy = tmp_path / "legacy.doc"
    legacy.write_bytes(b"legacy ole placeholder")

    scan = enumerate_supported_source_files(cfg, legacy)
    summary = import_sources(cfg, legacy)
    results = list(discover_source_results(cfg, legacy))

    assert scan.candidates == ()
    assert scan.skipped[0].reason.startswith("unsupported_legacy_doc")
    assert results[0].skip_reason.startswith("unsupported_legacy_doc")
    assert summary.counts["processed"] == 0
    assert summary.counts["skipped"] == 1
    assert _card_paths(vault) == []
