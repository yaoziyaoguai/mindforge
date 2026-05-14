# RFC 0002: Wiki Presentation v2 — Structured Rendering + Safety

> **Status**: Draft
> **Date**: 2026-05-14
> **Author**: MindForge Team
> **Related**: [V0_2_ROADMAP.md](../roadmap/V0_2_ROADMAP.md), [SDD_WIKI_PRESENTATION_V2.md](../sdd/SDD_WIKI_PRESENTATION_V2.md)

---

## Abstract

在现有 LLM-first Wiki synthesis 基础上增强展示层：从当前 Plain Markdown file dump 升级为结构化 Wiki 视图模型，支持 section 导航、card/source provenance 引用面板、安全渲染和空/错/加载状态。同时为未来的 graph view / 多视图展示预留接口。

---

## 1. Context

### 1.1 Current State (v0.1)

v0.1 Wiki 能力：

- **Wiki Service** (`src/mindforge/wiki_service.py`)：
  - `rebuild_main_wiki()`：deterministic template（不调 LLM）
  - `llm_rebuild_wiki()`：LLM synthesis（调用 configured model）
  - 输出：`30-Wiki/Main-Wiki.md`，纯 Markdown 文件
- **Wiki CLI** (`src/mindforge/wiki_cli.py`)：`wiki status/rebuild/show`
- **Web Wiki Router** (`src/mindforge_web/routers/wiki.py`)：Rebuild Wiki API
- **Web Wiki Page**：显示 Markdown 内容 + Rebuild 按钮 + Advanced deterministic fallback

当前 Wiki 展示方式：
- 后端返回 Markdown raw text
- 前端（如已实现）做基础 Markdown 渲染
- 无结构化 section 导航
- 无 card/source provenance 引用面板
- Empty/error/loading states 基础

### 1.2 Known Pain Points

1. **展示粗糙**：Wiki 内容以单个 Markdown blob 展示，用户难以浏览
2. **缺少结构化 section**：LLM 生成的 sections 在 Markdown 中，但没有结构化数据来支撑导航
3. **缺少 TOC / navigation**：没有侧边栏目录或 section 间跳转
4. **缺少 card/source reference 展示**：每个 section 关联的 approved card 和 source 以注释形式存在，用户不可见
5. **empty/error/loading states 不够好**：无 approved cards 或 LLM 调用失败时，用户体验差

---

## 2. Problem

v0.1 Wiki 的展示层停留在"文件 dump"阶段。Wiki synthesis 本身已经通过 LLM 生成了 structured JSON（overview + sections + card_ids），但渲染层没有利用这个结构。用户看到的是 Markdown 文件，而不是一个可浏览的知识页面。

---

## 3. Goals

1. **结构化 Wiki 视图模型**：从 LLM synthesis JSON 构建 `WikiPageViewModel`，不丢 section/card 结构
2. **Table of Contents**：根据 section 层级自动生成侧边栏/顶部 TOC
3. **Section 导航**：TOC 条目可跳转到对应 section，section 间可前后导航
4. **Provenance/References 面板**：每个 section 展示关联的 approved card 和原始 source
5. **安全 Markdown 渲染**：sanitized rendering，XSS 防护
6. **Empty/Error/Loading states**：覆盖所有非正常状态
7. **未来 graph view 接口**：renderer registry，text/markdown view 现在实现，graph view 留注册点

---

## 4. Non-goals

- **不改 knowledge card schema**
- **不改 ai_draft / human_approved 状态机**
- **不改 approval semantics**
- **Wiki 只能基于 human_approved**：这个规则不变，渲染层只读不写
- **不实现 graph database**
- **不实现 graph visualization**
- **不实现 Mermaid/diagram rendering**（留接口但在 RFC/SDD 中标记为 future）
- **不新增 Wiki 的持久化格式**：Wiki 仍然是 derived view，approved cards 是 source of truth
- **不改变 Wiki rebuild 的触发方式**：仍然是用户手动触发（Web button / CLI command）

---

## 5. Proposed Design

### 5.1 Wiki View Model

