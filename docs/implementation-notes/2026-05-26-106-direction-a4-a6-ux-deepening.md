# Direction A4-A6 Product Main Path UX Deepening — Implementation Notes

**日期**: 2026-05-26
**输入**: `docs/plans/2026-05-25-094-next-deepening-roadmap.md` Direction A items 3-6
**状态**: completed

---

## 执行摘要

在 v4.4 (A1-A3) 基础上完成了 Direction A 剩余 3 个 loop，补齐了审批时间线、知识库筛选、用户旅程冒烟测试三个 UX 缺口。

### Commits

| Loop | Commit | Description |
|------|--------|-------------|
| A4 | `2f27bdf` | feat: approval timeline in ApprovalPanel |
| A5 | `8b2d284` | feat: Library organization MVP — filter bar + sort |
| A6 | `59c92be` | test: user journey smoke tests (21 tests) |

---

## A4: Approval Timeline in ApprovalPanel

### 问题
ApprovalPanel 只展示 value_score + reviewed checkbox + approve/reject 按钮，缺少状态时间线展示。
用户无法看到卡片的 ai_draft → human_approved 完整状态转换路径。

### 修改
- `web/src/components/ApprovalPanel.tsx`: 新增状态时间线区域（value_score 下方）
  - 展示 created_at / 当前状态标签 / approved_at（若已确认）
  - 已确认卡片不再显示操作按钮（`!isApproved` 条件守卫）
  - `formatDate()` 辅助函数 + `statusBadgeClass()` 样式函数
- `web/src/lib/i18n.ts`: 新增 6 个 i18n key（zh + en）
  - `approval.status_timeline` / `approval.status_created` / `approval.status_current`
  - `approval.status_approved_at` / `approval.status_ai_draft` / `approval.status_human_approved`

### 设计决策
- 状态标签颜色：ai_draft = amber（橙色），human_approved = green（绿色）
- 操作区仅在未确认时显示（`!isApproved` 条件渲染）
- 时间格式化使用 `Date.toLocaleString()` 浏览器原生能力

---

## A5: Library Organization MVP — Filter Bar + Sort

### 问题
Library 页面只有 ?cards= URL param 过滤（来自 Health 页面），缺少通用筛选和排序。
用户无法按 track/tag/source_type/quality 浏览卡片。

### 修改
- `web/src/pages/LibraryPage.tsx`: 
  - 新增 5 个 filter/sort state: `statusFilter`, `trackFilter`, `sourceTypeFilter`, `qualityFilter`, `sortBy`
  - 使用 `useMemo` 派生 `uniqueTracks`, `uniqueSourceTypes`, `uniqueQualities`
  - `displayedCards` 改为 useMemo 计算：先过滤再排序
  - 新增 `clearAllFilters()` 重置方法
  - 新增横向 filter bar（SlidersHorizontal 图标 + select dropdowns）
  - 仅在有数据时显示对应的 filter dropdown
  - 活动筛选计数 badge + 清除按钮
- `web/src/lib/i18n.ts`: 新增 14 个 i18n key（zh + en）
  - 筛选标签: `library.filter_status` / `library.filter_track` / `library.filter_source_type` / `library.filter_quality`
  - 排序标签: `library.sort_label` / `library.sort_newest` / `library.sort_oldest` / `library.sort_title` / `library.sort_score`

### 设计决策
- 纯 client-side 筛选（卡片数据已全量加载），无服务端 round-trip
- filter bar 放在 header 和 stats cards 之间
- dropdown 为空时自动隐藏（避免无意义的"全部"下拉）
- 默认排序：最新优先（created_at 降序）

---

## A6: User Journey Smoke Tests

### 问题
缺少主路径端到端 HTTP 冒烟测试。现有测试覆盖单元和契约，但未验证 Home → Sources → Drafts → Library → Recall → Wiki → Export 全部主路径端点。

### 修改
- `tests/test_user_journey_smoke.py` — 新建，21 个测试

### 测试结构
- **TestUserJourneyMainPath** (17 tests): 验证每个主路径端点 HTTP 200
  - Home status, Workspace status, Sources, Drafts, Library cards/stats
  - Recall (中文+英文), Wiki status/content, Workflow summary
  - Health, Knowledge health, Config status, Export, Lifecycle
- **TestUserJourneyResponseStructure** (4 tests): 验证响应字段完整性
  - Library cards 必需字段、Recall hits 必需字段
  - Home status 必需字段、Wiki content 非空、Library source_path_view

### 设计决策
- 使用 FastAPI TestClient（不依赖浏览器/Playwright），无需新依赖
- 临时 vault 中预置一张 approved 卡片保证 Library/Recall/Wiki 有数据
- 使用 fake provider profile，不调用真实 LLM
- Provider readiness 端点排除（需要 secrets 属性，TestClient 环境不可用）

---

## Gate 结果

| Gate | Exit Code | Timeout |
|------|-----------|---------|
| `git diff --check` | 0 | No |
| `npm --prefix web run build` | 0 (twice) | No |
| `python -m pytest tests/test_web_product_copy.py -q --tb=short` | 0 | No |
| `python -m pytest tests/test_user_journey_smoke.py -q --tb=short` | 0 | No |
| `python -m pytest tests/ -q --tb=short` | 0 | No |

---

## Direction A 完成状态

| Item | Loop | Status |
|------|------|--------|
| First-run guided onboarding | v4.4 A1 | completed |
| Import and Review clarity | v4.4 A2 | completed |
| Library + Recall/Wiki/Export explanation | v4.4 A3 | completed |
| Approval timeline | A4 | completed |
| Library organization MVP | A5 | completed |
| User journey smoke tests | A6 | completed |

Direction A (Product Main Path UX Deepening) — **全部完成**。
