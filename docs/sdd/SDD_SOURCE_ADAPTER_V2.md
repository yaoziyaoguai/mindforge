# SDD: SourceAdapter v2 — Multi-source Ingestion

> **Status**: Draft
> **Date**: 2026-05-14
> **Depends on**: [RFC_0001_SOURCE_ADAPTER_V2.md](../rfc/RFC_0001_SOURCE_ADAPTER_V2.md)
> **Related**: [V0_2_ROADMAP.md](../roadmap/V0_2_ROADMAP.md), [SDD_WIKI_PRESENTATION_V2.md](SDD_WIKI_PRESENTATION_V2.md)

---

## 1. Scope

本 SDD 定义 v0.2 SourceAdapter 层的模块结构、数据结构和实现顺序。不包含 processor / approval / wiki 层的变更。

---

## 2. Current Behavior (v0.1)

### 2.1 Module Map

```
src/mindforge/sources/
├── base.py              # SourceAdapter ABC, SourceDocument, Highlight, compute_content_hash
├── plain_markdown.py    # PlainMarkdownAdapter: .md → SourceDocument
├── pdf.py               # PdfAdapter: .pdf → SourceDocument (pypdf), OptionalDependencyError, PdfNoTextError
├── docx.py              # DocxAdapter: .docx → SourceDocument (python-docx), OptionalDependencyError
├── common_document.py   # CommonDocumentAdapter: .txt/.html/.json/.csv/.tsv/.xml/.url/.webloc → SourceDocument
├── registry.py          # _BUILTIN_ADAPTERS dict, build_active_adapters()
├── cubox_markdown.py
├── webclip_markdown.py
├── cubox_api.py
├── obsidian_vault.py
├── chat_export.py
└── stubs.py
```

### 2.2 SourceDocument v1 Fields

```
source_id, source_type, source_path, title, author, source_url,
created_at, captured_at, tags, highlights, raw_text, metadata,
content_hash, adapter_name
```

### 2.3 Registry Dispatch Flow

```
configs/mindforge.yaml → SourcesConfig.active_entries()
    → build_active_adapters() → dict[source_type, SourceAdapter]
    → scanner 按子目录派发
```

---

## 3. Target Behavior (v0.2)

### 3.1 Module Map (target)

```
src/mindforge/sources/
├── base.py              # ✏️ 修改：SourceDocument 增加 extraction_warnings + provenance_blocks
├── plain_markdown.py    # ⚬ 不变：characterization tests pass
├── txt.py               # ✨ 新增：TxtAdapter
├── html_adapter.py      # ✨ 新增：HtmlAdapter（避免与 stdlib html 冲突）
├── pdf.py               # ✏️ 修改：增加 page provenance
├── docx.py              # ✏️ 修改：增加 structure extraction
├── common_document.py   # ✏️ 修改：移除 .txt/.html parsing，保留 JSON/CSV/TSV/XML/URL/webloc
├── registry.py          # ✏️ 修改：增加 TxtAdapter + HtmlAdapter，增加 dispatch priority
├── adapter_result.py    # ✨ 新增：AdapterResult, ExtractionWarning, ProvenanceBlock
├── (unchanged)
│   ├── cubox_markdown.py
│   ├── webclip_markdown.py
│   ├── cubox_api.py
│   ├── obsidian_vault.py
│   ├── chat_export.py
│   └── stubs.py
```

### 3.2 Adapter Type Map (target)

| source_type | Adapter Class | File | Status |
|-------------|---------------|------|--------|
| `plain_markdown` | PlainMarkdownAdapter | plain_markdown.py | unchanged |
| `txt` | TxtAdapter | txt.py | **new** |
| `html` | HtmlAdapter | html_adapter.py | **new** |
| `pdf` | PdfAdapter | pdf.py | enhanced |
| `docx` | DocxAdapter | docx.py | enhanced |
| `common_document` | CommonDocumentAdapter | common_document.py | reduced scope |
| `cubox_markdown` | CuboxMarkdownAdapter | cubox_markdown.py | unchanged |
| `webclip_markdown` | WebClipMarkdownAdapter | webclip_markdown.py | unchanged |
| `cubox_api` | CuboxApiAdapter | cubox_api.py | unchanged |
| `obsidian_note` | ObsidianVaultSourceAdapter | obsidian_vault.py | unchanged |
| `chat_export` | ChatExportAdapter | chat_export.py | unchanged |

