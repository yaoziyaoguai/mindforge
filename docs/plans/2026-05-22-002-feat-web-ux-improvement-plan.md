---
title: MindForge Web UX Improvement Plan
type: feat
status: active
date: 2026-05-23
---

## Milestone Status

| Milestone | Status | Date |
|-----------|--------|------|
| A | done | 2026-05-22 |
| B | done | 2026-05-23 |
| C | done | 2026-05-23 |
| D | done | 2026-05-23 |
| E | done | 2026-05-23 |
| F | done | 2026-05-23 |
| G | done | 2026-05-24 |


# MindForge Web UX Improvement Plan

## Summary

对 MindForge Web 做渐进式 UX 改进，覆盖 P0（阻塞可用性）、P1（提升 dogfood 体验）、P2（视觉一致性）三个优先级。总计 ~500 LOC 改动，不引入新依赖，不改后端，不改设计系统基础设施。

---

## Problem Frame

Web-first real LLM dogfood 跑通后暴露出 Web 的工程感过重、用户引导缺失、术语暴露、视觉单调等问题。当前 Web 适合熟悉 LLM 技术栈的工程师自用，但 Setup 页面的配置复杂度、审批流程的语义混淆、空状态的零引导会使非技术用户放弃。本次改进聚焦最低成本的体验修正，不做设计系统大重写。

---

## Requirements

- **R1.** Setup 页面必须以步骤式引导降低首次配置的认知负担
- **R2.** 审批按钮的视觉语义必须从"危险/破坏性"修正为"确认/正向"
- **R3.** UI 文案必须从内部状态码（`ai_draft`, `human_approved`）改为用户可理解的标签
- **R4.** 空状态页面必须包含下一步引导，而非仅显示空白面板
- **R5.** 侧边栏导航必须有逻辑分组，帮助用户理解页面之间的关系
- **R6.** 状态指示器不能仅依赖颜色，须增加图标作为辅助辨识手段
- **R7.** 搜索结果不得暴露内部算法名称和技术评分格式
- **R8.** 知识卡片只读视图的排版应优化阅读体验

---

## Scope Boundaries

- 不改动后端 API、provider、LLM pipeline、审批语义
- 不新增 npm 依赖（使用已有的 lucide-react 图标库和 Tailwind CSS）
- 不修改 `tailwind.config.ts` 中的设计 token 定义
- 不引入路由库（保持当前的 `pushState` + `popstate` 方案）
- 不引入动画库、组件库、暗色模式
- 不添加前端测试基础设施

### Deferred to Follow-Up Work

- **P3 设计系统演进**（响应式断点、loading skeleton、图标系统规范化）: 后续独立 plan
- **P3 前端 accessibility**（form field id/name/aria-label 关联修复）: → 已纳入 Milestone C (U12)
- **P4 品牌视觉**（插图、空状态图形、情感化设计）: 后续独立 plan
- **前端测试基础设施**（vitest + testing-library 搭建、页面 smoke test）: 后续独立 plan
- **Setup 页面深度重构**（从表单式改为对话式引导、provider 自动检测）: 待 P0 修复收集更多 dogfood 反馈后决定

---

## Context & Research

### Relevant Code and Patterns

- `web/src/pages/SetupPage.tsx` — ~600 行，使用本地 `useState` 管理表单状态，`JSON.stringify` 做脏检测，`EditingModel | null` 模式管理内联编辑
- `web/src/components/ApprovalPanel.tsx` — 两步确认流：checkbox + "Approve..." 按钮 → 红色确认面板
- `web/src/lib/utils.ts` — `friendlyStatus()` 状态文案映射，`statusTone()` 颜色类映射，`cx()` 类名拼接
- `web/src/components/EmptyState.tsx` — Props: `{ title: string; action?: NextAction | null }`，虚线边框面板
- `web/src/components/Sidebar.tsx` — 8 个导航项平铺数组，`{ href, label, icon }` 结构
- `web/src/components/CardWorkspace.tsx` — `CardSections` 解析 `##` 标题分段渲染，编辑模式 `textarea` + `font-mono`
- `web/src/pages/RecallPage.tsx` — `hit.score.toFixed(2)` 展示，`why_this_matched` 文本
- `web/src/styles.css` — 仅 38 行，Tailwind 指令 + 系统字体栈 + focus-visible 样式
- `web/tailwind.config.ts` — 9 个语义颜色 token + 1 个阴影，无自定义字体/间距/圆角

