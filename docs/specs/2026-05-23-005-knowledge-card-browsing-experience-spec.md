# MindForge Web UX Milestone F: Knowledge Card Browsing Experience Spec

**Date**: 2026-05-23
**Type**: feat
**Status**: draft
**Precursor audit**: 《MindForge Web Knowledge Experience Stage Review & Brainstorm》(2026-05-23, in-session)

---

## 1. Background

Milestones A-E 已将 Web 主路径、Setup、i18n、Dashboard、Action Guidance 推进到基本可用状态。当前最大问题不再是「功能是否可用」，而是「知识卡片是否值得浏览、阅读、探索」。

CEO 阶段审计 (2026-05-23) 的核心发现：

| 维度 | 当前评分 | 根因 |
|------|----------|------|
| Library 浏览体验 | 3/10 | 340px Card List Sidebar 是「数据库行转置」，不是知识浏览 |
| Card Grid 视觉 | 4/10 | CardSections 排版 clean 但单调，metadata pills 缺上下文 |
| 关系可见性 | 4/10 | LocalGraphPreview 框架在，但仅 WikiSection 有，Card Detail 缺少 |
| 卡片操作完整性 | 3/10 | View/Edit/Approve 之外缺少知识操作（related cards, quick scan） |

已有后端数据支持：`LibraryCardDetailResponse.related_cards` 字段已存在，无需任何新增端点即可实现 Related Cards 功能。

**本 milestone 目标：将 Library / Knowledge Card 从「工程列表」升级为「知识浏览体验」。**

---

## 2. Goals

1. Library 从 340px sidebar 列表感升级为 Card Grid 浏览体验
2. Knowledge Card Detail 提供更清晰的信息层级（Summary Panel）
3. Related Cards / relationship hints 让用户能从一张卡继续探索
4. Empty state 继续提供下一步引导
5. i18n / copy policy 持续生效
6. 不改变 approval / recall / BM25 语义
7. 不新增后端 API — 所有数据来自现有 endpoint

---

## 3. Non-Goals

明确排除以下内容：

1. 完整知识图谱页面（全局 Graph）
2. RAG / embedding / semantic search
3. 新后端 related endpoint — 已有 `LibraryCardDetailResponse.related_cards`
4. 大型 Markdown parser 替换（继续使用现有 `renderMarkdown`）
5. 图形库 / animation library / UI framework
6. Mail storage
7. Real LLM 调用
8. Approval flow 重构
9. Drafts approval queue 大重构
10. Setup / Sources 再重构
11. 全局设计系统重写
12. 暗色模式完整实现
13. Wiki TOC Scroll Spy / Print Export / Reader mode — 纳入 future section，本轮不实现

---

## 4. Implementation Units

### U1. Card Grid Layout

**Goal:** Library 默认视图从 340px sidebar 数据列表升级为响应式 card grid，每张卡片可扫描、可辨识。

**Data source:** `LibraryCardsResponse.cards` — 现有 `getLibraryCards()` API。

**Card grid design:**

每张 card 卡片展示：
- **Title** (title 或 fallback to 「未命名卡片」)
- **Status badge** (friendlyStatus + statusIcon + statusTone，复用现有)
- **Source type chip** (Markdown/PDF/Word/HTML/Text，小字 uppercase)
- **Track chip** (如有)
- **Tags preview** (最多 3 个 tag chips)
- **Updated date** (相对时间或日期)

**Responsive breakpoints:**
- `< 640px` (mobile): 1 column, full width
- `640px-1024px` (tablet): 2 columns
- `> 1024px` (desktop): 3 columns
- `> 1400px` (wide): 4 columns

**Card interaction:**
- 点击卡片 → 展开右侧 detail view（保持现有 selected/onSelect 模式）
- Selected 卡片有 primary border highlight

**Cover fallback strategy:**
- 不依赖图片（卡片正文以 Markdown 为主，无图片提取 pipeline）
- Source type-based 颜色 accent: 每个 source type 对应一个柔和的 accent 色条（卡片顶部 4px border-top）
- 无图片时不显示空白占位符

