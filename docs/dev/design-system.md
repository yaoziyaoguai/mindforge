# MindForge Local Console Design System

轻量级设计系统文档 —— 设计原则 + token 参考 + 组件使用规范 + 页面结构规则。
P3 Design System Foundation, 2026-05-28.

---

## Product Identity

MindForge Local Console is the local-first Web surface for MindForge. It is a
single-user, localhost-only personal knowledge workbench for people who want to
configure, inspect, review, approve, reject, and recall their own knowledge
cards without living in a CLI.

It is not a SaaS product, not an admin dashboard, and not a marketing website.
It should feel like a quiet local tool sitting over the user's own files:
transparent, reversible where possible, and explicit whenever a write can
change long-term memory.

## Design Principles

- Calm: default surfaces are quiet, readable, and low-drama. The UI avoids
  marketing copy, busy gradients, and decorative animation.
- Trustworthy: every page shows what local state it is reading and what action
  will happen next.
- Beginner-safe: empty states explain the next command or local action instead
  of assuming CLI fluency.
- Review-focused: drafts are treated as work awaiting human judgment, not as
  generated content to rubber-stamp.
- Local-first: the product language, status labels, and Safety Bar emphasize
  localhost, current vault, and local files.
- Explicit write actions: write-capable controls are visually distinct and
  state exactly what will be written.
- Transparent configuration: model setup status is shown as configured/missing
  only; secret values never appear.
- No hidden automation for approval: `human_approved` can only be produced by
  an explicit user confirmation.

---

## 1. Design Tokens

Token 集中引用文件：`web/src/design/tokens.ts`

### 1.1 双系统现状

MindForge Web 前端有两套 token 系统并存，**值不完全对齐**：

| 语义角色 | Tailwind (A套) | CSS 变量 (B套) |
|---------|---------------|---------------|
| 页面背景 | `surface: #f7f5f1` | `--mf-bg: #faf9f5` |
| 卡片背景 | `panel: #ffffff` | `--mf-surface: #ffffff` |
| 主文字 | `ink: #23211d` | `--mf-text-primary: #1c1b18` |
| 次级文字 | `muted: #6d685f` | `--mf-text-secondary: #5e5c56` |
| 第三级文字 | Tailwind opacity | `--mf-text-tertiary: #8a8880` |
| 边框 | `line: #ddd8cf` | `--mf-border: rgba(0,0,0,0.08)` |
| 强调色 | `primary: #2368d1` (蓝) | `--mf-accent: #2d7d5f` (绿) |
| 成功 | `safe: #237a57` | `--mf-approved: #2d7d5f` |
| 警告 | `warn: #b66b13` | `--mf-warning: #cc7a00` |
| 错误 | `danger: #b42318` | `--mf-error: #c04040` |

**Token 源文件：**
- A 套：`web/tailwind.config.ts`
- B 套：`web/src/styles.css` `:root`
- TS 常量：`web/src/design/tokens.ts` (importable reference)

### 1.2 A 套使用者 (Tailwind utility classes)

主要组件：`Sidebar`, `ViewSwitcher`, `CollectionPanel`, `CardWorkspace`, `HealthStatusBar`, `FolderImportForm`, `SourcesPage`, `HomePage`, `SetupPage`, `LibraryPage`

用法：`className="text-ink bg-panel border-line"`

### 1.3 B 套使用者 (CSS 自定义属性)

主要组件：`DraftList`, `ApprovalPanel`, `StatusCard`, `AppShell`, `RecallPage`

用法：`style={{ color: "var(--mf-text-primary)" }}` 或 `className="text-[var(--mf-accent)]"`

### 1.4 字体

| Token | 值 | 用途 |
|-------|-----|------|
| `--mf-font-sans` | DM Sans, system-ui | 正文默认 |
| `--mf-font-serif` | Source Serif 4, Georgia | 标题 (PageHeader h1, DraftList, ApprovalPanel, LibraryPage) |
| `--mf-font-mono` | JetBrains Mono | 代码块 (CardWorkspace YAML, GraphCanvas, WikiReferenceCard, LibraryPage 元数据) |

### 1.5 阴影

| Token (A套) | 值 | 用途 |
|------------|-----|------|
| `shadow-subtle` | `0 1px 2px rgba(35,33,29,0.08)` | 卡片/面板轻抬起 |

