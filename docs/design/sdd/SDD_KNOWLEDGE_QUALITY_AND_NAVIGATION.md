# SDD: Knowledge Quality & Navigation — Technical Design

> **Status**: Draft
> **Date**: 2026-05-17
> **Depends on**: [RFC_0003_KNOWLEDGE_QUALITY_AND_NAVIGATION.md](../rfc/RFC_0003_KNOWLEDGE_QUALITY_AND_NAVIGATION.md)
> **Related**: [V0_3_ROADMAP.md](../roadmap/V0_3_KNOWLEDGE_QUALITY_AND_NAVIGATION_ROADMAP.md)

---

## 1. Scope

本 SDD 定义 v0.3 六个 milestone 的模块结构、数据模型、API 设计和实现顺序。所有设计遵循以下硬约束：

- 不引入 Vector DB / Embedding / Graph DB
- Quality metadata 为只读附属，不自动修改卡片 body/status
- 所有关系基于确定性规则，不做 semantic similarity
- 向后兼容 v0.2

---

## 2. Module Map

```
src/mindforge/
├── quality/
│   ├── __init__.py
│   ├── rubric.py              # CardQualityRubric, quality scoring logic
│   ├── card_type.py           # Card type classification (rule-based)
│   ├── warnings.py            # Quality warnings detection
│   └── suggestions.py         # Regenerate/split/merge suggestions
├── wiki/
│   ├── __init__.py
│   ├── wiki_service.py        # (existing) rebuild logic + quality hooks
│   ├── wiki_quality.py        # WikiQualityReport, coverage/faithfulness/staleness
│   └── wiki_reference.py      # Section-to-card reference tracking
├── relations/
│   ├── __init__.py
│   ├── graph.py               # Deterministic relationship resolver
│   ├── edge_types.py          # Relationship type definitions
│   └── related_cards.py       # Related cards computation
├── provenance/
│   ├── __init__.py
│   ├── location.py            # Source location format per source_type
│   └── location_parser.py     # Parse location from extraction metadata
├── health/
│   ├── __init__.py
│   ├── health_service.py      # Knowledge health report computation
│   └── checkers.py             # Individual health checkers
├── mindforge/
│   ├── health_cli.py          # `mindforge health` CLI command
│   └── ...
├── mindforge_web/
│   ├── routers/
│   │   ├── quality.py         # Quality API endpoints
│   │   ├── relations.py       # Related cards API endpoints
│   │   ├── health.py          # Health API endpoints
│   │   └── graph.py           # Local graph API endpoints
│   └── services/
│       ├── web_quality_service.py
│       ├── web_relations_service.py
│       ├── web_health_service.py
│       └── web_graph_service.py
web/src/
├── components/
│   ├── quality/
│   │   ├── QualityBadge.tsx       # Quality score badge (high/medium/low)
│   │   ├── QualityPanel.tsx       # Quality metadata panel in card detail
│   │   └── QualityWarnings.tsx    # Warning list display
│   ├── wiki/
│   │   ├── WikiQualityReport.tsx  # Wiki quality report display
│   │   ├── CoverageChart.tsx      # used/unused cards breakdown
│   │   └── SectionReferences.tsx  # Per-section card references
│   ├── relations/
│   │   ├── RelatedCards.tsx       # Related cards panel
│   │   └── RelationReason.tsx    # Relation reason badge
│   ├── graph/
│   │   ├── LocalGraph.tsx         # Local graph preview (list + mini graph)
│   │   └── GraphNode.tsx          # Clickable graph node
│   └── health/
│       ├── HealthPage.tsx         # Health dashboard page
│       └── HealthIssue.tsx        # Single health issue display
├── api/
│   ├── quality.ts
│   ├── relations.ts
│   ├── health.ts
│   └── graph.ts
└── pages/
    └── HealthPage.tsx             # Knowledge health page route
```

---

## 3. Data Models