**Status/source/tag chips:**
- 复用现有 `statusIcon()` + `statusTone()` + `friendlyStatus()`
- Source type labels: 复用现有 `sourceTypeLabels` (Markdown/Text/HTML/PDF/Word)

**Empty state:**
- 卡片列表为空时，显示现有 EmptyState 组件（`library.empty_*` i18n keys）

**Files:**
- Modify: `web/src/pages/LibraryPage.tsx`
- Modify: `web/src/styles.css` (card grid specific rules only)

### U2. Card Summary Panel

**Goal:** 每张知识卡片在 detail view 中有一个「快速概览」面板，帮助用户在 5 秒内判断卡片是否值得通读。

**Data source:** 从 `LibraryCardDetailResponse.body` (Markdown 字符串) 前端提取。

**Summary 内容:**

1. **卡片元数据行**: title + status badge + source type + updated time（紧凑单行）
2. **Headings outline**: 从 body Markdown 中提取 `## ` 和 `### ` 标题，展示为缩进大纲列表
   - 没有 heading 时显示正文前 150 字符作为 excerpt
3. **Tags**: 从 `LibraryCardResponse` 的 `tags` 字段展示（如有）
4. **Track & Strategy**: 展示 track 和 strategy label（如有）

**展开/折叠:**
- Summary Panel 默认展开（detail view 打开时可见）
- 「收起概览」按钮将面板折叠为一行元数据
- Collapse state 不持久化（每次打开 detail 默认展开）

**Source priority（摘要内容优先级）:**
1. Headings outline (从 body `##`/`###` 提取) — 纯前端，零依赖
2. Tags (从 `card.tags`) — API 已有
3. First paragraph excerpt (前 150 chars，去掉 Markdown 标记) — 纯前端

**不依赖 LLM:** 所有 summary 内容来自前端 Markdown 解析或已有 API 字段。

**中文学习型说明**: Summary Panel 是前端展示提取，不是 AI summary。不生成新内容，仅结构化展示现有数据。

**Files:**
- Modify: `web/src/components/CardWorkspace.tsx`

### U3. Related Cards Horizontal Strip

**Goal:** 在 reading pane 底部 (Source & History 之前或之后) 展示 Related Cards 横向滚动条，让用户从一张卡探索到相关卡片。

**Data source:** `LibraryCardDetailResponse.related_cards: RelatedCardResponse[]` — 后端已提供。

不使用 `RelationCardReasonResponse` 的 strength/reason 做「AI 推荐」叙事。仅展示关联关系作为「可浏览的相关卡片」。

**Design:**
- 横向滚动条 (`overflow-x-auto` + `flex gap-3`)
- 每条小卡片：title + source type chip + status dot
- 每条小卡片点击跳转到对应 detail → 更新 URL `?card=` param
- Section label: 「相关卡片」(zh) / 「Related Cards」(en)
- 小程序段下方显示关联原因 (如 "shared source: xxx", "same track: yyy") — 来自 `reasons[].label`
- **不显示 strength 数值** — 避免误解为 semantic/AI relevance score

**Related cards reasons 展示策略:**

`RelatedCardReasonResponse` 有 `reason`, `label`, `detail`, `strength` 字段。只展示 `label` 和 `detail`，不展示 `strength` 数字。这样用户看到的是「为什么关联」而不是「关联多强」。

**Fallback 策略:**
- `related_cards.length === 0`: 不渲染 Related Cards section（空白不可见）
- `related_cards` 缺失/loading: 不显示 placeholder/skeleton（避免闪烁）

**不在 Library grid 中显示 related cards** — 仅在 card detail read mode 中显示。

**中文学习型说明**: Related Cards 使用后端确定性关联数据（shared source, tag, wiki section, track），不是 AI semantic recommendation。不引入 RAG/embedding/vector similarity。

**Files:**
- Modify: `web/src/components/CardWorkspace.tsx`

### U4. Card Visual Polish

**Goal:** Card workspace 和 Library list view 中 status colors、source icon、provenance display、action footer 的信息呈现更清晰。不做大范围 design system，只在 card browsing 范围内调整。