### Patterns to Follow

- 表单状态: `useState` + 展开不可变更新，手动 `onChange` handler
- API 调用: 通过 `web/src/api/` 模块化函数
- 组件通信: props 传递 + `onNavigate` callback（无全局状态管理）
- 图标: lucide-react，`className="h-4 w-4"` 尺寸约定
- 按钮: `bg-primary text-white` (主操作), `border border-line bg-panel` (次要), `bg-danger text-white` (危险)
- 状态色: `statusTone()` 返回单个 className 字符串（如 `"text-safe bg-green-50 border-green-200"`），调用方直接用于 `className` 插值

### External References

- Claude Design 渐进式信息披露原则 — 核心功能优先，高级选项按需展开
- Material Design Elevation 系统 — 用阴影区分表面高度层次
- Linear / Vercel 空状态模式 — 插图 + 标题 + 描述 + CTA 四段式

---

## Key Technical Decisions

- **Setup 步骤化采用步骤指示器而非子页面拆分**: 避免引入路由变更和组件拆分复杂度，用一个 `step` 状态变量控制 `SetupPage.tsx` 内的区域显隐。改动的 blast radius 最小，配置逻辑零变更
- **审批按钮从 `bg-danger` 迁移到 `bg-primary`**: `danger` token (`#b42318`) 在 UI 惯例中表示破坏性操作。审批知识卡片是正向确认行为，应使用 `primary` (`#2368d1`)。保留两步确认的安全机制，仅改变颜色语义和文案语气
- **空状态增强采用 `action` prop 扩展而非每个页面内联**: 在 `EmptyState` 组件接口增加可选的 button label + onClick，各页面传参即可。避免在每个页面重复引导按钮代码
- **不使用 `React.FC`**: 遵循项目 convention，所有组件用普通函数声明
- **状态图标映射到新增 helper 而非改 statusTone() 签名**: `statusTone()` 当前返回单个 className 字符串，被 StatusCard/ConfigChecklist 等多个调用方直接用于 `className` 插值。不改其签名，新增 `statusIcon(status: string): LucideIcon | null` 和 `statusLabel(status: string): string` 两个纯函数，在 badge 渲染处组合调用

---

## Open Questions

### Resolved During Planning

- **Setup 步骤化 vs 子页面拆分**: 步骤指示器内联方案 — blast radius 最小，不改路由
- **P2 是否纳入本次 plan**: 纳入 — Recall 文案和 CardWorkspace 字体改动量极小（~30 LOC），分批提交的价值低于一次性 polish
- **是否需要新增 npm 依赖**: 否 — lucide-react 已有 28+ 图标在使用，足够覆盖本次新增

### Deferred to Implementation

- 步骤指示器的具体 UI 样式（顶部 stepper vs 侧边 steps panel）— 实现时根据 SetupPage 当前布局决定
- `statusIcon()` 返回的具体 Lucide 图标组件选择（`CheckCircle` vs `CheckCircle2` 等图标变体）— 实现时根据视觉一致性决定

---

## Implementation Units

### U1. Setup 页面步骤指示器

**Goal:** 为 SetupPage 增加步骤式引导，将 ~600 行的配置表单分为 3 个逻辑步骤，降低首次配置的认知负担

**Requirements:** R1

**Dependencies:** None

**Files:**
- Modify: `web/src/pages/SetupPage.tsx`

**Approach:**
- 新增 `step` state（`"models" | "sources" | "review"`）
- 在表单顶部渲染步骤指示器（横向 3 步，当前步骤高亮）
- 每步只显示相关表单区域，隐藏其他内容
- 步骤 1（连接模型）: 模型 CRUD 表单 + 路由分配
- 步骤 2（选择知识源）: vault root + wiki settings + source adding
- 步骤 3（检查配置）: 诊断信息 + prompt preview
- 保留现有的 validate/save/revert 逻辑不变
- 保留现有的脏检测逻辑不变
- Save 按钮增加 loading 状态: 保存中禁用按钮，显示 spinner + "保存中..."
- Save 失败时显示 inline error banner（红色），展示后端返回的错误信息，不吞错误

