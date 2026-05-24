# v0.4 U2 Card Relationship Panel — Implementation Notes

**Date:** 2026-05-24
**Spec:** `docs/specs/2026-05-24-009-v0_4-knowledge-relationship-experience-spec.md` §5 U2
**Status:** implemented

## 已完成内容

### U2 — Card Relationship Panel 增强

将 `CardWorkspace.tsx` 中的 `RelatedCardsStrip`（简单水平滚动列表）升级为 `RelatedCardsPanel`（按 RelationReason 分组展示）。

### 变更

- **`web/src/components/CardWorkspace.tsx`**: 新增 `RelatedCardsPanel` 组件，替换原 `RelatedCardsStrip`
  - 按 `relation.reason` 分组展示（same_source、same_tag、same_wiki_section、same_review_batch、source_location_neighbor）
  - 每组显示关系类型标题 + 卡片数量 badge
  - 每个 related card 显示 title + source type icon + quality dot indicator
  - 空状态时显示引导文案（`library.related_empty_guide`）
  - 同一张卡片如果有多条不同 reason，会在多个分组中复用出现

- **`web/src/lib/i18n.ts`**: 新增 12 个 i18n key（zh + en）
  - 5 个 reason group 标题 key（`library.related_group_*`）
  - 1 个空状态引导 key（`library.related_empty_guide`）

### 关键设计决策

- **为什么分组而非排序**：按 RelationReason 分组能让用户快速扫描"这张卡片有哪些类型的关联"，比平铺列表更易理解知识关系结构
- **为什么多 reason 卡片在多个组中复用**：用户在不同关系维度下都能发现这张卡片，避免"同源组里找不到同标签的关联卡片"
- **为什么不新增后端/API**：已有 `/api/library/{id}` 返回的 `related_cards` 数据（`RelatedCardEdge.reason`）足够前端分组使用
- **为什么每 reason 组不过滤重复卡片**：排序已施加 per-reason cap（backend 各 reason ≤5），分组不做额外截断

### Tests

no new Python tests — 纯前端 UI 改动，覆盖路径：
- `test_web_product_copy.py` — `test_related_cards_do_not_show_strength` 已适配（断言 `r.label` 仍在 source 中）
- `test_web_product_copy.py` — 全部 50 tests pass
- Browser smoke — 验证分组展示和空状态

## 修改文件

| 文件 | 变更 |
|------|------|
| `web/src/components/CardWorkspace.tsx` | +55 / -44 — `RelatedCardsStrip` → `RelatedCardsPanel` |
| `web/src/lib/i18n.ts` | +12 i18n keys |

## Gate 验证

| Gate | Result |
|------|--------|
| `npm --prefix web run build` | exit 0 |
| `ruff check src/ tests/test_wiki_related_sections.py` | All checks passed |
| `python -m pytest tests/test_web_product_copy.py -q` | 50/50 pass |
| `git diff --check` | exit 0 |
