# SDD: Wiki Web Presentation Addendum — Personal Knowledge Base UX

> **Status**: Draft — Accepted for v0.2 implementation
> **Date**: 2026-05-15
> **Depends on**: [RFC_0002_WIKI_PRESENTATION_V2.md](../rfc/RFC_0002_WIKI_PRESENTATION_V2.md), [SDD_WIKI_PRESENTATION_V2.md](SDD_WIKI_PRESENTATION_V2.md)
> **Related**: [V0_2_ROADMAP.md](../roadmap/V0_2_ROADMAP.md)

---

## 1. Status

本文档是 RFC_0002 / SDD_WIKI_PRESENTATION_V2 的 **Web UX 补充文档**。

目标：指导 Wiki Web 展示从 "功能可用" 升级为 "个人知识库阅读体验"。

不改变知识状态机、ViewModel contract、synthesis 逻辑、approval 边界。

---

## 2. Context

### 2.1 当前状态

v0.2 Wiki Presentation 已完成一轮实现：

- `WikiPageViewModel` + `WikiSectionView` + `WikiReferenceView`（frozen dataclasses）
- `WikiRenderer` ABC + `WikiGraphRenderer`（NotImplementedError extension point）
- API endpoints: `GET /api/wiki/page`, `/sections`, `/references`
- Web components: `WikiTOC`, `WikiSection`, `WikiReferencePanel`, `WikiEmptyState`, `WikiErrorState`, `WikiLoadingState`
- Frontend rendering: `marked` → Markdown to HTML → `DOMPurify` → safe HTML → DOM
- 139 backend tests passing, TypeScript build passing, ruff clean

### 2.2 UX 现状评分（来自 Gap Audit）

| 维度 | 分 | 现状 |
|------|----|------|
| Reading area | 5/10 | 有基础 prose typography，缺 max-width / line-height 调优 |
| Navigation | 6/10 | TOC 存在但仅 sticky nav，缺 scroll-spy / prev-next |
| References/provenance | 7/10 | 有 provenance 数据但默认折叠，用户不易发现 |
| Long-form reading | 4/10 | 缺 read time / back-to-top / scroll-spy |
| Typography | 4/10 | Tailwind prose defaults，非 knowledge-base 定制 |
| Responsive | 3/10 | TOC 固定宽度，mobile 无 collapse 处理 |
| Visual quality | 4/10 | 功能可用但像 developer tool |

**总评：5/10 — 功能正确，体验不足。**

### 2.3 目标

MindForge Wiki 应该像 **个人知识库阅读界面**，不是调试页面。

v0.2 不追求：
- 复杂 graph view
- Full editable Wiki
- Rich text editor
- CMS-style page builder

v0.2 先把 **阅读展示** 做好。

---

## 3. Product Intent

### 3.1 产品意图

MindForge Wiki 是用户知识库的 **结构化阅读界面**——不是 Markdown dump，不是 developer debug panel。

产品意图：
- 让用户阅读 **human_approved 知识的综合结构**
- 让用户快速理解主题（overview → sections 层级）
- 让用户信任内容来源（provenance / references 可见）
- 让用户知道每段内容可追溯到哪些 approved cards / sources
- 让长文阅读舒适（typography / spacing / rhythm）
- 为未来 graph view / editable override 留边界——但不现在实现

### 3.2 设计原则

1. **Local-first personal knowledge base**：界面应传达 "这是你的知识库"，不是 "这是 LLM 输出"
2. **Reading-first, not editing-first**：v0.2 专注于阅读体验，编辑能力留到后续 RFC
3. **Provenance visible, not hidden**：用户应看到每段知识从哪里来
4. **Clean, not complex**：不引入拖拽、卡片排序、fancy animation——保持阅读界面克制
5. **Responsive enough**：desktop 三栏 → tablet 两栏 → mobile 单栏，但不需要 pixel-perfect

---

## 4. Non-goals（v0.2 Web 展示边界）

以下明确不在 v0.2 范围：

- ❌ 不实现 graph database
- ❌ 不实现 graph visualization
- ❌ 不实现 editable Wiki persistence（saving / override storage）
- ❌ 不修改 approved cards
- ❌ 不修改 source documents
- ❌ 不自动 approve
- ❌ 不让 ai_draft / pending / rejected 进入 final Wiki view
- ❌ 不做 RAG / embedding
- ❌ 不做 Obsidian plugin
- ❌ 不在后端做默认 HTML 渲染
- ❌ 不引入重型 CMS / rich text editor（TipTap / Slate / Quill / Lexical）
- ❌ 不改 card schema
- ❌ 不改 approval / library / recall 语义
- ❌ 不把 Wiki rendering、Wiki editing、approval、source adapter、library/recall 混成一个巨石模块

