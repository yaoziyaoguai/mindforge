# MindForge Web Design Refresh — Implementation Roadmap

**日期**: 2026-05-26
**状态**: proposed
**输入**: docs/design/2026-05-26-102-mindforge-web-design-direction.md
**参考仓库**: https://github.com/VoltAgent/awesome-design-md

---

## 1. Goals

将 MindForge Web 从当前功能性 UI 迁移到 "Calm Editorial Knowledge Compiler" 设计方向。核心交付：

1. **设计 token 系统落地** — CSS 变量覆盖色彩、排版、间距、阴影、圆角
2. **排版层级建立** — Source Serif 4 (headings) + DM Sans (body/UI) + JetBrains Mono (code)
3. **审批体验成为视觉中心** — Review Queue 和 ApprovalPanel 是最高优先级页面
4. **组件视觉一致性** — Button、Card、Badge、EmptyState 等基础组件统一风格
5. **不改变产品逻辑** — 不改路由、不改 API 调用、不改状态管理、不改审批安全语义

---

## 2. Non-Goals

- 不新增页面或功能
- 不改变后端 API 或数据模型
- 不修改审批安全语义（explicit approval / human_approved）
- 不做 Graph/Sensemaking 页面扩张（lab 页面只做最小样式调整）
- 不引入新的前端框架或大型依赖（Google Fonts `<link>` 不算）
- 不做暗色模式（Stage 5+ 再考虑）
- 不做动画/动效系统（只保留现有 transition）
- 不修改 product copy 内容（只调整视觉呈现）

---

## 3. Current Baseline

### 现有前端栈
- **框架**: React 19 + TypeScript 5.7
- **构建**: Vite 6 + `tsc -b && vite build`
- **CSS**: Tailwind CSS 3.4（未深度定制 theme）
- **图标**: Lucide React 0.468
- **字体**: 系统默认 sans-serif（无 Google Fonts）
- **测试**: Playwright 1.57（E2E），无 vitest
- **页面数**: 13（Home, Setup, Sources, Drafts, Review, Library, Recall, Health, Trash, Wiki, Dogfood, Graph, Sensemaking）
- **组件数**: ~29

### 现有色彩（styles.css）
- 文字色: `#23211d` (warm dark)
- 背景色: `#f7f5f1` (warm paper — 已接近目标 `#faf9f5`)
- Focus outline: `#2368d1` (blue — 需要替换为 Forest Green)

### 关键差距
| 维度 | 当前 | 目标 |
|------|------|------|
| 字体 | system sans-serif | Source Serif 4 + DM Sans + JetBrains Mono |
| 设计 token | Tailwind 默认 + 少量 CSS 变量 | 完整 token 系统 |
| 色彩 | 隐式暖色 | 显式 warm paper palette + 语义色 |
| 阴影 | Tailwind 默认 | Notion 风格多层柔和阴影 |
| 卡片 | Tailwind 默认 | whisper border + 多层阴影 |
| 品牌色 | 无 | Forest Green #2d7d5f |
| 状态色 | Tailwind 默认 | 语义 amber/green/gray |
| 排版层级 | 默认 | serif 标题 + sans 正文 |

---

## 4. Staged Implementation

### Stage 0 — Design Direction Lock （本轮，已完成）

**交付物**:
- [x] `docs/design/2026-05-26-102-mindforge-web-design-direction.md`
- [ ] `docs/plans/2026-05-26-103-web-design-refresh-roadmap.md` (本文档)

**Gate**: `git diff --check`

---

### Stage 1 — Design Token Foundation

**目标**: 建立 CSS 变量体系，引入字体，更新 Tailwind 配置，不改变任何组件外观。

**Implementation Units**:

#### U1.1 Font Loading
- 在 `index.html` 中添加 Google Fonts `<link>`: Source Serif 4 (wght@400;500), DM Sans (wght@400;500;600), JetBrains Mono (wght@400)
- Fallback: `Georgia, serif` / `-apple-system, sans-serif` / `monospace`
- **不引入 npm 字体包**（保持零依赖）

