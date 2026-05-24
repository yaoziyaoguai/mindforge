---
title: MindForge v0.4 — Knowledge Relationship Experience Spec
type: feat
status: spec
date: 2026-05-24
roadmap: V0_4_KNOWLEDGE_RELATIONSHIP_EXPERIENCE
---

# v0.4: Knowledge Relationship Experience

## 1. Background

v0.3 建立了知识质量层和导航层的基础设施：Card Quality scoring、Wiki Quality reports、Related Cards 计算引擎、Source Location/Provenance、Knowledge Health 报告、Local Graph Preview。但这些能力在用户体验层面是碎片化的——Related Cards 只是卡片详情页的一个列表、Local Graph Preview 是独立的预览区、Wiki 页面缺少 section 间导航、Knowledge Health 列出了问题但缺少可操作的探索路径。

**v0.4 的核心命题**：把这些已有的关系数据能力编织成连贯的"知识关系体验"，让用户从任意入口（卡片、Wiki、Health Report）都能沿着关系链路探索知识库。

## 2. Goals

1. **Wiki Related Sections** — 每个 Wiki section 展示关联的兄弟 section 和引用的卡片，让 Wiki 从"长页面"变成"可导航的知识网络"
2. **Card Relationship Panel 增强** — 从简单列表升级为分组展示、可点击跳转的关系面板
3. **Source Trail / Provenance Trail** — 从一张卡片出发，沿 source → sibling cards → wiki sections 构建可追溯的 provenance 链路
4. **Local Graph Lite** — 在现有 1-hop graph 基础上增强节点交互（click to navigate, hover preview）
5. **Knowledge Health 增强** — 为 orphan/low-quality/no-source/duplicate 问题提供一键跳转到相关卡片/关系的探索入口
6. **Relationship Tests & Browser Smoke** — 用 golden fixtures 和浏览器冒烟覆盖所有新增关系展示路径

## 3. Non-Goals

- 不做 RAG / embedding / vector DB
- 不做 full graph 大屏（不做 force-directed canvas、不做全局 graph exploration）
- 不调用真实 LLM
- 不处理真实私人资料
- 不写真实 Obsidian vault
- 不做 mail storage
- 不改变 approval / human_approved 安全语义
- 不新增 Python/npm 依赖（除非 spec 明确批准）
- 不做 semantic similarity based 关系发现
- 测试是支撑，不是 v0.4 主创新方向

## 4. Design Decisions

### 4.1 关系数据层复用

v0.4 不新建关系计算引擎。所有关系数据来源：
- `related_cards.py` → RelatedCardEdge（已存在）
- `local_graph.py` → GraphNode/GraphEdge（已存在）
- `health_service.py` → HealthIssue with affected_card_ids（已存在）
- `wiki_quality.py` → coverage/unused_cards/stale_sections（已存在）

v0.4 的工作是将这些已有数据编织成连贯的 UI 体验。

### 4.2 Wiki Related Sections 设计

每个 Wiki section 在渲染时计算 related sections（共享卡片最多的前 3 个 section），在 section heading 旁展示为可点击的链接标签。

```
## Section A  [Related: Section B, Section C]
```

数据来源：Wiki markdown 中的 WIKI_SECTION_START 标记 + card wiki_sections 字段。纯确定性计算，不需要 LLM。

### 4.3 Provenance Trail 设计

从一张卡片出发，沿以下链路展示 provenance trail：

```
Card → Source → Sibling Cards (same source) → Wiki Sections (that reference these cards)
```

每一步都是可点击的，用户沿链路探索。数据来自已有的 Related Cards 和 Wiki section references。

### 4.4 Local Graph Lite 增强

保持 1-hop 约束，增强节点交互：
- 节点 click → 导航到对应卡片/Wiki section
- 节点 hover → tooltip 预览（title + quality badge）
- Section 节点 → show referenced card count

不引入 force-directed layout、canvas、d3 或任何 graph visualization library。

### 4.5 Knowledge Health 增强

