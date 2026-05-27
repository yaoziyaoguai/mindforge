# Direction F: Structured Knowledge Workbench — Spec

日期: 2026-05-28
状态: active
输入: `docs/product/2026-05-28-001-mindforge-product-innovation-review.md` Direction F
授权: Direction F — Structured Knowledge Workbench, 无外部依赖, 无 embedding/RAG, 不改变审批边界

---

## Problem Frame

当前 Library 的组织能力仅限于 client-side 筛选（status/track/source_type/quality）和排序（newest/oldest/title/quality）。用户无法保存筛选视图、无法手动分组卡片、无法合并重复卡片、无法批量维护。Library 停留在"浏览已审批卡片"阶段，尚未升级为"结构化知识工作区"。

产品创新审计 Direction F 的核心洞察：**对 approved-only 知识卡片的结构化组织** 是 PKM 工具的差异化方向——Tana 有结构化但无 approval gate，MindForge 有 approval gate 但无结构化能力。两者结合是独特的。

## Scope Boundary

### In Scope (MVP — v0.8)

1. **Saved Views**: 保存/命名/切换 Library 筛选+排序组合，存储在 vault 本地文件
2. **Collections**: 手动/规则驱动的卡片分组，存储为 JSON sidecar
3. **Card Manual Linking**: 手动建立 related card 关系
4. **Bulk Maintenance**: 批量 tag、批量 track 修改

### Out of Scope

- 可视化 query builder（MVP 用 saved view 覆盖；query builder 是 v0.9）
- Card merge/split（需要 diff/conflict resolution，v0.9）
- Collections 自动规则 engine（MVP 仅手动 + 简单 tag-match 规则）
- 跨用户 shared views/collections（本地 only）
- 不改变 approval 语义
- 不新增依赖

## Architecture Constraint

```
library_service.py ──→ CardManager (cards dir)
              └──→ ViewStore (saved views JSON)
              └──→ CollectionStore (collections JSON)
              └──→ LinkStore (manual links JSON)

web_facade.py ──→ saved views API / collections API / bulk API
routers/library.py ──→ new GET/POST/DELETE endpoints
LibraryPage.tsx ──→ ViewSwitcher + CollectionPanel + BulkActions
```

所有数据存为 vault 内的 JSON sidecar 文件，不使用数据库，不改变 card 的 YAML frontmatter（除 manual links 追加到 source card frontmatter）。

## Implementation Units

### U1: Saved Views — Backend

**Goal**: 用户可保存当前筛选+排序状态为命名视图，可在视图间切换。

**Files**:
- CREATE `src/mindforge/services/view_store.py` — `SavedView` dataclass + `ViewStore` (CRUD)
- MODIFY `src/mindforge_web/services/web_facade.py` — 新增 `list_views()`, `save_view()`, `delete_view()`
- MODIFY `src/mindforge_web/routers/library.py` — 新增 3 个 endpoints

**SavedView schema**:
```python
@dataclass(frozen=True)
class SavedView:
    id: str  # kebab-case slug derived from name
    name: str  # 用户可见名称
    status_filter: str = "all"
    track_filter: str = "all"
    source_type_filter: str = "all"
    quality_filter: str = "all"
    sort_by: str = "newest"
    created_at: str = ""
```

**API**:
- `GET /api/library/views` → `{"views": [SavedView, ...]}`
- `POST /api/library/views` → `{"view": SavedView}` (body: partial SavedView)
- `DELETE /api/library/views/{view_id}` → `{"ok": true}`

**Storage**: `{vault}/.mindforge/views.json` — list of SavedView dicts

### U2: Saved Views — Frontend

**Goal**: LibraryPage 上方新增 ViewSwitcher dropdown + Save Current View 按钮。

**Files**:
- MODIFY `web/src/pages/LibraryPage.tsx` — 新增 ViewSwitcher 组件
- MODIFY `web/src/lib/i18n.ts` — 新增 views i18n keys
- CREATE `web/src/components/ViewSwitcher.tsx` — dropdown + save dialog

**Behavior**:
1. 默认视图: "All Cards"（built-in, 不可删除）
2. 筛选/排序调整后，Save Current View 按钮出现（状态与已保存视图不同时）
3. 视图切换：加载已保存的筛选+排序参数到 URL searchParams
4. 删除确认：dialog 确认（仅对用户创建的视图）

