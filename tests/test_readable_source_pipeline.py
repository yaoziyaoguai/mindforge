"""Readable document source pipeline regression tests.

中文学习型说明：这些测试覆盖 fresh-clone 风格的最小用户配置，而不是手写
完整 ``sources`` 段。目标是守住产品承诺：用户从 Web/CLI import 本地可读文档
时，source discovery 必须走默认 readable adapter registry，后续 pipeline 只生成
``ai_draft``，不会自动 approve，也不会调用真实 LLM/API。
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from mindforge.app_context import load_app_config
from mindforge.assets_runtime import asset_root
from mindforge.cards import read_card_frontmatter
from mindforge.config import PromptVersions
from mindforge.ingestion_service import import_sources
from mindforge.llm import LLMResult, ResolvedModel, StageCallResult
from mindforge.processors.pipeline import Pipeline
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


class _NoOpLogger:
    run_id = "readable-source-test"

    def emit(self, event: str, **fields: object) -> None:
        return None


class _PromptScoringLLMClient:
    """按 triage prompt 内容打分的本地替身，不调用真实 LLM/API。

    中文学习型说明：P2-1 的问题发生在 adapter 输出进入 triage prompt 的边界。
    这里替身化模型返回，但仍走真实 Pipeline + prompt rendering；这样能证明
    high-signal PDF/DOCX 正文确实进入 triage，而不是把 threshold 降低或绕过。
    """

    def resolve_model_for_stage(self, stage: str) -> ResolvedModel:
        return ResolvedModel(
            stage=stage,
            model_alias="stub",
            provider="stub",
            actual_model="stub-model",
            type="stub",
        )

    def generate(self, *, stage: str, prompt: str, options=None) -> StageCallResult:  # type: ignore[no-untyped-def]
        if stage == "triage":
            high_signal = "local-first storage model" in prompt or "reliable document ingestion" in prompt
            payload = {
                "track": "agent-runtime",
                "value_score": 7 if high_signal else 1,
                "should_process": high_signal,
                "reason": "prompt-scoring stub",
                "topic_keywords": ["readable-source"],
            }
        elif stage == "distill":
            payload = {
                "title": "Readable Source",
                "slug": "readable-source",
                "tags": ["readable-source"],
                "confidence": 0.8,
                "source_excerpt": "synthetic excerpt",
                "ai_summary_bullets": ["High-signal readable source was processed."],
                "ai_inference_bullets": [],
                "reusable_prompts_or_principles": ["Keep source extraction noise out of triage scoring."],
            }
        elif stage == "link_suggestion":
            payload = {"suggested_links": [], "project_hooks": []}
        elif stage == "review_questions":
            payload = {"review_questions": []}
        elif stage == "action_extraction":
            payload = {"action_items": []}
        else:
            raise AssertionError(f"unexpected stage: {stage}")
        return StageCallResult(
            resolved=self.resolve_model_for_stage(stage),
            result=LLMResult(
                text=json.dumps(payload, ensure_ascii=False),
                tokens_in=len(prompt),
                tokens_out=1,
                latency_ms=0,
                raw={"stub": True},
            ),
        )


def _prompt_scoring_pipeline() -> Pipeline:
    return Pipeline(
        client=_PromptScoringLLMClient(),  # type: ignore[arg-type]
        logger=_NoOpLogger(),  # type: ignore[arg-type]
        prompts_dir=asset_root().joinpath("prompts"),
        prompt_versions=PromptVersions(
            triage="v1",
            distill="v1",
            link_suggestion="v1",
            review_questions="v1",
            action_extraction="v1",
        ),
        triage_threshold=5,
        learning_tracks_text="tracks:\n  - id: agent-runtime\n    keywords: [storage, ingestion]\n",
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


# ---------------------------------------------------------------------------
# P2-1: PDF/DOCX triage scoring — smart excerpt + prompt guidance
# ---------------------------------------------------------------------------


def test_smart_excerpt_skips_pdf_docx_front_matter() -> None:
    """pdf/docx 长文本的 smart excerpt 应跳过前 10% 的 TOC/header 区域。

    中文学习型说明：pdf/docx 提取文本前面经常是目录、页眉等低信息噪音。
    _smart_excerpt 在文本 >8000 chars 时应从 10% 位置取 excerpt，避免 triage
    看到全是 TOC 而给出 value_score=0。
    """
    from mindforge.processors.pipeline import _smart_excerpt

    # 模拟一个长 PDF 提取文本：前 ~1200 字是目录/页眉噪音，后面是正文
    front_noise = "TABLE OF CONTENTS\n\n1. Introduction ........... 1\n2. Methods ................ 3\n" * 30  # ~1500 chars of TOC
    real_content = "\n\n## Architecture Design\n\nThe system uses a local-first storage model with immutable event log.\n" * 50  # ~4000 chars of real content
    text = front_noise + real_content + "\n\n## More content\n" + "Additional details for padding to reach minimum length requirement.\n" * 200
    assert len(text) > 8000, f"text too short: {len(text)} chars"

    result = _smart_excerpt(text, "pdf")

    assert len(result) > 0
    assert "source_type=pdf" in result
    assert "total_chars≈" in result
    assert "excerpt from ~10%" in result
    # body 应该包含正文而不是纯目录
    assert "Architecture Design" in result
    assert "local-first storage" in result
    # 不应以前 10% 的目录噪音开头
    assert not result.split("\n\n", 1)[1].startswith("TABLE OF CONTENTS")


def test_smart_excerpt_short_text_unchanged() -> None:
    """短文本（<=prompt budget）不从中间截取，保留原文完整给 triage。"""
    from mindforge.processors.pipeline import _smart_excerpt

    short = "## Short document\n\nJust a brief note.\n" * 50
    assert len(short) < 8000

    result = _smart_excerpt(short, "pdf")
    # 短文本原文全部保留，不以 [...]truncated 结束
    assert "[...truncated for prompt budget...]" not in result
    assert "## Short document" in result


def test_high_quality_pdf_docx_sources_pass_triage_without_force(tmp_path: Path) -> None:
    """高质量 text-based PDF/DOCX 应正常通过 triage，不依赖 --force。

    中文学习型说明：这里不降低全局 threshold，也不让 pdf/docx 无条件通过；
    stub client 只在 high-signal 正文进入 triage prompt 时给 7 分。
    """

    front_noise = "TABLE OF CONTENTS\n1. Preface ........ 1\n2. Index ........ 2\n" * 40
    pdf_text = (
        front_noise
        + ("\n## Actionable Architecture\nThe local-first storage model keeps an immutable event log.\n" * 80)
    )
    docx_text = (
        front_noise
        + ("\n# Reliable Document Ingestion\nA reliable document ingestion pipeline keeps provenance intact.\n" * 80)
    )
    pipeline = _prompt_scoring_pipeline()

    pdf_outcome = pipeline.run(
        _document(tmp_path / "paper.pdf", source_type="pdf", adapter_name="PdfTextAdapter", raw_text=pdf_text)
    )
    docx_outcome = pipeline.run(
        _document(tmp_path / "brief.docx", source_type="docx", adapter_name="DocxTextAdapter", raw_text=docx_text)
    )

    assert pdf_outcome.status == "processed"
    assert docx_outcome.status == "processed"
    assert pdf_outcome.card_payload is not None
    assert docx_outcome.card_payload is not None
    assert pdf_outcome.card_payload["structured_payload"]["card"]["value_score"] == 7
    assert docx_outcome.card_payload["structured_payload"]["card"]["value_score"] == 7


def test_low_quality_txt_html_sources_still_skip_triage(tmp_path: Path) -> None:
    """TXT/HTML 低质量文本仍可被 triage skipped，避免把 PDF/DOCX 修复扩散成全局放宽。"""

    pipeline = _prompt_scoring_pipeline()
    txt_outcome = pipeline.run(
        _document(
            tmp_path / "noise.txt",
            source_type="txt",
            adapter_name="TxtAdapter",
            raw_text="cookie banner subscribe share login footer " * 50,
        )
    )
    html_outcome = pipeline.run(
        _document(
            tmp_path / "noise.html",
            source_type="html",
            adapter_name="HtmlAdapter",
            raw_text="script style nav advertisement cookie banner " * 50,
        )
    )

    assert txt_outcome.status == "skipped"
    assert html_outcome.status == "skipped"
    assert "value_score=1" in (txt_outcome.skip_reason or "")
    assert "value_score=1" in (html_outcome.skip_reason or "")


def test_smart_excerpt_non_pdf_docx_unchanged() -> None:
    """plain_markdown / txt 等非 pdf/docx 类型不走 smart excerpt，保持原行为。"""
    from mindforge.processors.pipeline import _smart_excerpt

    long_md = "# Title\n\n## Section\n\nBody text.\n" * 300
    assert len(long_md) > 8000

    result = _smart_excerpt(long_md, "plain_markdown")
    # markdown 类型保持从开头取 excerpt
    assert result.startswith("# Title")
    assert "[...truncated for prompt budget...]" in result
    # 不应有 source_type 前缀
    assert "source_type=" not in result


def test_triage_prompt_includes_pdf_docx_in_source_type_examples() -> None:
    """triage prompt v1 的 source_type 示例必须包含 pdf 和 docx。

    中文学习型说明：修复前示例只有 cubox_markdown / plain_markdown / ...，
    缺少 pdf/docx/html，LLM 看到陌生 source_type 影响评分。修复后必须包含。
    """
    from pathlib import Path

    from mindforge.prompts_runtime import load_prompt

    prompts_dir = Path("src/mindforge/assets/prompts")
    text = load_prompt(prompts_dir, "triage", "v1")
    assert "pdf" in text
    assert "docx" in text
    assert "html" in text
    assert "txt" in text


def test_triage_prompt_includes_extraction_quality_guidance() -> None:
    """triage prompt v1 必须包含提取格式注意章节，指导 LLM 忽略 pdf/docx/html 提取噪音。

    中文学习型说明：这是 P2-1 修复的关键——告诉 triage LLM 不要因为
    extract_text 导致的格式噪音（合并词、页眉残留）而给低分。
    """
    from pathlib import Path

    from mindforge.prompts_runtime import load_prompt

    prompts_dir = Path("src/mindforge/assets/prompts")
    text = load_prompt(prompts_dir, "triage", "v1")
    assert "提取格式注意" in text
    assert "pdf" in text
    assert "docx" in text
    assert "html" in text
    assert "pypdf" in text or "提取噪音" in text
    assert "聚焦内容实质" in text