为每种 HealthIssue 的 affected_card_ids 提供一键跳转：
- orphan cards → 跳转到卡片详情，展示"为什么这张卡片是孤立的"（无 Wiki 引用 + 无 related cards）
- low-quality cards → 跳转到卡片详情，高亮 quality issues
- no-source cards → 跳转到卡片详情，展示 provenance 缺失提示
- duplicate candidates → 并排展示两张卡片，方便比较

## 5. Implementation Units

### U1. Wiki Related Sections

**Goal:** 每个 Wiki section 展示 related sections 导航

**Files:**
- Modify: `src/mindforge/wiki_service.py` — 新增 `compute_wiki_related_sections()` 函数
- Modify: `src/mindforge_web/routers/wiki.py` — 新增 `GET /api/wiki/related-sections` endpoint
- Modify: `web/src/api/wiki.ts` — TypeScript 类型 + API 调用
- Modify: `web/src/pages/WikiPage.tsx` — section heading 旁渲染 related sections 标签
- Modify: `web/src/lib/i18n.ts` — `wiki.related_sections` 已在 v0.3 添加，本次直接使用

**Approach:**
- 解析 Wiki markdown 中的 WIKI_SECTION_START 标记，提取每个 section 的 card 列表
- 计算 section 间的 Jaccard overlap（共享 card 比例）
- 每个 section 返回 overlap 最高的前 3 个 related section
- 前端在 section heading 旁渲染为可点击的 link 标签

**Verification:**
- Golden test: 已知 sections 和 card 分配 → 验证 related sections 排序正确
- Browser smoke: Wiki 页面每个 section 显示 related sections 链接

**Estimate:** ~60 LOC backend + ~40 LOC frontend

---

### U2. Card Relationship Panel 增强

**Goal:** 将 CardDetailPage 的 Related Cards 从简单列表升级为分组展示面板

**Files:**
- Modify: `web/src/pages/CardDetailPage.tsx` — 重构 related cards 渲染
- Modify: `web/src/lib/i18n.ts` — 新增关系面板相关 i18n keys

**Approach:**
- 按 RelationReason 分组（同源、同标签、同 Wiki Section 等）
- 每组显示关系类型标题 + 卡片列表 + 跳转链接
- 每个 related card 显示 title + quality badge
- 空状态：无 related cards 时显示引导文案

**Verification:**
- Browser smoke: 打开多关系的卡片 → 分组展示正确
- Browser smoke: 打开孤立卡片 → 显示空状态引导

**Estimate:** ~50 LOC frontend

---

### U3. Source Trail / Provenance Trail

**Goal:** 卡片详情页展示可点击的 provenance trail

**Files:**
- Modify: `src/mindforge_web/routers/library.py` — 新增 `GET /api/library/{card_id}/trail` endpoint
- Modify: `web/src/api/library.ts` — TypeScript 类型 + API 调用
- Modify: `web/src/pages/CardDetailPage.tsx` — 渲染 provenance trail breadcrumb
- Modify: `web/src/lib/i18n.ts` — 新增 trail 相关 i18n keys

**Approach:**
- Trail endpoint 返回：source → sibling cards (same source, ≤ 5) → wiki sections (that reference these cards, ≤ 5)
- 前端渲染为水平 breadcrumb 风格的 trail bar
- 每步可点击跳转

**Verification:**
- Golden test: 已知卡片 → source trail 链路正确
- Browser smoke: 卡片详情页展示 trail bar，点击跳转正确

**Estimate:** ~50 LOC backend + ~50 LOC frontend

---

### U4. Local Graph Lite 交互增强

**Goal:** 增强 LocalGraphPreview 组件的节点交互

**Files:**
- Modify: `web/src/components/LocalGraphPreview.tsx` — 节点 click/hover 交互
- Modify: `web/src/lib/i18n.ts` — 新增 graph 交互相关 i18n keys

**Approach:**
- 节点添加 `cursor-pointer` + `onClick` → navigate to card/section
- 节点添加 `title` attribute 或 hover tooltip → 显示 label + 附加信息
- Section 节点显示引用卡片数 badge
- 保持纯 CSS/HTML 渲染，不引入 vis.js/cytoscape/d3