**Patterns to follow:**
- 现有 `useState` 模式，`cx()` 条件类名
- 现有按钮样式约定（主操作 `bg-primary`，次要 `border border-line`）
- 现有 SetupPage 中的错误展示模式（validation errors 已有渲染逻辑）

**Test scenarios:**
- Happy path: 用户从步骤 1 开始，依次完成 3 步配置，最后点击 Save 保存成功
- Edge case: 用户在步骤 1 填写了模型信息，点击"上一步"回到步骤 1 时数据保留
- Edge case: 步骤 3 中诊断结果显示 error，用户仍可回退修改
- Loading state: 点击 Save 后按钮变为 disabled + spinner + "保存中..."，保存完成后恢复
- Error state: Save API 返回错误时显示 inline error banner，用户可修改配置后重试

**Verification:**
- SetupPage 渲染时默认显示步骤 1
- 步骤指示器显示 3 个步骤标签，当前步骤视觉突出
- 点击"下一步"/"上一步"可在步骤间切换，表单数据不丢失
- Save/Revert 按钮在所有步骤中可见且可用
- 保存过程中 Save 按钮禁用并显示加载状态
- 保存失败时显示错误 banner，不静默吞错

---

### U2. 审批 UX 修正和状态文案中文化

**Goal:** 修正审批按钮颜色语义（danger → primary），中文化审批流程文案，调整 `friendlyStatus()` 映射表

**Requirements:** R2, R3

**Dependencies:** None

**Files:**
- Modify: `web/src/components/ApprovalPanel.tsx`
- Modify: `web/src/lib/utils.ts`

**Approach:**
- `ApprovalPanel.tsx`:
  - 两个审批确认按钮从 `bg-danger` 改为 `bg-primary`
  - 第二确认面板的红色警告背景改为蓝色信息面板
  - 文案调整: checkbox label 改为"我已审查来源内容和 AI 草稿"，最终确认按钮改为"确认并保存此知识"
  - 第二步标题从 "Second confirmation required" 改为 "确认知识卡片"
- `utils.ts` `friendlyStatus()`:
  - `"ai_draft"` → `"待审查"`
  - `"human_approved"` → `"已确认"`
  - `"insufficient_content"` → `"内容不足"`（若存在）
  - 其余状态保持英文但审查一致性

**Patterns to follow:**
- 现有 `statusTone()` 颜色约定不受影响（green/amber/red 映射正确）
- 现有两步确认逻辑（checkbox + `confirming` state）完全保留

**Test scenarios:**
- Happy path: 用户勾选 checkbox → 点击"确认并保存此知识" → 二次确认面板显示蓝色而非红色 → 再次确认 → 审批成功
- Edge case: checkbox 未勾选时确认按钮 disabled
- Edge case: 取消按钮恢复初始状态
- Happy path: `friendlyStatus("ai_draft")` 返回 `"待审查"`

**Verification:**
- 审批按钮使用 `bg-primary`，不再是 `bg-danger`
- 第二确认面板使用蓝色调，不再是红色警告
- `friendlyStatus()` 返回中文化标签
- 现有审批功能不受影响（两步确认流程完整）

---

### U3. 空状态引导增强

**Goal:** 为空状态组件增加引导 action，让用户在初次进入 Library/Drafts/Home 页面时有明确的下一步操作

**Requirements:** R4

**Dependencies:** None

**Files:**
- Modify: `web/src/api/types.ts`（扩展 `NextAction` 接口，增加可选 `onClick` 字段）
- Modify: `web/src/components/EmptyState.tsx`
- Modify: `web/src/pages/HomePage.tsx`
- Modify: `web/src/pages/LibraryPage.tsx`（仅传 action prop，不要求 onNavigate — 可用 href 走 `<a>` 标签）
- Modify: `web/src/pages/DraftsPage.tsx`（同上）

