---
title: "v2.4 Source Ingestion & Local Workspace Pipeline — Implementation Note"
date: 2026-05-25
status: Complete
version: v2.4
---

# v2.4 Source Ingestion & Local Workspace Pipeline — Implementation Note

## What was done

v2.4 完成了本地资料导入管线的安全路径强化。

### U1: Markdown Folder Import Adapter

- 新增 `POST /api/knowledge/import/folder-preview` — 扫描文件夹 .md 文件，dry-run 预览
- 新增 `POST /api/knowledge/import/folder` — 批量导入为 ai_draft 卡片
- `WebFacade.preview_folder_import()` — 扫描、验证、提取标题/正文预览
- `WebFacade.import_from_folder()` — 按索引批量导入
- 安全检查：拒绝隐藏文件/系统文件/非 .md/超大文件(>1MB)
- 前端 `FolderImportForm` — 三步骤：输入路径 → 预览选择 → 结果展示

### U2: Import Dedup Detection

- `WebFacade._find_duplicates()` — exact title match + fuzzy Jaccard (>=0.6)
- 集成到 `import_card()` 和 `preview_folder_import()`
- `ImportCardResponse.potential_duplicates` 新增
- `_FolderImportPreviewFile.potential_duplicates` 新增
- 前端预览中展示去重警告（精确+模糊匹配）

### U3: Batch Paste Import

- 新增 `POST /api/knowledge/import/batch` — 批量导入端点
- `ImportCardForm` 检测 body 中 `---` 分隔的多篇文档
- 自动解析每篇的 title（YAML frontmatter → # heading fallback）
- Manifest-style 导入结果展示

### U4: Workspace Pipeline Status View

- 延至 v2.5（UI enhancement，与 Workspace Home 一起实现）

### U5: Safe Validation Framework

- 前置校验：title 非空、body 非空（已在 import_card 实现）
- 路径安全检查：拒绝系统路径（/、/System、/etc、/var、/tmp、/usr、/bin、/sbin）
- 文件过滤：隐藏文件、系统文件、非 .md、>1MB
- 新增 `tests/test_import_validation.py` — 16 个 validation tests
- 导入失败时结构化错误返回、非 500 crash

### U6: Zip Export Package

- 新增 `POST /api/knowledge/export/download` — streaming zip 下载
- zip 包含：cards.md + manifest.json
- 前端 LibraryPage 新增 zip 格式选项
- 基于 v1.5 I4 deferred zip 特性

## Changes

- `src/mindforge_web/schemas.py` — +7 schemas (folder import, batch import, dedup)
- `src/mindforge_web/services/web_facade.py` — +150 lines (folder import, dedup, markdown parsing)
- `src/mindforge_web/routers/library.py` — +4 endpoints (folder preview, folder import, batch import, zip download)
- `web/src/api/types.ts` — +4 interfaces (folder import, dedup)
- `web/src/api/library.ts` — +2 API functions
- `web/src/components/FolderImportForm.tsx` — NEW (220 lines)
- `web/src/components/ImportCardForm.tsx` — Rewritten (batch paste support)
- `web/src/pages/LibraryPage.tsx` — Zip format + folder import integration
- `web/src/lib/i18n.ts` — ~30 new keys (zh + en)
- `tests/test_import_validation.py` — NEW (16 tests)

## Design Rationale

- **ai_draft only**: 所有导入默认 ai_draft，不自动 approve（保持 explicit approval 语义）
- **No LLM / external calls**: 纯本地文件操作，适合 fake dogfood
- **Best-effort dedup**: 去重是建议性警告，不阻塞导入（与 explicit approval 原则一致）
- **Safe by default**: 拒绝系统路径、隐藏文件、超大文件
- **Streaming zip**: 不在 JSON response 中嵌 base64，避免大文件内存问题

## Non-goals

- 不做文件上传（仅粘贴文本/本地文件夹路径）
- 不做 Obsidian vault 写入
- 不处理真实私人资料
- 不自去 approve

## Gates

- ruff check: exit 0
- pytest full (~560+): exit 0, 100% pass (1 skipped)
- npm build: exit 0
- product copy: exit 0
- git diff --check: exit 0
