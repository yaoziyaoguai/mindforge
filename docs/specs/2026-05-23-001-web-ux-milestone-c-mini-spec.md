---
title: Web UX Milestone C Mini Spec
type: spec
status: draft
date: 2026-05-23
origin: docs/plans/2026-05-22-002-feat-web-ux-improvement-plan.md
---

# Web UX Milestone C Mini Spec

## 1. Goal

继续提升 Web UX，覆盖 6 个方向（对应 plan R9-R14），不改后端：

1. **Review card 视觉层级优化** (R9) — ApprovalPanel 信息层次更清晰
2. **Source History / provenance 展示优化** (R10) — 来源追溯链路用户可理解
3. **Recall 文案和状态精炼** (R11) — 搜索引导/结果/错误文案精炼
4. **spacing / typography 小范围统一** (R12) — 修正页面间排版不一致
5. **form field accessibility 修复** (R13) — 关键 form field 加 id/name/aria-label
6. **中英文 UI 可切换** (R14) — 消除中英混杂，用户自由切换

## 2. Non-Goals (Explicit Exclusions)

- ❌ mail storage / email / SMTP / inbox — 任何 mail 相关实现
- ❌ backend API i18n — 后端错误信息不做国际化
- ❌ provider / approval / recall 后端语义改动
- ❌ RAG / embedding / vector DB
- ❌ real LLM 调用
- ❌ 大型设计系统重写（不改 tailwind.config.ts token）
- ❌ 新 UI framework（不引入 React Router / Redux / Zustand 等）
- ❌ 多语言 CMS / RTL 语言支持
- ❌ Obsidian vault 写入
- ❌ 前端测试基础设施搭建（仍在 Deferred to Follow-Up Work）

## 3. i18n / 中英文切换策略

### 3.1 方案选型

采用**轻量 locale dictionary**，不引入外部 i18n 框架。

理由：当前需要翻译的 key < 80 个，页面 < 10 个，react-intl / i18next 引入的 boilerplate 超过核心逻辑代码量。如果实现阶段发现轻量方案确实无法支撑（如需要 plural / interpolation / date formatting），停止并升级 review，再由 review 决定是否引入轻量依赖。

### 3.2 核心设计

**LocaleDict 类型:**

```typescript
type Locale = "zh" | "en";

type LocaleDict = Record<string, string>; // key → 文案映射

const copy: Record<Locale, LocaleDict> = {
  zh: { ... },
  en: { ... },
};
```

**翻译函数:**

```typescript
function t(key: string, locale: Locale): string {
  return copy[locale]?.[key] ?? copy.en[key] ?? key;
}
```

Fallback 链：当前 locale dict → en dict → key 自身（纯英文 string）。

**useLocale hook:**

```typescript
function useLocale() {
  const [locale, setLocaleState] = useState<Locale>(() =>
    (localStorage.getItem("mindforge-locale") as Locale) ?? "zh"
  );
  const setLocale = (l: Locale) => {
    localStorage.setItem("mindforge-locale", l);
    setLocaleState(l);
  };
  return { locale, setLocale, t: (key: string) => t(key, locale) };
}
```

### 3.3 设计决策（本次 mini spec 确定，不再 deferred）

| 问题 | 决策 | 原因 |
|------|------|------|
| 默认语言 | 简体中文 (`zh`) | 当前用户群中文为主，英文为备选 |
| 切换入口 | Sidebar footer | 最小改动路径，不引入 Settings 子页面 |
| locale 文件结构 | 单一 `web/src/lib/i18n.ts`，`copy` 对象按页面分区注释 | < 80 keys 不需要拆分多文件 |
| 持久化 | `localStorage` key `mindforge-locale` | 刷新后保持用户选择 |

### 3.4 内部状态字段 vs 用户展示 copy 的边界

**内部字段不变（英文）：** `ai_draft`、`human_approved`、`source_id`、`run_id`、`stage_models`、`source_content_hash` 等后端/API 字段保持英文。

**用户展示通过 locale copy 映射：**

