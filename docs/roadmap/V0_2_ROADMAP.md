# MindForge v0.2 Roadmap: Multi-source Ingestion + Wiki Presentation

> **Status**: Draft
> **Branch**: feat-wiki-llm-synthesis → future v0.2 branch
> **Date**: 2026-05-14
>
> This roadmap defines v0.2 scope. Implementation follows RFCs and SDDs under
> `docs/rfc/` and `docs/sdd/`; development rules are in `docs/V0_2_DEVELOPMENT_RULES.md`.

---

## 1. v0.1 Baseline

v0.1 已完成并作为 baseline 上线：

- **local-first / LLM-first 主链路**：Source → AI Draft → Human Review → Explicit Approve → Approved Card
- **Web Setup**：模型配置、API key 管理（local secret store）
- **Markdown source**：`PlainMarkdownAdapter` + `CommonDocumentAdapter` 覆盖 .md
- **ai_draft 生成**：五段 Knowledge Card Workflow（Triage / Distill / Link / Review / Action）
- **explicit approve**：`ai_draft` → 用户显式确认 → `human_approved`
- **Library / Recall / Wiki**：基于 `human_approved` cards 的 Library 浏览、BM25 检索、LLM-first Wiki synthesis
- **Workspace / Config / Secrets anchor**：`mindforge init` 创建 workspace，runtime config 与 secret store 分离
- **Provider timeout/retry**：有界 timeout，可配置 retry
- **Public docs / CI**：README、RELEASE_NOTES、TESTING、GitHub Actions CI

现有 source adapter 清单（v0.1）：

| Adapter | source_type | 状态 |
|---------|-------------|------|
| PlainMarkdownAdapter | plain_markdown | implemented |
| CommonDocumentAdapter | common_document | implemented（涵盖 .txt/.html/.json/.csv 等） |
| PdfAdapter | pdf | implemented（pypdf, text-based only） |
| DocxAdapter | docx | implemented（python-docx, paragraphs only） |
| CuboxMarkdownAdapter | cubox_markdown | implemented |
| WebClipMarkdownAdapter | webclip_markdown | implemented |
| CuboxApiAdapter | cubox_api | implemented（real_api opt-in） |

现有 Wiki 能力（v0.1）：

- **deterministic rebuild**：`rebuild_main_wiki()`，模板渲染，不调 LLM
- **LLM synthesis**：`llm_rebuild_wiki()`，调用配置模型生成 overview + sections + card references
- **Wiki CLI**：`mindforge wiki status/rebuild/show`
- **Web Wiki page**：Rebuild Wiki 按钮 + Advanced 折叠区 deterministic fallback
- **展示粗糙**：纯 Markdown 文件输出，无结构化渲染、无 TOC、无 section nav、empty/error state 有限

---

## 2. v0.2 Scope

### 2.1 SourceAdapter v2

将 v0.1 中分散在 `CommonDocumentAdapter` 内的 TXT/HTML 解析和已有独立 adapter 统一为第一级 `SourceAdapter` 实现：

- **Markdown baseline compatibility**：保持 `PlainMarkdownAdapter` 行为不变，所有 regression test 通过
- **TXT source support**：独立 `TxtAdapter`，UTF-8 编码检测、换行保留、二进制拒绝
- **PDF text source support**：保持 `PdfAdapter` text-based only，增加 page-level provenance
- **local HTML file source support**：独立 `HtmlAdapter`，script/style strip、title/main/body extraction、links/headings/lists 保留
- **DOCX source support**：保持 `DocxAdapter`，增加 heading/paragraph/list/table structure extraction
- **legacy DOC research**：单独评估 `.doc` 支持方案（见 §2.3），不作为 v0.2 第一阶段保证
- **unsupported source friendly skip**：不明格式给出明确 skip reason，不静默成功
- **source provenance**：每个 adapter 输出 extraction_warnings + provenance metadata

### 2.2 Wiki Presentation

在现有 LLM-first Wiki synthesis 基础上增强展示层：

