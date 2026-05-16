# RFC 0001: SourceAdapter v2 — Multi-source Ingestion

> **Status**: Draft
> **Date**: 2026-05-14
> **Author**: MindForge Team
> **Related**: [V0_2_ROADMAP.md](../roadmap/V0_2_ROADMAP.md), [SDD_SOURCE_ADAPTER_V2.md](../sdd/SDD_SOURCE_ADAPTER_V2.md)

---

## Abstract

将 v0.1 中分散的 source parsing 逻辑（`CommonDocumentAdapter` 内联 parser + 独立 adapter）统一为第一级 `SourceAdapter` 实现。每个支持格式有独立 adapter，输出统一 `SourceDocument`，为 processor 提供格式无关的合约。

---

## 1. Context

### 1.1 Current State (v0.1)

v0.1 source adapter 架构：

```
src/mindforge/sources/
├── base.py              # SourceAdapter ABC, SourceDocument, Highlight
├── plain_markdown.py    # PlainMarkdownAdapter (.md)
├── pdf.py               # PdfAdapter (.pdf, pypdf, text-only)
├── docx.py              # DocxAdapter (.docx, python-docx, paragraphs only)
├── common_document.py   # CommonDocumentAdapter (.txt/.html/.json/.csv/.tsv/.xml 等)
├── cubox_markdown.py    # CuboxMarkdownAdapter
├── webclip_markdown.py  # WebClipMarkdownAdapter
├── cubox_api.py         # CuboxApiAdapter
├── obsidian_vault.py    # ObsidianVaultSourceAdapter
├── chat_export.py       # ChatExportAdapter
├── stubs.py
└── registry.py          # _BUILTIN_ADAPTERS, build_active_adapters()
```

关键问题：

1. **TXT/HTML 不是独立 adapter**：`CommonDocumentAdapter` 用内联 parser function `_parse_text()` / `_parse_html()` 处理，source_type 统一为 `common_document`，丢失了格式 provenance。
2. **HTML parser 粗糙**：`_parse_html()` 只是 strip tag + unescape，不保留 headings/links/lists 结构。
3. **TXT parser 无编码检测**：`_parse_text()` 假设 UTF-8，无 fallback。
4. **PDF/DOCX adapter 缺少 extraction_warnings**：解析失败信息通过 exception 抛给上层，没有结构化 warning 机制。
5. **SourceDocument 缺少 provenance 字段**：没有 `extraction_warnings` / `provenance_blocks` 让下游了解"这个文档解析过程中遇到了什么问题"。

### 1.2 Why Now

v0.2 的 Multi-source ingestion 主题要求扩展 source type 支持。在现有 adapter 基础上做 incremental 增强，比从头设计成本更低，且不会破坏 v0.1 的 Markdown 主路径。

---

## 2. Problem

当前 source ingestion 存在三个 gap：

1. **格式 provenance 丢失**：TXT/HTML 文件处理后被标记为 `common_document`，用户和下游无法区分原始格式。
2. **解析质量参差不齐**：HTML parser 丢失结构，TXT parser 无编码容错，DOCX parser 只取 paragraphs。
3. **缺少结构化 warning 机制**：解析问题通过 exception 或静默处理，没有供下游决策的 warning 信息。

---

## 3. Goals

1. 每个常见 source 格式有独立 `SourceAdapter` 实现，输出准确的 `source_type`
2. `SourceDocument` 增加 `extraction_warnings` 和 `provenance_blocks` 字段，保持 backward-compatible
3. TXT 适配增强编码检测和容错
4. HTML 适配保留文档结构（headings / links / lists）
5. PDF 适配增加 page-level provenance
6. DOCX 适配保留更多语义结构（headings / lists / tables）
7. Legacy `.doc` 单独评估，不与 `.docx` 混淆
8. Processor 完全不接触格式细节，只消费 `SourceDocument`

---

## 4. Non-goals

- 不做 OCR / 图片 PDF
- 不做 URL crawling / remote HTML
- 不做 .doc（除非 M5 research gate 通过）
- 不改 processor pipeline
- 不改 knowledge card schema
- 不改 approval 语义
- 不做 RAG / embedding

---

## 5. Proposed Design

### 5.1 SourceAdapter Interface

`SourceAdapter` 接口（v0.2 唯一 contract）：

```python
class SourceAdapter(ABC):
    name: str                    # stable identifier, e.g. "TxtAdapter"
    source_type: SourceType      # e.g. "txt", "html", "pdf", "docx"

    @abstractmethod
    def can_handle(self, path: str) -> bool: ...
    @abstractmethod
    def load(self, path: str) -> AdapterResult: ...

    def capabilities(self) -> frozenset[str]: ...  # inherited
```