#### U1.2 CSS Custom Properties
- 在 `styles.css` 中定义完整的 `:root` 变量集
- 覆盖: 色彩角色、语义色、排版 scale、间距 scale、阴影层级、圆角 scale
- 变量名使用 `--mf-` 前缀以避免与 Tailwind 或其他库冲突
- 保留现有 `color` / `background` / `font-family` 作为 fallback

#### U1.3 Tailwind Theme Extension
- 在 `tailwind.config.js` 中 extend theme:
  - `colors`: 映射 CSS 变量到 Tailwind color tokens
  - `fontFamily`: serif, sans, mono
  - `fontSize`: 排版层级
  - `borderRadius`: 圆角 scale
  - `boxShadow`: 阴影层级
- 不使用 `preset`，只做最小 extend

#### U1.4 Focus Ring Update
- 将 `styles.css` 中的 focus outline 颜色从 `#2368d1` 改为 `#2d7d5f` (Forest Green)
- 将 `outline-offset` 从 `2px` 改为 `2px`（保持，可读性够）
- 匹配 `--mf-color-accent`

**Gate**:
- `npm --prefix web run build` — exit 0
- `git diff --check`

**风险**: 低。只加变量不改组件，构建通过即安全。

---

### Stage 2 — Shell & Navigation

**目标**: AppShell + Sidebar 视觉重设计，建立应用框架的温暖纸质感。

**Implementation Units**:

