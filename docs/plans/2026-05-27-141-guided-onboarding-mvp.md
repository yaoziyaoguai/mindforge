# Guided Onboarding MVP — Implementation Plan

日期: 2026-05-27

## Problem Frame

MindForge 当前首次运行体验为空白首页 + 内联 FirstRunGuide（4 步卡片网格）。用户需要零配置跑通第一轮主路径才能理解产品价值。当前缺少：
1. 无示例工作区（demo 知识卡片）一键创建
2. 无跨页面上下文引导
3. FirstRunGuide 仅展示步骤但不可交互执行

## Scope Boundary

**In scope:**
- QuickStartWizard: 3 步首次向导（欢迎 → 创建示例工作区 → 查看结果）
- Sample Workspace Service: 后端生成 6 张 MindForge 概念 demo 卡片
- OnboardingHint: 8 个主要页面可关闭顶部提示横幅
- `POST /api/sample-workspace` endpoint
- i18n (zh/en) 所有 onboarding 文案
- Python service tests + 前端组件 tests + product-copy tests

**Out of scope:**
- 页面遮罩/高亮 tour overlay
- localStorage 持久化 onboarding 状态（MVP 用 per-session dismiss）
- 真实 API key 配置引导
- Graph/Sensemaking 页面提示
- 多语言扩展（仅 zh/en）

## Non-Goals / Hard Constraints

- 不改变 `ai_draft` → `human_approved` 审批边界
- 不调用真实 LLM
- 不读取 .env/secrets
- 不新增依赖
- Demo 卡片带 `[demo sample]` source tag，可被用户删除

## Implementation Units

### U1: Sample Workspace Service (`src/mindforge/services/sample_workspace.py` — NEW)

创建 `create_sample_workspace(workspace_dir)` 函数：
1. 在 workspace 下生成 6 个 Markdown source 文件（MindForge 核心概念）
2. 使用 fake provider 处理 → 6 张 `ai_draft` 卡片
3. 自动审批为 `human_approved`（系统 demo，非用户数据）
4. 返回创建结果摘要

Demo 卡片主题（来自 docs/CURRENT_PROJECT_STATE.md + README）：
1. "What is MindForge" — local-first personal knowledge compiler
2. "Approval-First Architecture" — ai_draft → human_approved explicit boundary
3. "Why Local-First" — privacy, offline, no cloud dependency
4. "Knowledge Lifecycle" — Source → Draft → Review → Approve → Library → Recall → Wiki → Export
5. "BM25 Recall vs. Vector Search" — deterministic lexical search, no embedding
6. "Demo Mode & Fake Provider" — zero-config safe local simulation

### U2: API Endpoint (`routers/library.py` — MODIFY)

`POST /api/sample-workspace`:
- 调用 U1 的 `create_sample_workspace()`
- 返回 `{success: true, card_count: 6, message: "..."}` 
- 幂等：如果已有卡片，返回已有状态不重复创建

### U3: OnboardingHint Component (`web/src/components/OnboardingHint.tsx` — NEW)

```typescript
interface OnboardingHintProps {
  pageKey: string;  // "home" | "setup" | "sources" | "review" | "library" | "recall" | "wiki" | "export"
  onDismiss: () => void;
}
```

- 渲染顶部可关闭横幅（蓝色半透明背景，左侧灯泡图标，右侧关闭按钮）
- 根据 pageKey 从 i18n 读取对应文案
- 与 SafetyBar 配合：SafetyBar 在上，OnboardingHint 在 SafetyBar 和 Breadcrumb 之间

### U4: QuickStartWizard Component (`web/src/components/QuickStartWizard.tsx` — NEW)

3 步向导：
- Step 1: 欢迎页 — "MindForge 已就绪，Demo 模式运行中，无需 API key"
- Step 2: 创建示例工作区 — 一键按钮调用 `POST /api/sample-workspace`，显示 loading/result
- Step 3: 完成 — "你已完成首个知识循环！" + 跳转按钮到 Library/Review

状态：`welcome` | `creating` | `done` | `error`

### U5: HomePage Integration (`web/src/pages/HomePage.tsx` — MODIFY)

- 替换内联 `FirstRunGuide` → `<QuickStartWizard>`
- QuickStartWizard 显示条件：`totalCards === 0 && sourceCount === 0`
- 创建完成后刷新 HomePage 数据
- 每页添加 OnboardingHint（在 AppShell 中统一注入）

### U6: Page Hint Integration (`web/src/components/AppShell.tsx` — MODIFY)

在 AppShell 中注入 OnboardingHint，根据 path 自动匹配 pageKey。
每个 hint 可独立关闭（per-session state in AppShell）。

### U7: i18n (`web/src/lib/i18n.ts` — MODIFY)

新增 `onboarding.*` 键组：
- `onboarding.hint.*` — 每页提示文案
- `onboarding.wizard.*` — 向导步骤文案
- `onboarding.sample.*` — 示例工作区相关文案

### U8: Tests

- `tests/test_sample_workspace.py` — U1 服务测试
- `web/src/components/__tests__/OnboardingHint.test.tsx` — U3 组件测试  
- `web/src/components/__tests__/QuickStartWizard.test.tsx` — U4 组件测试
- `tests/test_web_product_copy.py` — 补充 onboarding 文案键

## Implementation Order

U1 → U2 → U3 → U4 → U5 → U6 → U7 → U8
(Backend service → API endpoint → UI components → integration → i18n → tests)

## Risks

- 低风险：所有 demo 内容来自现有 docs，fake provider 已稳定
- 无数据风险：demo 卡片标记清晰，用户可删除
- 无安全风险：不触碰 secrets/LLM/approval 边界