**load() 返回 AdapterResult**：
- `AdapterResult.status` = `"loaded"` → `document` 非 None，传给 processor
- `AdapterResult.status` = `"skipped"` → `skip_reason` 非空，`document` 为 None
- `AdapterResult.status` = `"failed"` → `error_message` 非空，`document` 为 None
- 正常 skip（unsupported format / scanned PDF / decode error）走 skipped/failed，**不用** bare `raise ValueError`
- Processor **只**接收 `status="loaded"` 后的 `AdapterResult.document`

**职责**：
- `can_handle(path)` → 判断能否处理此文件（按后缀 + 可选 peek 文件头）
- `load(path)` → 解析文件 → 返回 `AdapterResult`（loaded / skipped / failed）
- 所有格式特异性在 `load()` 内部消化

**不负责**：
- LLM processing
- ai_draft generation
- approval
- recall
- wiki synthesis
- 写文件 / 修改 source
- 存储 secrets

### 5.2 SourceDocument v2

在现有 `SourceDocument`（frozen dataclass, 13 fields）基础上增加两个 backward-compatible 字段。**不引入新别名**，保持 v0.1 字段语义不变。

| 字段 | 类型 | 说明 |
|------|------|------|
| `source_id` | `str` | 稳定主键（sha1 of path） |
| `source_type` | `SourceType` | 来源类型枚举 |
| `source_path` | `str` | 原始文件路径（v0.1 字段，不变） |
| `title` | `str \| None` | 文档标题 |
| `raw_text` | `str` | LLM 真正读到的文本（v0.1 字段，不变） |
| `metadata` | `dict` | adapter 特有元信息（v0.1 字段，不变） |
| `content_hash` | `str` | sha256 content hash（v0.1 字段，不变） |
| `adapter_name` | `str` | adapter 类名（v0.1 字段，不变） |
| `extraction_warnings` | `list[ExtractionWarning]` | **v0.2 新增**：解析过程中的 warning |
| `provenance_blocks` | `list[ProvenanceBlock]` | **v0.2 新增**：provenance 链 |

**Backward-compatibility 策略**：
- v0.2 只新增 `extraction_warnings` 和 `provenance_blocks`，使用 `field(default_factory=list)`
- v0.1 字段全部保留原语义：`source_path` / `raw_text` / `content_hash` 不重命名
- 不引入 `original_path` / `extracted_text` / `content_fingerprint` / `provenance` 等别名字段——这些命名是 rejected alternatives
- 所有现有 adapter 无需立即修改（两个新字段默认空 list）

> **实现注意**：修改现有 `SourceDocument` dataclass（加两个 default-factory 字段），不新建 `SourceDocumentV2`。原则是最小化对 v0.1 adapter 的影响。

### 5.3 AdapterRegistry

```
AdapterRegistry
├── _adapters: dict[SourceType, SourceAdapter]
├── register(adapter) → None
├── find_for_path(path) → SourceAdapter | None
├── find_for_type(source_type) → SourceAdapter | None
└── list_supported_types() → list[SourceType]
```

Priority dispatch:
1. 按文件后缀精确匹配 → adapter
2. 无匹配 → 尝试 `can_handle()` 逐个 adapter
3. 仍无匹配 → 返回 UnsupportedSource skip

### 5.4 AdapterResult — 统一 Adapter 输出 Contract

`SourceAdapter.load()` 的唯一返回类型是 `AdapterResult`。不再通过 bare exception（如 `raise ValueError(skip_reason)`）表达正常 skip 路径。

```python
@dataclass(frozen=True)
class AdapterResult:
    """Adapter.load() 的唯一返回类型。"""
    status: str                          # "loaded" | "skipped" | "failed"
    document: SourceDocument | None      # status == "loaded" 时非 None
    skip_reason: str | None              # status == "skipped" 时：skip reason code
    error_message: str | None            # status == "failed" 时：error message
    warnings: list[ExtractionWarning]    # status == "loaded" 时的 extraction warnings

@dataclass(frozen=True)
class ExtractionWarning:
    code: str                          # e.g. "encoding_fallback", "table_loss"
    message: str                       # human-readable
    location: str | None               # page number / line number / section

@dataclass(frozen=True)
class ProvenanceBlock:
    source_type: str                   # "pdf" / "docx" / "txt" / "html"
    page: int | None                   # page number (PDF)
    section: str | None                # section heading (DOCX/HTML)
    offset_start: int | None           # byte offset in original
    offset_end: int | None
    extracted_as: str                  # "text" / "markdown_table" / "markdown_list"
```