**Scope:**
- Card grid 卡片层次：title (bold) > metadata line (muted) > tags (subtle)
- Source & History section：source 信息用 `source_path_view` 的 safe display path，保留 copy/open 操作
- Action footer：仅 draft mode 保留 save/move-to-trash，library mode 不需要 action footer（detail 本身已是最终态）
- Status badge/chip 复用现有 `friendlyStatus()`/`statusIcon()`/`statusTone()`
- Source type icon: 从现有 `sourceTypeLabels` 增加对应 lucide icon 映射（FileText/FileCode/FileType/Globe）

**Source type icon mapping (新增，lite):**

```
plain_markdown → FileText
txt → FileText
html → FileCode
pdf → FileType
docx → FileEdit
其他 → File
```

不新建 `SourceTypeIcon` 组件，在 CardWorkspace 内 inline 处理。

**Files:**
- Modify: `web/src/components/CardWorkspace.tsx`
- Modify: `web/src/pages/LibraryPage.tsx`

### U5. i18n / Product Copy / Contract Tests

**Goal:** 所有新增用户可见 copy 有 zh/en 双 key，product copy tests 更新覆盖新 layout 的展示规则。

**新增 i18n keys:**
| Key | zh | en |
|-----|----|----|
| `library.card_count` | {count} 张卡片 | {count} cards |
| `library.card_count_with_status` | {count} 张（{status}） | {count} ({status}) |
| `library.updated_at` | 更新于 {date} | Updated {date} |
| `library.related_cards` | 相关卡片 | Related Cards |
| `library.related_empty` | 暂无相关卡片 | No related cards |
| `library.summary_title` | 卡片概览 | Card Overview |
| `library.summary_collapse` | 收起概览 | Collapse Overview |
| `library.summary_expand` | 展开概览 | Expand Overview |
| `library.source_type_markdown` | Markdown | Markdown |
| `library.source_type_text` | 纯文本 | Text |
| `library.source_type_html` | HTML | HTML |
| `library.source_type_pdf` | PDF | PDF |
| `library.source_type_docx` | Word 文档 | Word |
| `library.related_reasons` | 关联原因 | Related via |
| `library.select_to_view` | 选择卡片查看详情 | Select a card to view details |

**Contract test updates:**
- `test_i18n_library_browsing_keys_complete`: 新增 keys 在 zh/en 字典中均有且非空
- `test_library_card_grid_uses_friendly_status`: card grid 不使用 raw status 字符串
- `test_related_cards_do_not_show_strength`: CardWorkspace 中不渲染 `strength` 数值字段
- `test_card_summary_is_frontend_only`: Summary Panel 代码不含 `fetch`/`llm`/`ai_summary`

**Files:**
- Modify: `web/src/lib/i18n.ts`
- Modify: `tests/test_web_product_copy.py`

---

## 5. File Scope

**允许修改:**
| File | Unit |
|------|------|
| `web/src/pages/LibraryPage.tsx` | U1 (Card Grid) |
| `web/src/components/CardWorkspace.tsx` | U2 (Summary Panel), U3 (Related Cards), U4 (Visual Polish) |
| `web/src/lib/i18n.ts` | U5 (i18n keys) |
| `web/src/lib/utils.ts` | U4 (source type icon helper, if needed) |
| `web/src/styles.css` | U1 (card grid CSS), U4 (minor visual tweaks) |
| `tests/test_web_product_copy.py` | U5 (contract tests) |

**绝对禁止修改:**
- Provider / approval / recall / BM25 后端语义
- `web/src/pages/SetupPage.tsx`
- `web/src/pages/SourcesPage.tsx`
- `web/src/pages/WikiPage.tsx`
- `web/src/components/ApprovalPanel.tsx`
- Backend `src/` 任何文件
- `web/src/api/` — 不新增 API 函数，仅使用现有的 `getLibraryCards()` / `getLibraryCardDetail()`

**如果 implementation 发现需要修改禁止列表中的文件 → 停止并 Ask User。**

---

## 6. Design Decisions

### 6.1 Card Grid Responsive Breakpoints