#### U2.1 AppShell Layout Polish
- 整体背景色使用 `--mf-color-bg` (#faf9f5)
- 移除任何冷灰/蓝灰残留
- Header（如有）使用暖色表面

#### U2.2 Sidebar Redesign
- 主路径页面链接保持平铺
- Lab/internal 页面（Graph、Sensemaking、Health）折叠到 "实验室" 折叠区
- 当前页面高亮使用 Forest Green 左侧细线（3px）+ 暖色背景
- 导航文字使用 DM Sans，caption 大小
- Sidebar 底色使用 `--mf-color-surface-alt` (#f3f1eb) 与主内容区形成微妙差异

#### U2.3 SafetyBar Polish
- 调整为更体面的 callout 样式
- 使用 whisper border
- 不改变内容逻辑

**Gate**:
- `npm --prefix web run build` — exit 0
- `python -m pytest tests/test_web_product_copy.py -q --tb=short` — exit 0
- Playwright smoke（如已有 setup/home 导航测试）

**风险**: 低-中。Sidebar 结构调整需确保所有 13 个路由可访问。

---

### Stage 3 — Review Queue & Approval（最高优先级）

**目标**: Review Queue 成为视觉中心，审批操作为核心差异化体验。

**Implementation Units**:

#### U3.1 DraftList / ReviewQueueItem Redesign
- 全宽卡片列表（非网格）
- 每项：source 名 → ai_draft 标题（serif）→ summary → 价值分数 → 预览片段
- 已批准卡片降低对比度（opacity 0.6 + 暖灰文字）
- Amber 标签（#b8860b）标记 ai_draft 状态

#### U3.2 ApprovalPanel Redesign
- 使用 serif 小标题
- 时间线组件（ApprovalTimeline）使用 Forest Green 点 + 暖灰线
- Approve 按钮使用 Forest Green，Reject 使用暖红
- 按钮设计谨慎但不隐藏——用户能找到但不会误触
- 确认交互保留（不改变 explicit approval 安全语义）

#### U3.3 DraftDetailPage Reading Layout
- 宽阅读列（max-width: 720px）居中
- Serif 标题，宽松行高正文（1.6）
- Provenance trail 使用 mono 字体
- 元数据使用 caption 大小 + secondary text 颜色

**Gate**:
- `npm --prefix web run build` — exit 0
- `python -m pytest tests/test_web_product_copy.py -q --tb=short` — exit 0

**风险**: 中。审批体验是核心差异化，视觉不能影响操作安全性。必须确保 approve/reject 按钮清晰可辨，状态转换视觉明确。

---

### Stage 4 — Library & Cards

**目标**: Library 页成为温暖的图书馆目录体验。

**Implementation Units**:

#### U4.1 KnowledgeCard Redesign
- 白色表面 + whisper border + 多层阴影
- 圆角 10px
- 卡片内部：标题（serif）、summary（sans body L）、元数据行（caption）、状态 badge
- Hover: 阴影轻微加深

#### U4.2 LibraryPage Layout Polish
- 顶部 filter bar 保留（现有 A5 实现），视觉 polish
- 响应式网格：1 col (mobile) / 2 cols (tablet) / 3 cols (desktop)
- 统计行使用 caption 样式

#### U4.3 Status Badge System
- `ai_draft` → amber 背景 (10% opacity) + amber 文字 + amber 点
- `human_approved` → green 背景 (10% opacity) + green 文字 + green 点
- `lab/internal` → warm gray 背景 + gray 文字
- Badge 使用 pill 形状 (radius-full)

**Gate**:
- `npm --prefix web run build` — exit 0
- `python -m pytest tests/test_web_product_copy.py -q --tb=short` — exit 0

**风险**: 低-中。卡片是最高频展示组件，需验证长文本截断、空卡片、特殊字符等边界。

---

### Stage 5 — Recall, Wiki & Export Polish

**目标**: 搜索/召回、Wiki、导出页面的视觉 polish。

**Implementation Units**:

#### U5.1 RecallPage Polish
- 搜索框使用 serif 占位文字（"搜索你的知识库..."）
- 搜索结果卡片保留现有匹配解释面板
- 零结果使用温暖的 EmptyState

#### U5.2 WikiPage Reading Layout
- 宽阅读列（max-width: 720px）
- Serif 标题，分节清晰
- 现有 WikiSection 组件视觉 polish

#### U5.3 Export/Sources Page Polish
- 格式选择区域清晰分组
- 安全说明使用 SafetyNotice 样式
- 不改变导出逻辑

#### U5.4 EmptyState 统一
- 所有页面的空状态使用一致的温暖引导风格
- 不写营销文案，用中性指示性语言
- 如已有样本数据的入口，提供引导链接

**Gate**:
- `npm --prefix web run build` — exit 0
- `python -m pytest tests/test_web_product_copy.py -q --tb=short` — exit 0

**风险**: 低。这些页面改动边界清晰，主要是视觉 polish。

---

### Stage 6 — Design QA & Polish

**目标**: 视觉一致性审查、可访问性检查、最终 polish。

**Implementation Units**:

#### U6.1 Visual Consistency Pass
- 逐页检查色彩使用是否符合 token 体系
- 确保没有硬编码颜色（全部走 CSS 变量或 Tailwind token）
- 确保 serif/sans/mono 使用一致

#### U6.2 Accessibility Pass
- 色彩对比度检查（WCAG AA 最小 4.5:1 正文，3:1 大文本）
- Focus ring 可见性（所有交互元素）
- Tab order 合理性
- （如已安装 Playwright）axe-core 自动检查

#### U6.3 Responsive Polish
- 320px - 1440px 宽度测试
- 移动端 sidebar 折叠行为
- 卡片网格断点验证

**Gate**:
- `npm --prefix web run build` — exit 0
- `python -m pytest tests/test_web_product_copy.py -q --tb=short` — exit 0
- Playwright browser smoke（如可用）

**风险**: 中。需要在真实浏览器中验证，不能仅靠 build pass。

---

## 5. Page Priority

按用户价值和设计差异化排序：

| Priority | Page | Stage | Rationale |
|----------|------|-------|-----------|
| **P0** | Review Queue (DraftsPage + DraftDetailPage + ApprovalPanel) | Stage 3 | 审批是核心差异化，最高优先 |
| **P0** | AppShell + Sidebar | Stage 2 | 应用框架，所有页面共享 |
| **P1** | Library (LibraryPage + KnowledgeCard + filter bar) | Stage 4 | 最高频使用的浏览页面 |
| **P1** | Card Detail / DraftDetailPage | Stage 3 | 深度阅读体验 |
| **P2** | Recall/Search (RecallPage) | Stage 5 | 第二高频操作 |
| **P2** | Wiki (WikiPage) | Stage 5 | 长文阅读 |
| **P2** | Sources/Import (SourcesPage) | Stage 5 | 知识入口 |
| **P3** | Home (HomePage) | Stage 5 | Dashboard 页 |
| **P3** | Setup (SetupPage) | Stage 5 | 配置页 |
| **P3** | Export (嵌入 SourcesPage/SetupPage) | Stage 5 | 导出功能 |
| **Lab** | Graph + Sensemaking | Stage 5 | 只做最小样式调整，不改功能 |

---

## 6. Component Priority

按复用频率和视觉影响排序：

| Priority | Component | Stage | Current State |
|----------|-----------|-------|---------------|
| **P0** | CSS Custom Properties (:root) | Stage 1 | 不存在 |
| **P0** | AppShell | Stage 2 | 存在，需重设计 |
| **P0** | Sidebar | Stage 2 | 存在，需重设计 |
| **P0** | ApprovalPanel + ApprovalTimeline | Stage 3 | 存在，需重设计 |
| **P0** | DraftList / DraftViewer | Stage 3 | 存在，需重设计 |
| **P1** | KnowledgeCard | Stage 4 | 不存在独立组件（内嵌在页面中） |
| **P1** | Status Badge (内嵌) | Stage 4 | 不存在独立组件 |
| **P1** | Filter Bar (现有 A5) | Stage 4 | 存在，视觉 polish |
| **P2** | EmptyState | Stage 5 | 存在，需统一风格 |
| **P2** | SafetyNotice / SafetyBar | Stage 5 | 存在，需视觉 polish |
| **P2** | ProvenanceTrail / provenance | Stage 3 | 存在，需 polish |
| **P3** | LoadingSkeleton | Stage 5 | 存在，视觉 polish |
| **P3** | ErrorState | Stage 5 | 存在，视觉 polish |
| **P3** | Breadcrumb | Stage 5 | 存在，视觉 polish |
| **P3** | ConfigChecklist | Stage 5 | 存在，视觉 polish |
| **Lab** | GraphCanvas / GraphExplorer / GraphNavigationPanel | Stage 5 | 存在，最小样式调整 |

### 组件提取决策

以下组件建议从页面中提取为独立文件：

| 新组件 | 提取自 | Rationale |
|--------|--------|-----------|
| `KnowledgeCard` | LibraryPage / DraftsPage 内嵌卡片逻辑 | 卡片在 Library、Drafts、Recall 三处复用 |
| `StatusBadge` | 各处内嵌状态标签 | ai_draft / human_approved / lab 状态在多个页面展示 |
| `PageHeader` | 各页面内嵌标题 | 统一的页面标题 + 描述布局 |

---

## 7. Design Tokens — Candidate Specification

以下为候选 token，Stage 1 实际落地时微调。

### 7.1 Colors

```css
:root {
  /* ── Surface ── */
  --mf-color-bg: #faf9f5;
  --mf-color-surface: #ffffff;
  --mf-color-surface-alt: #f3f1eb;

  /* ── Text ── */
  --mf-color-text-primary: #1c1b18;
  --mf-color-text-secondary: #5e5c56;
  --mf-color-text-tertiary: #8a8880;

  /* ── Border ── */
  --mf-color-border: rgba(0, 0, 0, 0.08);
  --mf-color-border-hover: rgba(0, 0, 0, 0.12);

  /* ── Brand ── */
  --mf-color-accent: #2d7d5f;
  --mf-color-accent-hover: #236b4f;
  --mf-color-accent-subtle: rgba(45, 125, 95, 0.1);

  /* ── Status ── */
  --mf-color-status-draft: #b8860b;
  --mf-color-status-draft-subtle: rgba(184, 134, 11, 0.1);
  --mf-color-status-approved: #2d7d5f;
  --mf-color-status-approved-subtle: rgba(45, 125, 95, 0.1);
  --mf-color-status-lab: #8a8880;
  --mf-color-status-lab-subtle: rgba(138, 136, 128, 0.1);

  /* ── Semantic ── */
  --mf-color-warning: #cc7a00;
  --mf-color-error: #c04040;
}
```

### 7.2 Typography

```css
:root {
  --mf-font-serif: 'Source Serif 4', Georgia, serif;
  --mf-font-sans: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  --mf-font-mono: 'JetBrains Mono', 'SF Mono', monospace;

  --mf-text-display: 500 36px/1.15 var(--mf-font-serif);
  --mf-text-h1: 500 28px/1.2 var(--mf-font-serif);
  --mf-text-h2: 500 22px/1.25 var(--mf-font-serif);
  --mf-text-h3: 600 18px/1.3 var(--mf-font-sans);
  --mf-text-body-lg: 400 16px/1.6 var(--mf-font-sans);
  --mf-text-body: 400 15px/1.5 var(--mf-font-sans);
  --mf-text-body-sm: 400 14px/1.45 var(--mf-font-sans);
  --mf-text-caption: 500 12px/1.35 var(--mf-font-sans);
  --mf-text-code: 400 13px/1.5 var(--mf-font-mono);
}
```

### 7.3 Spacing

```css
:root {
  --mf-space-2xs: 4px;
  --mf-space-xs: 8px;
  --mf-space-sm: 12px;
  --mf-space-md: 16px;
  --mf-space-lg: 24px;
  --mf-space-xl: 32px;
  --mf-space-2xl: 48px;
  --mf-space-3xl: 64px;
}
```

### 7.4 Shadows

```css
:root {
  --mf-shadow-flat: none;
  --mf-shadow-raised: 0px 2px 12px rgba(0,0,0,0.03),
                       0px 1px 4px rgba(0,0,0,0.015),
                       0px 0.4px 1.5px rgba(0,0,0,0.008);
  --mf-shadow-overlay: 0px 4px 24px rgba(0,0,0,0.06);
}
```

### 7.5 Border Radius

```css
:root {
  --mf-radius-sm: 4px;
  --mf-radius-md: 8px;
  --mf-radius-lg: 10px;
  --mf-radius-xl: 14px;
  --mf-radius-full: 9999px;
}
```

---

## 8. Risk List

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Google Fonts 加载失败导致 fallback 字体体验差异大 | 低 | 中 | 可靠的 fallback stack；serif fallback Georgia 接近 Source Serif 4 |
| Tailwind extend 与现有 utility class 冲突 | 低 | 中 | 只 extend 不覆盖；使用 `--mf-` 前缀 CSS 变量 |
| 审批按钮视觉改变导致用户困惑 | 低 | 高 | 保留现有按钮位置和文案；只改颜色/圆角/阴影 |
| 卡片组件提取引入 regression | 中 | 中 | 渐进提取；每阶段 build + test |
| 色彩对比度不达标（尤其 amber on warm paper） | 中 | 中 | Stage 6 做 WCAG AA 对比度检查 |
| Sidebar lab 折叠导致无法访问 Graph/Sensemaking 页面 | 低 | 低 | 折叠区可展开；URL 直接访问仍有效 |

---

## 9. Acceptance Criteria

### Per-Stage Criteria
- `npm --prefix web run build` exit 0
- `git diff --check` exit 0
- 无新增 `console.log` 调用
- 相关 product copy tests 通过
- 无硬编码颜色值（CSS 变量或 Tailwind token）

### Final Acceptance (Stage 6 Complete)
- [ ] 13 个页面全部可访问（URL 路由可用）
- [ ] Serif 标题 + Sans 正文 在所有页面一致
- [ ] ai_draft → amber, human_approved → green 状态色一致
- [ ] 无冷蓝/冷灰残留（背景、边框、文字）
- [ ] WCAG AA 对比度达标（正文 4.5:1, 大文本 3:1）
- [ ] Focus ring 在所有交互元素上可见
- [ ] 320px-1440px 响应式可用
- [ ] ApprovalPanel 的 approve/reject 操作路径清晰
- [ ] Lab 页面有 LabFeatureBanner 标识
- [ ] 安全边界说明可见

---

## 10. Test / Build Plan

### 每阶段必跑
```bash
npm --prefix web run build          # TypeScript + Vite build, must exit 0
git diff --check                     # Whitespace check
python -m pytest tests/test_web_product_copy.py -q --tb=short  # Product copy tests
```

### Playwright Smoke（如环境可用）
```bash
npx playwright test --project=chromium  # 或最小 smoke 脚本
```

### Stage 6 专项
- 手动 browser smoke：13 页面逐一访问
- 对比度检查工具（axe-core 或 Chrome DevTools）
- 320px / 768px / 1024px / 1440px 响应式验证

---

## 11. Design Review Checkpoints

| Checkpoint | After Stage | What to Review |
|-----------|-------------|----------------|
| Token Review | Stage 1 | CSS 变量命名、色彩值、排版 scale 是否合理 |
| Shell Review | Stage 2 | 温暖纸质感是否正确，Sidebar 导航是否清晰 |
| Approval Review | Stage 3 | 审批体验是否成为视觉中心，安全语义是否保留 |
| Library Review | Stage 4 | 卡片风格是否符合 "图书馆目录" 感受 |
| Polish Review | Stage 5 | 全页面视觉一致性 |
| Final QA | Stage 6 | 可访问性、响应式、色彩对比度 |

每个 checkpoint 后可用 `/design-review` 做视觉验收。

---

## 12. Recommended Next Slash Command Sequence

完成本计划文档后，推荐以下命令序列：

```
1. /design-shotgun     — 基于设计方向生成 3-5 个静态视觉变体，验证 token 选择
2. /plan-design-review — 审查设计方向 + shotgun 结果，锁定 token
3. /design-html        — 将选定方向转化为关键页面的 HTML/CSS 原型
4. /design-review      — 视觉验收，对照设计方向检查原型
5. /mf-autopilot       — 按本 plan 的 Stage 1-6 逐一实现
```

**注意**: `/design-shotgun` 和 `/design-html` 阶段仍为静态原型，不修改 `web/src/` 下的生产代码。只有 `/mf-autopilot` 阶段才进入实现。

---

## 13. Auto-run Guardrails

以下约束在 auto-run 实现阶段始终生效：

1. **每个 Stage 独立 commit/push** — 不在多个 Stage 完成后才 commit
2. **每个 Stage 必须有 gate** — build + product copy test
3. **不新增 npm 依赖** — 字体用 Google Fonts CDN `<link>`
4. **不改变 API 调用逻辑** — 只改组件外观
5. **不修改审批安全语义** — explicit approval 流程不变
6. **不恢复 Graph/Sensemaking 扩张** — lab 页面只做最小样式
7. **不做暗色模式** — 等待后续 spec
8. **不复制参考站点的品牌标识** — 所有 token 为独立选择
9. **不做全量一次性重设计** — 按 Stage 递增
10. **不在 context < 15% 时开始新 Stage** — 写 handoff 后暂停

---

## Self-Review

| Check | Verdict |
|-------|---------|
| 是否从设计方向文档正确翻译？ | Yes — 所有 token、组件、页面目标来自 design direction |
| 是否可被 /mf-autopilot 直接执行？ | Yes — 每个 Stage 有明确的 Implementation Units + Gate |
| 是否尊重审批安全语义？ | Yes — explicit approval 标记为不可变 |
| 是否保护了 lab 边界？ | Yes — Graph/Sensemaking 只在 Stage 5 做最小样式 |
| 是否可独立验证每个 Stage？ | Yes — 每个 Stage 有独立 gate |
| 是否避免了过度工程化？ | Yes — 不引入新依赖、新框架、新构建工具 |
| 是否考虑了现有前端栈？ | Yes — Tailwind 3、React 19、Vite 6、Lucide React |
