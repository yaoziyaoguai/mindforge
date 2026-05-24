# v0.4 U1 Wiki Related Sections — Implementation Notes

**Date:** 2026-05-24
**Spec:** `docs/specs/2026-05-24-009-v0_4-knowledge-relationship-experience-spec.md` §5 U1
**Status:** implemented

## 已完成内容

### U1 — Wiki Related Sections

`compute_wiki_related_sections()` 基于 section 间共享 card 的 Jaccard overlap 计算 related sections：

```
Jaccard(A, B) = |cards(A) ∩ cards(B)| / |cards(A) ∪ cards(B)|
```

每个 section 返回 overlap 最高的前 3 个 related section。

### Backend
- `src/mindforge/wiki_service.py`: 新增 `compute_wiki_related_sections(section_card_map, top_n=3)` — 纯确定性计算，无 LLM/embedding
- `src/mindforge_web/routers/wiki.py`: 新增 `GET /api/wiki/related-sections` endpoint — 从 Wiki markdown 解析 section→card 映射后计算

### Frontend
- `web/src/api/wiki.ts`: 新增 `WikiRelatedSection` 和 `WikiRelatedSectionsResponse` 类型
- `web/src/pages/WikiPage.tsx`: 并行 fetch `/api/wiki/related-sections`
- `web/src/components/wiki/WikiReadingPane.tsx`: 接受并透传 `relatedSections` prop
- `web/src/components/wiki/WikiSection.tsx`: section heading 旁渲染 related sections 链接标签，复用已有 i18n key `wiki.related_sections`

### Tests
- `tests/test_wiki_related_sections.py`: 8 golden tests — 覆盖空 map、单 section、共享 card、top_n 限制、零共享、空 card 列表、Jaccard 精度

## 关键设计决策

- **为什么用 Jaccard 而非简单计数**：Jaccard 归一化了 section 大小差异。大 section（很多 cards）不会仅因为 card 多就主导 related sections 结果
- **为什么 top_n=3**：Web UI 中每个 section heading 旁的空间有限，3 个链接标签是可读性上限
- **为什么是独立 endpoint 而非嵌入 `/api/wiki/page`**：related sections 是纯 UI 增强数据，不影响 Wiki 内容本身；独立 endpoint 允许前端按需加载
- **为什么 section 间只比较共享 card**：不做 content similarity、不做 LLM-based 关系发现——保持确定性、可测试

## 修改文件

| 文件 | 变更 |
|------|------|
| `src/mindforge/wiki_service.py` | +58 `compute_wiki_related_sections()` |
| `src/mindforge_web/routers/wiki.py` | +32 `/api/wiki/related-sections` endpoint |
| `web/src/api/wiki.ts` | +12 TypeScript 类型 |
| `web/src/components/wiki/WikiReadingPane.tsx` | +10 接受/透传 relatedSections |
| `web/src/components/wiki/WikiSection.tsx` | +23 related sections 链接渲染 |
| `web/src/pages/WikiPage.tsx` | +9 fetch + 注入 relatedSections |
| `tests/test_wiki_related_sections.py` | new (8 tests) |

## Gate 验证

| Gate | Result |
|------|--------|
| `ruff check src/mindforge/wiki_service.py src/mindforge_web/routers/wiki.py` | All checks passed |
| `npm --prefix web run build` | exit 0 |
| `python -m pytest tests/test_wiki_related_sections.py -q` | 8/8 pass |
| `python -m pytest tests/test_web_product_copy.py -q` | all pass |
| `python -m pytest tests/ -q` | all pass (1 pre-existing failure) |
| `git diff --check` | exit 0 |
