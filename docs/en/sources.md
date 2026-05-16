# Source Management

Sources are local files that MindForge processes through a unified adapter layer into AI-generated knowledge cards.

---

## Supported Formats

| Format | Status | Notes | Dependency |
|--------|--------|-------|------------|
| Markdown | Supported | Full support | Base install |
| TXT | Supported | Plain text | Base install |
| HTML | Supported | Local files only; no URL crawling | Base install |
| PDF (text-based) | Supported | Text extraction only; no OCR | `pypdf` (optional) |
| DOCX | Supported | Modern `.docx` format | `python-docx` (optional) |
| DOC (legacy) | Unsupported | Research gate | — |

---

## Optional Dependencies

The base install (`pip install mindforge`) supports Markdown, TXT, and local HTML.

For PDF and DOCX support, install the optional extras:

```bash
pip install "mindforge[pdf,docx]"
```

Or install the packages directly:

```bash
pip install pypdf python-docx
```

No code changes are needed — the adapters use lazy imports and skip gracefully when optional dependencies are missing.

---

## Limitations

- **PDF**: Text-based only. Scanned documents and image-based PDFs are detected and skipped with a clear reason. No OCR is performed.
- **HTML**: Local files only. The adapter does not follow links or fetch remote content.
- **DOC (legacy `.doc`)**: Not supported. Binary `.doc` files from older Word versions cannot be processed. Convert to `.docx` or Markdown first.
- **Large files**: Files over 50 MB are skipped. PDFs with more than 500 pages generate a warning but are still processed.

---

## How Processing Works

When you add a source via `mindforge watch add` or `mindforge import`:

1. The file is detected by its extension and routed to the matching adapter.
2. The adapter extracts structured text, including page-level provenance for PDFs.
3. Extracted content is fed into the five-stage processing pipeline: Triage → Distill → Link Suggestion → Review Questions → Action Extraction.
4. The result is an `ai_draft` card ready for review.

Source files are never modified by MindForge. Processing reads the file and archives a content hash for provenance tracking.

---

## Related

- [中文 Source 管理](../zh-CN/sources.md)
- [User Guide](user-guide.md)
- [Model Setup](model-setup.md)