**Approach:**
- `api/types.ts`: 扩展 `NextAction` 接口，增加 `onClick?: () => void` 字段（用于 programmatic 导航，如 `pushState`），与现有 `href` 互斥使用
- `EmptyState.tsx`: 在组件内部渲染 action 按钮 — 当 `action.label` 和 `action.href` 同时存在时渲染 `<a href={action.href}>` 链接按钮；当 `action.label` 和 `action.onClick` 同时存在时渲染 `<button onClick={action.onClick}>`；不新增 `actionLabel`/`onAction` 等重叠 prop
- `HomePage.tsx`: 无知识卡片时传 `action={{ label: "前往 Setup 配置", href: "/setup", description: "..." }}` — HomePage 已有 `onNavigate` prop，但 EmptyState 直接用 `href` 触发导航更简单
- `LibraryPage.tsx`: 无卡片时传 action — **注意 LibraryPage 当前无 `onNavigate` prop**，需新增 `onNavigate?: (href: string) => void` prop 并在父组件（`App.tsx`）中传入，或使用 `href` 走 `<a>` 标签导航（后者更简单，无需改 LibraryPage 接口）
- `DraftsPage.tsx`: 无待审查卡片时传 action — 同 LibraryPage，优先使用 `href` 方案避免接口变更

**Patterns to follow:**
- 现有 `EmptyState` 组件 `action?: NextAction | null` 接口 — 不改 prop 名称，只扩展 `NextAction` 类型和渲染逻辑
- 现有按钮样式约定
- HomePage 现有 `onNavigate` prop 模式（如需新增到其他页面时参照）

**Test scenarios:**
- Happy path: 新 workspace 无任何卡片，Library 页面显示空状态 + "前往 Sources" 按钮，点击后导航到 Sources
- Happy path: 无待审查卡片，Drafts 页面显示空状态 + 引导按钮
- Edge case: `action` 为 `null` 或不存在时，仅显示标题和虚线面板（向后兼容）

**Verification:**
- 3 个页面在空数据状态下显示引导按钮
- 按钮点击触发正确的页面导航
- 不影响非空状态下的正常渲染

---

### U4. 侧边栏导航分组

**Goal:** 将 8 个平铺导航项分为"知识处理"和"知识使用"两个逻辑组，帮助用户理解页面关系

**Requirements:** R5

**Dependencies:** None

**Files:**
- Modify: `web/src/components/Sidebar.tsx`

**Approach:**
- 将导航项数组重组为分组结构，分组标签不可点击
- 分组标签使用 `text-xs font-semibold text-muted uppercase tracking-wider`
- 分组之间用 `my-2` 间距分隔，不添加分割线
- 保持现有的 active 检测逻辑和样式
- **Sidebar 分组映射（显式枚举）:**

  知识处理（配置与审核）:
    Setup     → /setup      (⚙️ Cog 图标)
    Sources   → /sources    (📂 FolderOpen 图标)
    Review    → /drafts     (📝 FileText 图标)
    Trash     → /trash      (🗑️ Trash2 图标)

  知识使用（查阅与检索）:
    Home      → /           (🏠 Home 图标)
    Library   → /library    (📚 Library 图标)
    Wiki      → /wiki       (📖 BookOpen 图标)
    Search    → /recall     (🔍 Search 图标)

**Patterns to follow:**
- 现有 Sidebar 导航项渲染模式
- 现有 Tailwind 排版 token（`text-xs`, `text-muted`）

**Test scenarios:**
- Happy path: Sidebar 渲染两个分组标签和 8 个导航项
- Edge case: active 状态在分组后仍然正确高亮（按 `path.startsWith` 匹配）
- Edge case: 窄屏下分组标签不换行

**Verification:**
- 分组标签以 muted 小字显示，不可点击
- 分组间有视觉间距
- 所有 8 个导航项功能不变

---

### U5. 状态 Badge 图标化

**Goal:** 新增 status icon/label helper，为状态 badge 增加图标辅助辨识（无障碍 + 快速扫描）

**Requirements:** R6

**Dependencies:** U2（依赖 `friendlyStatus()` 文案调整后的 context）

**Files:**
- Modify: `web/src/lib/utils.ts`
- Modify: `web/src/components/StatusCard.tsx`（badge 渲染处增加图标）
- Modify: `web/src/components/ConfigChecklist.tsx`（badge 渲染处增加图标）
- Modify: `web/src/components/CardWorkspace.tsx`（status badge 处增加图标）

**Approach:**
- 不改 `statusTone()` 签名 — 它继续返回单个 className 字符串，现有调用方零改动
- 新增 `statusIcon(status: string): LucideIcon | null`:
  - `"ok"` → `CheckCircle`
  - `"warn"` → `AlertTriangle`
  - `"error"` → `X`
  - 其他 → `null`
- 新增 `statusLabel(status: string): string`:
  - `"ok"` → `"正常"`
  - `"warn"` → `"警告"`
  - `"error"` → `"错误"`
  - 其他 → `""`
