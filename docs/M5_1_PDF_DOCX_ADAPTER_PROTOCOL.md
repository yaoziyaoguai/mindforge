# M5.1 — PDF / Docx SourceAdapter Protocol（v0.2.5 最小真实实装）

> 状态：**最小真实实装**。v0.2.5 起 `PdfAdapter` / `DocxAdapter` 已具备最小文本抽取
> 能力，**通过 lazy import** 暴露在 `mindforge[pdf]` / `mindforge[docx]` extras。
> 本文锁定**做了什么、不做什么**、未来增强的边界。

---

## 1. 当前行为（v0.2.5）

- 类位置：`src/mindforge/sources/pdf.py`、`src/mindforge/sources/docx.py`
  （旧路径 `src/mindforge/sources/stubs.py` 仍可 import，作向后兼容 shim）
- `source_type`：`pdf` / `docx`
- `can_handle(path)`：按扩展名识别
- `load(path)`：
  - 若 `pypdf` / `python-docx` 未安装 → 抛 `OptionalDependencyError`，
    错误消息形如 `pip install mindforge[pdf]`，并指向本协议文档。
  - 若文件可解析但无文本层（典型扫描件 PDF）→ 抛 `PdfNoTextError`，
    **不**降级为空内容卡片、**不**做 OCR。
  - 否则返回完整 `SourceDocument`（含 `raw_text` + `content_hash` + `metadata`）。
- `configs/mindforge.yaml`：`registry.pdf` / `registry.docx` 默认 `enabled: false`。
  → 即使把文件放进 `00-Inbox/PDFs/`，未在 `sources.enabled` 显式开启时不会被处理。

## 2. 为什么仍然不做 OCR / 表格 / 版式还原

1. 复杂度高、回报低；扫描件 OCR 是单独项目。
2. 不引入 tesseract / paddleocr / 云 OCR，守住"零外网依赖、可离线跑"。
3. 不引入 GPL/LGPL 依赖；`pypdf` / `python-docx` 均为 BSD-style。
4. 表格 / 多栏版式重建不是 MindForge 的差异化。

## 3. 硬性边界（v0.2.5 起强制遵守）

1. **不做 OCR**：无文本层 PDF → `PdfNoTextError`，state.json 记 `error_code = no_text_layer`。
2. **不做表格抽取**：表格按行连接成纯文本兜底，不重建结构。
3. **不做版式还原**：page header/footer/页码不主动剥离，仅按页拼接 `raw_text`。
4. **lazy import**：未启用 PDF/Docx 的用户不该被强制安装 `pypdf` / `python-docx`。
5. **不抓 PDF 内嵌超链接做"自动相关性"**——这是 RAG 范畴。
6. **遵守 SourceDocument 契约**：title / created_at / raw_text / content_hash 字段必须齐全；
   解析失败显式异常，不裸抛、不静默成功。

## 4. 错误信息约定

- `OptionalDependencyError("pip install mindforge[pdf]") `
- `PdfNoTextError("no text layer ...; see docs/M5_1_PDF_DOCX_ADAPTER_PROTOCOL.md")`

## 5. 不变量

| 项 | v0.2.5 现状 | 增强落地后（候选） |
|---|---|---|
| 是否在 `sources.enabled` 默认列表 | ❌ | 由用户显式开启 |
| 是否依赖外网 / OCR | ❌ | ❌ |
| 是否能修改原始 PDF/Docx | ❌ | ❌ |
| 是否调用 LLM | ❌ | 仅在 process pipeline 中（同其他 adapter） |
| 是否引入新 GPL 依赖 | ❌ | ❌ |
| 是否抽表格 | ❌ | 仅"行连接兜底" |
