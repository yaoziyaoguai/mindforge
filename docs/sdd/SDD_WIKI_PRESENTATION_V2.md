# SDD: Wiki Presentation v2 — Structured Rendering + Safety

> **Status**: Draft
> **Date**: 2026-05-14
> **Depends on**: [RFC_0002_WIKI_PRESENTATION_V2.md](../rfc/RFC_0002_WIKI_PRESENTATION_V2.md)
> **Related**: [V0_2_ROADMAP.md](../roadmap/V0_2_ROADMAP.md), [SDD_SOURCE_ADAPTER_V2.md](SDD_SOURCE_ADAPTER_V2.md)

---

## 1. Scope

本 SDD 定义 v0.2 Wiki 展示层的模块结构、数据结构和实现顺序。不改变 Wiki synthesis 逻辑、card schema、approval 语义。

---

## 2. Current Behavior (v0.1)

### 2.1 Module Map

```
src/mindforge/wiki_service.py    # rebuild_main_wiki, llm_rebuild_wiki, WikiStatus, LLMWikiResult, CardDigest
src/mindforge/wiki_cli.py        # wiki status/rebuild/show CLI commands
src/mindforge_web/routers/wiki.py # Wiki API endpoints (GET status, POST rebuild, GET content)
web/...                           # Wiki page React component
```

### 2.2 Wiki Output Format (current)

`llm_rebuild_wiki()` 输出的 `30-Wiki/Main-Wiki.md`：

```markdown
# MindForge Main Wiki
> LLM synthesis · Model: main · Last rebuilt: 2026-05-14T10:30:00+0800
> Cards included: 12

## Overview
...overview text...

## Knowledge Sections

<!-- WIKI_SECTION_START card_ids=card1,card2 -->
### Section Title
...section body...

**Related approved cards:**
- [Card Title](../20-Knowledge-Cards/card-file.md)
  - Original source: source-name.pdf

<!-- WIKI_SECTION_END -->
---

## Additional Approved Cards
...
```

### 2.3 Current Issues

- 展示层直接取 Markdown 文件内容，不做结构化拆分
- Section 边界只有 HTML comment markers，不是结构化数据
- 没有 TOC 生成
- 没有 card reference panel（reference info 在 Markdown 中，以纯链接形式）
- 没有明确的 loading/error/empty state 处理

---

## 3. Target Behavior (v0.2)

### 3.1 Module Map (target)

```
src/mindforge/
├── wiki_service.py             # ⚬ 不变（synthesis 逻辑）
├── wiki_view_model.py          # ✨ 新增：WikiPageViewModel, WikiSectionView, WikiReferenceView, WikiRenderOptions
├── wiki_renderer.py            # ✨ 新增：WikiRenderer ABC, WikiMarkdownRenderer, WikiGraphRenderer (interface only)
├── wiki_cli.py                 # ✏️ 修改：使用 WikiPageViewModel 增强 wiki show
│
src/mindforge_web/
├── routers/wiki.py             # ✏️ 修改：API 返回 WikiPageViewModel JSON 而非 raw Markdown
│
web/src/                        # ✏️ 修改：Wiki page 使用结构化数据渲染
├── components/wiki/
│   ├── WikiPage.tsx            # Wiki 主页组件
│   ├── WikiTOC.tsx             # 目录组件
│   ├── WikiSection.tsx         # Section 卡片组件
│   ├── WikiReferencePanel.tsx  # Card/source 引用面板
│   ├── WikiEmptyState.tsx      # 空态组件
│   ├── WikiErrorState.tsx      # 错误态组件
│   └── WikiLoadingState.tsx    # 加载态组件
```

### 3.2 Data Flow

```
llm_rebuild_wiki()
    │
    ├──→ LLM Synthesis JSON (overview + sections + card_ids)
    │
    ▼
WikiPageViewModel.build(synthesis_json, card_digests)
    │
    ├──→ WikiPageViewModel (structured data)
    │
    ▼
API: GET /api/wiki/page → WikiPageViewModel (JSON)
    │
    ▼
Web WikiPage.tsx
    ├──→ WikiTOC.tsx (sidebar)
    ├──→ Overview section
    ├──→ WikiSection.tsx[] (main content)
    │   └──→ WikiReferencePanel.tsx (per section)
    ├──→ Additional Approved Cards section
    └──→ Open Questions section
```

---

## 4. Proposed Modules