---

## 5. Layout Specification

### 5.1 Desktop Layout（>= 1024px）

```
┌──────────────────────────────────────────────────────────────────────┐
│  Wiki Header（title / status / last rebuilt / rebuild action）      │
├────────────┬─────────────────────────────────┬───────────────────────┤
│  TOC       │  Reading Column                 │  References Panel     │
│  (sticky)  │                                 │                       │
│            │  ┌─────────────────────────┐    │  Section refs chips   │
│  Section 1 │  │ Overview                │    │                       │
│  Section 2 │  │ (Markdown → safe HTML)  │    │  ┌─────────────────┐  │
│  Section 3 │  └─────────────────────────┘    │  │ card title      │  │
│            │                                 │  │ source type     │  │
│            │  ┌─────────────────────────┐    │  │ tags / score    │  │
│            │  │ Section 1               │    │  └─────────────────┘  │
│            │  │ ### Heading             │    │                       │
│            │  │ Body text...            │    │  Additional approved  │
│            │  │ [Related cards: 3]      │    │  cards (uncited)      │
│            │  └─────────────────────────┘    │                       │
│            │                                 │                       │
│            │  ┌─────────────────────────┐    │                       │
│            │  │ Section 2 ...           │    │                       │
│            │  └─────────────────────────┘    │                       │
│            │                                 │                       │
│            │  Open Questions                │                       │
│            │  Additional Cards              │                       │
│            │  Warnings (if any)             │                       │
│            │                                 │                       │
│            │  [Advanced: fallback rebuild]   │                       │
├────────────┴─────────────────────────────────┴───────────────────────┤
│  Footer（optional）                                                  │
└──────────────────────────────────────────────────────────────────────┘
```

**布局规则**：
- 阅读列 max-width: ~720px（适合长文阅读）
- TOC sticky，宽 ~200px
- References panel 宽 ~240px，sticky
- 阅读列居中在三栏中的主区域
- Advanced fallback 在页面底部折叠区域，不混入主阅读流

### 5.2 Tablet Layout（640px - 1023px）

```
┌──────────────────────────────────────────┐
│  Wiki Header                             │
├────────────┬─────────────────────────────┤
│  TOC       │  Reading Column             │
│  (可折叠)  │                             │
│            │  Overview + Sections        │
│  [展开/收起]│                             │
│            │  References at bottom        │
├────────────┴─────────────────────────────┤
│  References Panel（下移到 sections 下方） │
│  Advanced fallback                       │
└──────────────────────────────────────────┘
```

**规则**：
- TOC 可折叠（hamburger / toggle button）
- References panel 移到阅读列下方
- 阅读列 keep max-width

### 5.3 Mobile Layout（< 640px）

```
┌──────────────────────────┐
│  Wiki Header             │
│  [TOC toggle button]     │
├──────────────────────────┤
│  Reading Column          │
│  (full width)            │
│                          │
│  Overview + Sections     │
│  References inline       │
│  Advanced fallback       │
└──────────────────────────┘
```

**规则**：
- Single column，全宽
- TOC 以 overlay / drawer 方式展示，不占固定空间
- References 在 section 内或底部 inline 展示
- No fixed-width sidebar
- 保持可读间距（minimum horizontal padding）

---

## 6. Reading Experience

### 6.1 页面结构

页面从上到下：
1. **Page header**：title "MindForge Main Wiki" + metadata（mode, rebuilt time, card count）+ Rebuild 按钮
2. **Overview**：Wiki summary text，在 sections 前
3. **Sections**：按序排列，每 section 有 heading + body + related references
4. **Open Questions**：如有，列表展示
5. **Additional Cards**：未被任何 section 引用的 approved cards
6. **Warnings**：如有 synthesis warnings，可折叠展示
7. **Advanced**：Troubleshooting fallback，折叠区域

### 6.2 Typography

- 阅读列 **max-width: 720px**
- Body text **line-height: 1.75**（中文阅读舒适）
- Section headings 清晰层级：**h2 → h3 → h4**
- Paragraph spacing: **margin-bottom: 1em**
- 代码块：等宽字体，浅色背景，圆角
- 引用块：左边框，浅色背景，斜体可选
- 列表：适当缩进，list-style-position: outside
- 表格：border-collapse，striped rows 可选