### 3.1 Card Quality (M1)

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class QualityLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class CardType(str, Enum):
    FACT = "fact"
    CLAIM = "claim"
    DECISION = "decision"
    METHOD = "method"
    RISK = "risk"
    QUESTION = "question"
    INSIGHT = "insight"

@dataclass(frozen=True)
class QualityRubricScore:
    """单个 rubric 维度的评分"""
    dimension: str          # completeness, structure, specificity, source_citation, consistency
    score: float            # 0.0 - 1.0
    max_score: float        # 维度满分
    notes: str = ""         # 评分说明

@dataclass(frozen=True)
class QualityWarning:
    """质量警告"""
    code: str               # too_short, missing_sections, no_source_citation, vague_language, possible_duplicate
    severity: str           # info, warn, critical
    message: str
    suggestion: str = ""

@dataclass(frozen=True)
class CardQuality:
    """卡片质量元数据（只读附属）"""
    overall_level: QualityLevel
    overall_score: float            # 0.0 - 100.0 (normalized)
    rubric_scores: tuple[QualityRubricScore, ...]
    warnings: tuple[QualityWarning, ...]
    card_type: Optional[CardType] = None
    regenerate_suggestion: Optional[str] = None
    split_candidate: bool = False
    merge_candidate: bool = False
    dedup_candidates: tuple[str, ...] = ()  # card_ids of potential duplicates
```

### 3.2 Wiki Quality (M2)

```python
@dataclass(frozen=True)
class SectionReference:
    """Wiki section 到 card 的引用"""
    section_title: str
    card_ids: tuple[str, ...]
    relevance: str          # primary, supporting, mentioned

@dataclass(frozen=True)
class WikiQualityReport:
    """Wiki 质量报告"""
    wiki_version: str
    rebuild_time: str
    total_approved_cards: int
    used_card_ids: tuple[str, ...]
    unused_card_ids: tuple[str, ...]
    unused_reasons: dict[str, str]   # card_id -> reason
    section_references: tuple[SectionReference, ...]
    stale_sections: tuple[str, ...]  # section titles
    faithfulness_scores: dict[str, float]  # section_title -> 0.0-1.0
    faithfulness_issues: tuple[str, ...]   # human-readable issue descriptions
    knowledge_gaps: tuple[str, ...]        # topic areas with no coverage
    conflicting_claims: tuple[tuple[str, str], ...]  # (card_id_a, card_id_b, topic)
    dedup_suggestions: tuple[tuple[str, str], ...]   # (card_id_a, card_id_b)
```

### 3.3 Related Cards (M3)

```python
class RelationReason(str, Enum):
    SAME_SOURCE = "same_source"
    SAME_TAG = "same_tag"
    SAME_WIKI_SECTION = "same_wiki_section"
    SAME_REVIEW_BATCH = "same_review_batch"
    SOURCE_LOCATION_NEIGHBOR = "source_location_neighbor"
    MANUAL_LINK = "manual_link"  # reserved for future — v0.3 API must not emit this edge type

@dataclass(frozen=True)
class RelatedCardEdge:
    """确定性关系边"""
    source_card_id: str
    target_card_id: str
    reason: RelationReason
    reason_detail: str = ""    # e.g. "Both from source: introduction.md"
    strength: float = 0.5      # 0.0-1.0, deterministic weight
```

### 3.4 Source Location (M4)

```python
@dataclass(frozen=True)
class SourceLocation:
    """卡片在 source 中的精确位置"""
    source_type: str
    # Markdown: heading path + line range
    heading_path: Optional[tuple[str, ...]] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    # HTML
    css_selector: Optional[str] = None
    # PDF
    page_number: Optional[int] = None
    # DOCX
    paragraph_start: Optional[int] = None
    paragraph_end: Optional[int] = None
    
    def to_display(self) -> str:
        """生成人类可读的位置描述"""
        ...