```python
@dataclass(frozen=True)
class WikiPageViewModel:
    """Wiki 页面的结构化视图模型，从 LLM synthesis JSON 构建。"""
    title: str                              # "MindForge Main Wiki"
    mode: str                               # "llm" | "deterministic"
    model_id: str | None                    # LLM model used (llm mode only)
    last_rebuilt_at: str | None
    overview: str                           # Wiki overview text (Markdown)
    sections: list[WikiSectionView]         # Ordered sections
    open_questions: list[WikiQuestionView]  # Open questions (if any)
    included_card_count: int
    additional_card_count: int              # uncited cards in appendix
    warnings: list[str]                     # synthesis warnings (e.g. unknown card_id)

@dataclass(frozen=True)
class WikiSectionView:
    """单个 Wiki section 的视图。"""
    id: str                                 # stable section id (generated)
    title: str                              # section heading
    body: str                               # section body (Markdown)
    level: int                              # heading level (1-6)
    card_refs: list[WikiReferenceView]      # referenced approved cards
    anchor: str                             # anchor for TOC navigation (e.g. "#section-title")

@dataclass(frozen=True)
class WikiReferenceView:
    """单个 card/source 引用的视图。"""
    card_id: str
    card_title: str
    source_title: str | None
    source_type: str | None                 # "markdown" / "pdf" / "docx" / "txt" / "html"
    source_path: str | None
    track: str | None
    tags: list[str]
    value_score: int | None
    approved_at: str | None
    card_rel_path: str                      # relative path to card file

@dataclass(frozen=True)
class WikiQuestionView:
    """Open question 的视图。"""
    question: str

@dataclass
class WikiRenderOptions:
    """渲染选项（用户可配置但不影响 Wiki 数据）。"""
    show_provenance_panel: bool = True      # 展示 provenance/引用面板
    show_toc: bool = True                   # 展示目录
    toc_position: str = "sidebar"           # "sidebar" | "top" | "none"
    sanitize_html: bool = True              # 启用 HTML sanitization
    enable_mermaid: bool = False            # future: Mermaid diagram rendering
    enable_code_highlight: bool = True      # 代码块语法高亮
```

### 5.2 Rendering Boundary

```
┌─────────────────────────────────────────────────────┐
│                  Wiki Page (Web UI)                  │
├─────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌────────────────────────────────┐   │
│  │   TOC    │  │          Main Content          │   │
│  │ (sidebar)│  │                                │   │
│  │          │  │  ┌──────────────────────────┐  │   │
│  │ Section1 │  │  │ Overview                 │  │   │
│  │ Section2 │  │  └──────────────────────────┘  │   │
│  │ Section3 │  │  ┌──────────────────────────┐  │   │
│  │ ...      │  │  │ Section: ...             │  │   │
│  │          │  │  │ Body (rendered Markdown)  │  │   │
│  │          │  │  │ ┌────────────────────┐    │  │   │
│  │          │  │  │ │ References Panel   │    │  │   │
│  │          │  │  │ │ - Card title       │    │  │   │
│  │          │  │  │ │ - Source: xxx.pdf  │    │  │   │
│  │          │  │  │ └────────────────────┘    │  │   │
│  │          │  │  └──────────────────────────┘  │   │
│  └──────────┘  └────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**渲染管线（v0.2 唯一默认路径）**：

```
LLM Synthesis JSON
    │
    ▼
WikiPageViewModel  (build from JSON + CardDigest index)
    │
    ▼
API: GET /api/wiki/page → WikiPageViewModel (JSON)
    │  section.body_markdown = canonical Markdown text (not HTML)
    │  section.card_refs = [{card_id, source_type, ...}]
    │
    ▼
Frontend: Markdown library → HTML → DOMPurify → safe HTML → DOM
    │  no unsafe innerHTML
    │  CSP: default-src 'self'; script-src 'none'
    │
    ├── WikiMarkdownRenderer (frontend, v0.2 active path)
    │
    └── WikiGraphRenderer     (future extension point, v0.2 raises NotImplementedError)
```

### 5.3 Rendering Boundary（默认唯一路径）

**v0.2 默认路径**：API 返回结构化 JSON，前端负责 Markdown → safe HTML 渲染。后端不生成最终 HTML。

```
API: GET /api/wiki/page → WikiPageViewModel (JSON)
    │
    │  section.body_markdown = "# Section Title\n\nSection content..."
    │  section.card_refs = [{card_id, card_title, source_type, ...}]
    │
    ▼
Frontend: WikiPage.tsx
    │
    ├── 1. Markdown → HTML（前端 markdown library）
    │
    ├── 2. HTML Sanitizer（DOMPurify，前端唯一 sanitization 点）
    │
    ├── 3. Render sanitized HTML into DOM（React dangerouslySetInnerHTML + DOMPurify）
    │
    └── CSP: default-src 'self'; script-src 'none'
```

**为什么是前端渲染**：
- 避免双重 sanitizer 责任不清（Python bleach + 前端 DOMPurify 同时存在）
- Markdown 渲染本是前端展示关注点，由前端统一控制
- 后端只负责 structured data + provenance metadata

**CLI 路径**：`mindforge wiki show` 输出纯文本/原始 Markdown，不做 HTML 渲染。

### 5.4 Renderer Abstraction（for future extension）

```python
class WikiRenderer(ABC):
    """Wiki 渲染器的抽象基类。为未来多视图扩展留接口。"""
    name: str

