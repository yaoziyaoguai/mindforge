# Breadcrumb / SafetyBar Component Tests — Implementation Notes

Date: 2026-05-27
Baseline HEAD: `140a472`
Task type: `feature_implementation`
Workstream: Quality Platform / Frontend Test Coverage

---

## Summary

为 Breadcrumb 和 SafetyBar 组件添加测试，解决 useLocale() i18n context provider 问题。测试文件从 4 → 6，测试用例从 25 → 50。

## Key Challenge: useLocale() Context Provider

Breadcrumb 和 SafetyBar 都使用 `useLocale()` hook 调用 i18n 翻译函数 `t()`。该 hook 通过 `useContext(LocaleContext)` 获取 locale 上下文，如果不在 LocaleProvider 内使用会抛出错误。

解决方案：创建 `renderWithLocale()` 辅助函数，用 `LocaleProvider` 包裹被测组件，提供完整的 i18n context（locale + t 函数）。

## Changes

### U1: Breadcrumb Tests (9 tests)

File: `web/src/components/__tests__/Breadcrumb.test.tsx`

覆盖：
- 根路径 "/" 返回 null（无 segments）
- nav 元素 aria-label="Breadcrumb"
- Home 链接显示中文标签 "首页"
- 单段路径当前页渲染为 span（非 a 链接）
- 多段路径中间段渲染为 a 链接
- 多段路径最后一段渲染为 span
- 未知路由回退到 segment 文本本身
- /library 路径中文标签
- /recall/search 混合已知/未知路由

### U2: SafetyBar Tests (16 tests)

File: `web/src/components/__tests__/SafetyBar.test.tsx`

覆盖：
- null/undefined safety → loading 状态
- local_only=true → "本地运行"
- local_only=false → "主机警告"
- vault_path 显示（含截断）
- provider_state=ready → "就绪"
- provider_state=blocked → "待检查"（使用正则匹配，因 JSX 表达式产生独立文本节点）
- explicit_approval → "需显式确认"
- read_only → "只读模式"
- pending_drafts_count 显示
- 无警告时显示 "安全本地读取"
- 有警告时显示第一条警告文本
- 有警告时不显示 safe 状态
- 图标正确渲染

### Remedy: Split Text Node Matching

SafetyBar 的 provider state 渲染使用了两个 JSX 表达式：
```tsx
{t("safety.model_setup")}{safety.provider_state === "ready" ? ...}
```

在 happy-dom 中，这产生两个独立的文本节点。`getByText("就绪")` 无法跨文本节点匹配，需使用正则 `getByText(/模型配置：\s*就绪/)` 匹配整个 span 的 textContent。

## Gates

| Gate | Command | Exit Code | Timeout |
|------|---------|-----------|---------|
| git diff | `git diff --check` | 0 | no |
| npm build | `npm --prefix web run build` | 0 | no |
| vitest | `npm --prefix web run test` | 0 (50 passed, 6 files) | no |
| product copy | `python -m pytest tests/test_web_product_copy.py -q --tb=short` | 0 (84 passed) | no |

## Safety

- 仅新增测试文件，未修改任何产品代码
- 未修改 API contract
- 未修改 approval 语义
- 未引入新依赖
- 未引入 RAG/embedding/vector DB
- 未调用真实 LLM

## Deferred

- Page-level smoke tests — 需要 routing/i18n provider 集成设置
- 更多组件测试扩展 — 基于现有的 renderWithLocale 模式可继续扩展
