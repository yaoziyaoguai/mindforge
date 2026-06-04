---
name: knowledge-library-ux-redesign-spec
description: Specification for Knowledge Library and Detail page UX redesign — information architecture, component boundaries, reading path
metadata:
  type: spec
---

# Knowledge Library UX Redesign Specification

Date: 2026-06-04
Status: Draft — awaiting human review

## 1. Current Library Page Problems

`LibraryPage.tsx` 当前问题：

1. **控制太密集**：5 个 filter tabs（2 个 disabled）、4 个下拉过滤器、搜索、批量操作——个人知识库不需要这么多过滤
2. **标签没有展示**：`LibraryCardResponse` 缺少 `tags` 字段，前端 `const tags: string[] = Array.isArray(raw.tags) ? (raw.tags as string[]) : [];` 返回空数组
3. **统计行冗余**：`approved=total`（因为只有 approved 卡片会展示）
4. **三列表格太宽**：标题、状态、来源三列，没有展示标签和一句话摘要
5. **没有阅读路径**：用户不知道先看什么——是搜索、是浏览标签、是按质量排序
6. **像管理后台**：过滤、排序、批量操作——个人知识管理不需要这些企业级功能
7. **空状态不友好**：没有卡片时只有空列表，没有引导

## 2. Current Detail Page Problems

`CardWorkspace.tsx` 当前问题：

1. **一句话摘要 bug**：`const summary = useMemo(() => { const stripped = stripMarkdown(body); return stripped ? stripped.slice(0, 150) + ... : null; }, [body]);` — 取 body 前 150 字符，经常是 `## Source Excerpt` 的开头
2. **分组是 pipeline 视角**：KnowledgeSections 分组为 "understanding"（AI Summary, Human Note, Key Points）和 "processing"（Source Excerpt, AI Inference, Reusable Prompts, Project Hooks, Review Questions, Action Items）——这是 pipeline 产出结构，不是用户阅读路径
3. **7 个主要区域平铺**：没有优先级，所有字段平等展示
4. **技术细节不够折叠**：虽然有 `<details>`，但内容太多（prompt_versions, stage_models, quality_score）
5. **关系区包装过度**：14 种 edge 类型，大多数是技术关系（same_source, same_tag），不是知识关系
6. **标签只在详情区**：标签应该在首屏就能看到（帮助判断这条知识属于什么领域）

## 3. New Information Architecture Goals

1. **首屏即价值**：用户打开卡片后，第一屏就能判断"这条知识对我有没有价值"
2. **阅读路径清晰**：先知道"是什么"，再知道"怎么用"，再知道"还有什么"
3. **技术不干扰**：pipeline 产出记录、prompt 版本、质量评分不进入主要阅读路径
4. **关系真实**：只展示真正有语义关联的知识，不把同标签/同来源包装成"图谱"
5. **渐进披露**：普通用户看核心信息，高级用户看技术证据
6. **搜索友好**：Library 首页让用户快速找到想要的知识

## 4. Library Home Page Organization

### 4.1 简化过滤器

**当前**：5 filter tabs + 4 dropdown filters + search + bulk operations

**v2**：

```
┌─────────────────────────────────────────────────────────┐
│ Knowledge Library                          [12 cards]   │
│                                                         │
│ [Search...]                              [Sort ▼] [Tags]│
│                                                         │
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐          │
│ │ All  │ │Type: │ │ Topic│ │Quality│ │ Source│          │
│ │ (12) │ │insight│ │arch  │ │high   │ │web   │          │
│ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘          │
└─────────────────────────────────────────────────────────┘
```

**变化**：
- tabs 从 5 个减少到 1 个（All），其他变为可选 filter chips
- 搜索框始终可见
- Sort 默认为 "by value_score desc"，可选 "by date", "by title", "by type"
- Tags filter 是弹出式，不是下拉——用户可以选择多个标签
- 没有批量操作（个人知识管理不需要）

### 4.2 卡片列表展示

**当前**：三列表格（标题、状态、来源）

**v2**：