| Breakpoint | Columns | Rationale |
|-----------|---------|-----------|
| < 640px | 1 | 手机全宽，卡片单列 |
| 640-1024px | 2 | 平板两列，卡片仍可扫描 |
| 1024-1400px | 3 | 标准桌面三列 |
| > 1400px | 4 | 宽屏四列，充分利用空间 |

使用 CSS grid + Tailwind responsive: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4`

### 6.2 Cover Fallback Strategy

**不提取图片。** Current pipeline 不生成卡片缩略图，不新增图片提取/缩略图生成逻辑。

Fallback: 每张卡片顶部有 4px 彩色 accent bar，颜色基于 source type:
- `plain_markdown` → slate-400
- `txt` → gray-400
- `html` → orange-400
- `pdf` → red-400
- `docx` → blue-400
- 其他 → neutral-300

### 6.3 Summary Source Priority

1. `##`/`###` headings extracted from body → outline list
2. `card.tags` → tag chips
3. Body first 150 chars (Markdown stripped) → excerpt text
4. `card.track` + `card.strategy_label` → metadata pills

不写 Markdown parser — 使用简单 regex `/^## /gm` 和 `/^### /gm` 提取标题。

### 6.4 Related Cards Data Source and Fallback

**Data:** `LibraryCardDetailResponse.related_cards` — 后端已有，前端不需要新 API。
**Reasons display:** 仅展示 `reasons[].label` 和 `reasons[].detail`，不展示 `strength`。
**Fallback:** `related_cards.length === 0` → 不渲染 section（不显示空状态占位符）。

### 6.5 Card Density and Read Mode Scope

**本轮 scope:** 仅一个 card density（默认）。CardWorkspace body 区域保持 `max-w-[720px]`。
**Deferred:** compact/comfortable density toggle → future milestone。

### 6.6 Wiki Changes

**Not in scope.** Wiki TOC Scroll Spy / Print Export / Reader mode → deferred to future milestone。

### 6.7 Layout Transition

**当前 Layout:**
```
lg:grid-cols-[340px_1fr]  (card list sidebar 340px + detail pane)
```

**新 Layout (Desktop):**
```
Top: Card Grid full-width (replaces sidebar)
Bottom: Detail pane (selected card detail, visible when a card is clicked)
```

Detail pane 在选中卡片后显示在 grid 下方，不是替代 grid。

**交互流程:**
1. 用户进入 Library → 看到 Card Grid (全宽)
2. 用户点击某张卡片 → Grid 上方/下方出现 detail pane (类似 Wikipedia mobile "expand a section")
3. 用户可以关闭 detail pane 回到 grid，也可以点击另一张卡片切换 detail

**Desktop variant:** Grid 3-4 columns + selected card detail below grid。

### 6.8 Layout Selection Rationale

选择「Grid top, detail below」而非「Grid + side panel」的理由：
- Card Grid 从全宽受益最大，不应被 340px sidebar 压缩
- Detail below grid 是 Wikipedia mobile / Notion 的已验证模式
- 避免同时维护 grid + sidebar 两套列表数据
- 与现有 `selected` state 兼容 — 不需要新增路由或 panel toggle

---

## 7. Risk Register

| # | Risk | Mitigation |
|---|------|------------|
| 1 | Related Cards 被误解为 AI semantic recommendation | 不展示 strength 数值，只展示 deterministic reason label |
| 2 | 前端 Markdown heading 提取正则过脆（无法处理 edge case like `##` inside code block） | 宽松正则 `/^#{2,3} .+$/gm` + try/catch fallback 到 excerpt |
| 3 | Card Grid 信息过载（太多字段让卡片看起来像另一个数据列表） | 每张卡片最多 3 行 metadata: 1 status + 1 source + 1 date |
| 4 | Visual polish 扩散成 design system 重构 | Scope 限定 CardWorkspace + LibraryPage + styles.css |
| 5 | i18n key 散落 — 新 copy 又出现硬编码 | 所有新增文案先加 i18n key，再加 component code |
| 6 | Product copy tests 过脆（regex 断言 vs 代码结构强耦合） | Tests 仅检查 i18n key 存在性和特定字符串 absence，不检查 DOM 结构 |
| 7 | Browser smoke 只看首页导致 card detail 漏测 | Smoke checklist 明确覆盖 card grid → select card → summary panel → related cards |

