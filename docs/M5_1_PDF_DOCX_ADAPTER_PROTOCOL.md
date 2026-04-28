# M5.1 — PDF / Docx SourceAdapter Protocol（v0.2.4 stub 状态）

> 状态：**仅占位 stub**。v0.2.4 起 `PdfAdapter` / `DocxAdapter` 仍然是 stub，
> 调用 `load()` 会抛 `NotImplementedError`。本文锁定**为什么是 stub**、
> **未来落地的边界**，以及**绝不会在 MindForge 里做的事**。

---

## 1. 当前行为

- 类位置：`src/mindforge/sources/stubs.py`
- `source_type`：`pdf` / `docx`
- `can_handle(path)`：始终返回 `False`（避免被 Scanner 误派发）
- `load(path)`：抛 `NotImplementedError("PDF/Docx adapter 仍为占位 ...")`
- `configs/mindforge.yaml`：`registry.pdf.enabled = false` / `registry.docx.enabled = false`
- `sources.enabled` 默认**不**包含 `pdf` / `docx`

→ 用户即使把 PDF / Docx 文件放进 `00-Inbox/PDFs/` 或 `00-Inbox/Docs/`，
Scanner 也不会处理它们，更不会上传到任何远端。

## 2. 为什么 v0.2.4 仍然不实现

1. **复杂度高、回报低**：PDF 真实世界的解析问题（多栏、表格、扫描件、字符
   编码、嵌入图片、注释层）一旦展开会迅速吃掉一个 milestone。
2. **不是 MindForge 的差异化**：Cubox / Web Clipper / 手写 Markdown 已经覆盖了
   作者本人 90% 以上的输入；PDF / Docx 主要是工作场景，可单独项目处理。
3. **避免 OCR 引入大依赖**：tesseract / paddleocr / 云 OCR 都会破坏 v0.x"零
   外网依赖、可离线跑"的承诺。
4. **避免 PDF 解析库的 GPL/LGPL 风险**：未来若引入需要单独审计协议。

## 3. 未来落地（M5.1+）的硬性边界

如果未来真的要做，必须遵守：

1. **不做 OCR**：扫描件不在 v1 范围；遇到无文本层 PDF 直接归档为 `failed`，
   并在 state.json 记录 `error_code = no_text_layer`。
2. **不做表格抽取**：表格一律转成"行连接"的纯文本兜底，不试图重建结构。
3. **不做版式还原**：footer / header / 页码统一去除，保留正文段落。
4. **库选型：只用 pure-Python**（如 `pypdf`、`python-docx`），且 **lazy import**。
   未启用 PDF/Docx 的用户不该被强制安装这些依赖。
5. **不抓取 PDF 内嵌的超链接做"自动相关性"**——这越界进入 RAG 范畴。
6. **依然遵守 SourceDocument 契约**：title / source_url / created_at /
   raw_text / content_hash 字段必须齐全；解析失败必须降级到"原文件名 + 文件
   长度"作为 hash 输入，而不是抛裸异常。

## 4. 错误信息约定

stub 抛出的异常消息中包含字符串 `M5_1_PDF_DOCX_ADAPTER_PROTOCOL`，方便用户
搜索本协议文档。

## 5. 不变量

| 项 | 现在（v0.2.4） | 未来 v1 落地后 |
|---|---|---|
| 是否在 `sources.enabled` 默认列表 | ❌ | 由用户显式开启 |
| 是否依赖外网 / OCR | ❌ | ❌ |
| 是否能修改原始 PDF/Docx | ❌ | ❌ |
| 是否调用 LLM | ❌ | 仅在 process pipeline 中（同其他 adapter） |
| 是否引入新 GPL 依赖 | ❌ | ❌ |
