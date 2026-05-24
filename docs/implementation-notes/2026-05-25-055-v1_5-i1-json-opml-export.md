# v1.5 I1: JSON/OPML 导出格式 — Implementation Note

**Date:** 2025-05-25
**Status:** Complete

## What was done

扩展现有 Markdown-only 导出端点，新增 JSON 和 OPML 格式支持。前端导出预览面板增加格式选择器。

## Changes

### Backend — schemas.py
- `ExportCardsRequest.format`: 新增可选字段，默认 `"markdown"`，支持 `"json"`, `"opml"`
- `ExportCardsResponse`: 新增 `json_data`（alias `"json"`）、`opml`、`format` 字段

### Backend — routers/library.py
- 重构导出逻辑为统一的 card data 收集 → 按 format 序列化
- JSON 格式: `{"exported_at": ..., "card_count": N, "cards": [{title, status, created_at, source_title, body}]}`
- OPML 格式: 标准 OPML 2.0 XML，cards 作为 `<outline type="card">` 元素，含 status/source/created 属性和 `_note` body 摘要
- 所有格式保持白名单安全策略（仅导出 title/status/created_at/source_title/body）

### Frontend — LibraryPage.tsx
- `exportFormat` state: `"markdown" | "json" | "opml"`，默认 markdown
- 导出预览面板新增格式切换按钮组（Markdown / JSON / OPML）
- `confirmExport()`: 发送 format 参数，根据格式选择正确的 MIME type 和文件扩展名
- 文件扩展名: `.md` / `.json` / `.opml`

### Frontend — i18n.ts
- 新增 `library.export_format` (zh: "导出格式", en: "Format")

## Design rationale

- **White-label safety**: 所有格式遵守相同的字段白名单（title/status/created_at/source_title/body），不泄露 source_path、internal IDs、secrets
- **JSON for interoperability**: JSON 格式可直接被脚本/工具解析，适合自动化处理
- **OPML for outline tools**: OPML 是思维导图/大纲工具的标准格式，支持用 OmniOutliner/MindNode 等工具打开
- **Field alias for "json"**: Pydantic BaseModel 的 `json` 方法冲突，使用 `Field(alias="json")` 保持 API 响应兼容

## Non-goals

- 不做 OPML body 完整导出（仅前 500 字符放入 `_note` 属性）
- 不做 YAML/CSV 格式

## Gates

- npm build: exit 0
- ruff check: All checks passed
- pytest: exit 0, 100% pass
- git diff --check: clean