```typescript
// 内部：card.status === "ai_draft"
// 用户看到（zh）："待审阅"
// 用户看到（en）："Pending Review"
const label = friendlyStatus(card.status); // 已有函数，内部已返回中文
// i18n 之后：friendlyStatus 仍返回内部 key → t(key) 映射到当前语言
```

`friendlyStatus()` 和 `statusLabel()` 改为接受 locale 参数或在调用方通过 `t()` 包装。不影响内部 status string。

## 4. File Scope (Exact List)

### 4.1 New Files

| File | Purpose |
|------|---------|
| `web/src/lib/i18n.ts` | locale dictionary + `t()` + `useLocale` hook |

### 4.2 Modified Files — i18n + Visual Polish Combined

| File | i18n Changes | Visual/Other Changes |
|------|-------------|---------------------|
| `web/src/components/Sidebar.tsx` | 导航标签 + 分组标签 → `t()` | 语言切换 toggle 入口 (sidebar footer) |
| `web/src/components/ApprovalPanel.tsx` | 审批文案 → `t()` | R9: 信息层次微调 |
| `web/src/components/CardWorkspace.tsx` | 卡片标签/来源历史文案 → `t()` | R9: review 视觉层级; R10: provenance 展示 |
| `web/src/components/EmptyState.tsx` | — | R9: action 引导文案已通过 props 传入 |
| `web/src/components/DraftList.tsx` | 列表标签/状态文案 → `t()` | — |
| `web/src/components/StatusCard.tsx` | 卡片描述文案 → `t()` | — |
| `web/src/pages/RecallPage.tsx` | 搜索引导/结果/错误文案 → `t()` | R11: copy 精炼; R13: 搜索框 id/name/label |
| `web/src/pages/SetupPage.tsx` | 步骤标签/配置文案 → `t()` | R12: stepper 间距 |
| `web/src/pages/LibraryPage.tsx` | 页面标题/空状态文案 → `t()` | R12: 卡片列表间距 |
| `web/src/pages/DraftsPage.tsx` | 页面标题/空状态文案 → `t()` | — |
| `web/src/pages/HomePage.tsx` | StatusCard description/NextAction → `t()` | — |
| `web/src/pages/SourcesPage.tsx` | 状态/操作文案 → `t()` | R13: frequency combobox id/name |
| `web/src/styles.css` | — | R12: 排版基线微调 |

### 4.3 Files NOT Modified

| File | Reason |
|------|--------|
| `web/src/lib/utils.ts` | `friendlyStatus()`/`statusLabel()` 现有签名不变。i18n 通过 `t()` 在调用处包装 |
| `web/src/api/*` | API 层零变更 |
| `web/src/pages/TrashPage.tsx` | 暂无用户可见 hardcoded 文案 |
| `web/src/components/ConfigChecklist.tsx` | 当前无硬编码中文文案，checklist item label 来自 API |
| `web/src/components/LocalGraphPreview.tsx` | 当前英文文案为技术说明，保留 |
| `web/src/pages/WikiPage.tsx` | Wiki 内容来自 vault，非 UI copy |
| `src/mindforge/**` | 后端零变更 |

## 5. Execution Order

```
Step 1: U11 + U12 (accessibility) — form field id/name/label + spacing/typography
         ↓ (独立视觉修正和 a11y 修复，无依赖)
Step 2: U10 (Recall copy) — settle Recall 页面终态文案
         ↓ (先定文案终态，避免后续 i18n 抽取后反复修改)
Step 3: U8 + U9 (Review card + Source provenance) — 视觉层级和来源展示
         ↓ (依赖 U7 已有的 CardWorkspace 排版基础)
Step 4: U13 (i18n) — 创建 locale dictionary → 抽取所有硬编码文案 → 加切换入口
         ↓ (最后抽取 copy，此时所有页面 copy 已稳定)
Step 5: browser smoke — npm build → start server → verify all pages zh/en switch
```