**status 语义**：
- `loaded`：成功解析，`document` 非 None，`warnings` 可能非空
- `skipped`：正常 skip（unsupported format / scanned PDF / binary file / decode error 等），`skip_reason` 必填，`document` 为 None
- `failed`：解析异常（permission error / corrupt file / optional dep missing），`error_message` 必填，`document` 为 None

**Contrast with v0.1**：
- v0.1 用 `raise ValueError` / `raise PdfNoTextError` 表达 skip——scanner 必须 catch exception 来区分 skip 和 crash。
- v0.2 `load()` 不抛 exception 来表达正常 skip/fail。只有真正的编程错误（如 `NotImplementedError`）才允许抛。
- unsupported source / scanned PDF / decode error 必须走 `AdapterResult(status="skipped")` 或 `AdapterResult(status="failed")`，**不得**出现 `status="loaded"` + `document.raw_text=""` 的静默空输出。

### 5.5 Markdown Compatibility

`PlainMarkdownAdapter` 保持不变。所有 v0.1 Markdown 行为必须通过 characterization test 验证。

**Migration path**：
- Phase 1：characterization tests 捕获当前行为
- Phase 2：确认 `SourceDocument` 新字段与 Markdown adapter 兼容
- Phase 3：Markdown adapter 可选增加 extraction_warnings（如 frontmatter parse warning）

### 5.6 TXT Policy

| 项 | 决策 |
|----|------|
| 文件后缀 | `.txt` |
| source_type | `txt` |
| 编码检测 | UTF-8 first, chardet/cchardet fallback（optional dependency） |
| 编码失败 | friendly skip, reason = `decode_error` |
| 换行保留 | 保留原始换行，不做 normalize |
| 二进制检测 | 文件头非文本 → skip, reason = `binary_file` |
| 空文件 | 接受，`raw_text = ""`, warning = `empty_file` |
| 大文件 | > 10MB 给出 warning，> 50MB friendly skip |
| Line-based provenance | 可选：记录行数，不要求逐行 provenance |

### 5.7 HTML Policy

| 项 | 决策 |
|----|------|
| 文件后缀 | `.html`, `.htm` |
| source_type | `html` |
| 来源 | **local file only**，不做 URL 抓取 |
| Script/Style strip | 必做：移除 `<script>`, `<style>` 标签及内容 |
| Title extraction | 从 `<title>` tag 或第一个 `<h1>` 取 |
| Body extraction | 从 `<body>` 或整个 `<html>` 提取文本 |
| Headings 保留 | `<h1>`-`<h6>` → Markdown headings |
| Links 保留 | `<a href="...">` → `[text](url)` |
| Lists 保留 | `<ul>/<ol>/<li>` → Markdown lists |
| Noisy HTML | 提取文本占比 < 标签占比时发出 warning |
| External assets | 不 fetch `<img>`, `<link>`, `<script src>` 等外部资源 |
| Malformed HTML | best-effort parse, warning = `malformed_html` |
| 不执行 JS | 不解析/执行任何 JavaScript |
| 不保留 CSS | 不提取 style 信息 |

### 5.8 PDF Policy

| 项 | 决策 |
|----|------|
| 文件后缀 | `.pdf` |
| source_type | `pdf` |
| 文本提取 | pypdf `page.extract_text()`, 每页独立 |
| OCR | **不**做 |
| 扫描件 PDF | 文本层为空 → skip, reason = `scanned_pdf_no_text` |
| Page provenance | 每页一个 `ProvenanceBlock`（page=N） |
| 表格 | 不做 structured extraction |
| 多栏 | 不做 layout-aware extraction |
| 加密 PDF | skip, reason = `encrypted_pdf` |
| File size guard | > 50MB → skip, reason = `file_too_large` |
| Page count guard | > 500 pages → warning, 继续处理 |
| Metadata | 提取 title / author from PDF metadata |

### 5.9 DOCX Policy

| 项 | 决策 |
|----|------|
| 文件后缀 | `.docx` |
| source_type | `docx` |
| 文本提取 | python-docx, 遍历 `Document.paragraphs` + `Document.tables` |
| Headings | 识别 paragraph style heading → Markdown H1-H6 |
| Lists | 识别 numbered/bullet lists → Markdown list |
| Tables | 提取为 Markdown table（简单表格），复杂合并单元格 → plain text + warning |
| 宏 | 不执行，不做 macro extraction |
| 外部资源 | 不 fetch linked images / OLE objects |
| 格式丢失 warning | SmartArt, text boxes, embedded objects 不在提取范围时记录 warning |
| 不保证布局 | 明确声明不做 pixel-perfect 版式还原 |