class WikiMarkdownRenderer(WikiRenderer):
    """当前实现标记。v0.2 的 Markdown 渲染在前端完成。"""
    name = "markdown"

class WikiGraphRenderer(WikiRenderer):
    """未来：Graph visualization。v0.2 只定义接口，不实现。"""
    name = "graph"
    # v0.2: raise NotImplementedError("Graph renderer is not implemented in v0.2")
```

### 5.5 Rendering Safety

**Sanitization 规则**（前端 DOMPurify）：

```
User Input (Wiki section body Markdown)
    │
    ▼
Markdown → HTML（前端 library，如 marked/react-markdown）
    │
    ▼
DOMPurify.sanitize(html, config)
    │
    ├── ALLOW: h1-h6, p, ul, ol, li, a, strong, em, code, pre, blockquote, table, thead, tbody, tr, th, td
    ├── STRIP: script, iframe, object, embed, form, input, button, style
    ├── STRIP ATTRS: onclick, onerror, onload, onmouseover, style (inline)
    ├── ALLOW <a> href: http/https/mailto only
    └── ALLOW <img>: src (data: only if explicitly enabled), alt
    │
    ▼
Safe HTML → DOM
```

**硬性规则**：
- 不直接 `innerHTML` 未净化内容——所有 HTML 必须先经过 DOMPurify
- 默认禁用 unsafe embedded HTML
- CSP header: `Content-Security-Policy: default-src 'self'; script-src 'none'; style-src 'self' 'unsafe-inline'`
- 如果未来支持 Mermaid：render 在 sandboxed iframe 中，strict CSP
- 后端 API 返回的 JSON 中不包含预渲染的 HTML 字符串——只包含 canonical Markdown text

### 5.5 Provenance / References

每个 Wiki section 的 "References" 面板展示：

```markdown
## Related Approved Cards

- [Card Title](link-to-card) — approved 2026-05-10
  - Source: research-paper.pdf (pdf)
  - Track: science / Value: 8

- [Another Card](link-to-card) — approved 2026-05-12
  - Source: meeting-notes.html (html)
  - Track: work / Value: 6
```

Reference panel 数据来源：
- `WikiPageViewModel.sections[].card_refs[]` 包含所有关联 card 信息
- 信息来自 `CardDigest`（title, track, tags, value_score, approved_at, source_title, source_path）
- Source type 需要从 card 的 source metadata 中获取（如果 card 记录了 source_type）

### 5.6 Empty / Loading / Error States

| 状态 | 触发条件 | 展示 |
|------|---------|------|
| **Empty: No approved cards** | `approved_card_count == 0` | "还没有已审批的知识卡片。请先 Import source → Review → Approve"，指向 Review 页面 |
| **Empty: Wiki not built** | `!wiki_path.exists()` | "Wiki 尚未生成。点击 Rebuild Wiki 基于已审批卡片生成。" |
| **Loading: Synthesis in progress** | `rebuild` API 返回后等待 | Progress indicator / spinner + "正在通过 LLM 合成 Wiki..." |
| **Error: LLM failed** | LLM call timeout / error | "Wiki 合成失败：{error_message}。旧 Wiki 保持不变。你可以重试或使用 Deterministic Rebuild。" |
| **Error: JSON parse failed** | LLM 返回非 JSON | "LLM 返回了无效格式。旧 Wiki 保持不变。你可以重试。" |
| **Error: No model configured** | `wiki.mode=llm` 但无 model | "需要配置 Wiki model。请先在 Setup 中添加模型。" |

### 5.7 Future Graph View Extension Point

```python
# v0.2: 只定义接口，不实现
class WikiGraphData:
    """Graph view 的数据模型（future）。"""
    nodes: list[GraphNode]    # cards / topics / sources
    edges: list[GraphEdge]    # relations

class WikiGraphRenderer(WikiRenderer):
    """Graph visualization renderer（future）。"""
    name = "graph"
    
    def render(self, view_model, options):
        raise NotImplementedError(
            "Graph renderer is not implemented in v0.2. "
            "This interface is reserved for future graph view support."
        )
```

接口要求：
- `WikiRenderer` registry 允许注册多个 renderer
- Web Wiki page 可以通过 `?view=graph` (future) 切换 renderer
- Graph renderer 不依赖图数据库（数据从 `WikiPageViewModel` 的 card_refs 构建）

---

## 6. CLI UX

```
$ mindforge wiki status
Wiki Status:
  Wiki file: vault/30-Wiki/Main-Wiki.md
  State: Built (LLM)
  Model: main
  Sections: 5
  Cards included: 12
  Last rebuilt: 2026-05-14T10:30:00+0800

$ mindforge wiki show
  [显示 Wiki 摘要 + section 列表 + TOC]
  （不做 Markdown 渲染，但提供结构化 section 概览）