```
┌──────────────────────────────────────────────────────────────────┐
│ ┌──────────────────────────────────────────────────────────────┐│
│ │ 不可变数据的核心价值是可读性                     [insight]    ││
│ │ 不可变数据不仅是为了防止 bug，更重要的是让代码的阅读顺序变... ││
│ │ functional-programming · data-design · immutability          ││
│ │ Source: inbox/immutable-data.md    ·  Value: 0.85            ││
│ └──────────────────────────────────────────────────────────────┘│
│ ┌──────────────────────────────────────────────────────────────┐│
│ │ 函数组合的本质是类型匹配                        [method]     ││
│ │ 函数组合不是链式调用，而是通过类型签名确保每个函数的输出...   ││
│ │ functional-programming · type-theory · composition           ││
│ │ Source: https://example.com/...    ·  Value: 0.72            ││
│ └──────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

**展示字段**：
- **标题**：knowledge card title
- **类型标签**：knowledge_type（insight / concept / method / ...）
- **一句话摘要**：one_sentence_takeaway（截断到 150 字符）
- **标签**：前 3 个 tags
- **来源**：source_trace.file_path 或 source_trace.url（截断）
- **价值评分**：value_score（数值，不是 quality_level）

**不再展示**：
- status 列（Library 只展示 human_approved，ai_draft 在 Review 页面）
- 多个来源字段（只展示一个主要来源）
- 质量等级（quality_level 进入详情页技术区）

### 4.3 空状态设计

当前空状态：空列表

v2 空状态：

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│           📚                                          │
│                                                         │
│  你的知识库里还没有知识卡片                              │
│                                                         │
│  知识卡片是从原文中提炼的可复用洞察。                     │
│  你可以：                                               │
│                                                         │
│  [导入文件]  [粘贴 URL]  [粘贴文本]                      │
│                                                         │
│  导入后，AI 会提炼出知识卡片供你审阅。                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## 5. Card Detail First Screen

**v2 详情页第一屏（Layer 1 — 价值首屏）**：

```
┌───────────────────────────────────────────────────────────┐
│ ← Back to Library                                        │
│                                                           │
│ 不可变数据的核心价值是可读性                     [insight] │
│                                                           │
│ ─────────────────────────────────────────────────────── │
│                                                           │
│ 不可变数据不仅是为了防止 bug，更重要的是让代码的阅读      │
│ 顺序变得线性——你不需要追踪对象在哪些地方可能被修改。      │
│                                                           │
│ ─────────────────────────────────────────────────────── │
│                                                           │
│ Tags: functional-programming · data-design · immutability │
│ Source: inbox/immutable-data.md                           │
│                                                           │
│ [核心洞察 ▼]                              [Edit] [Review] │
└───────────────────────────────────────────────────────────┘
```

**第一屏包含**：
1. 返回按钮
2. 标题 + knowledge_type 标签
3. one_sentence_takeaway（完整展示，不截断）
4. tags（全部展示）
5. source_trace（简化展示）
6. 核心洞察（默认展开，因为它是卡片的核心价值）
7. 编辑/审阅按钮（如果是 ai_draft）

## 6. Default Expanded Sections

以下区域默认展开：

| Section | 理由 |
|---------|------|
| Core Insight | 卡片的核心价值所在，用户首先应该读这个 |
| Reusable Principle | 用户需要知道"能直接应用什么" |

## 7. Default Collapsed Sections

以下区域默认折叠（`<details>`）：

| Section | 理由 |
|---------|------|
| Applicable Context | 不是所有用户都需要知道适用场景 |
| Limitations & Caveats | 不是所有用户都需要知道限制条件 |
| Supporting Evidence | 证据区较长，按需展开 |
| Related Questions | 引导性问题，不是核心内容 |
| Next Actions | 行动项，不是核心阅读内容 |
| Human Note | 初始为空，用户自己填写 |
| Source Excerpt | 原文较长，按需查阅 |

## 8. Technical Fields in Advanced Info

以下技术字段进入"高级信息"区（页面底部 `<details>`）：

| Field | 展示方式 |
|-------|---------|
| prompt_versions | 文本：`distill: v2, triage: v1` |
| stage_models | 文本：`triage: sonnet-4.6, distill: sonnet-4.6` |
| quality_score | 数值：`0.8` |
| quality_level | 文本：`good` |
| value_score | 数值：`0.85` |
| confidence | 文本：`high` |
| body 全文 | 原始 Markdown |

**高级信息区标题**：`技术信息（调试用）`

**访问方式**：点击页面底部的 `<details>` 展开

## 9. Tags Display

**当前问题**：tags 没有透出到 API，前端只展示在详情页的 body 区域

**v2 方案**：

1. **Library 列表页**：展示前 3 个 tags
2. **Detail 首屏**：展示全部 tags（第一屏，标题下方）
3. **Library 过滤器**：弹出式 tag 选择器
4. **API 修复**：LibraryCardResponse 必须包含 tags 字段

### API 需求

```typescript
// types.ts
interface LibraryCardResponse {
  // ... existing fields ...
  tags: string[];           // NEW: 知识分类标签
  knowledge_type: string;   // NEW: concept | claim | insight | ...
  one_sentence_takeaway: string | null;  // NEW: 一句话核心
}
```

## 10. Source Display

**当前**：source_excerpt, source_url, source_file_path, source_type, source_saved_at 平铺

**v2**：

1. **Library 列表页**：展示一个主要来源（source_trace.file_path 或 URL 的域名）
2. **Detail 首屏**：展示简化来源（file_path 或 URL）
3. **Detail 详情区**：在高级信息区展示完整来源（所有字段）

### 来源追溯格式

```
Source: inbox/immutable-data.md
  or
