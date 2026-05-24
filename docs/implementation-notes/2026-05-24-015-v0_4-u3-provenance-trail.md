# v0.4 U3 Provenance Trail 实现笔记

## 日期
2026-05-24

## 目标
在 Card Detail 页面展示知识溯源面包屑：来源 → 兄弟卡片 → Wiki Sections。

## 实现方案

### Backend

**新增 API endpoint**：`GET /api/library/trail?ref=<card_ref>`

**数据来源**：基于已实现的 Related Cards 和 Wiki Related Sections，做确定性聚合：

1. **Source**：从 `CardSummary.source_title` 获取来源标题
2. **Sibling Cards**：从 Related Cards 中筛选 `same_source` 关系的卡片（最多 5 张），展示其 quality 信息
3. **Wiki Sections**：聚合 self + siblings 的 wiki_sections，按卡片数排序（最多 5 个 section）

**Schemas**（`schemas.py`）：
- `ProvenanceTrailSource` — source_id, source_title
- `ProvenanceTrailSiblingCard` — card_id, title, quality_level, quality_score
- `ProvenanceTrailSection` — title, card_count
- `ProvenanceTrailResponse` — card_id, source, sibling_cards, wiki_sections

**Service**（`web_facade.py`）：
- `provenance_trail(self, ref)` — 入口方法，调用 `_provenance_trail_response(cfg, detail)`
- `_provenance_trail_response()` — 确定性聚合逻辑
- 关键修复：`detail.card` 是 `LibraryCard` 类型，需通过 `card.summary` 访问 `CardSummary` 的 `source_id`/`source_title`

**Router**（`routers/library.py`）：
- `provenance_trail()` endpoint，返回 `ProvenanceTrailResponse`
- card 不存在时返回 404

### Frontend

**API 层**：
- `web/src/api/library.ts`：`getProvenanceTrail(ref)` 函数
- `web/src/api/types.ts`：TypeScript 类型定义

**组件**（`CardWorkspace.tsx`）：
- 新增 `ProvenanceTrail` 组件，水平面包屑展示：
  - Source（灰色标签）
  - → Sibling Cards（可点击导航，标注 quality）
  - → Wiki Sections（标注卡片数）
- 通过 `useEffect` 在 ref 变化时 fetch
- 当 `trail` 数据为空时，面包屑自动隐藏

**i18n**：10 个新 key（zh/en）：trail 标题、来源、兄弟卡片、sections、空状态

## 关键设计决策

1. **不做 RAG/embedding/vector DB**：完全基于已存在的 Related Cards API 和 Wiki Section 数据，做确定性聚合
2. **不调用真实 LLM**：所有数据均为本地确定性计算
3. **与 U1/U2 复用数据**：trail 调用的 related cards 和 wiki sections 是 U1/U2 已实现并缓存的
4. **空状态优雅降级**：如果 source_title 为空或没有 sibling cards / wiki sections，面包屑自动隐藏而不显示空容器

## 边界处理

- Card 不存在 → 404 user_error
- source_title 为 None → 不显示 source 部分
- sibling_cards 为空 → 不显示箭头和 sibling 区域
- wiki_sections 为空 → 不显示 sections 区域

## 已知限制

- 当 card 无 Related Cards 且无 wiki_sections 时，整个 trail 面包屑不显示
- same_source 关系依赖 U2 的 Related Cards API 已正确返回该 reason

## 测试覆盖

- `tests/test_web_product_copy.py`：现有 copy test 通过（包括 card_detail 页面的 header_block 和 provenance 相关内容）
- Browser smoke：手动确认面包屑正确渲染，Source、Sibling Cards、Wiki Sections 均可见
