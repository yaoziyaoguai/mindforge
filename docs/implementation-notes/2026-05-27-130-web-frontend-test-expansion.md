# Web Frontend Test Coverage Expansion — Implementation Notes

Date: 2026-05-27
Baseline HEAD: `91f5ec7`
Task type: `feature_implementation`
Source: `docs/plans/2026-05-27-129-web-frontend-test-expansion.md`

---

## Summary

扩展前端组件测试覆盖，从 1 文件/2 测试 → 4 文件/25 测试。选择 3 个纯展示组件（LoadingSkeleton、EmptyState、StatusCard），无需 hooks/context/provider 设置。

---

## Changes

### U1: LoadingSkeleton Tests

**Files:**
- `web/src/components/__tests__/LoadingSkeleton.test.tsx` — 2 个 test case (default variant + 10 variants via it.each)

纯 CSS 骨架屏动画组件，无外部依赖。测试验证每个 variant 正常渲染且包含 `animate-pulse` class。

### U2: EmptyState Tests

**Files:**
- `web/src/components/__tests__/EmptyState.test.tsx` — 6 个 test case

覆盖：title 渲染、action label/description 渲染、command 渲染为 `<code>`、href 渲染为 `<a>`、onClick 渲染为 `<button>`、无 action 时不渲染交互元素。

关键设计发现：EmptyState 仅在 action 有 href 或 onClick 时渲染 label（链接/按钮内），纯 label+description 时不渲染 label 文本。

### U3: StatusCard Tests

**Files:**
- `web/src/components/__tests__/StatusCard.test.tsx` — 6 个 test case

覆盖：label/value 渲染、status badge、detail 文本、nextAction、href 时渲染为 `<button>`、无 href 时渲染为 `<section>`。

---

## Gates

| Gate | Command | Exit Code | Timeout |
|------|---------|-----------|---------|
| ruff | `ruff check src/ tests/` | 0 | no |
| git diff | `git diff --check` | 0 | no |
| npm build | `npm --prefix web run build` | 0 | no |
| vitest | `npm --prefix web run test` | 0 (25 passed, 4 files) | no |
| product copy | `python -m pytest tests/test_web_product_copy.py -q --tb=short` | 0 (84 passed) | no |

---

## Safety

- 仅新增测试文件，未修改任何产品代码
- 未修改 API contract
- 未修改 approval 语义
- 未引入新依赖
- 未引入 RAG/embedding/vector DB

## Deferred

- Breadcrumb/SafetyBar — 需要 useLocale hook context 设置
- Page-level smoke tests — 需要 routing/i18n provider
- 更多组件测试扩展