Source: example.com/article-name
```

## 11. AI Summary / Source Excerpt / Human Note Reordering

**当前顺序**：AI Summary → Human Note → Key Points → Source Excerpt → AI Inference → Reusable Prompts → Project Hooks → Review Questions → Action Items

**v2 顺序**（按阅读路径）：

1. **one_sentence_takeaway**（首屏，不在 section 中）
2. **Core Insight**（默认展开）—— 对应 v1 的 AI Summary
3. **Applicable Context**（默认折叠）—— 新字段
4. **Reusable Principle**（默认展开）—— 对应 v1 的 Reusable Prompts/Principles
5. **Limitations & Caveats**（默认折叠）—— 新字段
6. **Supporting Evidence**（默认折叠）—— 对应 v1 的 AI Inference
7. **Related Questions**（默认折叠）—— 对应 v1 的 Review Questions
8. **Next Actions**（默认折叠）—— 对应 v1 的 Action Items
9. **Human Note**（默认折叠，初始为空）—— 只能由人填写
10. **Source Excerpt**（默认折叠）—— 原文完整摘录
11. **技术信息**（默认折叠）—— pipeline 记录

### 设计原则

- 用户价值高的字段在上面，技术证据在下面
- 默认展开的字段是用户最需要读的
- 默认折叠的字段是按需查阅的
- 技术字段在底部，不污染主要阅读路径

## 12. Related Knowledge Area Renaming & Restructuring

### 12.1 重命名

**当前**：GraphNavigationPanel / "知识图谱"

**v2**：`RelatedKnowledgePanel` / "相关知识"

**理由**：
- 当前关系数据是同标签/同来源，不是真正的知识图谱
- "图谱"暗示了 graph/visualization，当前没有
- "相关知识"准确反映了功能：展示相关的其他知识卡片

### 12.2 关系类型简化

**当前**：14 种 edge 类型（derived_from, has_tag, shares_tag, same_source, ...）

**v2**：

| Relation | 来源 | 展示 |
|----------|------|------|
| same_tag | 同标签（至少 1 个） | "同标签" |
| same_topic | 同目录 topic | "同主题" |
| mentioned_by | 一张卡提到另一张的标题/slug | "被提及" |

**移除的关系**：
- `derived_from`（pipeline 技术关系）
- `shares_tag`（与 same_tag 重复）
- `same_source`（同来源不是知识关系）
- 其他纯技术关系

### 12.3 展示方式

```
┌─────────────────────────────────────────────────────┐
│ 相关知识 (3)                                        │
│                                                     │
│ ┌─────────────────────────────────────────────────┐│
│ │ 函数组合的本质是类型匹配              [同标签]   ││
│ │ 函数组合不是链式调用，而是通过类型签名确保...   ││
│ └─────────────────────────────────────────────────┘│
│ ┌─────────────────────────────────────────────────┐│
│ │ React 状态管理的不可变模式             [同主题]  ││
│ │ React 中不可变状态是 React 设计哲学的核心...    ││
│ └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