### 3.3 Processor Boundary (critical invariant)

```
Processor
    │
    ├── uses: SourceDocument (ONLY)
    │
    └── NEVER imports: pdf, docx, txt, html_adapter, bs4, pypdf, python-docx, chardet
```

Processor 通过 `SourceDocument.raw_text` 获取内容，通过 `SourceDocument.source_type` 获知格式（用于 provenance 展示，不用于格式分支逻辑）。

验证方式：测试中 mock `sys.modules`，确保 processor 不 import 任何 format-specific 库。

---

## 4. Proposed Modules

### 4.1 `src/mindforge/sources/base.py` (modified)

```python
# 新增 import
from dataclasses import dataclass, field

# 新增数据类
@dataclass(frozen=True)
class ProvenanceBlock:
    """单块 provenance 记录。"""
    source_type: str            # "pdf" / "docx" / "txt" / "html"
    page: int | None = None     # PDF page number
    section: str | None = None  # section heading
    offset_start: int | None = None
    offset_end: int | None = None
    extracted_as: str = "text"

@dataclass(frozen=True)
class ExtractionWarning:
    """解析过程中产生的 warning。"""
    code: str                   # "encoding_fallback", "table_loss", "empty_file", etc.
    message: str
    location: str | None = None

# 修改 SourceDocument — 增加两个字段（backward-compatible default）
@dataclass(frozen=True)
class SourceDocument:
    # ... existing fields unchanged ...
    extraction_warnings: list[ExtractionWarning] = field(default_factory=list)  # NEW
    provenance_blocks: list[ProvenanceBlock] = field(default_factory=list)      # NEW
```

> **不变**：`source_id`, `source_type`, `source_path`, `title`, `author`, `source_url`, `created_at`, `captured_at`, `tags`, `highlights`, `raw_text`, `metadata`, `content_hash`, `adapter_name` 保持原样。

### 4.2 `src/mindforge/sources/txt.py` (new)

```
TxtAdapter(SourceAdapter)
  name = "TxtAdapter"
  source_type = "txt"
  
  can_handle(path) → path.endswith(".txt")
  
  load(path) → AdapterResult:
    1. 检查文件存在 / 可读
       - 不存在 → AdapterResult(status="failed", error_message="FileNotFoundError: ...")
       - 无权限 → AdapterResult(status="failed", error_message="PermissionError: ...")
    2. 检测是否为二进制文件（null bytes in first 1024 bytes）
       - 是二进制 → AdapterResult(status="skipped", skip_reason="binary_file")
    3. 编码检测：UTF-8 → chardet fallback（如果已安装）
    4. 编码失败 → AdapterResult(status="skipped", skip_reason="decode_error")
    5. 空文件 → AdapterResult(status="loaded", document=SourceDocument(raw_text=""), warnings=[ExtractionWarning(code="empty_file")])
    6. 大文件 > 10MB → 在 warnings 中附加 ExtractionWarning(code="large_file")
    7. 大文件 > 50MB → AdapterResult(status="skipped", skip_reason="file_too_large")
    8. 成功 → AdapterResult(status="loaded", document=SourceDocument(...))
       - title = first_line or filename stem
       - provenance_blocks = [ProvenanceBlock(source_type="txt", offset_start=0, offset_end=len(text))]
```

### 4.3 `src/mindforge/sources/html_adapter.py` (new)