@dataclass(frozen=True)
class ProvenanceBlockV2:
    """增强版 provenance block（v0.2 兼容）"""
    source_path: str
    source_type: str
    location: Optional[SourceLocation] = None
    excerpt: str = ""          # 来源段落摘录
    card_id: str = ""
```

### 3.5 Knowledge Health (M5)

```python
class HealthSeverity(str, Enum):
    INFO = "info"
    WARN = "warn"
    CRITICAL = "critical"

@dataclass(frozen=True)
class HealthIssue:
    """单个健康问题"""
    code: str
    severity: HealthSeverity
    title: str
    description: str
    affected_items: tuple[str, ...]    # card_ids / source_ids / section titles
    suggested_action: str
    auto_fixable: bool = False

@dataclass(frozen=True)
class HealthReport:
    """知识健康报告"""
    generated_at: str
    workspace: str
    summary: str                       # 一句话总结
    issues: tuple[HealthIssue, ...]
    stats: dict[str, int]              # total_cards, approved, drafts, orphans, low_quality, stale_sections...
```

### 3.6 Local Graph (M6)

```python
@dataclass(frozen=True)
class GraphNode:
    """图谱节点"""
    id: str
    type: str           # card, source, wiki_section, tag
    label: str
    href: Optional[str] = None   # 点击跳转链接

@dataclass(frozen=True)
class GraphEdge:
    """图谱边"""
    source_id: str
    target_id: str
    reason: RelationReason
    label: str = ""

@dataclass(frozen=True)
class LocalGraph:
    """围绕中心节点的 local graph"""
    center_id: str
    center_type: str
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    max_depth: int = 1      # v0.3 仅支持 1-hop
```

---

## 4. API Design

### 4.1 Quality API

```
GET  /api/quality/cards/{card_id}         → CardQualityResponse
POST /api/quality/cards/{card_id}/score   → Trigger re-scoring (returns CardQuality)
```

### 4.2 Wiki Quality API

```
GET  /api/wiki/quality-report              → WikiQualityReportResponse
GET  /api/wiki/sections/{section}/refs     → SectionReferencesResponse
```

### 4.3 Related Cards API

```
GET  /api/relations/cards/{card_id}/related  → RelatedCardsResponse
GET  /api/relations/edge-types                → List[RelationReason] (metadata)
```

### 4.4 Graph API

```
GET  /api/graph/card/{card_id}              → LocalGraphResponse (centered on card)
GET  /api/graph/wiki-section/{section}      → LocalGraphResponse (centered on wiki section)
```

### 4.5 Health API

```
GET  /api/health/report                     → HealthReportResponse
POST /api/health/refresh                    → Trigger re-computation
```

### 4.6 Health CLI

```
$ mindforge health                  # Print health report summary
$ mindforge health --verbose        # Full report with details
$ mindforge health --json           # JSON output for scripting
```

---

## 5. Quality Rubric Design (M1)

### 5.1 Rubric Dimensions

| Dimension | Rule | Weight | Score 0 | Score 1 |
|-----------|------|--------|---------|---------|
| completeness | Has required sections (## Summary, ## Details) | 25% | Missing all | Has all |
| structure | Well-formed sections, no orphan text | 20% | No sections | Well-structured |
| specificity | Non-vague language, concrete facts | 25% | All vague | All specific |
| source_citation | References source file/paragraph | 20% | No citation | Explicit citation |
| consistency | No internal contradiction | 10% | Contradicts self | Consistent |

### 5.2 Quality Level Mapping

- **high**: overall_score ≥ 70
- **medium**: overall_score 40-69
- **low**: overall_score < 40

### 5.3 Warning Detection

| Warning Code | Detection Rule |
|-------------|----------------|
| too_short | Body length < 100 chars |
| missing_sections | No `## ` section markers found |
| no_source_citation | Card has no source_id or source_path |
| vague_language | High ratio of vague terms ("something", "maybe", "probably", "might be") |
| possible_duplicate | Title similarity > 80% with another card (case-insensitive token overlap) |