---

## 8. Stop Conditions

以下任一条件满足时，**必须停止并 Ask User:**

1. 需要新增 related cards 后端 API（当前已有 `LibraryCardDetailResponse.related_cards`，不需要）
2. 需要 RAG / embedding / semantic search
3. 需要真实 LLM summary
4. 需要大型 Markdown parser (`unified`/`remark`)
5. 需要引入 graph / animation / UI framework
6. 需要改 approval / recall / provider 语义
7. P0/P1/P2 无法 2 次回退内关闭
8. Visual redesign 影响全站 layout（超出 LibraryPage + CardWorkspace）

---

## 9. Test Strategy

### 9.1 Gate Commands

```bash
npm --prefix web run build          # exit code = 0
python -m pytest tests/test_web_product_copy.py -q  # exit code = 0
git diff --check                     # exit code = 0
```

### 9.2 New Product Copy Tests

```python
def test_i18n_library_browsing_keys_complete() -> None:
    """U5: 新增 library card browsing i18n keys 必须完整。"""
    # 验证 ~16 个新 key 在 zh/en 中均存在且非空

def test_library_card_grid_uses_friendly_status() -> None:
    """U1: Card grid 不能展示 raw status 字符串。"""
    # 验证 LibraryPage 使用 statusIcon/statusTone/friendlyStatus

def test_related_cards_do_not_show_strength() -> None:
    """U3: Related Cards 不渲染 RelatedCardReasonResponse.strength 数值。"""
    # 验证 CardWorkspace 不含 ".strength" 渲染

def test_card_summary_is_frontend_only() -> None:
    """U2: Summary Panel 不调用 LLM 生成摘要。"""
    # 验证 CardWorkspace 不含 fetch/summary/llm/ai_summary 等字符串
```

### 9.3 Browser Smoke Checklist

- [ ] Library 页面打开 → Card Grid 可见
- [ ] 卡片可点击 → Detail view 展开
- [ ] Detail view 有 Summary Panel
- [ ] Summary Panel 有 headings outline 或 excerpt
- [ ] Related Cards section 可见或有合理空状态
- [ ] Related Cards 点击跳转到对应卡片
- [ ] Related Cards 不显示 strength 数值
- [ ] Empty state 显示（card 为空时）
- [ ] zh/en 切换后所有新文案正常
- [ ] Mobile/responsive 布局不崩溃
- [ ] Console 无 error
- [ ] Network 无 4xx/5xx
- [ ] 不调用真实 LLM（network 中无 `/api/*/chat` 或 `/api/wiki/rebuild`）
- [ ] 不读取 secrets

---

## 10. Execution Plan

1. **写本 spec** ← 当前步骤
2. **自审 spec** — 检查 scope、risk、stop conditions
3. **Spec 通过** → 进入 implementation
4. **Spec 不通过** → 回退修 spec (最多 2 次)
5. **Implementation**: U1 → U2 → U3 → U4 → U5 顺序
6. **Implementation notes**: 记录实际变更、设计决策、known issues
7. **Code self-review**: 检查 P0/P1/P2
8. **Gate**: build + test + diff-check
9. **Browser smoke**
10. **Commit + push main**

---

## 11. Future / Parallel (Deferred)

以下项目明确属于未来 milestone，本轮不实现：

| Item | Deferred to | Reason |
|------|-------------|--------|
| Wiki TOC Scroll Spy | Future | 需要 IntersectionObserver + Wiki page 改动 |
| Wiki Print / Export PDF | Future | 需要 `@media print` CSS + WikiHeader button |
| Wiki Reader Mode | Future | 需要 font size controller + wide mode toggle |
| Card density toggle | Future | 需要 compact card variant + user preference |
| Dark Mode | Future | 需要 CSS variable + 全站 token migration |
| Drafts Approval Queue | Future | 需要 DraftsPage 大重构 + ApprovalPanel redesign |
| Full Knowledge Graph | Future | 需要 graph layout + visualization strategy |
| Card Cover Image extraction | Future | 需要 backend image extraction pipeline |