**为什么 i18n (U13) 必须最后:**
U10/U8/U9 都可能调整文案措辞。如果在这些 step 之前做 i18n 抽取，每次调整都需要同时改 locale dict 中 zh/en 两个 key，增加出错概率和重复劳动。先 settle 所有 copy 终态，再一次性抽取到 locale dict。

## 6. Acceptance Criteria

### 6.1 Visual Polish (U8/U9/U11/R9/R10/R12)

- [ ] Review card 信息层次清晰：标题 → 状态 → 摘要 → 操作区，主操作视觉突出
- [ ] Source provenance 展示用户可理解：路径用 `display_path`，不暴露 `source_id`/`run_id`
- [ ] Setup/Recall/Library 页面间 h1/h2 标题层级、卡片间距视觉一致
- [ ] 不改变 `tailwind.config.ts` 设计 token

### 6.2 Accessibility (U12/R13)

- [ ] Recall 搜索框有 `id` 和 `aria-label` 关联
- [ ] Sources 页 frequency combobox 有 `id` 和 `aria-label` 关联
- [ ] Chrome DevTools accessibility audit 不再报告对应 form field hint

### 6.3 Recall Copy (U10/R11)

- [ ] 搜索引导明确说明 BM25 词法匹配，不误导为 RAG/semantic search
- [ ] 搜索结果 score 标签为中国用户直观的 "高相关"/"相关"/"低相关"
- [ ] Error/loading/empty 三态文案完整

### 6.4 i18n (U13/R14)

- [ ] `web/src/lib/i18n.ts` 存在，locale dictionary `zh`/`en` 两套完整
- [ ] Sidebar footer 有语言切换入口（简体中文 / English toggle）
- [ ] 切换语言后，以下页面关键文案变更：
  - Sidebar 导航标签和分组标签
  - Home StatusCard 描述
  - Setup 步骤标签和配置说明
  - Drafts 空状态
  - Library 页面标题和空状态
  - Recall 搜索引导/结果/错误文案
  - CardWorkspace 状态 badge、编辑按钮、来源历史
  - ApprovalPanel 审批文案
- [ ] 未知 locale key fallback 到 key 自身（不 crash、不显示 undefined/null）
- [ ] 切换语言不触发页面刷新（`location.reload()`）
- [ ] 刷新页面后保持用户选择的语言（`localStorage`）
- [ ] 不引入新 npm 依赖

### 6.5 Red Lines (Must NOT Break)

- [ ] 内部业务字段不变：`ai_draft` / `human_approved` 等保持英文
- [ ] API contract 不变：所有 API 请求/响应格式零变更
- [ ] `npm --prefix web run build` exit code = 0
- [ ] `git diff --check` exit code = 0
- [ ] 不改 `src/mindforge/**` (后端)
- [ ] 不新增 npm 依赖
- [ ] no mail storage / email / SMTP implementation
- [ ] browser smoke 通过（console 无 error，network 无 4xx/5xx）

## 7. Verification Plan

### 7.1 Build Gate

```bash
npm --prefix web run build   # must exit 0
git diff --check             # must exit 0
```

### 7.2 Browser Smoke

启动 Web server 后逐页检查：

1. **Sidebar**: 语言切换 toggle 存在，切换 zh↔en 后导航标签跟随
2. **Home**: StatusCard 描述文案根据语言切换
3. **Setup**: 步骤标签、表单标签根据语言切换
4. **Drafts**: 空状态文案根据语言切换
5. **Library**: 页面标题、卡片标签根据语言切换
6. **Recall**: 搜索引导、结果标签根据语言切换
7. **Console**: 无 error / warning (P3 hint 除外)
8. **Network**: 所有 XHR/fetch 200，无 4xx/5xx

### 7.3 Regression Checks

- [ ] 所有页面可正常导航，sidebar active state 正确
- [ ] StatusCard/ConfigChecklist badge 图标 + 标签显示正确
- [ ] 审批两步确认流程完整
- [ ] Setup 3 步 stepper 正常
- [ ] Source path copy/reveal fail-closed 策略不变
- [ ] 空状态引导 action 可用