### 6.3 可选增强（v0.2 不做但留接口）

- Estimated read time
- Back-to-top floating button
- Scroll-spy TOC active section highlighting
- Section prev/next navigation
- Print-friendly styles

这些不阻塞 v0.2 polish，但代码结构应允许后续添加。

---

## 7. Provenance / Trust Design

### 7.1 核心原则

**用户应能看到每段知识从哪里来。**

Provenance 不应被藏起来——它是 MindForge Wiki 与普通 LLM 输出关键区别：每段内容可追溯到 approved cards。

### 7.2 References 展示要求

每个 section 的 references：
- **默认可见性**：section-level references 应默认可见（不折叠到 details 里面），至少展示关联的 card 数量和标题
- **Reference card/chip** 展示：
  - card title（主要识别信息）
  - source type icon（pdf/markdown/html/docx/txt）
  - approved status indicator
  - tags（最多展示 3 个）
  - value score（如有，小星星图标）
- **不可折叠到底**：Reference 信息应有最小可见摘要，详细部分可折叠
- **"Related approved cards"** 文案 → "Knowledge sources" 或 "From your knowledge cards"，更接近产品意图

### 7.3 全局 References

页面底部的 Additional approved cards 列表：
- 默认可见，非折叠
- 展示 card title + source type + approved date

---

## 8. Product Wording Rules

### 8.1 禁止词汇（用户界面主路径）

以下开发术语 **禁止** 出现在普通用户可见的主路径 UI 中：

| 禁用 | 原因 | 替换 |
|------|------|------|
| "no model" | 开发者术语 | 不出现在按钮/标签中 |
| "fake" | 暗示虚假数据 | 不出现在 UI |
| "demo" | 暗示非真实 | 不出现在 UI |
| "deterministic" | 非用户概念 | "Safe template fallback" |
| "raw JSON" | 调试概念 | 不出现在 UI |
| "debug" | 调试概念 | 不出现在 UI |
| "Template rebuild" | 开发者概念 | "Safe fallback rebuild" |

### 8.2 替代表达

| 场景 | 推荐表达 |
|------|---------|
| LLM synthesis rebuild | "Rebuild Wiki" / "Generate Wiki" / "Refresh Wiki" |
| Fallback method | "Safe fallback" / "Troubleshooting fallback" |
| Fallback description | "Uses a template-based method that does not require a model. Suitable for troubleshooting." |
| Advanced section | "Advanced" / "Troubleshooting" |

### 8.3 Fallback 位置规则

- Fallback 只能出现在 **Advanced / Troubleshooting** 折叠区域
- 主 Rebuild 按钮 **必须是 LLM-first**
- 不要把 "no model" / "template" / "deterministic" 写成普通用户能力
- CLI 中 `--mode deterministic` flag 保持 `hidden=True`（已实现）

---

## 9. Renderer / Plugin Decision

### 9.1 当前选择

| 组件 | 库 | 角色 |
|------|----|------|
| Markdown → HTML | `marked` | 将 canonical Markdown text 转换为 HTML |
| HTML sanitization | `dompurify` | 唯一 sanitization 点，strip XSS payload |
| 数据源 | Backend `WikiPageViewModel` JSON | 提供 structured data + canonical Markdown text |

**Sanitization 链**：
```
Backend: canonical Markdown text (no HTML)
   ↓ GET /api/wiki/page
Frontend: marked → HTML → DOMPurify → safe HTML → dangerouslySetInnerHTML
```

### 9.2 为什么 v0.2 不用 react-markdown / remark / rehype

- `marked` 足够：LLM synthesis 输出 canonical Markdown（headings, lists, bold, italic, code, links, tables），不需要 AST-level transforms
- `react-markdown` 适合需要自定义组件渲染的场景（如自定义 code block with copy button），v0.2 不需要
- `remark` / `rehype` 插件生态适合高级 Markdown transforms（如 custom syntax、auto-link headers），v0.2 不需要
- 引入更多依赖增加 bundle size 和维护成本，对当前需求没有收益

### 9.3 升级条件（future）

以下条件满足任一个时，应考虑升级：
- 需要 **component-level rendering**（如在 Markdown 中嵌入 React 组件）
- 需要 **AST transforms**（自定义 Markdown 语法）
- 需要 **plugin ecosystem**（如 math rendering、diagram support）
- 需要 **MDX** 支持（Markdown + JSX）