- **Wiki structured rendering**：Wiki page 从纯 Markdown 文件输出升级为结构化视图模型
- **Wiki TOC / section navigation**：根据 section 自动生成目录，支持跳转
- **Wiki card/source references**：展示每个 section 关联的 approved card 和原始 source provenance
- **Wiki empty/error/loading states**：无 approved cards / LLM 调用失败 / 正在合成 等状态
- **Wiki rendering safety**：Markdown sanitization、XSS 防护、禁止 unsafe embedded HTML

---

## 3. v0.2 Non-goals

以下明确不作为 v0.2 scope：

- **OCR**：不做扫描件 PDF / 图片 OCR
- **URL crawling**：不做远程网页抓取
- **Browser extension**：不做浏览器插件
- **RAG / embedding**：不做向量检索 / embedding
- **Obsidian plugin**：不做 Obsidian 插件
- **graph database**：不做图数据库
- **graph visualization**：不做知识图谱可视化
- **automatic semantic merge**：不做自动语义合并
- **changing knowledge card schema**：不改 `ai_draft` / `human_approved` card schema
- **changing approval semantics**：不改 approval 状态机
- **claiming full .doc support**：除非 extractor dependency 被明确接受，否则不宣称 Word 全支持
- **preserving full Word/PDF visual formatting**：不做 Word/PDF 版式还原

---

## 4. Milestones

### Milestone 1: SourceAdapter Foundation

**Goal**: 确立 v0.2 SourceAdapter 接口规范，完成 Markdown adapter 的 characterization 和 registry/dispatch 增强。

**User value**: 保证 Markdown 行为不回退，为后续 adapter 建立统一基础。

**Non-goals**: 不新增 adapter 类型，不改 processor 逻辑。

**Acceptance criteria**:
- `SourceAdapter` 接口不变（保持 `can_handle` + `load` 契约）
- `SourceDocument` 增加 `extraction_warnings` 和 `provenance_blocks` 字段（backward-compatible）
- `PlainMarkdownAdapter` characterization tests 全部通过（作为 regression baseline）
- Registry 支持 adapter 优先级和 fallback
- Unsupported source 产生友好 skip reason（结构化 `AdapterResult`），不抛 unhandled exception

**Required tests**:
- `tests/test_source_adapter_v2_contract.py`：SourceAdapter 接口契约
- `tests/test_source_document_v2.py`：SourceDocument v2 字段验证
- `tests/test_markdown_adapter_characterization.py`：Markdown 现有行为不变
- `tests/test_registry_priority.py`：adapter 优先级派发
- `tests/test_unsupported_skip.py`：不明格式 friendly skip

**Evidence to collect**:
- 所有 adapter characterization tests pass
- Markdown adapter no-regression evidence

**Review gate**: RFC review + SDD alignment + characterization test report

---

### Milestone 2: TXT and Local HTML Adapters

**Goal**: TXT 和 HTML 作为独立 `SourceAdapter` 实现，替换 `CommonDocumentAdapter` 中的内联 parser。

**User value**: 用户可以 import `.txt` 和 `.html` 文件，获得明确的 source_type 和 provenance。

**Non-goals**: 不做 URL fetching、不做 browser rendering、不做 CSS layout extraction。

**Acceptance criteria**:
- `TxtAdapter`：UTF-8 编码检测、换行保留、二进制文件拒绝、encoding 失败时 friendly skip
- `HtmlAdapter`：script/style strip、`<title>` extraction、headings/links/lists 保留为 Markdown-ish text、noisy HTML 输出 warning
- 两个 adapter 输出标准 `SourceDocument`，含 `extraction_warnings`
- `CommonDocumentAdapter` 不再承担 .txt/.html 解析

**Required tests**:
- `tests/adapters/test_txt_adapter.py`：synthetic TXT fixtures（UTF-8 / 空文件 / 二进制 / 大文件）
- `tests/adapters/test_html_adapter.py`：synthetic HTML fixtures（简单页面 / 含 script / 含 style / malformed / 空 title）
- `tests/test_common_document_boundary.py`：确认 .txt/.html 不再经过 CommonDocumentAdapter

**Evidence to collect**:
- TXT adapter 对 edge cases 的 extraction_warnings 记录
- HTML adapter 对 noisy input 的 warning 记录

