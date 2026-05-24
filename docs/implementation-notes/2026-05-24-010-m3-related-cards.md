# M3 Related Cards — Implementation Notes

**Date:** 2026-05-24
**Spec:** `docs/design/roadmap/V0_3_KNOWLEDGE_QUALITY_AND_NAVIGATION_ROADMAP.md` §7
**Status:** implemented (squash-merged into main via PR #7, commit `9e813d2`)

## 合并说明

M3 未生成独立 spec 文件和独立 commit，而是与 M5、M6 及 Wiki LLM Synthesis 一起通过 squash merge (PR #7) 进入 main。原因：M3/M5/M6 共享同一批卡片数据的索引结构（source_index, tag_index, section_index），在 `feat-wiki-llm-synthesis` 分支上作为关系/健康/图谱三层一起实现，squash merge 保持了这三层的原子一致性。

## 已完成内容

M3 实现了确定性 Related Cards 计算引擎。不做 semantic similarity，不引入 embedding，全部 in-memory。

### 关系类型

`src/mindforge/relations/related_cards.py` (196 lines) 定义 6 种 RelationReason：

| Reason | Strength | 匹配逻辑 |
|--------|----------|---------|
| `SAME_SOURCE` | 0.8 | source_id 相同 |
| `SAME_WIKI_SECTION` | 0.7 | wiki_sections 交集 |
| `SAME_TAG` | 0.5 | tags 交集 |
| `SOURCE_LOCATION_NEIGHBOR` | 0.4 | 同 source 的相邻位置 |
| `SAME_REVIEW_BATCH` | 0.3 | 同 run_id 或 review_batch |
| `MANUAL_LINK` | 1.0 | reserved — v0.3 不发出此边类型 |

### 关键设计决策

- **种类上限**: 每种 reason 最多返回 5 条边，防止一张热门卡片淹没整个关系面板
- **Library context 过滤**: `context="library"` 时仅匹配 human_approved 卡片；`context="review"` 包含 pending
- **确定性优先**: 所有关系基于字段精确匹配，无排序模型、无向量相似度、无 embedding

### API 暴露

- Web API endpoint 在 `routers/library.py` 中暴露 related cards 数据
- 前端 `CardDetailPage.tsx` 展示 Related Cards 面板

## 修改文件

| 文件 | 变更 |
|------|------|
| `src/mindforge/relations/related_cards.py` | new (196 lines) |
| `src/mindforge/relations/__init__.py` | new |
| `tests/relations/test_related_cards.py` | new (13 tests) |

## Gate 验证

| Gate | Result |
|------|--------|
| `ruff check src/` | All checks passed |
| `python -m pytest tests/relations/test_related_cards.py -q` | 13/13 pass |
| `git diff --check` | exit 0 |