| Token (B套) | 用途 |
|------------|------|
| `--mf-shadow-flat` | 无阴影 |
| `--mf-shadow-raised` | 列表卡片、状态卡片 (DraftList, StatusCard, ApprovalPanel, RecallPage) |
| `--mf-shadow-card` | 较深卡片 |
| `--mf-shadow-overlay` | Modal/Dropdown |

### 1.6 圆角 (B套)

| Token | 值 | 用途 |
|-------|-----|------|
| `--mf-radius-sm` | 4px | 小元素 |
| `--mf-radius-md` | 8px | 状态卡片、召回结果 |
| `--mf-radius-lg` | 10px | 审阅面板 |
| `--mf-radius-xl` | 14px | 大卡片 |
| `--mf-radius-full` | 9999px | 圆形元素 |

### 1.7 已知 Token 缺陷

- `--mf-warn` 未定义 (ExportPage 引用，定义的是 `--mf-warning`)
- `--mf-info` 未定义 (ExportPage 引用)
- `--mf-success` 未定义 (QuickStartWizard 引用)
- SensemakingPage 使用独立第三套 inline CSS 变量 (`--bg-secondary`, `--text-muted` 等)
- 部分组件直接使用 Tailwind 原色 (`red-500`, `amber-500`, `emerald-500`) 而非 token
- A/B 双套 accent 色不同 (蓝 vs 绿)，导致不同页面视觉不一致

---

## 2. Layout

### 2.1 页面结构模板

```
AppShell
├── SafetyBar (顶部安全状态栏, 始终可见)
├── Sidebar (左侧导航, w-64, shrink-0)
└── <main> (右侧内容区, flex-1, overflow-y-auto)
    ├── PageHeader (页面标题 + 描述, 可选)
    │   ├── h1 (serif, --mf-text-h1, 28px)
    │   └── p (description, --mf-text-body-s, 14px, --mf-text-tertiary)
    ├── OnboardingHint (首次使用提示, 可选, localStorage dismiss)
    └── 页面特有内容
```

### 2.2 AppShell

- 文件：`web/src/components/AppShell.tsx`
- 全高 flex 布局 (`h-screen flex`)
- 背景色：`--mf-bg` (`#faf9f5`)
- Right detail panel: 用于 draft metadata/source context/approval panel (窄屏时 stack 到下方)

### 2.3 Sidebar

- 文件：`web/src/components/Sidebar.tsx`
- 背景：`bg-[#efebe3]` (特殊米色，非 token)
- 导航分组：Processing (Setup/Sources/Drafts) → Using (Home/Library/Wiki/Recall) → Tools (Health/Export/Trash) → Lab (折叠: Graph/Sensemaking/Dogfood)
- 高亮规则：`path === item.href || (item.href !== "/" && path.startsWith(item.href))`
- 底部：语言切换 (zh/en) + GitHub Issues 反馈链接

### 2.4 PageHeader (CSS class: `.page-header`)

- h1: serif 字体, `--mf-text-h1` (28px), `--mf-text-primary`, font-weight 500
- p (描述): `--mf-text-body-s` (14px), `--mf-text-tertiary`
- 下间距: `--mf-space-lg` (24px)

---

## 3. Color Semantics

- Green (`safe` / `--mf-accent` / `--mf-approved`): safe, local, ready, completed.
- Amber (`warn` / `--mf-warning`): needs attention, real environment, incomplete config, real vault warning.
- Red (`danger` / `--mf-error`): destructive or irreversible write, failed safety condition, dangerous action.
- Blue (`primary`): the next recommended action and ordinary navigation focus.
- Neutral (`ink`/`muted`/`line`): reading, review, metadata, informational state.

These colors carry meaning. Do not use red for decoration or green for ordinary branding.

---

## 4. 页面列表 (14 pages)