### 9.4 不做的事

- ❌ 不在后端做 Markdown → HTML 渲染（双重 sanitization 责任不清）
- ❌ 不使用 unsafe raw HTML embedding
- ❌ 不为 Mermaid/diagram 渲染做 v0.2 实现（留接口在 RFC 中即可）

---

## 10. Rendering Safety

### 10.1 当前安全状态

| 检查项 | 状态 | 详情 |
|--------|------|------|
| DOMPurify config | ✅ | ALLOWED_TAGS / FORBID_TAGS / FORBID_ATTR / ALLOWED_URI_REGEXP |
| dangerouslySetInnerHTML | ✅ | 仅 2 处，均经 DOMPurify |
| script tag rejection | ✅ | FORBID_TAGS 包含 script |
| event handler rejection | ✅ | FORBID_ATTR 包含 onclick/onerror/onload/onmouseover |
| javascript: protocol | ✅ | ALLOWED_URI_REGEXP 限制 http/https/mailto/ftp |
| inline style rejection | ✅ | FORBID_ATTR 包含 style |
| backend HTML rendering | ✅ | 后端只输出 canonical Markdown text |
| graph view implementation | ✅ | NotImplementedError |

### 10.2 CSP Header（推荐加固）

`Content-Security-Policy: default-src 'self'; script-src 'none'; style-src 'self' 'unsafe-inline'`

- 这是 **推荐加固**，不阻塞 v0.2 polish
- 如果前端已有 CSP middleware 或可快速添加，建议在 polish 期间一起做
- 不做 CSP 不算安全缺陷——DOMPurify 已经是客户端侧的充分防护

### 10.3 安全测试（已有）

- `test_wiki_sanitization.py` — script/iframe 禁止
- `test_wiki_xss_prevention.py` — XSS payload + sanitization 契约
- `test_wiki_secret_exposure.py` — API key / token / secret pattern

---

## 11. Editable Wiki Boundary

### 11.1 v0.2 决策：不实现

v0.2 **不实现** editable Wiki persistence。

原因：
- Wiki editing 语义尚未定义（override? annotation? edit draft?）
- 需要明确与 ai_draft / human_approved 的边界
- 需要定义 storage format
- 如果现在强加实现，未来必然重构
- 需要用 **独立 RFC** 来定义编辑模型

### 11.2 未来推荐模型

当后续版本实现 editable Wiki 时，推荐设计为：

**WikiManualOverride / UserAnnotation layer**：
- 修改对象：Wiki section body / overview（LLM synthesis 的产物）
- 不修改 approved card（card 仍是 source of truth）
- 不修改 source document（完全不碰）
- 不污染 ai_draft / human_approved 状态机
- 保存动作代表用户显式确认该 override（不是自动 approve）
- 需要 `version` / `updated_at` / `clear override` 能力
- 可以 clear override 回到 synthesized wiki
- 编辑存储为独立层（如 `.mindforge/wiki_overrides.json`），不写入 wiki Markdown 文件

**编辑边界**：
```
User edits Wiki section body (overview / section text)
        ↓
WikiManualOverride stored (separate layer)
        ↓
WikiPageViewModel reads: synthesis + override overlay
        ↓
Frontend renders merged output
        ↓
User can "Clear override" → back to pure synthesis
```

**不编辑的对象**：
- Approved card body ❌
- Source document ❌
- Card schema ❌
- LLM synthesis JSON ❌（override 独立存储，不修改原始 synthesis 输出）

### 11.3 v0.2 可以做的预留

- UI 可以预留 edit action placeholder（如 section 旁的 "Edit" icon button，disabled/not-implemented tooltip）
- 文案可以是 "Edit support planned for future version"
- 不实现保存
- 不实现 override storage
- 不改变后端 ViewModel

---

## 12. Component Hierarchy

### 12.1 推荐组件树

```
WikiPage（页面级状态管理 + fetch + rebuild）
├── WikiHeader（title + metadata + rebuild action）
├── WikiToc（section list with anchors, scroll-spy optional）
├── WikiReadingPane（main reading area）
│   ├── WikiOverview（overview Markdown → safe HTML）
│   ├── WikiSection[]（heading + body + references）
│   │   └── WikiReferenceChip[]（inline reference indicators）
│   ├── WikiOpenQuestions（列表）
│   ├── WikiAdditionalCards（uncited approved cards）
│   │   └── WikiReferenceCard[]（card metadata）
│   └── WikiWarnings（collapsible if non-empty）
└── WikiAdvancedActions（collapsible: troubleshooting fallback）
```

