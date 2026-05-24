---
title: "v2.3 Optional Embedded Graph Backend Spike — Implementation Note"
date: 2026-05-25
status: Complete
version: v2.3
---

# v2.3 Optional Embedded Graph Backend Spike — Implementation Note

## What was done

v2.3 完成了 embedded graph backend 评估的边界形式化和 GraphPort 契约加固。

### U1: GraphPort Formalization

- 确认 `GraphPort` ABC 定义了 4 个抽象方法：`get_node`、`get_edges`、`get_graph`、`get_path`
- `DeterministicGraphBuilder` 正确实现 Port 接口
- 新增 `tests/relations/test_graph_port.py` — 9 个 Port contract tests：
  - 接口实现验证（isinstance、abstract 不可实例化）
  - 必需方法存在性验证（4 个 abstractmethod）
  - get_graph 返回类型验证
  - 空数据/确定性/get_path/get_edges 方向过滤验证

### U2: Graph Query Capability Gap Analysis

- 新增 `docs/adr/2026-05-25-004-graph-query-capability-gap-analysis.md`
- 盘点 8 种当前支持的图查询类型及复杂度
- 识别 5 类 In-Memory 方案限制，逐一评估是否需要 Kuzu
- 结论：无一满足 Kuzu 触发条件

### U3: Kuzu Spike

- 跳过（ADR-002 触发条件检查无一满足）

### U4: ADR-002 Refresh

- 更新 ADR-002，加入 v2.3 重新评估
- 对比 v1.3 vs v2.3 图查询能力变化（10 项增强）
- 更新推荐升级路径：networkx → SQLite-backed → Kuzu

## Changes

- `tests/relations/test_graph_port.py` — +9 tests (NEW)
- `docs/adr/2026-05-25-004-graph-query-capability-gap-analysis.md` — ADR-004 (NEW)
- `docs/adr/2026-05-24-002-kuzu-graph-backend.md` — v2.3 重新评估 (UPDATED)

## Design Rationale

- **不引入 Kuzu**：当前所有查询均 BFS-based + deterministic grouping，Kuzu 无边际收益
- **GraphPort 抽象保留**：9 个 contract tests 守护接口契约，未来可安全替换
- **升级路径明确**：networkx（算法）→ SQLite（持久化）→ Kuzu（最后手段）
- **Gap analysis 透明**：ADR-004 详细列出能力和限制，避免未来重复评估

## Non-goals

- 不做 Kuzu spike（无触发条件）
- 不引入任何新的图依赖
- 不修改 GraphPort 接口

## Gates

- ruff check: exit 0
- pytest full: exit 0, 100% pass
- npm build: exit 0
- product copy: exit 0
- git diff --check: exit 0