```
HtmlAdapter(SourceAdapter)
  name = "HtmlAdapter"
  source_type = "html"
  
  can_handle(path) → path.endswith((".html", ".htm"))
  
  load(path) → AdapterResult:
    1. 读取文件为 raw HTML
       - 不存在 → AdapterResult(status="failed", error_message="FileNotFoundError: ...")
    2. Strip <script> / <style> tags and content
    3. Extract <title>
    4. Parse DOM (beautifulsoup4 if available, else stdlib html.parser)
    5. Extract body text with structure:
       - <h1>-<h6> → Markdown headings
       - <p> → paragraphs
       - <a> → [text](url)
       - <ul>/<ol>/<li> → Markdown lists
       - <table> → Markdown table (simple)
       - <blockquote> → Markdown blockquote
    6. 不 fetch external resources
    7. Noisy HTML detecting → 在 warnings 中附加 ExtractionWarning(code="noisy_html")
    8. 成功 → AdapterResult(status="loaded", document=SourceDocument(...))
       - title = <title> text or first <h1> or filename stem
       - provenance_blocks = [ProvenanceBlock(source_type="html")]
```

### 4.4 `src/mindforge/sources/pdf.py` (modified)

现有 `PdfAdapter` 修改点：
- `load()` 返回 `AdapterResult`：
  - 成功 → `AdapterResult(status="loaded", document=SourceDocument(...))`
  - `SourceDocument.provenance_blocks`：
    ```
    provenance_blocks = [
        ProvenanceBlock(source_type="pdf", page=i+1, extracted_as="text")
        for i in range(len(reader.pages))
    ]
    ```
- 增加 file size guard (>50MB → `AdapterResult(status="skipped", skip_reason="file_too_large")`)
- 增加 page count warning (>500 pages → 在 warnings 中附加 ExtractionWarning)
- 保持现有 scanned PDF detection → `AdapterResult(status="skipped", skip_reason="scanned_pdf_no_text")`

### 4.5 `src/mindforge/sources/docx.py` (modified)

现有 `DocxAdapter` 修改点：
- 在遍历 `Document.paragraphs` 时识别 style → heading level
- 遍历 `Document.tables` 提取为 Markdown table
- 识别 numbered/bullet lists
- `load()` 返回 `AdapterResult`：
  - `provenance_blocks`：每个 section/table 一个 ProvenanceBlock
  - `warnings`：table_loss, smartart_skipped, embedded_object_skipped
- 保持不执行宏

### 4.6 `src/mindforge/sources/adapter_result.py` (new)

```python
@dataclass(frozen=True)
class AdapterResult:
    """Adapter.load() 的唯一返回类型。status 必填。"""
    status: str                          # "loaded" | "skipped" | "failed"
    document: SourceDocument | None = None
    skip_reason: str | None = None       # status == "skipped" 时必填
    error_message: str | None = None     # status == "failed" 时必填
    warnings: list[ExtractionWarning] = field(default_factory=list)

@dataclass(frozen=True)
class SkipReason:
    """预定义 skip reason 常量。在 AdapterResult.skip_reason 中使用。"""
    UNSUPPORTED_LEGACY_DOC = "unsupported_legacy_doc"
    SCANNED_PDF_NO_TEXT = "scanned_pdf_no_text"
    ENCRYPTED_PDF = "encrypted_pdf"
    DECODE_ERROR = "decode_error"
    BINARY_FILE = "binary_file"
    FILE_TOO_LARGE = "file_too_large"
    UNSUPPORTED_FORMAT = "unsupported_format"
    MISSING_OPTIONAL_DEPENDENCY = "missing_optional_dependency"
    EMPTY_FILE = "empty_file"
```

### 4.7 `src/mindforge/sources/registry.py` (modified)

修改点：
- 新增 `TxtAdapter` / `HtmlAdapter` import
- `_BUILTIN_ADAPTERS` 增加映射
- 增加 `find_adapter_for_path(path) -> SourceAdapter | None`
- 增加 `SKIP_REASONS` mapping for known unsupported extensions（.doc → unsupported_legacy_doc）

---

## 5. Data Structures

### 5.1 SourceDocument v2 (full field list)

