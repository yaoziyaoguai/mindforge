# RFC 0003 — Legacy .doc 格式支持评估

> **Status**: Accepted（Deferred to v0.3+）
> **Author**: Source Module Independent Audit
> **Date**: 2026-05-15
> **References**: RFC_0001 §5.9, SDD §11 M5, ~~V0_2_ROADMAP~~ §4 M5 (removed 2026-05-27 — docs cleanup batch 1)

---

## 1. Context

### 1.1 背景

v0.2 SourceAdapter 通过 `DocxTextAdapter` 支持现代 `.docx`（Office Open XML）格式。
`.docx` 是 ECMA-376 / ISO/IEC 29500 标准格式，实质是 ZIP 压缩的 XML 文档集合，
可用纯 Python 库 `python-docx` 解析。

legacy `.doc` 是 Microsoft Word 97-2003 使用的 **OLE Compound Document Binary** 格式
（Microsoft Compound File Binary Format, CFB）。它与 `.docx` 在结构、解析方式上
完全不同：

| 特性 | `.docx` | `.doc` |
|------|---------|--------|
| 格式标准 | ECMA-376 (Open XML) | 无公开标准 |
| 容器 | ZIP | OLE CFB (binary) |
| 解析方式 | XML DOM / SAX | 二进制反序列化 |
| 纯 Python 库 | python-docx, lxml | 无成熟方案 |
| 跨平台 | 天然 | 依赖外部工具 |

### 1.2 问题

用户在 import 过程中可能遇到 `.doc` 文件。当前 v0.2 对其行为：
- `DocxTextAdapter.can_handle("file.doc")` → `False`
- `AdapterRegistry` 无匹配 → unsupported skip
- 用户看到的 skip reason 是通用 unsupported，未区分 "永不支持" vs "未来可能支持"

需要明确决策并记录在 RFC 中。

---

## 2. Decision

**v0.2 不实现 legacy .doc 支持。**

- `.doc` 通过 `can_handle` 直接拒绝，返回 unsupported。
- 不新增 Java / LibreOffice / external command 依赖。
- 不执行宏。
- 不调用外部程序进行格式转换。
- `.doc` 支持留待 v0.3+，届时可基于 explicit dependency decision 重新评估。

---

## 3. Options Considered

### 3.1 Apache Tika

- **方案**：Apache Tika server / `tika-python` 包装器
- **优点**：格式覆盖极广，text extraction 质量高
- **风险**：
  - 内置 Java runtime 依赖（JVM ≥ Java 8）
  - Tika server 需独立进程管理
  - 平台兼容性：JVM 在 ARM macOS 上的行为差异
  - 与 local-first / 零外部进程原则冲突

### 3.2 LibreOffice headless

- **方案**：`soffice --headless --convert-to txt` 管道
- **优点**：格式还原度最高，支持几乎所有 Word 版本
- **风险**：
  - 需要安装 LibreOffice（macOS: ~800MB, Linux: apt-get 依赖链）
  - 进程管理复杂（启动时间、并发、超时、zombie 进程）
  - 平台依赖强（Windows / macOS / Linux 安装路径不同）
  - 可能与 MindForge shell 进程模型冲突

### 3.3 antiword / catdoc

- **方案**：Linux/macOS 原生命令行工具
- **优点**：轻量，启动快
- **风险**：
  - macOS 上 antiword 已多年未维护（Homebrew 无官方 formula）
  - 仅提取纯文本，丢失所有结构
  - Windows 不可用
  - 输出质量参差不齐

### 3.4 MarkItDown

- **方案**：Microsoft 开源的 MarkItDown（Python）
- **优点**：Python 生态内，支持多种格式
- **风险**：
  - 对 `.doc` 的支持依赖于后台调用 LibreOffice 或 Textract
  - 非纯 Python 方案，仍依赖外部进程
  - 仍在早期阶段，API 不稳定

### 3.5 Pure Python fallback

- **方案**：`olefile` + 手动 CFB 解析
- **优点**：零外部依赖
- **风险**：
  - 无成熟 Word 97-2003 binary format parser
  - Word Binary File Format (.doc) 规范超过 500 页
  - 自行实现工作量大且极易出错
  - 社区共识：不建议自行实现 .doc binary parser

---

## 4. Decision Rationale

选择 **v0.2 不做 .doc** 的原因：

1. **local-first 安全**：所有外部进程方案（Tika / LibreOffice / antiword）都违反 local-first / zero external process 原则，可能引入进程逃逸 / 资源泄漏 / 平台兼容风险。

2. **dependency footprint**：任何可行方案都会显著增加 MindForge 的依赖链——Java runtime (~200MB)、LibreOffice (~800MB) 或不可靠的平台原生工具。

3. **platform portability**：MindForge 目标是 macOS / Linux / Windows 三平台。目前的外部工具方案在至少一个平台上存在可用性问题。

4. **no external process**：MindForge 作为 Python CLI 工具，生命周期内不应 fork 不可控外部进程。

5. **avoid hidden execution risk**：.doc 格式历史上有宏病毒风险。虽然本方案不执行宏，但外部转换工具（如 LibreOffice）在转换过程中可能触发宏执行，增加安全风险。

---

## 5. Current Behavior

- `.doc` 不被任何 v0.2 adapter 声称支持。
- `.docx` 由 `DocxTextAdapter` 支持（headings / tables / extraction_warnings）。
- `.doc` 路径在 `AdapterRegistry.find_for_path()` 中返回 `None`（unsupported）。
- `classify_source_path()` 对 `.doc` 返回 `{matched: false, status: "unsupported"}`。
- `preview_source_load()` 对 `.doc` 返回 `AdapterResult.skipped`。

---

## 6. Future Work (v0.3+)

v0.3 可在以下条件下重新评估 `.doc` 支持：

1. **明确的依赖选择**：选择一个维护良好的方案（如 MarkItDown 成熟版本），并在 pyproject.toml 中显式声明为 `[project.optional-dependencies]` 的 `legacy-doc` 组。
2. **用户 opt-in**：用户须显式安装 `mindforge[legacy-doc]`，默认不安装。
3. **安全沙箱**：如果方案涉及外部进程，必须定义进程超时、资源限制、错误恢复策略。
4. **测试覆盖**：synthetic `.doc` fixtures + malformed file handling + process timeout 测试。
5. **人工审批**：dependency decision 需要 RFC review + 人工审批。

---

## 7. Non-goals (v0.2)

- 不实现 full Word layout preservation
- 不执行宏（任何格式）
- 不在 v0.2 集成 LibreOffice / Tika / antiword / catdoc / MarkItDown
- 不宣称 "Word 全支持"
- 不修改 card schema 以适配 .doc

---

## 8. Acceptance Criteria

- [x] `.doc` vs `.docx` 区分在代码中清晰可见（`DocxTextAdapter.can_handle`）
- [x] `.doc` 被 `can_handle` 拒绝，不尝试任何解析
- [x] Legacy DOC 设计边界记录在 `docx_adapter.py` module docstring
- [x] 本 RFC 记录了决策、备选方案评估、未来工作路径
- [ ] v0.3+ 重新评估（如有需求）

---

## 9. Review Sign-off

| Reviewer | Role | Date | Status |
|----------|------|------|--------|
| — | Source Module Auditor | 2026-05-15 | Accepted |
| — | — | v0.3+ | Deferred |
