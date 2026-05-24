---
title: MindForge v0.6 — Search & Discovery Spec
type: feat
status: spec
date: 2026-05-24
roadmap: V0_6_SEARCH_DISCOVERY
parent: 2026-05-24-022-v0_6-next-phase-planning-review.md
---

# v0.6: Search & Discovery

## 1. Background

v0.3-v0.5 建立了完整的知识质量层、关系体验层和 Dogfood 就绪链路。当前搜索体验停留在 v0.2 的 BM25 关键词搜索——无过滤、无分组、无排序。

Library 中的卡片数增长后，线性浏览和单一关键词搜索不可持续。用户需要按 status、source、tags 等维度过滤和分组搜索结果，才能高效导航知识库。

**v0.6 的核心命题**：不引入外部搜索引擎或向量 DB，在现有 BM25 + 卡片元数据基础上叠加过滤、分组、排序，让搜索从"关键词匹配"升级为"多维探索"。

## 2. Goals

1. **Search Filter Panel** — status / source / tags 多选过滤，URL query params 持久化，组合过滤
2. **Search Results Grouping** — 按 status 或 source 分组展示搜索结果
3. **Search Sorting** — relevance / date / quality score 排序选项
4. **Wiki Search Integration** — Wiki 页面内 section 搜索
5. **Search UX Polish** — 空状态引导、loading skeleton、error states

## 3. Non-Goals

- 不做向量搜索 / semantic search / embedding
- 不做 Elasticsearch / Meilisearch / Typesense 等外部搜索引擎
- 不做 RAG / vector DB
- 不修改 BM25 核心算法
- 不新增大型依赖
- 不做跨语言搜索或 NLP 分词升级

## 4. Safety Constraints

| # | 约束 | 验证方式 |
|---|------|---------|
| S1 | 不做 embedding / vector DB | code review |
| S2 | 不调用真实 LLM | code review |
| S3 | 搜索过滤不泄露卡片 body 内容（仅返回元数据） | code review |
| S4 | URL query params 不包含敏感信息 | code review |
| S5 | 向后兼容现有 Recall API | test |

## 5. Implementation Units

### S1: Search Filter Panel

**Goal**: Library 页面添加过滤面板，支持 status/source/tags 多选过滤。

**Scope**:
- 过滤栏 UI：水平 chip/tag 组，每个维度一组
- Status 过滤: ai_draft / human_approved / archived 等
- Source 过滤: 按 source path 分组
- Tags 过滤: 从现有卡片元数据提取所有 tags
- URL query params 持久化: `?status=human_approved&source=reading-notes/`
- 组合过滤: 多个维度 AND 逻辑
- Active filter count badge
- "Clear all filters" 按钮

**Files**: `web/src/pages/LibraryPage.tsx`, `web/src/components/LibraryFilterPanel.tsx` (new), `web/src/api/library.ts`

### S2: Search Results Grouping

**Goal**: 搜索结果按 status 或 source 分组展示。

**Scope**:
- Group-by 选择器: "None" / "Status" / "Source"
- 分组 UI: 每个 group 显示 label + count badge + 折叠/展开
- Default expanded: 前 3 个 group 展开，其余折叠
- 空 group 不展示
- Group 内保持现有排序

**Files**: `web/src/pages/LibraryPage.tsx`, `web/src/components/LibrarySearchResults.tsx` (可能 new)

### S3: Search Sorting

**Goal**: 搜索结果支持多种排序方式。

**Scope**:
- 排序选择器: "Relevance" (default) / "Date (newest)" / "Date (oldest)" / "Quality (high-low)"
- Relevance: 现有 BM25 score
- Date: `updated_at` 或 `created_at`
- Quality: quality score（已有 CardQuality API）
- Sort order 持久化到 URL query params

**Backend**:
- Recall API 新增 `sort_by` 和 `sort_order` query params
- `sort_by`: `relevance` | `updated_at` | `created_at` | `quality`
- `sort_order`: `asc` | `desc`

**Files**: `web/src/pages/LibraryPage.tsx`, `src/mindforge_web/routers/recall.py`, `src/mindforge/recall/`

### S4: Wiki Search Integration

**Goal**: Wiki 页面内搜索 section。

**Scope**:
- Wiki 页面顶部添加 section 搜索输入框
- 实时过滤: 输入关键词后实时过滤 section 列表
- 高亮匹配文本
- "No sections match" 空状态
- 不影响现有 Wiki 页面结构和导航

**Files**: `web/src/pages/WikiPage.tsx`, `web/src/components/WikiSectionSearch.tsx` (new)

### S5: Search UX Polish

**Goal**: 覆盖搜索路径的 loading、empty、error states。

**Scope**:
- Loading skeleton for search results
- Empty state with guidance ("No cards match your search. Try different keywords or clear filters.")
- Error state with retry button
- Debounced search input (300ms)
- Search input 保留光标位置（不因 re-render 丢失焦点）

**Files**: `web/src/pages/LibraryPage.tsx`

## 6. Verification

### Gate Matrix

| Unit | ruff | pytest | npm build | product copy | git diff | browser smoke |
|------|------|--------|-----------|-------------|----------|---------------|
| S1 Filter Panel | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| S2 Grouping | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| S3 Sorting | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| S4 Wiki Search | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| S5 UX Polish | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### Browser Smoke Checklist

- [ ] `/library` — 过滤面板渲染、chip 可点击、URL params 更新
- [ ] `/library` — 搜索结果分组展示、折叠/展开
- [ ] `/library` — 排序选择器可切换
- [ ] `/library` — 空状态/loading/error states
- [ ] `/wiki` — section 搜索实时过滤
- [ ] 0 console errors
- [ ] 0 API 5xx

## 7. Dependencies

- 无新外部依赖
- 依赖现有 Recall API (BM25)
- 依赖现有 Card metadata (status, source, tags, quality scores)

## 8. References

- Parent review: `docs/specs/2026-05-24-022-v0_6-next-phase-planning-review.md`
- v0.5 spec: `docs/specs/2026-05-24-011-v0_5-dogfood-readiness-spec.md`
- Engineering workflow: `docs/dev/engineering-workflow.md`