**Review gate**: RFC alignment + synthetic fixture test coverage + processor pipeline 只消费 SourceDocument

---

### Milestone 3: PDF Text Adapter Enhancement

**Goal**: 增强 PdfAdapter，增加 page-level provenance 和更明确的 scanned-PDF detection。

**User value**: PDF 处理后能看到每页文本的来源（page provenance），扫描件能得到友好提示。

**Non-goals**: 不做 OCR、不做表格完美提取、不做图片 PDF。

**Acceptance criteria**:
- `PdfAdapter` 输出 page-level provenance（`provenance_blocks`）
- Scanned PDF 明确标记为 `unsupported_scanned_pdf`，输出 skip reason
- File size guard：超过阈值（如 50MB）友好跳过
- Page count guard：超过阈值（如 500 页）友好警告

**Required tests**:
- `tests/adapters/test_pdf_adapter.py`：synthetic text-based PDF（单页 / 多页 / 空文本层 / 大文件 size guard）
- `tests/test_pdf_page_provenance.py`：page-level provenance 验证

**Evidence to collect**:
- page provenance 格式样例
- scanned PDF detection 准确率（synthetic fixtures）

**Review gate**: RFC alignment + page provenance contract + no OCR claims

---

### Milestone 4: DOCX Adapter Enhancement

**Goal**: 增强 DocxAdapter，保留更多语义结构（headings / lists / tables）。

**User value**: DOCX 文档处理后保留层级结构和列表，不只是纯文本段落拼合。

**Non-goals**: 不做样式保留、不做宏执行、不做外部资源加载、不保证 pixel-perfect 布局。

**Acceptance criteria**:
- Headings 保留层级关系（H1-H6），转为 Markdown heading
- Paragraphs 保留段落分隔
- Lists 保留有序/无序列表结构（Markdown list syntax）
- Tables 转为 Markdown table（feasible 范围内）
- Extraction warnings 记录格式丢失（如 SmartArt / embedded objects）
- 不执行宏、不 fetch 外部资源

**Required tests**:
- `tests/adapters/test_docx_adapter.py`：synthetic DOCX（含 headings / lists / tables / 混合内容 / 空文档）
- `tests/test_docx_extraction_warnings.py`：格式丢失 warning 验证
- `tests/test_docx_safety.py`：不执行宏（恶意 fixture 安全测试）

**Evidence to collect**:
- DOCX → Markdown 转换样例（headings / lists / tables）
- Extraction warnings 记录

**Review gate**: RFC alignment + semantic structure preservation + macro safety

---

### Milestone 5: Legacy DOC Research Gate

**Goal**: 评估 `.doc` 支持方案，做出 go/no-go/optional-extra 决策。

**User value**: 明确 `.doc` 支持策略，不误导用户"Word 全支持"。

**Non-goals**: 不实现 `.doc` adapter（除非决策通过），不在评估前做任何 `.doc` 承诺。

**Acceptance criteria**:
- 对比以下方案的技术风险：
  - **Apache Tika**：Java runtime 依赖、平台兼容性、text extraction 质量
  - **LibreOffice headless**：`soffice --headless --convert-to` 管道、进程管理、平台依赖
  - **antiword / catdoc**：Linux/macOS 可用性、输出质量
  - **MarkItDown**（如支持）：Python 生态内方案、格式覆盖范围
- 输出决策文档：`docs/rfc/RFC_0003_LEGACY_DOC_EVALUATION.md`（或作为 RFC_0001 的附录）
- 决策结果：support / skip / optional-extra（需人工审批）

**Required tests**: 无需代码测试（research-only gate）。

**Evidence to collect**:
- 每个方案的 dependency / platform risk 矩阵
- 推荐方案及其 trade-offs

**Review gate**: 人工审批 dependency decision

---

### Milestone 6: Wiki Presentation Foundation

**Goal**: 建立 Wiki 结构化展示层，替代当前纯 Markdown 文件 dump。

**User value**: 用户看到更好的 Wiki 阅读体验——结构化布局、章节导航、来源引用。

**Non-goals**: 不改 card schema、不改 approval 语义、不实现 graph view、不新增数据持久化。