| 路由 | 页面 | 分组 | 令牌体系 | 特有 CSS |
|------|------|------|---------|---------|
| `/` | HomePage | Using | A套 | dashboard grid |
| `/setup` | SetupPage | Processing | A套 | 表单卡片 |
| `/sources` | SourcesPage | Processing | A套 | 文件导入 + source 列表 |
| `/drafts`, `/review` | DraftsPage | Processing | B套 | DraftList + ApprovalPanel |
| `/library` | LibraryPage | Using | A套 + B套字体 | 卡片浏览/筛选 |
| `/recall`, `/search` | RecallPage | Using | B套 | BM25 搜索 |
| `/wiki` | WikiPage | Using | A套 | `.wiki-prose` 排版 |
| `/health` | HealthPage | Tools | A套 | 8 项诊断卡片 |
| `/export` | ExportPage | Tools | A套 | 格式选择 + 下载 |
| `/trash` | TrashPage | Tools | A套 | 回收站列表 |
| `/graph` | GraphPage | Lab (internal) | A套 | vis-network 图 |
| `/sensemaking` | SensemakingPage | Lab | 独立第三套 | bridge/evolution |
| `/dogfood` | DogfoodPage | Lab (internal) | A套 | 开发者维护工具 |

---

## 5. Component Semantics

### 5.1 共享组件

| 组件 | 文件 | 用途 |
|------|------|------|
| `AppShell` | `components/AppShell.tsx` | 全局布局容器 |
| `Sidebar` | `components/Sidebar.tsx` | 全局导航 |
| `SafetyBar` | `components/SafetyBar.tsx` | 安全状态条 (每页可见) |
| `Breadcrumb` | `components/Breadcrumb.tsx` | 面包屑导航 |
| `OnboardingHint` | `components/OnboardingHint.tsx` | 首次使用提示 (localStorage dismiss) |
| `ErrorState` | `components/ErrorState.tsx` | 错误展示 (human-readable, 不含 raw traceback) |
| `LoadingSkeleton` | `components/LoadingSkeleton.tsx` | 加载骨架 (按页面 variant) |

### 5.2 Safety Bar Rules

Safety Bar 内容属于产品契约：

- 显示 "Local only" + host (当运行在 `127.0.0.1`/`localhost`)
- 显示当前 vault path (真实 vault 用 amber 警告)
- 显示 model setup status: `configured` 或 `missing` (不显示 API key)
- 显示 write mode: `read-only` 或 `explicit approval required`
- 显示 pending draft count
- 短标签，无 raw stack traces 或 config dumps

### 5.3 页面级组件

| 组件 | 文件 | 使用页面 |
|------|------|---------|
| `DraftList` | `components/DraftList.tsx` | DraftsPage |
| `ApprovalPanel` | `components/ApprovalPanel.tsx` | DraftsPage (卡片审阅，必须二次确认) |
| `StatusCard` | `components/StatusCard.tsx` | 多页面通用状态卡片 |
| `ViewSwitcher` | `components/ViewSwitcher.tsx` | LibraryPage |
| `CollectionPanel` | `components/CollectionPanel.tsx` | LibraryPage |
| `CardWorkspace` | `components/CardWorkspace.tsx` | LibraryPage |
| `BulkActions` | `components/BulkActions.tsx` | LibraryPage |
| `KnowledgeCommunityPanel` | `components/KnowledgeCommunityPanel.tsx` | LibraryPage |
| `LocalGraphPreview` | `components/LocalGraphPreview.tsx` | LibraryPage (卡片详情) |
| `WikiReferenceCard` | `components/WikiReferenceCard.tsx` | WikiPage |
| `QuickStartWizard` | `components/QuickStartWizard.tsx` | HomePage |
| `GraphExplorer` | `components/GraphExplorer.tsx` | GraphPage |
| `GraphCanvas` | `components/GraphCanvas.tsx` | GraphPage |
| `GraphNavigationPanel` | `components/GraphNavigationPanel.tsx` | GraphPage |
| `FolderImportForm` | `components/FolderImportForm.tsx` | SourcesPage |
| `SourceAddPanel` | `components/SourceAddPanel.tsx` | SourcesPage |
| `ImportCardForm` | `components/ImportCardForm.tsx` | SourcesPage |
| `NextActionCard` | `components/NextActionCard.tsx` | 多页面 |
| `HealthStatusBar` | `components/HealthStatusBar.tsx` | HealthPage |

### 5.4 状态交互规范

- **Active/Selected**: `border-[var(--mf-accent)] bg-[var(--mf-accent)]/8 text-[var(--mf-accent)]` (B套), 或 `text-primary bg-primary/8 border-primary` (A套)
- **Lab/Internal 页面**: 顶部 LAB/INTERNAL banner (SensemakingPage, DogfoodPage)
- **Error 状态**: `ErrorState` 组件
- **Loading 状态**: `LoadingSkeleton` 组件
- **Empty 状态**: 各页面独立处理，需说明 "为什么空 + 下一步做什么"