### 5.4 Card Type Classification (Rule-based)

```python
def classify_card_type(title: str, body: str) -> Optional[CardType]:
    """基于关键词的规则分类"""
    text = f"{title} {body[:500]}".lower()
    
    type_keywords = {
        CardType.FACT: ["is defined as", "was found", "measured", "observed", "recorded"],
        CardType.CLAIM: ["argues that", "claims that", "asserts", "contends", "purports"],
        CardType.DECISION: ["decided to", "chose to", "agreed on", "resolved", "committed to"],
        CardType.METHOD: ["how to", "steps to", "procedure", "method", "approach", "technique"],
        CardType.RISK: ["risk of", "pitfall", "failure mode", "edge case", "watch out", "caution"],
        CardType.QUESTION: ["how can", "why does", "what is", "when should", "open question"],
        CardType.INSIGHT: ["interesting", "surprising", "key insight", "lesson", "pattern emerges"],
    }
    
    scores = {ct: sum(1 for kw in kws if kw in text) for ct, kws in type_keywords.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None
```

---

## 6. Wiki Quality Design (M2)

### 6.1 Coverage Computation

```
coverage_rate = |used_cards| / |total_approved_cards|

used_cards: cards explicitly referenced by name/card_id in Wiki synthesis
unused_cards: approved cards not referenced in any Wiki section
unused_reason: card too short, card topic too narrow, card status stale, etc.
```

### 6.2 Faithfulness Check

对每个 Wiki section：
1. 提取 section 中引用的 card_ids
2. 对每张 card，计算其 body 与 section 内容的 token overlap（Jaccard similarity of key terms）
3. overlap < threshold (0.3) → 标记为 potential faithfulness issue
4. 人工审查标记（不自动修改）

### 6.3 Staleness Detection

- 检查每个 Wiki section 引用的 card 是否有 updated_at > wiki rebuild time
- 检查是否有新的 approved cards 在 wiki rebuild 后添加（其 topic 匹配已有 section）
- 标记受影响 section 为 stale

### 6.4 Conflicting Claims Detection (Rule-based)

```
针对同一 topic tag 的卡片对：
  如果 card A title 包含 "increases / improves / causes"
  且 card B title 包含 "decreases / worsens / prevents"
  且两者共享 ≥1 tag → 标记为 potential conflict
```

---

## 7. Related Cards Design (M3)

### 7.1 六种确定性关系

| Reason | Detection | Strength |
|--------|-----------|----------|
| same_source | 两张卡片引用同一 source_id | 0.8 |
| same_tag | 两张卡片共享 ≥1 tag | 0.5 |
| same_wiki_section | 两张卡片被同一 Wiki section 引用 | 0.7 |
| same_review_batch | 两张卡片在同一次 source processing 中生成 | 0.3 |
| source_location_neighbor | 两张卡片来自同一 source 的相邻段落 | 0.4 |
| manual_link | **reserved for future** — v0.3 API must not emit; Web must handle unknown/reserved reason gracefully | 1.0 (not in v0.3) |

### 7.2 排序与过滤

- 按 strength 降序排列
- Library context：仅显示 human_approved
- Review context：可显示 pending/rejected（如果 mode=draft）
- 每种 reason 最多显示 5 条（避免列表过长）
- **manual_link 不出现在 v0.3 API 输出中**；Web UI 对于 unknown/reserved reason 必须 graceful fallback（不作为 error）

### 7.3 计算策略

```python
def compute_related_cards(card_id: str, all_cards: list[Card]) -> list[RelatedCardEdge]:
    """
    所有计算在内存中完成。
    对于 1000 张卡片：预建 index maps (source->cards, tag->cards, wiki_section->cards)。
    单次查询 O(k) where k = 索引 key 中最大的卡片数。
    """
    ...
```

---

## 8. Source Location Design (M4)

### 8.1 Location Format per Source Type