### 4.1 `src/mindforge/wiki_view_model.py` (new)

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class WikiPageViewModel:
    """从 LLM synthesis JSON + CardDigest index 构建的结构化 Wiki 视图模型。"""
    title: str
    mode: str                           # "llm" | "deterministic"
    model_id: str | None
    last_rebuilt_at: str | None
    overview: str                       # Markdown
    sections: list["WikiSectionView"]
    additional_cards: list["WikiReferenceView"]   # uncited cards
    open_questions: list["WikiQuestionView"]
    included_card_count: int
    additional_card_count: int
    warnings: list[str]
    
    @classmethod
    def build(
        cls,
        synthesis_output: dict,          # LLM synthesis JSON output
        digests: list["CardDigest"],      # from wiki_service
        mode: str = "llm",
        model_id: str | None = None,
        last_rebuilt_at: str | None = None,
        warnings: list[str] | None = None,
    ) -> "WikiPageViewModel": ...

@dataclass(frozen=True)
class WikiSectionView:
    id: str                             # "section-1", "section-2", ...
    title: str
    body: str                           # Markdown
    level: int                          # heading level (default 2)
    card_refs: list["WikiReferenceView"]
    anchor: str                         # URL anchor

@dataclass(frozen=True)
class WikiReferenceView:
    card_id: str
    card_title: str
    source_title: str | None
    source_type: str | None             # "plain_markdown" | "pdf" | "docx" | "txt" | "html" | ...
    source_path: str | None
    track: str | None
    tags: list[str] = field(default_factory=list)
    value_score: int | None = None
    approved_at: str | None = None
    card_rel_path: str = ""

@dataclass(frozen=True)
class WikiQuestionView:
    question: str

@dataclass
class WikiRenderOptions:
    show_provenance_panel: bool = True
    show_toc: bool = True
    toc_position: str = "sidebar"       # "sidebar" | "top"
    sanitize_html: bool = True
    enable_mermaid: bool = False         # future
    enable_code_highlight: bool = True
```

**构建逻辑**：
1. 从 synthesis JSON 解析 `overview`, `sections[]`, `open_questions[]`
2. 每个 section 的 `card_ids[]` 在 `CardDigest` index 中查找对应卡片
3. 构建 `WikiReferenceView` 包含 full provenance（source_type, source_path, tags, value_score）
4. 未被任何 section 引用的 card 归入 `additional_cards`
5. 记录 synthesis warnings（unknown card_id, empty section 等）

### 4.2 `src/mindforge/wiki_renderer.py` (new)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass(frozen=True)
class RenderedOutput:
    content_html: str                   # safe HTML
    toc_html: str | None                # TOC HTML
    metadata: dict                      # renderer-specific metadata

class WikiRenderer(ABC):
    """Wiki 渲染器抽象基类。"""
    name: str
    
    @abstractmethod
    def render(
        self,
        view_model: "WikiPageViewModel",
        options: "WikiRenderOptions | None" = None
    ) -> RenderedOutput: ...

class WikiMarkdownRenderer(WikiRenderer):
    """Markdown → Safe HTML 渲染器（当前实现）。"""
    name = "markdown"
    
    def render(self, view_model, options=None) -> RenderedOutput:
        # 1. Render overview as Markdown → sanitized HTML
        # 2. Render each section as Markdown → sanitized HTML
        # 3. Build TOC from sections
        # 4. Apply sanitization
        # 5. Return RenderedOutput

class WikiGraphRenderer(WikiRenderer):
    """Graph visualization renderer（v0.2 only interface）。"""
    name = "graph"
    
    def render(self, view_model, options=None):
        raise NotImplementedError(
            "Graph renderer is not implemented in v0.2. "
            "This is a reserved extension point for future graph view support. "
            "See docs/rfc/RFC_0002_WIKI_PRESENTATION_V2.md §5.7."
        )
```

**Sanitization Pipeline**：

```
Markdown text
    │
    ▼
markdown.markdown() → HTML string
    │
    ▼
bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS)
    │
    ▼
safe HTML string
```

ALLOWED_TAGS: `h1-h6, p, ul, ol, li, a, strong, em, code, pre, blockquote, table, thead, tbody, tr, th, td, hr, br, img, details, summary`

ALLOWED_ATTRS:
- `a`: `href` (http/https/mailto/relative only), `title`
- `img`: `src`, `alt`
- `code`: `class` (for syntax highlighting)
- `th`, `td`: `align`

STRIP: `script, iframe, object, embed, form, input, button, style, link, meta, base, applet, audio, video, source, track, canvas, svg, math`

STRIP ATTRS: `onclick, onerror, onload, onmouseover, onmouseout, onfocus, onblur, style (inline), class (except on code)`

### 4.3 `src/mindforge/wiki_cli.py` (modified)

