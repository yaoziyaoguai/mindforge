---
title: "v2.1 U2 Multi-hop Relationship Expansion — Implementation Note"
date: 2026-05-25
status: Complete
version: v2.1
---

# v2.1 U2 Multi-hop Relationship Expansion — Implementation Note

## What was done

v2.1 U2 实现了 BFS 多层关系发现，替代原有的 1-hop `compute_related_cards()`。

### Core: BFS Multi-hop Traversal
- 新增 `compute_multi_hop_related_cards()` — 可配置深度的 BFS 关系发现
- 默认为 `max_depth=2`（2-hop），配置可扩展到 3-hop
- `compute_related_cards()` 保持向后兼容，委托给 `compute_multi_hop_related_cards(..., max_depth=1)`

### Path Visibility（via_path）
- 每条 edge 记录 `hop_distance` 和 `via_path`（中间卡片 ID 序列）
- 中心卡片到目标卡片的跳数完整可追溯
- 例如 c1→c2→c3：hop_distance=2, via_path=("c2",)

### Strength Decay
- `_HOP_DECAY = 0.7`：每增加 1 跳，强度乘以 0.7
- 2-hop 边的强度 = base_strength * 0.7
- 3-hop 边的强度 = base_strength * 0.49

### Refactoring
- `_build_indexes()` — 预建索引提取为共享函数（source/tag/section/batch/location）
- `_find_neighbors()` — 邻居发现提取为纯函数，复用预建索引
- `_RelationIndex` — 索引结构的 frozen dataclass

### Multi-reason Per Target
- BFS 允许同一 target 通过多个 reason 到达
- 只使用最短 hop 进展开（`visited_for_expansion`）
- 所有 reason edges 都保留（通过 `all_edges_by_target` 分组）

## Changes

- `src/mindforge/relations/related_cards.py` — BFS 实现 + 索引提取 + `RelatedCardEdge` 新字段
- `src/mindforge_web/schemas.py` — `RelatedCardReasonResponse` 增加 hop_distance/via_path
- `src/mindforge_web/services/web_facade.py` — 调用 `compute_multi_hop_related_cards(..., max_depth=2)`
- `web/src/api/types.ts` — TypeScript 类型同步
- `tests/relations/test_related_cards.py` — +11 tests (26 total)

## Design Rationale

- **BFS 保证最短路径**: visited 按 hop 递增记录，同一卡片在最早 hop 被发现
- **索引预建复用**: 所有 hop 共用同一组索引，避免每跳重建
- **自引用防护**: BFS 跳过 target == source_id（中间卡片匹配自身）和 target == center_id（回退到中心）
- **强度衰减**: 0.7 因子经验值，2-hop 仍有合理可见性，3-hop 显著衰减
- **不调用 LLM**: 所有计算均为确定性索引查找

## Non-goals

- 不做 semantic similarity-based expansion
- 不引入个性化 PageRank/graph embedding
- 不修改 GraphPort 接口
- 不做 real-time recommendation

## Gates

- ruff check: exit 0
- pytest full (380+): exit 0, 100% pass
- npm build: exit 0
- product copy: exit 0
- git diff --check: exit 0
