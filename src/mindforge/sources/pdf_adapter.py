"""v0.2 PdfTextAdapter — 文本型 PDF 的 SourceAdapter（v0.2 contract）。

RFC_0001 §5.8 要求 PDF adapter 提供 page-level provenance、scanned PDF
detection、file size guard，并返回 AdapterResult。本 adapter 是 v0.2 新增，
与 v0.1 ``PdfAdapter`` 并存，仅通过 ``create_default_registry()`` 接入。

设计边界：不做 OCR、不做 table extraction、不做 image PDF、不联网。
pypdf 为 lazy import（已在 pyproject.toml 的 [project.optional-dependencies] pdf 中）。
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from mindforge.sources.adapter_result import (
    AdapterResult,
    ExtractionWarning,
    ProvenanceBlock,
    SkipReason,
)
from mindforge.sources.base import SourceDocument, compute_content_hash
from mindforge.sources.source_adapter import SourceAdapter

_MAX_PDF_BYTES = 50 * 1024 * 1024
_MAX_PAGE_WARNING = 500


def _load_pdf_reader(path: Path):
    """lazy import pypdf.PdfReader，保持 pypdf optional dependency。

    把 pypdf lazy import 包在 helper 中，是为了让单元测试可以 patch adapter 边界，
    而不要求 CI 安装 pypdf。
    """
    from pypdf import PdfReader

    return PdfReader(str(path))


class PdfTextAdapter(SourceAdapter):
    """把本地文本型 ``.pdf`` 文件解析为 ``SourceDocument``（v0.2 contract）。

    与 v0.1 PdfAdapter 的区别：
    - 返回 AdapterResult（而非直接 SourceDocument 或 raise exception）
    - 包含 page-level provenance_blocks
    - 包含 file size / page count guards
    - scanned PDF → AdapterResult.skipped
    """

    name = "PdfTextAdapter"
    source_type = "pdf"

    def can_handle(self, path: str) -> bool:
        return Path(path).suffix.lower() == ".pdf"

    def load(self, path: str) -> AdapterResult:
        p = Path(path)

        if not p.exists():
            return AdapterResult(
                status="failed",
                error_message=f"FileNotFoundError: {p}",
            )

        # file size guard
        try:
            size = p.stat().st_size
        except OSError as exc:
            return AdapterResult(
                status="failed",
                error_message=f"{type(exc).__name__}: {p}",
            )
        if size > _MAX_PDF_BYTES:
            return AdapterResult(
                status="skipped",
                skip_reason=SkipReason.FILE_TOO_LARGE,
            )

        # lazy import pypdf + 打开 PDF（通过 _load_pdf_reader seam，供 mock patch）
        try:
            reader = _load_pdf_reader(p)
        except ImportError:
            return AdapterResult(
                status="failed",
                error_message=(
                    "OptionalDependencyError: pypdf is required for PDF processing. "
                    "Install with: pip install 'mindforge[pdf]' or pip install pypdf"
                ),
            )
        except Exception as exc:
            return AdapterResult(
                status="failed",
                error_message=f"PdfReadError: {p.name} — {exc}",
            )

        # page count guard（warning，不阻止处理）
        page_count = len(reader.pages)
        warnings: list[ExtractionWarning] = []
        if page_count > _MAX_PAGE_WARNING:
            warnings.append(
                ExtractionWarning(
                    code="large_page_count",
                    message=f"PDF has {page_count} pages; processing may be slow.",
                    location=None,
                )
            )

        # 逐页提取文本
        pages_text: list[str] = []
        for page in reader.pages:
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            pages_text.append(t)

        body = "\n\n".join(s.strip() for s in pages_text if s.strip())

        if not body.strip():
            return AdapterResult(
                status="skipped",
                skip_reason=SkipReason.SCANNED_PDF_NO_TEXT,
            )

        title = _pdf_title(reader, p)

        # 构建 page-level provenance
        provenance_blocks = [
            ProvenanceBlock(
                source_type=self.source_type,
                page=i + 1,
                extracted_as="text",
            )
            for i in range(page_count)
        ]

        document = SourceDocument(
            source_id="sha1:" + hashlib.sha1(str(p).encode("utf-8")).hexdigest(),
            source_type=self.source_type,
            source_path=str(p),
            title=title,
            raw_text=body,
            metadata={"page_count": page_count},
            content_hash=compute_content_hash(body, {"title": title, "page_count": page_count}),
            adapter_name=self.name,
            extraction_warnings=list(warnings),
            provenance_blocks=provenance_blocks,
        )

        return AdapterResult(status="loaded", document=document, warnings=warnings)


def _pdf_title(reader: object, p: Path) -> str:
    try:
        meta = getattr(reader, "metadata", None)
        if meta:
            t = getattr(meta, "title", None) or (meta.get("/Title") if hasattr(meta, "get") else None)
            if t:
                return str(t).strip()
    except Exception:
        pass
    return p.stem


__all__ = ["PdfTextAdapter"]