| Source Type | Location Fields | Display Example |
|-------------|----------------|-----------------|
| plain_markdown | heading_path, line_start, line_end | "§ Architecture > Authentication, lines 45-62" |
| txt | line_start, line_end | "Lines 120-145" |
| html | heading_path, css_selector | "h2#overview > p:nth-child(3)" |
| pdf | page_number | "Page 12" |
| docx | paragraph_start, paragraph_end | "Paragraphs 8-12" |

### 8.2 Backward Compatibility

- v0.2 provenance_blocks 包含 `source_path` 和 `source_type`
- v0.3 在 provenance_blocks 中新增可选 `location` 字段
- 没有 location 的旧卡片显示为 "Source file" 而非精确位置
- 当 source 路径通过 allowlist 验证后，copy/reveal 功能不变

---

## 9. Knowledge Health Design (M5)

### 9.1 Health Checkers

| Checker | Severity | Detection |
|---------|----------|-----------|
| review_backlog | info/warn | pending drafts count > threshold |
| missing_provenance | warn | approved cards without source_id |
| orphans | warn | cards with 0 related cards and 0 wiki references |
| low_quality | warn/critical | cards with quality level = low |
| wiki_stale | warn | sections marked stale |
| duplicates | info | potential duplicate pairs |
| extraction_warnings | info | sources with extraction warnings |
| unsupported_sources | info | failed source processing attempts |

### 9.2 Severity Heuristics

- **critical**: 需要立即关注（如 ≥5 low quality cards 或 orphan count > 20%）
- **warn**: 建议关注（如 1-10 orphan cards）
- **info**: 信息性（如 review backlog count）

### 9.3 Suggested Actions

每个 HealthIssue 的 `suggested_action` 为人类可读的操作建议：
- "Review and potentially regenerate this card" (low quality)
- "Check if this card belongs to a Wiki section" (orphan)
- "Review for duplicate content with card X" (duplicate)

---

## 10. Local Graph Design (M6)

### 10.1 Graph Construction

```
给定中心节点 center_id:
  1. 解析 center 的类型 (card/source/wiki_section/tag)
  2. 收集 1-hop neighbors:
     - card → same_source cards, same_tag cards, same_wiki_section cards, source node, tag nodes
     - wiki_section → referenced cards
     - source → cards extracted from this source
     - tag → cards with this tag
  3. 构建 edges (去重)
  4. 返回 LocalGraph
```

### 10.2 v0.3 Mini Graph — 视觉形态与硬约束

#### 10.2.1 硬约束

v0.3 Mini Graph 必须遵守以下强制约束：

| 约束 | 说明 |
|------|------|
| **不引入图形库** | 不安装 d3 / vis.js / cytoscape / viz.js / sigma.js / dagre / elkjs / mermaid |
| **不使用 canvas** | 不创建 `<canvas>` 元素做力导向图或自定义渲染 |
| **不做 force-directed graph** | 不模拟物理力、不计算节点斥力/引力 |
| **不使用 NetworkX** | NetworkX 不作为图计算/布局/可视化依赖（允许内置 dict/set/list 邻接表） |
| **HTML/CSS deterministic local graph** | 第一版 graph view 用 React组件 + CSS Flexbox/Grid + 简单 connector line 实现 |
| **必须支持 list fallback** | 每个 graph view 必须有等价的 list view fallback（CSS `@media` 或 JS fallback） |
| **Graph data contract 和 graph view 分离** | `LocalGraph` 数据模型通过 API 返回 JSON，不绑定任何 UI 库 |

#### 10.2.2 推荐视觉形态

**A. Card-centered local graph（卡片中心图谱）**