| # | Field | Type | Required | Default |
|---|-------|------|----------|---------|
| 1 | source_id | str | yes | — |
| 2 | source_type | SourceType | yes | — |
| 3 | source_path | str | yes | — |
| 4 | title | str \| None | no | None |
| 5 | author | str \| None | no | None |
| 6 | source_url | str \| None | no | None |
| 7 | created_at | datetime \| None | no | None |
| 8 | captured_at | datetime \| None | no | None |
| 9 | tags | list[str] | no | [] |
| 10 | highlights | list[Highlight] | no | [] |
| 11 | raw_text | str | no | "" |
| 12 | metadata | dict | no | {} |
| 13 | content_hash | str | yes | — |
| 14 | adapter_name | str | no | "" |
| 15 | extraction_warnings | list[ExtractionWarning] | **new** | [] |
| 16 | provenance_blocks | list[ProvenanceBlock] | **new** | [] |

### 5.2 AdapterResult

```
AdapterResult
├── status: str                            ("loaded" | "skipped" | "failed")
├── document: SourceDocument | None        (status == "loaded" 时非 None)
├── skip_reason: str | None                (status == "skipped" 时必填)
├── error_message: str | None              (status == "failed" 时必填)
└── warnings: list[ExtractionWarning]      (status == "loaded" 时的 extraction warnings)
```

### 5.3 ExtractionWarning

```
ExtractionWarning
├── code: str                  (e.g. "encoding_fallback", "table_loss")
├── message: str               (human-readable)
└── location: str | None       (page / line / section)
```

### 5.4 ProvenanceBlock

```
ProvenanceBlock
├── source_type: str
├── page: int | None
├── section: str | None
├── offset_start: int | None
├── offset_end: int | None
└── extracted_as: str          ("text" / "markdown_table" / "markdown_list")
```

---

## 6. CLI Integration

`mindforge import` / `mindforge watch add` 调用 registry dispatch：

```
1. resolve path → extension
2. find_adapter_for_path(path)
3. if adapter found:
     result = adapter.load(path) → AdapterResult

     if result.status == "loaded":
         if result.warnings: print warnings
         pass result.document to processing pipeline

     elif result.status == "skipped":
         print "✗ Skipped: {result.skip_reason}"
         record in run summary, continue to next file

     elif result.status == "failed":
         print "✗ Failed: {result.error_message}"
         record in run summary, continue to next file

     # 不得出现 loaded + document.raw_text="" 的静默空输出
4. if no adapter found:
     print "✗ Unsupported format: {extension}"
     record in run summary
```

`mindforge import` 增加 `--source-type` flag 用于手动指定 adapter（override auto-detection）。

---

## 7. Watch Integration

`mindforge watch add` 支持的新 source type：
- `txt`
- `html`
- `pdf`（已有）
- `docx`（已有）

watch 添加时展示 detected source_type 和 adapter。

---

## 8. Process Pipeline Integration

不变。Processor 只通过 `SourceDocument` 消费。Pipeline 中的 scanner：
1. 按 registry 派发 adapter
2. adapter.load() 返回 AdapterResult
3. status == "loaded" → 取 .document 传给 processor
4. status != "loaded" → 记录 skip/fail reason

Scanner 的变更：
- 增加 `find_adapter_for_path()` dispatch
- 处理 unsupported source → 记录 skip reason（不中断整个 scan）
- 处理 adapter error → 记录 error（不中断整个 scan）

---

## 9. Error Handling

`adapter.load(path)` 返回 `AdapterResult`，不抛 exception 表达 skip/fail：

```
adapter.load(path) → AdapterResult
                        │
                        ├─ status="loaded"   → document 传给 processor（warnings 记录但继续）
                        ├─ status="skipped"  → 记录 skip_reason，继续下一个文件
                        └─ status="failed"   → 记录 error_message，继续下一个文件
```

对应关系：
- FileNotFound / PermissionError → `AdapterResult(status="failed", error_message=...)`
- OptionalDependencyError → `AdapterResult(status="failed", error_message=...)`
- PdfNoTextError → `AdapterResult(status="skipped", skip_reason="scanned_pdf_no_text")`
- UnicodeDecodeError → `AdapterResult(status="skipped", skip_reason="decode_error")`
- 未知格式 → `AdapterResult(status="skipped", skip_reason="unsupported_format")`

Scanner 级处理：single file error → 记录 status → continue next file。不 crash。

---

## 10. Tests

### 10.1 New Test Files