**Acceptance criteria**:
- `WikiPageViewModel`：结构化 wiki 数据模型（overview / sections / references / metadata）
- `WikiSectionView`：section 视图（title / body / card_ids / source_refs）
- `WikiReferenceView`：card/source 引用视图（card title / source_path / source_type / approval date）
- `WikiRenderer`：渲染抽象（当前 text/markdown renderer，为 graph renderer 留注册点）
- `WikiMarkdownRenderer`：safe Markdown → HTML 渲染，含 sanitization
- TOC 自动生成（根据 sections 层级）
- Section 导航（within-page jump）
- 空态：无 approved cards / wiki 未生成
- 错误态：LLM synthesis 失败 / JSON 解析失败
- 加载态：synthesis 进行中

**Required tests**:
- `tests/wiki/test_wiki_view_model.py`：WikiPageViewModel 构建和序列化
- `tests/wiki/test_wiki_markdown_renderer.py`：Markdown 渲染 + sanitization
- `tests/wiki/test_wiki_empty_states.py`：空态/错误态渲染
- `tests/wiki/test_wiki_toc.py`：TOC 生成逻辑
- `tests/wiki/test_wiki_future_graph_interface.py`：graph renderer 注册点存在且不实现

**Evidence to collect**:
- Wiki page 渲染截图 / HTML 输出样例
- Sanitization test 覆盖（XSS payload）

**Review gate**: RFC alignment + rendering safety + future graph interface

---

### Milestone 7: Wiki Rendering Security and UX

**Goal**: 确保 Wiki 渲染安全（XSS 防护 / sanitization）和用户体验（可访问性 / 响应式）。

**User value**: 安全地查看 Wiki 内容，不会因为渲染引擎执行恶意脚本。

**Non-goals**: 不实现 Mermaid/diagram 渲染（留接口但不实现）。

**Acceptance criteria**:
- Markdown 渲染经过 sanitization（禁用 `<script>`、`<iframe>`、`onclick` 等）
- 禁用 unsafe embedded HTML by default
- 可选 Mermaid/code block 策略：如果未来支持，必须 sandbox / strict CSP
- 不直接 `innerHTML` 未净化内容
- No secret exposure in rendered output
- HTML `<title>` / `aria-label` 可访问性

**Required tests**:
- `tests/wiki/test_wiki_xss_prevention.py`：XSS payload 验证
- `tests/wiki/test_wiki_sanitization.py`：sanitization 规则测试
- `tests/wiki/test_wiki_secret_exposure.py`：secret 不出现于渲染输出
- `tests/wiki/test_wiki_accessibility.py`：可访问性基础标签

**Evidence to collect**:
- XSS test payload coverage
- Accessibility audit (Lighthouse)

**Review gate**: Security review + XSS test pass

---

## 5. Milestone Summary

| # | Milestone | Depends On | Estimated Effort |
|---|-----------|-----------|-----------------|
| M1 | SourceAdapter Foundation | — | S |
| M2 | TXT + HTML Adapters | M1 | M |
| M3 | PDF Adapter Enhancement | M1 | S |
| M4 | DOCX Adapter Enhancement | M1 | M |
| M5 | Legacy DOC Research Gate | M4 | S (research) |
| M6 | Wiki Presentation Foundation | — | L |
| M7 | Wiki Rendering Security + UX | M6 | M |

**Effort Key**: S = 1-3 days, M = 3-7 days, L = 7-14 days

---

## 6. Related Documents

- [RFC_0001_SOURCE_ADAPTER_V2.md](../rfc/RFC_0001_SOURCE_ADAPTER_V2.md)
- [RFC_0002_WIKI_PRESENTATION_V2.md](../rfc/RFC_0002_WIKI_PRESENTATION_V2.md)
- [SDD_SOURCE_ADAPTER_V2.md](../sdd/SDD_SOURCE_ADAPTER_V2.md)
- [SDD_WIKI_PRESENTATION_V2.md](../sdd/SDD_WIKI_PRESENTATION_V2.md)
- [V0_2_DEVELOPMENT_RULES.md](../V0_2_DEVELOPMENT_RULES.md)