### 5.10 Legacy DOC Policy

`.doc` (Microsoft Word 97-2003 binary format) 与 `.docx` (Office Open XML) 是**完全不同的格式**。

| 格式 | 容器 | 标准 | 解析方式 |
|------|------|------|----------|
| `.docx` | ZIP + XML | OOXML (ECMA-376) | python-docx, Mammoth, MarkItDown |
| `.doc` | OLE2 binary | proprietary | Apache Tika, LibreOffice, antiword |

**v0.2 第一阶段策略**：
- 不宣称"Word 全支持"，必须显式区分 `.docx` vs `.doc`
- `.doc` 文件在 registry dispatch 时产生 `unsupported_legacy_doc` skip reason
- M5 research gate 单独评估方案

**评估方案对比**：

| 方案 | Dependency | Platform Risk | Extraction Quality |
|------|-----------|---------------|-------------------|
| Apache Tika | JRE + tika-python | 高（Java runtime, 大 binary） | 高（元数据 + 文本） |
| LibreOffice headless | soffice binary | 高（需系统安装 LO, 进程管理） | 中（convert to docx/txt） |
| antiword | antiword binary | 中（macOS/Linux apt/brew） | 低（纯文本 only） |
| MarkItDown | Python package | 低（纯 Python 生态） | 中（需验证 .doc 支持） |

**推荐评估顺序**：MarkItDown → antiword (fallback) → skip

### 5.11 Unsupported Source Behavior

```python
class UnsupportedSourcePolicy:
    """所有不明格式的统一处理策略。"""
    
    # 已知但不支持的格式
    known_unsupported = {
        ".doc": "unsupported_legacy_doc",
        ".xlsx": "missing_optional_dependency",
        ".pptx": "missing_optional_dependency",
        ".epub": "missing_optional_dependency",
        ".rtf": "missing_optional_dependency",
        ".pages": "unsupported_proprietary_format",
        ".key": "unsupported_proprietary_format",
    }
    
    # 完全未知格式
    unknown_format_reason = "unsupported_format"
```

禁止行为：
- unsupported source **不能**静默成功（succeeded no-output）
- skip reason 必须被上层（CLI/Web）展示给用户
- skip reason 不泄露文件内容

### 5.12 Dependency Policy

| Dependency | 用途 | 状态 | 备注 |
|-----------|------|------|------|
| pypdf | PDF text extraction | optional: `mindforge[pdf]` | 已有 |
| python-docx | DOCX parsing | optional: `mindforge[docx]` | 已有 |
| chardet | TXT encoding detection | optional: `mindforge[txt]` | 新增（fallback to UTF-8） |
| beautifulsoup4 | HTML parsing | optional: `mindforge[html]` | 新增（fallback to stdlib html.parser） |
| mammoth | DOCX → HTML/Markdown | evaluate in M4 | 备选替代 python-docx |

所有 format-specific dependency 保持 optional extra。`mindforge` 基础安装只含 Markdown adapter。

### 5.13 Security / Privacy

- SourceAdapter **只读**，不修改原始文件
- HTML adapter **不执行** script/style 内容
- DOCX adapter **不执行**宏
- 所有 adapter **不 fetch** 外部资源（images, linked content, OLE objects）
- 不 auto-ingest 真实 Obsidian vault
- 不输出 secrets 到 SourceDocument
- Extraction warning 不泄露文件路径中的敏感信息（相对路径展示）

### 5.14 Error Handling

所有 adapter 返回 `AdapterResult`，不抛 exception 表达 skip/fail。Scanner 在 adapter 层统一处理：

```
AdapterResult(status="loaded")  → 继续 pipeline（document 传给 processor）
AdapterResult(status="skipped") → 记录 skip reason，继续下一个文件
AdapterResult(status="failed")  → 记录 error message，继续下一个文件
```

常见 status 映射：

| 场景 | status | 字段 |
|------|--------|------|
| 解析成功 | `loaded` | `document` 非 None |
| 不支持的格式 | `skipped` | `skip_reason="unsupported_format"` |
| Legacy .doc | `skipped` | `skip_reason="unsupported_legacy_doc"` |
| 扫描件 PDF 无文本 | `skipped` | `skip_reason="scanned_pdf_no_text"` |
| 编码检测失败 | `skipped` | `skip_reason="decode_error"` |
| 二进制文件 | `skipped` | `skip_reason="binary_file"` |
| 文件过大 | `skipped` | `skip_reason="file_too_large"` |
| 加密 PDF | `skipped` | `skip_reason="encrypted_pdf"` |
| 文件不存在 | `failed` | `error_message="FileNotFoundError: ..."` |
| 无读取权限 | `failed` | `error_message="PermissionError: ..."` |
| 可选依赖未安装 | `failed` | `error_message="OptionalDependencyError: ..."` |
| 文件损坏 / 解析异常 | `failed` | `error_message="..."` |