- 在各 badge 渲染处组合调用: `statusTone(status)` 提供颜色，`statusIcon(status)` 提供图标，`statusLabel(status)` 提供 screen-reader 文本
- badge 渲染模式: `<span className={statusTone(status)}><Icon className="h-3 w-3" /><span>{text}</span></span>`

**Patterns to follow:**
- 现有 `statusTone()` 的字符串返回 + className 插值模式（不改）
- 现有 `h-4 w-4` 图标尺寸约定（badge 用 `h-3 w-3` 更小）

**Test scenarios:**
- Happy path: `statusIcon("ok")` 返回 `CheckCircle` 组件
- Happy path: `statusIcon("warn")` 返回 `AlertTriangle` 组件
- Happy path: `statusIcon("unknown_status")` 返回 `null`
- Happy path: `statusLabel("ok")` 返回 `"正常"`
- Edge case: 所有现有 `statusTone()` 调用方行为不变（返回值类型未变）

**Verification:**
- 状态 badge 显示对应图标 + 色块 + 文字标签
- 色盲用户可通过图标形状区分状态（不依赖颜色）
- `statusTone()` 现有调用方零改动
- 无 TypeScript 编译错误

---

### U6. Recall 搜索结果展示优化

**Goal:** 隐藏技术评分格式（`toFixed(2)`），用用户可理解的标签替代内部算法名称

**Requirements:** R7

**Dependencies:** None

**Files:**
- Modify: `web/src/pages/RecallPage.tsx`

**Approach:**
- 分数展示从 `{hit.score.toFixed(2)}` 改为文字标签:
  - `score >= 0.7` → "高相关"（绿色）
  - `score >= 0.4` → "相关"（默认色）
  - `score < 0.4` → "低相关"（muted）
- `why_this_matched` 保留但增加引导性文案："匹配原因: {text}"
- 搜索框 placeholder 改为"搜索知识卡片..."
- 搜索中状态: 搜索按钮显示 spinner + "搜索中..."，输入框保持可用
- 搜索失败状态: 显示 inline error banner（红色），含错误摘要 + "重试" 按钮，不吞错误
- 无结果时显示 EmptyState + "尝试其他关键词" 提示

**Patterns to follow:**
- 现有 `RecallPage.tsx` 结构
- 现有 `EmptyState` 组件
- 现有 API client 的 try/catch 错误处理模式

**Test scenarios:**
- Happy path: 搜索结果分数 ≥ 0.7 时显示"高相关"标签而非数字
- Happy path: 搜索无结果时显示 EmptyState
- Loading state: 点击搜索后按钮显示 spinner + "搜索中..."
- Error state: API 调用失败时显示错误 banner + "重试" 按钮，点击重试重新发起搜索
- Edge case: 分数恰好 0.4 时显示"相关"

**Verification:**
- 搜索结果不展示原始浮点数分数
- `why_this_matched` 文本前有"匹配原因:"标签
- 空搜索结果显示引导而非空白
- 搜索过程中按钮禁用并显示 spinner
- 搜索失败时显示可操作的错误提示（含重试按钮）

---

### U7. 知识卡片阅读视图排版优化

**Goal:** 优化 `CardWorkspace` 只读模式下的排版 — section 标题间距、正文字体行高、元数据区域层次

**Requirements:** R8

**Dependencies:** None

**Files:**
- Modify: `web/src/components/CardWorkspace.tsx`
- Modify: `web/src/styles.css`

**Approach:**
- `CardSections` 渲染: section 标题 `text-lg font-semibold mb-2`，正文字体从等宽改为系统字体 `whitespace-pre-wrap text-sm leading-7`（保留换行处理，去掉 `font-mono`）
- 保持现有 `CardSections` 的 `space-y-4` 间距（已满足设计意图，无需修改）
- 元数据区域（Source & History, Technical Details）使用 `text-xs text-muted` 标签 + `text-sm` 值的两行布局，替换当前的平铺网格
- `styles.css`: 增加 `h1, h2, h3` 的基本排版复位（确保 section 标题层次）
- 保持编辑模式下的 `font-mono` 不变（编辑时需要等宽字体）

**Patterns to follow:**
- 现有 `CardSections` 解析逻辑不变
- 现有 Tailwind 排版类