### U3: Collections — Backend

**Goal**: 用户可创建命名集合（Collection），手动添加/移除卡片，或按 tag 规则自动匹配。

**Files**:
- CREATE `src/mindforge/services/collection_store.py` — `Collection` dataclass + `CollectionStore`
- MODIFY `web_facade.py` — `list_collections()`, `create_collection()`, `add_to_collection()`, `remove_from_collection()`, `delete_collection()`
- MODIFY `routers/library.py` — 5 个新 endpoints

**Collection schema**:
```python
@dataclass(frozen=True)
class Collection:
    id: str
    name: str
    description: str = ""
    card_refs: tuple[str, ...] = ()  # card refs (relative paths)
    rule_tags: tuple[str, ...] = ()  # 简单 tag-match 规则
    created_at: str = ""
```

**API**:
- `GET /api/library/collections` → `{"collections": [...]}`
- `POST /api/library/collections` → `{"collection": Collection}`
- `POST /api/library/collections/{id}/cards` → add card refs
- `DELETE /api/library/collections/{id}/cards` → remove card refs
- `DELETE /api/library/collections/{id}` → delete collection

**Storage**: `{vault}/.mindforge/collections.json`

### U4: Collections — Frontend

**Goal**: LibraryPage 侧栏新增 Collections 列表，可展开查看集合内卡片。

**Files**:
- CREATE `web/src/components/CollectionPanel.tsx` — 侧栏集合列表 + 添加弹窗
- MODIFY `web/src/pages/LibraryPage.tsx` — 集成 CollectionPanel
- MODIFY `web/src/lib/i18n.ts` — collections i18n keys

**Behavior**:
1. LibraryPage 侧栏显示 Collections（可折叠）
2. 在 "..." 菜单中可 "添加到集合"
3. 创建集合：名称 + 可选 description

### U5: Bulk Maintenance

**Goal**: 支持多选卡片后批量修改 tag/track。

**Files**:
- CREATE `web/src/components/BulkActions.tsx` — 批量操作 toolbar
- MODIFY `web/src/pages/LibraryPage.tsx` — 多选模式
- MODIFY `web_facade.py` — `bulk_update_cards()`
- MODIFY `routers/library.py` — `POST /api/library/bulk-update`

**API**:
- `POST /api/library/bulk-update` → body: `{card_refs: [...], set_tags: [...], set_track: "..."}`

**Behavior**:
1. 长按/checkbox 进入多选模式
2. 选中卡片后出现 BulkActions toolbar：修改 tags、修改 track
3. 操作后刷新列表

### U6: Manual Card Linking

**Goal**: 用户可手动关联两张 approved 卡片。

**Files**:
- MODIFY `library_service.py` — `link_cards(card1_ref, card2_ref, reason="manual")`
- MODIFY `web_facade.py` — `link_cards()`
- MODIFY `routers/library.py` — `POST /api/library/cards/link`
- MODIFY `web/src/components/CardDetail.tsx` — Related Cards 区域

**Link schema**: 写入 card frontmatter 的 `related_cards` 字段（若已存在相关代码复用）

### U7: Tests

- `tests/test_view_store.py` — ViewStore CRUD tests
- `tests/test_collection_store.py` — CollectionStore tests
- `tests/test_web_facade_bulk.py` — bulk update tests
- `web/src/components/__tests__/ViewSwitcher.test.tsx`
- `web/src/components/__tests__/CollectionPanel.test.tsx`
- `web/src/components/__tests__/BulkActions.test.tsx`
- `tests/test_web_product_copy.py` — 新增 i18n key 验证

### U8: i18n

zh/en keys: ~30 个（views, collections, bulk actions, card linking）

## Verification

每个 unit 完成后的 gate:
- Python: `ruff check src/ tests/` → `python -m pytest tests/ -q`
- Frontend: `npm --prefix web run build` + `npm --prefix web run test -- --run`
- Product copy: `python -m pytest tests/test_web_product_copy.py -q`

## Non-Goals

- 不构建可视化 query builder（by design — MVP 用 saved views 覆盖 80% 场景）
- 不实现 card merge/split（v0.9）
- 不改变 approval-first 边界
- 不引入新数据库或外部依赖