`mindforge wiki show` 增强：
```
$ mindforge wiki show
Wiki: MindForge Main Wiki
Mode: LLM · Model: main · Last rebuilt: 2026-05-14T10:30
Cards: 12 (10 cited in sections, 2 additional)

Sections:
  1. Section Title
     Cards: card-id-1, card-id-2
  2. Another Section
     Cards: card-id-3
  ...

Open Questions:
  - Q1: ...

$ mindforge wiki show --section 2
Section 2: Another Section
---
...section body (raw Markdown)...

Related Cards:
  - Card Title (source: report.pdf, pdf)
    approved 2026-05-12 · Track: work · Value: 6
```

### 4.4 `src/mindforge_web/routers/wiki.py` (modified)

API 扩展：

```
GET /api/wiki/status      → WikiStatusResponse (existing, unchanged)
POST /api/wiki/rebuild    → WikiRebuildResponse (existing, unchanged)
GET /api/wiki/page        → WikiPageViewModel (NEW, JSON)
  Query params:
    ?view=markdown        → default (current)
    ?view=graph           → future (400 in v0.2: "graph view not yet implemented")
GET /api/wiki/sections    → list[WikiSectionView] (NEW, JSON)
GET /api/wiki/references  → list[WikiReferenceView] (NEW, JSON)
```

### 4.5 Web Frontend Components (new/modified)

**WikiPage.tsx**:
```
┌──────────────────────────────────────────────────┐
│ [Top Bar] Wiki Title  [LLM Badge]  [Rebuild Btn] │
│           Model: main · Rebuilt: ...             │
├────────────┬─────────────────────────────────────┤
│ [TOC]      │ [Overview]                          │
│ Section 1  │ ...overview text...                  │
│ Section 2  ├─────────────────────────────────────┤
│ Section 3  │ [Section 1]                         │
│            │ ## Section Title                    │
│            │ ...body...                           │
│            │ ┌─────────────────────────────────┐ │
│            │ │ References (2 cards)     [展开] │ │
│            │ └─────────────────────────────────┘ │
│            ├─────────────────────────────────────┤
│            │ [Section 2] ...                     │
└────────────┴─────────────────────────────────────┘
```

**WikiReferencePanel.tsx**: 可折叠面板，展示 card 列表：
- Card title (link)
- Source type icon
- Source path
- Approval date
- Tags
- Value score

**WikiEmptyState.tsx**: "No approved cards yet" / "Wiki not built yet" with CTA

**WikiErrorState.tsx**: Error message + retry/suggest action

**WikiLoadingState.tsx**: Skeleton / spinner during rebuild

---

## 5. Data Structures

### 5.1 WikiPageViewModel

| Field | Type | Source |
|-------|------|--------|
| title | str | constant "MindForge Main Wiki" |
| mode | str | "llm" or "deterministic" |
| model_id | str \| None | from LLMWikiResult.model_id |
| last_rebuilt_at | str \| None | from LLMWikiResult.last_rebuilt_at |
| overview | str | from synthesis JSON output.overview |
| sections | list[WikiSectionView] | from synthesis JSON output.sections[] |
| additional_cards | list[WikiReferenceView] | uncited cards from digest index |
| open_questions | list[WikiQuestionView] | from synthesis JSON output.open_questions[] |
| included_card_count | int | len(digests) |
| additional_card_count | int | len(uncited) |
| warnings | list[str] | from LLMWikiResult.warnings |

### 5.2 WikiSectionView

| Field | Type | Source |
|-------|------|--------|
| id | str | generated: "section-{index}" |
| title | str | from synthesis section.title |
| body | str | from synthesis section.body (Markdown) |
| level | int | heading level (default 2) |
| card_refs | list[WikiReferenceView] | from digest index lookup by card_ids |
| anchor | str | slugified section title |

### 5.3 WikiReferenceView

| Field | Type | Source |
|-------|------|--------|
| card_id | str | from CardDigest.card_id |
| card_title | str | from CardDigest.title |
| source_title | str \| None | from CardDigest.source_title |
| source_type | str \| None | from card source metadata |
| source_path | str \| None | from card source metadata |
| track | str \| None | from CardDigest.track |
| tags | list[str] | from CardDigest.tags |
| value_score | int \| None | from CardDigest.value_score |
| approved_at | str \| None | from CardDigest.approved_at |
| card_rel_path | str | from CardDigest.card_rel_path |

---

## 6. Rendering Pipeline