```
┌──────────────────────────────────────────────────────┐
│  Knowledge Graph                              [List] │ ← toggle: graph / list
│                                                      │
│  ┌─────────────────────────────────┐                 │
│  │  ● Auth Pattern Guide           │ ← center card  │
│  │    fact · approved · high       │                 │
│  └───────────┬─────────────────────┘                 │
│              │                                       │
│     ┌────────┼────────┐                              │
│     │        │        │                              │
│     ▼        ▼        ▼                              │
│  ┌──────────────┐  ┌──────────────────┐              │
│  │ 📄 Sources    │  │ 🏷️ Tags          │              │
│  │              │  │                  │              │
│  │ docs/auth.md │  │ auth             │              │
│  │  · same_source│  │ security         │              │
│  │              │  │  · same_tag      │              │
│  └──────────────┘  └──────────────────┘              │
│                                                      │
│  ┌──────────────────────────────────────┐            │
│  │ 📚 Wiki Sections                     │            │
│  │                                      │            │
│  │ Authentication                       │            │
│  │  · same_wiki_section                 │            │
│  └──────────────────────────────────────┘            │
│                                                      │
│  ┌──────────────────────────────────────┐            │
│  │ 📋 Related Cards                     │            │
│  │                                      │            │
│  │ ○ OAuth 2.0 Setup · same_source     │            │
│  │ ○ API Token Security · same_tag     │            │
│  │ ○ Session Management · same_wiki    │            │
│  └──────────────────────────────────────┘            │
│                                                      │
│  ▸ Show all 12 connected items                       │
└──────────────────────────────────────────────────────┘
```

特点：
- Center card 在顶部，视觉上突出（border/background 区分）
- Neighbors 按 node type 分组：Sources → Tags → Wiki Sections → Related Cards
- 每组内 items 按 edge strength 降序排列
- 每条 edge 的 reason label 以 badge 形式显示
- 使用 CSS border-left / connector-line 或 indentation 表示层级关系
- 不渲染 canvas，不绘制贝塞尔曲线

**B. Wiki-section-centered local graph（Wiki Section 中心图谱）**

```
┌──────────────────────────────────────────────────────┐
│  Section Graph                              [List]   │
│                                                      │
│  ┌─────────────────────────────────┐                 │
│  │  📚 Authentication              │ ← center        │
│  │    Wiki Section                 │   wiki section  │
│  │    3 referenced cards           │                 │
│  └───────────┬─────────────────────┘                 │
│              │                                       │
│              ▼                                       │
│  ┌──────────────────────────────────────┐            │
│  │ 📋 Referenced Cards                  │            │
│  │                                      │            │
│  │ ○ Auth Pattern Guide                │            │
│  │   fact · high                       │            │
│  │   ─ shared via: same_source →       │            │
│  │     OAuth 2.0 Setup                 │            │
│  │                                      │            │
│  │ ○ OAuth 2.0 Setup                   │            │
│  │   method · medium                   │            │
│  │   ─ shared via: same_tag →          │            │
│  │     API Token Security              │            │
│  │                                      │            │
│  │ ○ Session Management                │            │
│  │   decision · high                   │            │
│  └──────────────────────────────────────┘            │
│                                                      │
│  ▸ Tags: auth, security, oauth                      │
│  ▸ Sources: docs/auth.md                            │
└──────────────────────────────────────────────────────┘
```

特点：
- Center 为 Wiki section，显示引用的卡片数
- Referenced cards 按 importance（primary > supporting > mentioned）排列
- 每张 card 下显示其与其他 card 的 shared relation（1-hop 扩展）
- Tag/source 节点在最下方以 compact inline list 展示

#### 10.2.3 List Fallback（强制）

当 graph view 不适用时（窄屏、JS 关闭、render 错误），自动切换为 relationship list view：

```
Knowledge Graph (List View)
─────────────────────────────
● Auth Pattern Guide (this card)
  │
  ├── 📄 Source: docs/auth.md
  │     · same_source → OAuth 2.0 Setup
  │     · same_source → API Token Security
  │
  ├── 🏷️ Tag: auth
  │     · same_tag → API Token Security
  │     · same_tag → Session Management
  │
  ├── 🏷️ Tag: security
  │     · same_tag → API Token Security
  │
  ├── 📚 Wiki: Authentication
  │     · same_wiki_section → OAuth 2.0 Setup
  │     · same_wiki_section → Session Management
  │
  └── 📋 Related Cards
        ├── OAuth 2.0 Setup (same_source, same_wiki_section)
        ├── API Token Security (same_tag)
        └── Session Management (same_tag, same_wiki_section)
```