所有 adapter error 不应 crash 整个 scan/process pipeline。Single file failure → 记录 skip/fail → 继续下一个文件。

---

## 6. CLI UX

扩展 `mindforge import` / `mindforge watch add` 的 source type 展示：

```
$ mindforge import document.txt
✓ Source added: document.txt (type: txt)
  Adapter: TxtAdapter
  Encoding: utf-8
  Lines: 42

$ mindforge import scanned.pdf
✗ Source skipped: scanned.pdf
  Reason: scanned_pdf_no_text — PDF has no extractable text layer (likely scanned).
  Suggestion: Run OCR externally before importing.

$ mindforge import legacy.doc
✗ Source skipped: legacy.doc
  Reason: unsupported_legacy_doc — .doc (Word 97-2003) is not the same as .docx.
  Supported formats: .md, .txt, .html, .pdf, .docx
```

---

## 7. Web UX

- **Sources page**：显示 source_type icon/label、adapter name、extraction warnings 数量
- **Add Source dialog**：显示支持的格式列表
- **Unsupported file**：红色 skip reason，hover 显示详情和建议

---

## 8. Testing Strategy

### 8.1 Characterization Tests
- PlainMarkdownAdapter 所有现有行为 → 不变
- CommonDocumentAdapter 现有行为 → TXT/HTML 移出后，验证剩余格式行为不变

### 8.2 Synthetic Fixture Tests
- 每个 adapter 提供：
  - 正常 fixture（valid TXT/HTML/PDF/DOCX）
  - 空文件 fixture
  - 大文件 fixture（size guard）
  - 恶意 fixture（XSS in HTML, macro DOCX, binary-as-TXT）
  - 边界 fixture（malformed HTML, encrypted PDF, corrupted DOCX）

### 8.3 Integration Tests
- Registry dispatch → adapter → SourceDocument → pipeline 全链路
- Processor 只通过 SourceDocument 消费，不直接依赖 adapter

### 8.4 Acceptance Tests
- 每个 acceptance criterion 至少一个 test case
- 见 ROADMAP 各 milestone acceptance criteria

---

## 9. Rollout Plan

| Phase | Content | Milestone |
|-------|---------|-----------|
| Phase 1 | SourceAdapter interface stabilization + characterization | M1 |
| Phase 2 | TXT + HTML standalone adapters | M2 |
| Phase 3 | PDF adapter enhancement (page provenance) | M3 |
| Phase 4 | DOCX adapter enhancement (structure preservation) | M4 |
| Phase 5 | Legacy DOC research gate + decision | M5 |

每个 phase 完成后可独立 ship。

---

## 10. Open Questions

1. **SourceDocument 升级方式**：修改现有 `SourceDocument`（加 default-factory 字段）vs 新建 `SourceDocumentV2` 并做 adapter 迁移？推荐前者以保持 backward-compat。
2. **TXT encoding detection library**：`chardet` vs `cchardet`？推荐 `chardet` 作为 optional dependency。
3. **HTML parsing library**：`beautifulsoup4` vs stdlib `html.parser`？推荐 `beautifulsoup4` 作为 optional dependency，stdlib 作为 fallback。
4. **Mammoth vs python-docx for DOCX**：Mammoth 输出更干净的语义 HTML/Markdown，但引入额外依赖。推荐保持 python-docx 作为默认，Mammoth 作为可选的 enhanced extraction path。
5. **CommonDocumentAdapter 未来**：TXT/HTML 移出后，剩余格式（JSON/CSV/TSV/XML/URL/webloc）是否保持为 common_document？推荐是——这些小众格式共享一个 adapter 是合理的。

---

## 11. Acceptance Criteria

- [ ] 每个支持格式有独立 `SourceAdapter` 实现
- [ ] `SourceDocument` 包含 `extraction_warnings` 和 `provenance_blocks` 字段
- [ ] Markdown characterization tests 全部 pass
- [ ] TXT/HTML 不在 `CommonDocumentAdapter` 中处理
- [ ] Processor 完全不 import 格式相关库
- [ ] 所有 unsupported format 产生友好 skip reason
- [ ] 安全测试通过（no script execution, no macro execution, no external fetch）
- [ ] `.doc` 与 `.docx` 在文档和代码中明确区分