**Test scenarios:**
- Happy path: 只读卡片正文使用系统字体渲染（非等宽）
- Happy path: Section 之间间距比原来更宽松
- Edge case: 元数据为空时不渲染空标签
- Edge case: 编辑模式下等宽字体保持不变

**Verification:**
- 卡片只读正文不使用 `font-mono`
- Section 标题和正文有清晰的视觉层次
- 编辑模式体验不变

---

## Milestone C: UX Polish, Accessibility & i18n

### Status

Milestone A 和 B 已完成（7 个 Implementation Unit 全部实现并 push main，browser smoke 通过）。Milestone C 为本次 plan 的下一阶段。

### Milestone C Requirements

- **R9.** Review card 视觉层级进一步优化 — 审批面板信息层次更清晰，用户一眼可见"需要我做什么"
- **R10.** Source History / provenance 展示更友好 — 来源追溯链路简化为用户可理解的路径和操作
- **R11.** Recall 页面文案和状态继续优化 — 搜索引导、结果展示、错误提示精炼
- **R12.** spacing / typography 小范围统一 — 页面间排版不一致处修正，不涉及设计 token 重定义
- **R13.** P3 accessibility hint 修复 — form field 增加合理 `id`/`name`/`aria-label` 关联
- **R14.** 中英文 UI 可切换 — 用户可在中文和英文界面之间自由切换，消除当前中英混杂状态

### R14: i18n / 中英文切换详细说明

**目标:**

当前 Web UI 存在中英文混杂问题（部分文案已中文化，部分仍为英文）。Milestone C 需要引入轻量 locale 方案，让用户可以在中文和英文 UI 之间自由切换。

**约束:**

1. **不引入大型 i18n 框架** — 除非 review 后证明现有技术栈无法支撑轻量方案
2. **优先做轻量 locale dictionary / copy map** — 一个按语言 key 索引的文案字典，组件按 key 取值
3. **不改变后端 API** — locale 切换纯前端行为，API 请求/响应不变
4. **不改变业务状态字段** — `ai_draft`、`human_approved`、`source_id` 等内部字段保持英文
5. **内部字段仍可以是 ai_draft / human_approved** — 仅用户侧展示通过 locale copy 映射
6. **不要把中英文 copy 散落在各页面里** — copy 需集中在 locale 模块中，页面只引用 key

**待 Milestone C mini spec / review 决定的设计点:**

7. **默认语言策略**: 默认中文，或跟随浏览器语言 (`navigator.language`)，具体由 review 决定
8. **语言切换入口位置**: Settings / Setup / sidebar footer，具体由 review 决定
9. **locale 文件结构**: 单一 JSON/TS 字典 vs 按模块拆分，具体由 review 决定
10. **切换后状态持久化**: localStorage vs sessionStorage vs 不持久化（每次恢复默认）

**非目标:**

- 不做完整 CMS 级多语言管理系统
- 不做后端 API 错误信息国际化
- 不做 RTL 语言支持
- 不做 a11y 多语言 screen reader 优化（超出 Milestone C 范围）

### Milestone C Implementation Units

#### U8. Review Card 视觉层级优化

**Goal:** 优化 ApprovalPanel 和 CardWorkspace review 模式的信息层次

**Requirements:** R9

**Files:**
- Modify: `web/src/components/ApprovalPanel.tsx`
- Modify: `web/src/components/CardWorkspace.tsx`

**Dependencies:** U2 (审批 UX 修正已完成)

**Verification:**
- Review card 的信息层次清晰：标题 → 状态 → 内容摘要 → 操作区
- 审批按钮视觉权重正确（主操作突出，次要操作降级）

---

#### U9. Source History / Provenance 展示优化

**Goal:** 简化来源追溯链路展示，用户可理解来源路径和操作

**Requirements:** R10

**Files:**
- Modify: `web/src/components/CardWorkspace.tsx`（来源与历史区域）

**Dependencies:** U7 (CardWorkspace 排版优化已完成)

**Verification:**
- 来源路径展示用户友好，不暴露内部结构
- 来源追溯操作（Copy path / Reveal in Finder）fail-closed 策略不变

---

#### U10. Recall 文案和状态精炼

**Goal:** 继续优化 Recall 页面搜索引导、结果展示、错误提示

**Requirements:** R11

**Files:**
- Modify: `web/src/pages/RecallPage.tsx`