$ mindforge wiki show --section 2
  [显示指定 section 内容]

$ mindforge wiki rebuild
Rebuilding Wiki via LLM synthesis...
  Model: main
  Cards collected: 12
  LLM response: received
  Sections generated: 5
  Warnings: none
  Wiki saved: vault/30-Wiki/Main-Wiki.md
  ✓ Done
```

---

## 7. Web UX

### 7.1 Wiki Page Layout

- **Top bar**: Wiki title, mode badge (LLM / Deterministic), last rebuilt time, Rebuild button
- **Left sidebar (optional)**: TOC with section links, active section highlight
- **Main area**: Overview → Sections (每个 section 一个 card/section block) → References → Open Questions
- **Right panel (optional)**: 选中 section 的 card references detail

### 7.2 Section Card Design

每个 section 渲染为可折叠/展开的 card：
- **Header**: section title + related card count badge
- **Body**: rendered Markdown
- **Footer (collapsible)**: Related approved cards 列表，每项含 source type icon + link

### 7.3 Reference Panel

每个 card reference 显示：
- Card title（链接到 card 详情）
- Source type icon（.md / .pdf / .docx / .txt / .html）
- Source path（相对路径）
- Approval date
- Tags
- Value score

---

## 8. Testing Strategy

### 8.1 Unit Tests
- `WikiPageViewModel` 从 synthesis JSON 构建
- `WikiSectionView` 和 `WikiReferenceView` 数据验证
- `WikiMarkdownRenderer` 渲染输出
- Sanitization 规则
- TOC 生成逻辑

### 8.2 Integration Tests
- `llm_rebuild_wiki()` → `WikiPageViewModel` → `WikiMarkdownRenderer.render()` 全链路
- Empty/error/loading state 渲染

### 8.3 Security Tests
- XSS payload 注入 wiki body
- Script tag bypass
- Event handler attribute injection
- Style injection
- Secret exposure in rendered output

### 8.4 Accessibility Tests
- Semantic HTML structure
- ARIA labels
- Keyboard navigation (future)

---

## 9. Rollout Plan

| Phase | Content | Milestone |
|-------|---------|-----------|
| Phase 1 | WikiPageViewModel + WikiSectionView + WikiReferenceView data models | M6 |
| Phase 2 | WikiRenderer + WikiMarkdownRenderer + sanitization | M6 |
| Phase 3 | TOC generation + section navigation | M6 |
| Phase 4 | Empty/loading/error states | M6 |
| Phase 5 | Future graph renderer interface (no implementation) | M6 |
| Phase 6 | Web Wiki page update (structured rendering) | M7 |
| Phase 7 | CLI wiki show enhancement | M7 |
| Phase 8 | Security testing + XSS prevention verification | M7 |
| Phase 9 | Accessibility audit | M7 |

---

## 10. Open Questions

1. **Wiki page as separate view vs inline in current page**：推荐升级现有 Wiki 页面为结构化视图，而非新建页面。
2. **TOC position**：sidebar (default) vs top inline？推荐 sidebar for desktop, top for mobile。
3. **Reference panel default state**：collapsed vs expanded？推荐 collapsed（减少信息过载）。
4. **Markdown sanitization library**：前端使用 `DOMPurify`（唯一 sanitization 点）。Python 端不做 HTML 渲染和 sanitize。
5. **Wiki rebuild 是否需要 per-section 重建**：当前全量 rebuild。未来可考虑 incrementally update sections，但 v0.2 保持全量。
6. **Graph view data model**：节点和边的 schema 是否应该在 v0.2 中定义具体字段？推荐只定义抽象接口 `WikiGraphData`，留具体 schema 给未来。

---

## 11. Acceptance Criteria

- [ ] `WikiPageViewModel` 正确构建自 LLM synthesis JSON
- [ ] `WikiSectionView` 包含 TOC anchor 和 card references
- [ ] `WikiReferenceView` 包含 source_type 和 source_path
- [ ] API 返回 `WikiPageViewModel` JSON，section body 为 canonical Markdown text（非预渲染 HTML）
- [ ] 前端 DOMPurify sanitization 通过 XSS test suite
- [ ] 不直接 `innerHTML` 未净化内容
- [ ] TOC 正确生成，section 可导航
- [ ] Empty/error/loading states 覆盖所有触发条件
- [ ] `WikiGraphRenderer` 接口定义，`NotImplementedError` with clear v0.2 message
- [ ] Wiki renderer 不修改任何 knowledge state
- [ ] Wiki renderer 不调用 approval 路径
- [ ] 后端不输出预渲染 HTML——只输出 JSON 和 Markdown text
- [ ] No secret exposure in rendered output
