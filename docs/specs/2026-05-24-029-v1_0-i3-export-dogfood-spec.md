---
title: v1.0 I3 Export + Dogfood SPEC
type: spec
status: draft
date: 2026-05-24
parent: 2026-05-24-005-v1_0-next-phase-planning-review.md
---

# v1.0 I3: Export + Dogfood — 知识可带走，新人可试用

## 0. 目标

让用户能导出知识卡片为 Markdown（安全白名单），并提供一键 dogfood 命令快速体验 MindForge。

## 1. Problem Frame

**现状**:
- 知识卡片仅限 MindForge 内部使用，无法导出到外部工具
- `scripts/fake_dogfood.sh` 可用但需手动执行，新人入门门槛高
- 没有 `just dogfood` 或等效一键命令

**用户痛点**:
- 用户想将知识卡片用于 Obsidian、Notion 或其他 Markdown 工具
- 新人想快速体验 MindForge 但不知道从何开始
- 导出安全性必须保证 — 不能泄露 API key、secrets、私人数据

**目标**:
- Library 页面支持多选导出 Markdown（安全白名单过滤）
- 一键 dogfood 命令快速搭建体验环境

## 2. Scope

### U1: Export API（Backend）

**Goal**: 新增 backend endpoint 将选中卡片导出为 Markdown。

**API Design**:
- `POST /api/knowledge/export` — 接受 `{ card_ids: string[] }`，返回 `{ markdown: string, card_count: number }`
- 单张卡片也可通过 `GET /api/knowledge/export/{card_id}` 导出
- 导出的 Markdown 包含：title、body（原始 markdown）、status badge、created_at、source reference
- **安全白名单**：仅导出 title + body + status badge + created_at + source_title — 不导出 source raw_text、Human Note、API keys、secrets、run_id

**涉及文件**: `src/mindforge_web/routers/library.py`（或新增 `export.py`）

### U2: Export UI（Frontend）

**Goal**: Library 页面新增导出按钮，支持多选卡片后导出 Markdown。

**改动**:
- LibraryPage 卡片列表每行新增 checkbox
- 工具栏新增"导出选中"按钮（选中 1+ 张卡片后可用）
- 导出后触发浏览器下载 `.md` 文件
- 未选中卡片时按钮 disabled

**涉及文件**: `web/src/pages/LibraryPage.tsx`, `web/src/lib/i18n.ts`

### U3: One-Click Dogfood

**Goal**: 提供一键命令快速运行 fake dogfood，新人无需了解内部细节即可体验。

**改动**:
- 新增 `just dogfood` target（通过 Justfile）或 `make dogfood`
- 命令内部调用 `scripts/fake_dogfood.sh`
- `just dogfood` 优先（如果系统已安装 just），fallback 到 `bash scripts/fake_dogfood.sh`

**涉及文件**: `justfile` (NEW)

## 3. Non-Goals

- 不做 PDF/HTML/DOCX 导出（仅 Markdown）
- 不做全量导出（仅选中导出）
- 不导出 Wiki sections
- 不做导入功能
- 不修改 dogfood 脚本逻辑
- 不新增依赖（just 是可选工具，非必需）

## 4. Implementation Units 汇总

| Unit | 描述 | 文件 | 新增/修改 |
|------|------|------|----------|
| U1 | Export API | `routers/library.py` | 修改现有 |
| U2 | Export UI | `LibraryPage.tsx` + i18n | 修改现有 |
| U3 | One-Click Dogfood | `justfile` | 新增 |

## 5. Test Plan

| 测试类型 | 用例 |
|----------|------|
| `./scripts/check.sh` | Python lint + type check |
| `npm --prefix web run build` | TypeScript 编译通过 |
| `test_web_product_copy.py` | 新 i18n key 有 zh/en 双值 |
| `python -m pytest tests/ -q` | 全量 pytest |
| Browser smoke | 导出按钮正常，下载文件内容正确 |
| Dogfood smoke | `just dogfood` 成功运行 |

## 6. i18n Keys（预计 ≤ 5 个）

- `library.export_selected` — "导出选中" / "Export Selected"
- `library.export_none_selected` — "请先选择要导出的卡片" / "Select cards to export"
- `library.select_all` — "全选" / "Select All"
- `library.deselect_all` — "取消全选" / "Deselect All"

## 7. 依赖

- v1.0 I1 Workbench Dashboard (done)
- v1.0 I2 Approval Visibility (done)
- 现有 LibraryPage + library router
- 现有 `scripts/fake_dogfood.sh`
- 无新后端/前端依赖

## 8. Self-Review Checklist

- [ ] 是否退化成普通搜索页？— 否
- [ ] 是否偷偷变成 RAG answering？— 否
- [ ] 是否需要新依赖？— 否。just 可选
- [ ] 是否破坏 ai_draft / human_approved 语义？— 否
- [ ] 是否导出敏感数据？— 否。白名单过滤
- [ ] 是否符合 plan 中的 I3 方向？— 是。Export + Dogfood
- [ ] API key/secrets/Human Note 是否可能泄露到导出文件？— 否。白名单明确排除