---

## 6. Approval Interaction

Approve 不是普通按钮。它意味着 `ai_draft -> human_approved`，卡片将进入长期记忆。

规则：
- Approval panel 必须在 approve 控件前显示 source/draft context
- Approve 需要二次确认
- 用户必须显式确认已审阅 source
- API payload 必须包含 `confirm: true` 和 `reviewed_source: true`
- Reject 可附带可选原因
- 第一版不需要 inline draft editing
- 第一版不需要 undo
- 无后台进程可标记卡片为 `human_approved`

---

## 7. Empty And Error States

每个 empty state 告诉用户下一步做什么：
- No vault: configure `vault.root`
- No sources: place supported files in inbox
- No drafts: check model setup, add source
- No approved cards: review and approve at least one draft

每个 error state 包含：
- Short human-readable explanation
- Whether the action read local files, attempted a write, or neither
- One next action
- No raw traceback for ordinary users

---

## 8. Accessibility

- 语义 HTML: `nav`, `main`, `section`, `article`, `button`
- 每个交互控件有 clear accessible label
- 键盘 focus 状态可见且高对比度 (`outline: 2px solid var(--mf-accent)`)
- Button 是 real button，不是 clickable div
- 颜色永远伴有文字标签
- Text contrast 在 calm/neutral/warning 状态下都保持可读

---

## 9. Naming Conventions

- 组件文件：PascalCase, `DraftList.tsx`
- 页面文件：PascalCase + Page 后缀, `HomePage.tsx`
- 工具函数：camelCase, `formatDate()`
- i18n key：`namespace.sub.key`, `nav.group.processing`
- CSS class：kebab-case, `.page-header`, `.wiki-prose`
- CSS 变量：`--mf-{category}-{name}`, `--mf-text-primary`

---

## 10. UI Copy Policy

面向用户的 Web UI 文本本地化策略。

### 核心规则

1. **用户可见 UI copy 必须本地化** — 所有标题、说明、按钮、状态标签、操作文案必须通过 `web/src/lib/i18n.ts` 的 `t(key)` 函数获取，支持 zh/en 切换。
2. **技术标识符降级展示** — 后端 internal status code、model ID 等仅作为次要信息展示（小字、灰色、括号内），用户侧主展示使用 `friendlyStatus()` 等 display mapping 函数。
3. **用户内容不翻译** — 卡片正文/标题、source title/path、用户自定义 model ID、产品名 "MindForge"、算法名 "BM25"、adapter 名称等禁止翻译。
4. **格式名保留原文** — Markdown、PDF、HTML、JSON、BM25、LLM、API key 保留原名，周围说明文本必须本地化。
5. **NextAction 契约** — `action_key`/`description_key` 是 machine-readable identifier，前端通过 `nextActionLabel()`/`nextActionDescription()` 做 display mapping。
6. **后端不翻译** — 后端 API 返回 machine-readable identifiers，前端负责 human-readable labels，多语言切换是纯前端关注点。

### 已有 display mapping 函数

| 函数 | 用途 |
|------|------|
| `friendlyStatus(status, locale?)` | ai_draft → "待确认" / "Pending Review" |
| `statusLabel(status, locale?)` | ok → "正常" / "OK" |
| `nextActionLabel(key, locale?)` | init_vault → "初始化知识库" |
| `nextActionDescription(key, locale?)` | home.go_to_review.desc → 审核说明 |
| `workflowStepLabel(stepId, locale?)` | triage → "初筛" |
| `strategyStatusLabel(status, locale?)` | default workflow → "默认工作流" |
| `sourceStatusLabel(status, locale?)` | active → "监控中" |
| `sourceRunStatusLabel(status, locale?)` | running → "处理中" |
| `sourceDueStatusLabel(status, locale?)` | overdue → "已逾期" |

### 防回归检查

容易引入中英混用的场景：新增 NextAction、新增状态标签、新增页面、操作按钮文案、空状态提示。必须通过 `t()` 或 display mapping 函数处理。`tests/test_web_product_copy.py` 包含回归测试。