**Verification:**
- Browser smoke: 点击 graph 节点 → 正确跳转
- Browser smoke: hover 节点 → tooltip 正确显示

**Estimate:** ~40 LOC frontend

---

### U5. Knowledge Health 增强 — 可操作探索入口

**Goal:** Health Report 中的每个 issue 提供跳转到相关卡片的探索入口

**Files:**
- Modify: `web/src/pages/HealthPage.tsx` — issue 卡片添加 "Explore" 按钮/链接
- Modify: `web/src/lib/i18n.ts` — 新增 health action 相关 i18n keys

**Approach:**
- orphan cards issue → "View orphan cards" 链接，跳转到 Library 并过滤
- low-quality cards issue → "Review low-quality cards" 链接
- no-source cards issue → "Check provenance" 链接
- duplicate candidates → "Compare duplicates" 链接
- 每个链接携带 card_ids 参数，Library 页面支持 `?cards=id1,id2` 过滤

**Verification:**
- Browser smoke: Health 页面每个 issue 有可点击的探索入口
- Browser smoke: 点击 → 跳转到 Library 并正确过滤

**Estimate:** ~40 LOC frontend

---

### U6. Relationship Golden Tests & Browser Smoke

**Goal:** 为所有新增关系展示路径添加 golden tests 和浏览器冒烟

**Files:**
- Create: `tests/test_v0_4_relationships.py` — golden tests for U1-U5
- Existing: 冒烟使用 Browser MCP

**Approach:**
- Golden fixtures: 构造已知 cards + wiki sections → 验证 related sections、trail、health explore links 正确
- Browser smoke: 使用 Browser MCP 验证所有 v0.4 页面和交互

**Verification:**
- 新 golden tests 全部通过
- Browser smoke 无 console error、无 4xx/5xx

**Estimate:** ~100 LOC tests

## 6. Dependencies

```
U1 (Wiki Related Sections) ──→ 独立，可最先实现
U2 (Relationship Panel)    ──→ 独立，可与 U1 并行
U3 (Provenance Trail)       ──→ 依赖 U2 的面板重构（共享 CardDetailPage）
U4 (Graph Lite Interactions)──→ 独立，可与 U1/U2 并行
U5 (Health Explore)         ──→ 独立
U6 (Tests & Smoke)          ──→ 在所有 UI 单元完成后执行
```

推荐执行顺序：U1 → U3 → U4 → U2 → U5 → U6

## 7. Gate Requirements

- `ruff check src tests` exit 0
- `pytest tests/test_v0_4_relationships.py -q` 全部通过
- `pytest tests/ -q` 全部通过（除已知前置失败 `test_sources_page_uses_source_path_view_not_raw_path_for_display_or_copy`）
- `npm --prefix web run build` exit 0
- `python -m pytest tests/test_web_product_copy.py -q` 全部通过
- `git diff --check` exit 0
- Browser MCP smoke: 所有 v0.4 页面无 console error、无网络 4xx/5xx

## 8. Risks

| Risk | Mitigation |
|------|------------|
| Wiki Related Sections 计算量大 | 只取 top 3，O(n*m) where n=sections, m=cards，可接受 |
| Provenance trail 链路断裂 | 每步独立渲染，缺失步骤不阻断整体展示 |
| Graph 节点过多导致 UI 拥挤 | 保持 1-hop 限制，每种关系类型最多 5 条边 |
| Health explore 跳转参数泄露敏感信息 | card_ids 只是数据库 id，不包含文件路径或内容 |
| 前端改动跨越太多页面 | 每个 U 独立实现、独立冒烟，减少交叉影响 |

## 9. Implementation Notes 要求

每个 U 实现后记录：
- 为什么选择这种交互方式（而非备选）
- 边界权衡（如 section 数量上限、trail 深度限制）
- 已知限制（如 Wiki section 解析对非标准格式的容忍度）