**Dependencies:** U6 (Recall 搜索结果优化已完成)

**Verification:**
- 搜索引导文案清晰，说明 BM25 词法匹配
- 结果展示不暴露技术评分格式
- Error/loading/empty 三态完整且文案合理

---

#### U11. Spacing / Typography 小范围统一

**Goal:** 修正页面间排版不一致处，不涉及设计 token 重定义

**Requirements:** R12

**Files:**
- Modify: `web/src/styles.css`
- Modify: `web/src/pages/SetupPage.tsx`（stepper/表单间距）
- Modify: `web/src/pages/RecallPage.tsx`（搜索区域间距）
- Modify: `web/src/pages/LibraryPage.tsx`（卡片列表间距）
- Modify: `web/src/components/CardWorkspace.tsx`（section 间距）

**Dependencies:** None (独立视觉修正)

**Verification:**
- 页面间标题层级、段落间距、卡片间距视觉一致
- 不改变 Tailwind 设计 token

---

#### U12. Form Field Accessibility 修复

**Goal:** 为 form field 增加合理 id/name/aria-label 关联

**Requirements:** R13

**Files:**
- Modify: `web/src/pages/RecallPage.tsx`（搜索框）
- Modify: `web/src/pages/SourcesPage.tsx`（频率 combobox）

**Dependencies:** None

**Verification:**
- Sources 页 frequency combobox 有 id/name 关联
- Recall 页搜索输入框有 id/name/label 关联
- Chrome DevTools accessibility audit 不再报告对应 hint

---

#### U13. 中英文 UI 可切换 (i18n)

**Goal:** 引入轻量 locale dictionary，用户可在中文和英文界面之间切换

**Requirements:** R14

**Execution order note:** U13 必须排在 U10 之后执行。U10 先 settle Recall copy/wording 终态，U13 再从各页面抽取 hardcoded copy 到 locale dictionary。颠倒顺序会导致 U10 在英文 locale key 上再做修改，产生重复劳动。

**Files:**
- Create: `web/src/lib/i18n.ts`（locale dictionary + `t()` 函数 + `useLocale` hook）
- Modify: `web/src/pages/RecallPage.tsx`（硬编码文案 → `t('key')`）
- Modify: `web/src/pages/SetupPage.tsx`（硬编码文案 → `t('key')`）
- Modify: `web/src/pages/LibraryPage.tsx`（硬编码文案 → `t('key')`）
- Modify: `web/src/pages/DraftsPage.tsx`（硬编码文案 → `t('key')`）
- Modify: `web/src/pages/HomePage.tsx`（硬编码文案 → `t('key')`）
- Modify: `web/src/components/ApprovalPanel.tsx`（硬编码文案 → `t('key')`）
- Modify: `web/src/components/CardWorkspace.tsx`（硬编码文案 → `t('key')`）
- Modify: `web/src/components/EmptyState.tsx`（硬编码文案 → `t('key')`）
- Modify: `web/src/components/Sidebar.tsx`（语言切换入口 + 导航标签 → `t('key')`）

**Approach:**
- 第一步：创建 `i18n.ts`，定义 `LocaleDict` 类型和 `zh`/`en` 两套 copy map
- 第二步：定义 `useLocale()` hook，暴露 `t(key)` 翻译函数和 `setLocale(locale)` 切换函数，locale 选择通过 `localStorage` 持久化
- 第三步：按 U10（Recall 终态）→ 其他页面顺序，逐步替换硬编码文案为 `t('key')` 调用
- 第四步：在 Sidebar footer 添加语言切换入口（简体中文 / English toggle）

**Verification:**
- 存在集中管理的 locale dictionary（非各页面散落）
- 语言切换入口可用，切换后所有页面文案跟随变化
- 切换不触发页面刷新（纯 React state）
- 不引入新 npm 依赖
- 未知 locale key fallback 到 key 自身（英文文案）

---

### Milestone C Execution Flow

Milestone C 的执行顺序必须是：

1. **先写 Milestone C mini spec** — 尤其是 i18n/copy strategy 和 locale 文件结构设计
2. **mini spec 必须 review** — 使用 `/ce:review` 或等效 review 流程
3. **review 通过后才实现** — 不在 review 前写实现代码
4. **实现时维护 implementation notes** — 记录决策、tradeoffs、deviations
5. **执行 gate**:
   - `npm --prefix web run build` (exit code 必须为 0)
   - `git diff --check` (exit code 必须为 0)
   - 必要时 browser smoke