**展示内容**：
- 相关卡片的标题
- 相关卡片的 knowledge_type 标签
- 相关原因（同标签/同主题/被提及）
- 相关卡片的一句话摘要（one_sentence_takeaway）

**不展示**：
- 关系类型的技术细节
- edge 的 metadata
- 社区检测算法结果

## 13. How to Avoid Fake "Knowledge Graph"

**当前问题**：14 种 edge 类型，大多数是同标签/同来源，包装成"图谱"

**v2 方案**：

1. **不叫"知识图谱"**：改叫"相关知识"
2. **不展示关系类型细节**：只展示"同标签"、"同主题"、"被提及"
3. **不展示社区检测结果**：社区检测是基于同标签聚类的算法结果，不是知识关系
4. **不展示 14 种 edge 类型**：只展示 3 种有意义的关系
5. **不展示关系强度**：同标签不等于强关联
6. **诚实标注关系来源**：明确说"基于标签匹配"，不包装成 AI 推断

**未来如果要做真正的知识图谱**：
- 需要引入 embedding / RAG / GraphRAG
- 需要用户明确理解"图谱"的含义
- 不能在当前数据基础上包装

## 14. Reading Mode vs Editing Mode

### 14.1 阅读模式（默认）

- 展示卡片的所有内容
- Human Note 区域显示空状态提示："还没有备注，点击添加"
- 审阅按钮在右上角（如果是 ai_draft）
- 不可编辑任何字段

### 14.2 编辑模式（审阅时）

- Human Note 区域变为可编辑 textarea
- 所有 LLM 生成字段可以编辑（点击字段旁编辑图标）
- 底部出现审阅操作按钮：
  - **Confirm**：确认内容正确
  - **Edit & Confirm**：保存编辑并确认
  - **Downgrade to Note**：降级为普通笔记
  - **Discard**：删除

### 14.3 模式切换

- 阅读模式 → 编辑模式：点击"编辑"按钮
- 编辑模式 → 阅读模式：点击"取消"或 Confirm/Discard 后
- ai_draft 卡片默认显示审阅引导
- human_approved 卡片可以进入编辑模式修改 human_note

## 15. Empty State Design

### 15.1 Library 空状态

