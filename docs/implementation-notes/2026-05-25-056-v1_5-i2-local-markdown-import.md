# v1.5 I2: Local Markdown Import Adapter — Implementation Note

**Date:** 2025-05-25
**Status:** Complete

## What was done

新增 `POST /api/knowledge/import` 端点，支持从 Markdown 内容创建 ai_draft 卡片。前端 LibraryPage 新增 Import 按钮和表单。

## Changes

### Backend — schemas.py
- `ImportCardRequest`: `title`, `body`, `source_name`（可选）
- `ImportCardResponse`: `id`, `title`, `rel_path`, `status`, `created_at`

### Backend — routers/library.py
- `POST /api/knowledge/import`: 校验 title/body 非空 → 调用 `facade.import_card()`

### Backend — web_facade.py
- `import_card(title, body, source_name)`: 从标题生成 slug id + uuid6 → 构造 frontmatter → 写入 `cards_dir/{id}.md` → 返回 ImportCardResponse
- 不调用 LLM / provider / external service

### Frontend — ImportCardForm.tsx
- 导入按钮 → 展开内联表单（标题/内容/来源名称）
- 提交后自动清空表单，刷新 Library 列表
- 错误/成功提示

### Frontend — LibraryPage.tsx
- Header 区域新增 `<ImportCardForm>` 组件

### Frontend — i18n.ts
- 新增 9 个 library.import_* 键（zh + en）

### Frontend — api/library.ts + api/types.ts
- `importCard()` API 函数 + `ImportCardResponse` 类型

## Design rationale

- **Safe default status**: 导入卡片自动设为 `ai_draft`，不自动 approve（保持 explicit approval 语义）
- **Source type marker**: `source_type: imported_markdown` 区别于 pipeline 生成的卡片
- **Slug-based id**: 标题 → slug + 6 位 uuid hex，保证唯一且可读
- **No LLM / external calls**: 纯本地文件写入，适合 fake dogfood 场景

## Non-goals

- 不做文件上传（仅粘贴文本）
- 不做批量导入
- 不做 Obsidian vault 写入

## Gates

- ruff check: All checks passed (exit 0)
- pytest: exit 0, 100% pass
- npm build: exit 0
- pytest test_web_product_copy.py: exit 0
- git diff --check: clean