6. **fast lane commit/push main** — 低风险前端改动，走 fast lane
7. **完成后 browser smoke review** — 参考 Milestone B smoke review 流程

### Milestone C Non-Goals

- 大型设计系统重写
- 新 UI framework
- 后端重构
- provider / approval / recall 语义改动
- RAG / embedding
- 真实 LLM 调用
- 前端测试基础设施搭建（已在 Deferred to Follow-Up Work 中）
- P4 品牌视觉（插图、空状态图形、情感化设计）

---

## System-Wide Impact

- **Interaction graph:** 所有改动局限于 React 组件树内部，不涉及 API 层、路由层、状态管理层变更
- **Error propagation:** 不变 — 现有错误处理路径不受影响
- **State lifecycle risks:** SetupPage 的 `step` state 需在页面切换时正确重置（或保留，取决于实现选择）。不涉及持久化
- **API surface parity:** 无 API 变更
- **Integration coverage:** 不涉及跨层交互
- **Unchanged invariants:**
  - 所有 API 端点、请求/响应格式不变
  - 路由逻辑不变（`pushState` + `popstate`）
  - 设计 token 定义不变（颜色、阴影）
  - 审批两步确认安全机制不变
  - 配置验证和后端校验逻辑不变

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| SetupPage 步骤化后表单验证逻辑需适配（某些字段可能在当前步骤不可见但在后端为必填） | 所有字段通过 React `useState` 统一管理，步骤切换仅控制 UI 显隐，不卸载字段对应的 DOM 节点，提交时 `JSON.stringify(patchFromForm(current))` 仍包含完整配置 |
| 新增 `statusIcon()`/`statusLabel()` 需在各 badge 渲染处组合调用 | 调用点集中在 StatusCard/ConfigChecklist/CardWorkspace 三处，改动量小且 TypeScript 编译器会捕获遗漏 |
| 空状态引导按钮的目标页面在 Edge case 下可能不存在（如 Sources 未配置时导航到 Sources 无意义） | 导航按钮始终可用 — 空状态下的用户正是需要去配置的人 |
| 无前端测试覆盖，改动后回归依赖手动验证 | P0 范围小且改动集中，手工 smoke test 可覆盖。测试基础设施作为 deferred item 规划 |
| **Milestone C — i18n locale key 散落风险**: 部分页面文案未被 `t('key')` 替换，出现中英混杂残留 | U13 的 `t()` 函数对未知 key fallback 到 key 自身（英文），TypeScript 类型系统约束 locale key 为已知字符串。browser smoke 逐页切换语言验证 |
| **Milestone C — U10/U13 Recall 文案合并冲突**: U10 优化 Recall 文案后 U13 抽取 copy，若顺序颠倒导致重复劳动 | 强制执行 U10 → U13 顺序：U10 settle Recall 终态文案 → U13 统一抽取到 locale dictionary |
| **Milestone C — locale 切换后 React re-render / 状态一致性**: 切换语言导致组件树 re-render，表单草稿、编辑状态丢失 | `useLocale` 仅修改 locale state，不触发页面级 `location.reload()`。表单 state 在各组件 `useState` 中独立持有，locale 切片不触碰 |
| **Milestone C — 硬编码 copy 漏抽取**: 大范围替换后仍有 hardcoded 中文/英文残留 | 抽取完成后 `grep` 逐文件检查残留中文硬编码模式；browser smoke 中英切换逐页比对 |
| **Milestone C — 大规模 copy 替换导致 UX regression**: `t()` 调用替换文案时 key 映射错误，用户看到错误标签 | 每个 `t('key')` key 与原始 hardcoded 文案一一对应；locale dict 中 zh/en 双写对照原始 UI 文案 |

---

## Sources & References

- Audit: 《MindForge Web UX & Design System Review》(2026-05-22, in-session)
- Dogfood plan: `docs/plans/2026-05-22-001-feat-real-llm-dogfood-plan.md` (removed 2026-05-27 — docs cleanup batch 1)
- Dogfood UI fix: `f5e071b fix: address dogfood review UI findings`
- Design tokens: `web/tailwind.config.ts`
- Global styles: `web/src/styles.css`
