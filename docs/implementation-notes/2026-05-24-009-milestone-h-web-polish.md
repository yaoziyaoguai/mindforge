# Milestone H — Last-Mile Web Polish — Implementation Notes

**Date:** 2026-05-24
**Plan:** `docs/plans/2026-05-24-003-feat-web-polish-planning-review.md`
**Status:** implemented

## 已完成内容

Milestone H 是 v0.3 六项 milestone (M1-M6) 全部完成后的"最后一公里"Web 体验打磨，纯前端改动，零后端变更。

### H1 — Loading Skeleton
- `LoadingSkeleton.tsx` (new): CSS-only skeleton 组件，使用 Tailwind `animate-pulse`，支持 wiki/library/drafts/default 四种变体
- `App.tsx`: 将纯文字 "Loading..." fallback 替换为 path-aware 的 `LoadingSkeleton`
- `WikiPage.tsx`: 初始加载阶段使用 `LoadingSkeleton variant="wiki"` 替代 spinner；rebuild busy 阶段保留 `WikiLoadingState`（有上下文相关的 building 文案）

### H2 — Sources Page A11y
- `SourcesPage.tsx`: 频率 `<select>` 元素新增 `name` 属性（已有 `id`、`aria-label`、`title`）

### H3 — Trash Empty State
- `TrashPage.tsx`: 空回收站从纯文字 `<div>` 升级为 `EmptyState` 组件，包含标题、描述文案和"前往审阅草稿"操作链接
- `i18n.ts`: zh/en 新增 3 个 key — `trash.empty_title`、`trash.empty_desc`、`trash.empty_action`

### H4 — Regression Browser Smoke
- 逐页验证：Home → Wiki → Library → Drafts → Sources → Trash，全部正常渲染
- i18n zh/en 切换验证通过
- Console error 检查通过（零 JS 错误）

## 修改文件

| 文件 | 变更 |
|------|------|
| `web/src/components/LoadingSkeleton.tsx` | new — CSS-only skeleton 组件 |
| `web/src/App.tsx` | +7/-1 — skeleton fallback |
| `web/src/pages/WikiPage.tsx` | +2/-1 — skeleton for initial load |
| `web/src/pages/SourcesPage.tsx` | +1 — name attribute on combobox |
| `web/src/pages/TrashPage.tsx` | +4/-1 — EmptyState 替代纯文字 |
| `web/src/lib/i18n.ts` | +6 — 3 zh + 3 en keys |

## Gate 验证

| Gate | Result |
|------|--------|
| `ruff check src/` | All checks passed |
| `npm --prefix web run build` | exit 0 |
| `python -m pytest tests/test_web_product_copy.py tests/test_wiki_quality.py -q` | 72/72 pass |
| `git diff --check` | exit 0 |
| Browser smoke (6 pages, zh/en) | All pages render, zero console errors |

## 设计决策记录

- **Skeleton vs Spinner**: 初始加载用 skeleton（视觉占位更流畅），rebuild 中保留 spinner+文案（用户需知道正在重建）
- **Skeleton 变体**: 每种页面布局有对应 skeleton，避免 generic skeleton 的布局跳变
- **Trash EmptyState**: 链接指向 `/drafts`（而非 `/sources`），因为清空回收站后用户最可能需要的是继续审阅