```
┌─────────────────────────────────────────────────────────┐
│                    📚                                   │
│                                                         │
│  你的知识库里还没有知识卡片                              │
│                                                         │
│  知识卡片是从原文中提炼的可复用洞察。导入原文后，        │
│  AI 会提炼出核心洞察、适用场景、可复用原则等内容，      │
│  供你审阅确认。                                         │
│                                                         │
│  [导入文件]  [粘贴 URL]  [粘贴文本]                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 15.2 Detail 空状态（字段为空时）

当 v1 卡片缺少 v2 字段时：

- `one_sentence_takeaway` 为 null → fallback 到 ai_summary_bullets 第一条
- `applicable_context` 为 null → 不展示该 section
- `limitations_or_caveats` 为 null → 不展示该 section
- `knowledge_type` 不存在 → 显示 "concept"（默认）
- tags 为空 → 不展示 tags

### 15.3 Related Knowledge 空状态

```
┌─────────────────────────────────────────────────────┐
│ 相关知识                                            │
│                                                     │
│ 还没有找到相关的知识卡片。                           │
│ 随着知识卡片增多，这里会出现相关内容。                │
└─────────────────────────────────────────────────────┘
```

## 16. Fake Demo Data Strategy

### 16.1 目标

让用户打开 demo 就能看到知识产品的价值，不是 `[fake]` 占位。

### 16.2 方案

1. **FakeProvider 输出有意义的 demo 内容**（见 distill_prompt_v2.md 第 13 节）
2. **预置 demo 卡片**：在 vault 中预置 3-5 张高质量的 human_approved 卡片
3. **Demo 模式检测**：当检测到 demo 模式时，展示预置卡片
4. **Demo 引导**：demo 首页展示引导文字"这些是 AI 提炼的知识卡片示例，你可以审阅、编辑、确认"

### 16.3 预置 Demo 卡片内容

1. **不可变数据的核心价值是可读性**（insight）
2. **函数组合的本质是类型匹配**（method）
3. **选择 TypeScript 而不是 Flow**（decision）
4. **CQRS 模式适合读写分离的场景**（concept）

每张卡片都包含完整的 v2 字段，展示知识的价值。

## 17. Component Boundaries

### 17.1 当前组件

| Component | 问题 | v2 建议 |
|-----------|------|---------|
| `LibraryPage.tsx` | 过滤太密集，三列表格 | 简化为搜索 + sort + tag filter |
| `CardWorkspace.tsx` | pipeline 分组，7 个区域平铺 | 五层阅读路径 |
| `GraphNavigationPanel.tsx` | 14 种 edge，社区检测 | 重命名为 RelatedKnowledgePanel，3 种关系 |
| `ReviewPage.tsx` | 只有 approve/reject | 支持 5 种操作 |
| `TopicBrowser.tsx` | 基本可用 | 保持，增加 v2 字段展示 |

### 17.2 v2 新增组件

| Component | 职责 |
|-----------|------|
| `ValueHero.tsx` | 首屏展示区（标题 + takeaway + type + tags） |
| `InsightSection.tsx` | Core Insight 区域（默认展开） |
| `ContextSection.tsx` | Applicable Context 区域（默认折叠） |
| `PrincipleSection.tsx` | Reusable Principle 区域（默认展开） |
| `LimitationsSection.tsx` | Limitations & Caveats 区域（默认折叠） |
| `EvidenceSection.tsx` | Supporting Evidence 区域（默认折叠） |
| `RelatedKnowledgePanel.tsx` | 相关知识（替换 GraphNavigationPanel） |
| `TechnicalDetailsPanel.tsx` | 技术信息区（替换当前 details） |
| `ReviewActions.tsx` | 审阅操作按钮 |
| `EmptyState.tsx` | 空状态组件 |

### 17.3 组件复用

- `LibraryCardRow.tsx`：从 LibraryPage 中提取为独立组件
- `TagChip.tsx`：标签展示组件，多处复用
- `MarkdownRenderer.tsx`：Markdown 渲染，已存在
- `SourceLink.tsx`：来源链接，统一处理 URL 和 file_path

## 18. API Field Requirements

### 18.1 LibraryCardResponse

```typescript
interface LibraryCardResponse {
  id: string;
  title: string;
  status: 'ai_draft' | 'human_approved' | 'human_rejected';
  track: string;
  knowledge_type: 'concept' | 'claim' | 'insight' | 'method' | 'decision' | 'question' | 'evidence' | 'todo';
  one_sentence_takeaway: string | null;
  tags: string[];
  value_score: number | null;
  source_trace: {
    url: string | null;
    file_path: string | null;
  } | null;
  created_at: string;
  updated_at: string;
}
```

### 18.2 CardDetailResponse

```typescript
interface CardDetailResponse extends LibraryCardResponse {
  core_insight: string | null;
  applicable_context: string | null;
  reusable_principle: string | null;
  supporting_evidence: string | null;
  evidence_quotes: Array<{ text: string; context: string }> | null;
  limitations_or_caveats: string | null;
  next_actions: string[] | null;
  related_questions: string[] | null;
  human_note: string | null;
  source_excerpt: string | null;
  prompt_versions: Record<string, string> | null;
  stage_models: Array<{ stage: string; model: string }> | null;
  quality_score: number | null;
  quality_level: string | null;
  confidence: 'high' | 'medium' | 'low' | null;
  related_cards: Array<{
    card_id: string;
    title: string;
    knowledge_type: string;
    one_sentence_takeaway: string | null;
    relation: 'same_tag' | 'same_topic' | 'mentioned_by';
  }> | null;
}
```

### 18.3 Presenter 层变更

`build_library_card_response()` 需要：
- 添加 tags 字段
- 添加 knowledge_type 字段
- 添加 one_sentence_takeaway 字段
- 添加 source_trace 对象

`build_library_relationship_context()` 需要：
- 简化关系类型为 same_tag / same_topic / mentioned_by
- 移除社区检测结果展示
- 返回 related_cards 的一句話摘要

## 19. Test Recommendations

### 19.1 Unit Tests

- `test_library_card_response_includes_tags`：API 返回 tags
- `test_library_card_response_includes_takeaway`：API 返回 one_sentence_takeaway
- `test_library_card_response_includes_knowledge_type`：API 返回 knowledge_type
- `test_v1_card_fallback_in_v2_api`：v1 卡片正确 fallback

### 19.2 Component Tests

- `test_value_hero_renders_takeaway`：首屏展示一句话核心
- `test_core_insight_expanded_by_default`：核心洞察默认展开
- `test_applicable_context_collapsed_by_default`：适用场景默认折叠
- `test_related_knowledge_panel_renamed`：关系面板叫"相关知识"
- `test_related_knowledge_panel_3_relations`：只有 3 种关系类型
- `test_technical_details_at_bottom`：技术信息在页面底部
- `test_empty_state_library`：Library 空状态正确
- `test_empty_state_related_knowledge`：相关知识空状态正确

### 19.3 Integration Tests

- `test_library_page_simplified_filters`：过滤器简化正确
- `test_card_detail_five_layer_path`：详情页五层阅读路径正确
- `test_review_page_five_operations`：审阅页支持 5 种操作

## 20. Acceptance Criteria

1. Library 页面过滤器简化为搜索 + sort + tag filter
2. Library 卡片列表展示 title + type + takeaway + tags + source
3. Library 响应包含 tags、knowledge_type、one_sentence_takeaway 字段
4. Detail 页面首屏展示 title + takeaway + type + tags + source
5. Detail 页面五层阅读路径（价值首屏 → 应用信息 → 知识连接 → 人工协作 → 技术证据）
6. Core Insight 和 Reusable Principle 默认展开
7. 其他内容区域默认折叠
8. 技术信息在页面底部，默认折叠
9. 相关知识面板重命名为 RelatedKnowledgePanel，只展示 3 种关系
10. 关系不包装成"图谱"，明确标注"基于标签匹配"
11. 审阅页面支持 5 种操作（Confirm / Edit & Confirm / Downgrade / Merge / Discard）
12. human_note 只能由人填写
13. 空状态有引导文字和操作按钮
14. FakeProvider 输出有意义的 demo 内容
15. v1 卡片在 v2 前端下正常展示（fallback 规则生效）

## 21. Risks & Rollback Strategy

### 21.1 Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| 前端重构引入回归 | 现有页面损坏 | 分阶段部署 + 充分测试 |
| API 变更破坏旧客户端 | 移动端或其他客户端报错 | 新字段可选，旧字段保留 |
| 关系简化后相关内容变少 | "相关知识"区域太空 | 同标签/同主题仍然有内容，只是关系类型简化 |
| FakeProvider 输出仍然垃圾 | demo 体验差 | 精心编写 demo 模板 |
| 五层布局在小屏幕溢出 | 移动端体验差 | 响应式设计测试 |

### 21.2 Rollback Strategy

1. **前端 feature flag**：通过 feature flag 控制 v2 布局，回滚时切换回 v1
2. **API 向后兼容**：新字段添加到响应中，旧客户端忽略未知字段
3. **保留旧组件**：不删除 CardWorkspace.tsx，重命名为 CardWorkspaceV1.tsx
4. **新组件独立**：新增组件使用新文件名，不影响旧代码
5. **回滚步骤**：
   - 切换前端 feature flag 回 v1 布局
   - API 新字段保持不变（旧客户端忽略）
   - 不需要数据回滚