#### 10.2.4 实现策略

1. **Phase 6a (必做)**: Relationship list view（用现有 React component pattern，不新增依赖）
2. **Phase 6b (可选)**: Mini graph view（HTML/CSS grid/flexbox，不超过 500 行 TSX）
3. **Phase 6c (不出现在 v0.3)**: Canvas / force-directed / 图形库

如果 Phase 6b 的 UI 复杂度超出时间预算 50%，则 v0.3 只交付 Phase 6a（list view），Phase 6b 降级为 v0.4 backlog。

#### 10.2.5 Graph Data Contract 与 View 分离

```typescript
// API response (data contract — 纯 JSON，不绑定 UI)
interface LocalGraphResponse {
  center: {
    id: string;
    type: "card" | "wiki_section";
    label: string;
    href?: string;
  };
  nodes: Array<{
    id: string;
    type: "card" | "source" | "wiki_section" | "tag";
    label: string;
    href?: string;
    metadata?: Record<string, unknown>;
  }>;
  edges: Array<{
    source_id: string;
    target_id: string;
    reason: RelationReason;
    label: string;
  }>;
}

// React component (view — 消费 data contract，独立演进)
function LocalGraphView({ data }: { data: LocalGraphResponse }) {
  // 根据 screen size / feature flag 选择 list 或 mini-graph
  // 不修改 data contract
}
```

### 10.3 性能优化

- 最多展示节点数: 50（超出截断 + "Show all N nodes"）
- 计算缓存: 同一 center 的 graph 在 5 分钟内复用
- 懒加载: 初始展示直接邻居，展开时追加

---

## 11. Implementation Order

```
Phase 1 (M1): Card Quality
  - src/mindforge/quality/*  (rubric, card_type, warnings, suggestions)
  - web/src/components/quality/*

Phase 2 (M4): Source Location
  - src/mindforge/provenance/* (location, location_parser)
  - Update provenance_blocks to v2

Phase 3 (M2): Wiki Quality
  - src/mindforge/wiki/wiki_quality.py
  - web/src/components/wiki/WikiQualityReport.tsx

Phase 4 (M3): Related Cards
  - src/mindforge/relations/*
  - web/src/components/relations/*

Phase 5 (M5): Knowledge Health
  - src/mindforge/health/*
  - mindforge health CLI
  - web/src/components/health/*

Phase 6 (M6): Local Graph Preview
  - src/mindforge/relations/graph.py extension
  - web/src/components/graph/*
```

---

## 12. Test Strategy

详见 [TDD_KNOWLEDGE_QUALITY_AND_NAVIGATION.md](../tdd/TDD_KNOWLEDGE_QUALITY_AND_NAVIGATION.md)。

核心测试策略：

- M1: Synthetic golden cards (known good/bad) → deterministic quality score
- M2: Synthetic fixture (10 cards) → verify wiki quality report accuracy
- M3: Golden fixtures (5 cards sharing sources/tags) → verify related cards
- M4: Per-source-type synthetic fixtures → verify location parsing
- M5: Synthetic vault with known issues → verify health report
- M6: Golden graph fixtures → verify nodes and edges

---

## 13. References

- [RFC 0003](../rfc/RFC_0003_KNOWLEDGE_QUALITY_AND_NAVIGATION.md)
- [V0.3 Roadmap](../roadmap/V0_3_KNOWLEDGE_QUALITY_AND_NAVIGATION_ROADMAP.md)
- [V0.2 Development Rules](../../internal/V0_2_DEVELOPMENT_RULES.md)
- [Product Contracts](../../internal/product-contracts.md)