### 12.2 组件职责边界

- **WikiPage**：只负责 fetch/rebuild + state orchestration，不包含 Markdown rendering
- **WikiSection**：只负责 single section 的 Markdown rendering，不 fetch data
- **WikiToc**：只负责 anchor links，不渲染内容
- **WikiReferencePanel / WikiReferenceChip**：只负责 provenance 展示，不做 Markdown
- **WikiRenderer**（lib/wiki-renderer.ts）：纯函数，不做 state management
- **WikiStateView**：empty / loading / error 由各自组件负责，不塞进 WikiPage

### 12.3 不推荐的反模式

- ❌ 把所有 Wiki UI 塞进一个 `WikiPage.tsx`
- ❌ 让 renderer 负责 fetch
- ❌ 让 reference panel 负责 Markdown rendering
- ❌ 让 advanced fallback actions 混入主阅读流
- ❌ 让 component 直接 import wiki_service（前端应通过 API 获取数据）

---

## 13. Acceptance Criteria

### 13.1 UX Acceptance

- [ ] Web Wiki 看起来像 personal knowledge base 阅读界面，不是 developer tool
- [ ] Desktop 有清晰 TOC / reading / references 布局
- [ ] Tablet 布局不崩（TOC 可折叠，references 下移）
- [ ] Mobile 单栏不崩（全宽阅读，TOC overlay）
- [ ] References/provenance 默认可见或有最小可见摘要（不再完全折叠到 details）
- [ ] Advanced fallback 不污染主阅读流
- [ ] "Template rebuild (no model)" 文案从普通 UI 消失
- [ ] 阅读列 max-width 适合长文阅读（~720px）
- [ ] Typography 舒适（line-height / paragraph spacing）

### 13.2 Safety Acceptance

- [ ] DOMPurify sanitizer 保持唯一 sanitization 点
- [ ] `dangerouslySetInnerHTML` 仅用于 DOMPurify 处理后的 HTML
- [ ] 后端不渲染 HTML
- [ ] ai_draft / pending / rejected 不进入 final Wiki view
- [ ] Graph view implementation 保持 NotImplementedError
- [ ] No secret / API key / token in rendered output

### 13.3 Build/Test Acceptance

- [ ] `cd web && npx tsc --noEmit` passes
- [ ] `cd web && npx vite build` passes
- [ ] `python -m pytest tests/wiki/ -q` passes（139 tests）
- [ ] `python -m ruff check src tests` passes
- [ ] No new dependency without rationale

### 13.4 Documentation Acceptance

- [ ] RFC_0002 §4 Non-goals 记录 editable Wiki 不在 v0.2 范围
- [ ] V0_2_ROADMAP 记录 Wiki Web UX polish milestone
- [ ] 本文档准确描述 v0.2 Web 展示设计

---

## 14. Implementation Plan

大步实现，分 commit。每步在对应文档 section 指导下完成。

| Phase | 内容 | 文件 | 依赖 |
|-------|------|------|------|
| P1 | Product wording cleanup | WikiPage.tsx, wiki_cli.py | §8 |
| P2 | Layout polish（desktop 三栏） | WikiPage.tsx, WikiTOC.tsx, new layout wrapper | §5.1 |
| P3 | Responsive（tablet + mobile） | All wiki components | §5.2, §5.3 |
| P4 | Typography / reading experience | WikiSection.tsx, index.css | §6 |
| P5 | Provenance UX（可见化） | WikiReferencePanel.tsx, new WikiReferenceChip | §7 |
| P6 | Empty/loading/error polish | WikiEmptyState, WikiErrorState, WikiLoadingState | §3, §8 |
| P7 | Final tests/build/self-audit | tests/wiki/, ruff, tsc, vite | §13 |

---

## 15. References

- [RFC_0002_WIKI_PRESENTATION_V2.md](../rfc/RFC_0002_WIKI_PRESENTATION_V2.md) — Wiki ViewModel + rendering boundary
- [SDD_WIKI_PRESENTATION_V2.md](SDD_WIKI_PRESENTATION_V2.md) — Wiki structure + safety + tests
- [V0_2_ROADMAP.md](../roadmap/V0_2_ROADMAP.md) — v0.2 feature roadmap
- [V0_2_DEVELOPMENT_RULES.md](../V0_2_DEVELOPMENT_RULES.md) — development rules + hard boundaries