```
┌─────────────────────────────────────────────────────────┐
│                  Wiki Rendering Pipeline                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. Synthesis                                           │
│     llm_rebuild_wiki() → LLMWikiResult + synthesis JSON │
│                                                         │
│  2. View Model Construction                             │
│     WikiPageViewModel.build(json, digests)              │
│                                                         │
│  3. Renderer Selection                                  │
│     renderer = registry.get(options.view or "markdown") │
│                                                         │
│  4. Rendering                                           │
│     renderer.render(view_model, options)                │
│     ├── Markdown → HTML (markdown library)              │
│     ├── Sanitize HTML (bleach)                          │
│     ├── Build TOC                                       │
│     └── Return RenderedOutput                           │
│                                                         │
│  5. API Response                                        │
│     GET /api/wiki/page → WikiPageViewModel (JSON)       │
│                                                         │
│  6. Frontend Rendering                                  │
│     WikiPage.tsx renders sections with React components │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 7. Markdown Sanitization

**库选择**：Python 端推荐 `bleach`（成熟稳定）；前端推荐 `DOMPurify`。

**Python sanitization rules**：
```python
ALLOWED_TAGS = [
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "br", "hr",
    "ul", "ol", "li",
    "a", "strong", "em", "code", "pre",
    "blockquote",
    "table", "thead", "tbody", "tr", "th", "td",
    "img",
    "details", "summary",
]

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title"],
    "img": ["src", "alt"],
    "code": ["class"],
    "th": ["align"],
    "td": ["align"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto", "ftp"]
```

---

## 8. HTML Safety

- **Server-side**：bleach sanitization before API response
- **Client-side**：DOMPurify sanitization before `innerHTML`（双重保险）
- **CSP header**：`Content-Security-Policy: default-src 'self'; script-src 'none'; style-src 'self' 'unsafe-inline'`
- **No inline event handlers**：所有事件处理通过 React `onClick` 等，不通过 HTML attribute
- **No raw HTML injection**：前端组件使用 React JSX，避免 `dangerouslySetInnerHTML` 除非经过 DOMPurify

---

## 9. Empty / Loading / Error States

### 9.1 State Machine

```
┌──────────┐   rebuild    ┌──────────┐   success   ┌──────────┐
│  EMPTY   │─────────────→│ LOADING  │────────────→│  READY   │
│          │              │          │             │          │
│ no cards │              │ spinner  │             │ wiki ok  │
│ or no    │              │ progress │             │          │
│ wiki     │              │          │             │          │
└──────────┘              └────┬─────┘             └──────────┘
                               │ failure
                               ▼
                          ┌──────────┐
                          │  ERROR   │
                          │          │
                          │ message  │
                          │ retry    │
                          └──────────┘
```

### 9.2 State Detection

| State | Condition | API Response |
|-------|-----------|-------------|
| EMPTY: no approved cards | `approved_card_count == 0` | `WikiStatus.exists=False, approved_card_count=0` |
| EMPTY: wiki not built | `!wiki_path.exists()` and `approved_card_count > 0` | `WikiStatus.exists=False, approved_card_count>0` |
| READY: wiki exists | `wiki_path.exists()` | `WikiStatus.exists=True` |
| LOADING | rebuild API called, waiting for response | Frontend-managed state |
| ERROR | rebuild API returned error | `{"error": "..."}` |

---

## 10. Future Graph Renderer Interface

```python
# Reserved interface only — no implementation in v0.2

@dataclass
class WikiGraphData:
    """Graph view 数据模型（future）。"""
    nodes: list                      # list of graph nodes
    edges: list                      # list of graph edges

class WikiGraphRenderer(WikiRenderer):
    """Graph visualization renderer（future）。"""
    name = "graph"
    
    def render(self, view_model, options=None):
        raise NotImplementedError(
            "Graph renderer is not implemented in v0.2. "
            "See docs/rfc/RFC_0002_WIKI_PRESENTATION_V2.md §5.7."
        )
```

Renderer registry 预留注册点：
```python
_WIKI_RENDERERS: dict[str, WikiRenderer] = {
    "markdown": WikiMarkdownRenderer(),
    # "graph": WikiGraphRenderer(),  # uncomment when implemented
}
```

API 预留 query param：`GET /api/wiki/page?view=graph` → 400 in v0.2

---

## 11. CLI Integration

`mindforge wiki show` 输出改为结构化展示：
1. Wiki status header（mode, model, rebuilt time, card count）
2. Section list with TOC
3. `--section N` flag 查看单 section 详情
4. `--references` flag 查看所有 card references

---

## 12. Web Integration

Web Wiki page 重构：
1. API 返回结构化 `WikiPageViewModel` JSON（替代 raw Markdown text）
2. 前端按 components 渲染：TOC + Sections + References
3. Rebuild 按钮触发 POST /api/wiki/rebuild，rebuild 完成后自动重新获取 page
4. 前端管理 loading state

---

## 13. Tests

### 13.1 New Test Files

```
tests/wiki/
├── test_wiki_view_model.py             # WikiPageViewModel build from synthesis JSON
├── test_wiki_renderer.py               # WikiMarkdownRenderer render output
├── test_wiki_sanitization.py           # Sanitization rules
├── test_wiki_xss_prevention.py         # XSS payload rejection
├── test_wiki_toc_generation.py         # TOC generation
├── test_wiki_empty_states.py           # Empty/error/loading state rendering
├── test_wiki_future_graph_interface.py # Graph renderer interface + NotImplementedError
├── test_wiki_secret_exposure.py        # No secret in rendered output
└── test_wiki_accessibility.py          # Semantic HTML / ARIA
```

### 13.2 Key Test Cases

**WikiPageViewModel.build()**:
- Valid synthesis JSON → valid WikiPageViewModel
- Empty sections → empty sections list
- Unknown card_ids in sections → warnings recorded
- Missing overview → empty string
- Missing open_questions → empty list

**WikiMarkdownRenderer.render()**:
- Valid view_model → RenderedOutput with safe HTML
- Markdown with script tag → script stripped
- Markdown with onclick → onclick stripped
- Markdown with iframe → iframe stripped
- Table Markdown → safe table HTML

**Sanitization**:
- `<script>alert(1)</script>` → stripped
- `<a href="javascript:alert(1)">` → href stripped
- `<img src="x" onerror="alert(1)">` → onerror stripped
- `<p style="color:red">` → style stripped
- `<iframe src="evil.com">` → iframe stripped

**Secret Exposure**:
- API response JSON 中不出现 API key pattern
- Rendered HTML 中不出现 API key pattern
- WikiPageViewModel 序列化后不包含敏感字段

**Future Graph Interface**:
- `WikiGraphRenderer().render()` → raises `NotImplementedError` with v0.2 message
- `GET /api/wiki/page?view=graph` → returns 400 with "not implemented in v0.2"

---

## 14. Implementation Phases

| Phase | Content | Files |
|-------|---------|-------|
| P1 | WikiPageViewModel + WikiSectionView + WikiReferenceView | wiki_view_model.py |
| P2 | WikiRenderer ABC + WikiMarkdownRenderer | wiki_renderer.py |
| P3 | Sanitization pipeline + tests | wiki_renderer.py, tests/wiki/ |
| P4 | TOC generation | wiki_renderer.py (in WikiMarkdownRenderer) |
| P5 | WikiGraphRenderer interface (NotImplementedError) | wiki_renderer.py |
| P6 | API: GET /api/wiki/page | routers/wiki.py |
| P7 | CLI: wiki show enhancement | wiki_cli.py |
| P8 | Web: WikiPage + WikiTOC + WikiSection + WikiReferencePanel | web/src/components/wiki/ |
| P9 | Web: Empty/Loading/Error states | web/src/components/wiki/ |
| P10 | Security tests (XSS, sanitization, secret exposure) | tests/wiki/ |

---

## 15. Rollback Plan

- WikiPageViewModel 和 WikiRenderer 是新增模块，不修改现有 wiki_service.py
- API 新增 `/api/wiki/page` endpoint，不改变现有 `/api/wiki/status` 和 `/api/wiki/rebuild`
- 前端 Wiki 页面可以 feature-flag 切换新旧渲染
- 如果 rollback：恢复旧的 `GET /api/wiki/content` (raw Markdown) 和旧的 Wiki page 组件

---

## 16. Done Criteria

- [ ] `WikiPageViewModel.build()` correctly constructs from synthesis JSON
- [ ] `WikiSectionView` contains anchor + card_refs
- [ ] `WikiReferenceView` contains source_type + source_path + full provenance
- [ ] `WikiMarkdownRenderer.render()` outputs sanitized HTML
- [ ] XSS test suite passes
- [ ] TOC correctly generated with section anchors
- [ ] Section navigation works (within-page jump)
- [ ] Empty/error/loading states cover all conditions
- [ ] `WikiGraphRenderer.render()` raises NotImplementedError with clear v0.2 message
- [ ] API `?view=graph` returns 400
- [ ] Wiki renderer does not modify knowledge state
- [ ] Wiki renderer does not call approval path
- [ ] Wiki renderer only uses human_approved cards
- [ ] No `innerHTML` of unsanitized content
- [ ] No secret exposure in rendered output
- [ ] ruff + pytest pass