```
tests/
├── adapters/
│   ├── test_txt_adapter.py         # TxtAdapter unit tests
│   ├── test_html_adapter.py        # HtmlAdapter unit tests
│   ├── test_pdf_provenance.py      # PDF page provenance tests
│   └── test_docx_structure.py      # DOCX structure extraction tests
├── test_source_adapter_v2_contract.py  # SourceDocument v2 contract
├── test_registry_dispatch.py       # Registry dispatch priority
├── test_unsupported_skip.py        # Unsupported format handling
├── test_processor_format_isolation.py  # Processor doesn't import format libs
└── test_common_document_boundary.py    # TXT/HTML no longer in common_document
```

### 10.2 Test Fixtures

```
tests/fixtures/
├── txt/
│   ├── valid_utf8.txt
│   ├── valid_utf8_bom.txt
│   ├── empty.txt
│   ├── binary_file.bin
│   └── large_file.txt              # > 10MB for size guard
├── html/
│   ├── simple_page.html
│   ├── with_script_style.html
│   ├── with_tables_lists.html
│   ├── malformed.html
│   └── xss_payload.html
├── pdf/
│   ├── text_single_page.pdf
│   ├── text_multi_page.pdf
│   ├── scanned_no_text.pdf
│   └── encrypted.pdf
└── docx/
    ├── headings_lists.docx
    ├── with_tables.docx
    ├── empty.docx
    └── macro_enabled.docm           # safety test
```

---

## 11. Implementation Phases

**M1 关键原则**：先 characterization tests + contract tests，后 production code edits。第一个 coding prompt **不允许**直接改 `base.py`。

| Phase | Content | Files |
|-------|---------|-------|
| P1 | Markdown characterization tests（捕获 v0.1 行为基线） | tests/test_source_adapter_v2_contract.py (skeleton) |
| P2 | Contract tests：SourceDocument v2 fields + AdapterResult contract | tests/（contract validation only） |
| P3 | SourceDocument v2 backward-compatible fields（`extraction_warnings` + `provenance_blocks`） | base.py |
| P4 | AdapterResult + ExtractionWarning + ProvenanceBlock | adapter_result.py |
| P5 | Registry update（TxtAdapter + HtmlAdapter registration, dispatch priority） | registry.py |
| P6 | TxtAdapter | txt.py, tests/adapters/test_txt_adapter.py |
| P7 | HtmlAdapter | html_adapter.py, tests/adapters/test_html_adapter.py |
| P8 | PdfAdapter provenance_blocks | pdf.py, tests/adapters/test_pdf_provenance.py |
| P9 | DocxAdapter structure | docx.py, tests/adapters/test_docx_structure.py |
| P10 | CommonDocument boundary cleanup | common_document.py, tests/test_common_document_boundary.py |
| P11 | Legacy DOC research | docs/rfc/RFC_0003_LEGACY_DOC_EVALUATION.md |
| P9 | Legacy DOC research | docs/rfc/RFC_0003_LEGACY_DOC_EVALUATION.md |

**推荐 adapter 实现顺序**：
1. Markdown characterization（baseline）
2. TXT adapter（最小风险）
3. HTML adapter
4. PDF adapter enhancement
5. DOCX adapter enhancement
6. Legacy DOC research gate

---

## 12. Rollback Plan

每个 phase 独立可回滚：
- Phase 1-2：移除新 adapter class + 移除 registry entry，不影响现有功能
- Phase 3-5：移除对应的 adapter 文件 + registry entry
- SourceDocument 新字段使用 `field(default_factory=list)`，移除后旧代码不受影响

---

## 13. Done Criteria

- [ ] 每个格式有独立 SourceAdapter 实现
- [ ] SourceDocument v2 包含 extraction_warnings 和 provenance_blocks
- [ ] PlainMarkdownAdapter characterization tests 全部通过
- [ ] TXT/HTML 不再由 CommonDocumentAdapter 处理
- [ ] Processor 不 import 任何 format-specific 库
- [ ] 所有 unsupported format 产生友好 skip reason
- [ ] .doc 和 .docx 在代码中明确区分
- [ ] 每个 adapter 有 synthetic fixture 单元测试
- [ ] 安全测试通过
- [ ] ruff + pytest 全绿
