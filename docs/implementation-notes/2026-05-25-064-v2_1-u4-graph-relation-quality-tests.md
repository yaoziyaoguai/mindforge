---
title: "v2.1 U4 Graph Relation Quality Tests — Implementation Note"
date: 2026-05-25
status: Complete
version: v2.1
---

# v2.1 U4 Graph Relation Quality Tests — Implementation Note

## What was done

v2.1 U4 新增 graph relation 质量守护测试，覆盖 golden tests、edge cases 和性能特征化。

### Golden Tests (`tests/relations/test_graph_golden.py`)

31 个 golden/edge case tests，验证确定性关系的精确正确性：

**compute_multi_hop_related_cards golden tests (7 tests):**
- `test_golden_1hop_from_c1` — 固定 5-card fixture 的 1-hop 邻居验证
- `test_golden_1hop_exact_count` — 固定输入 → 固定边数
- `test_golden_2hop_from_c1` — 2-hop 遍历 path 验证
- `test_golden_1hop_determinism` — 相同输入两次 → 相同输出
- `test_golden_backward_compat` — compute_related_cards() == multi_hop(max_depth=1)
- `test_golden_strength_decay_2hop` — 2-hop 边强度衰减
- `test_golden_via_path_present` — via_path 路径可见性

**detect_communities golden tests (7 tests):**
- community count、source/tag 成员精确验证、质量评分范围、确定性、hierarchy 和 overlap 检测

**assemble_discovery_context golden tests (4 tests):**
- reasoning 文本精确性、token 估计、确定性、direct/neighbor 分类正确性

**Edge case tests (9 tests):**
- 空 card、单 card、不存在 center、自引用防护、全连接图、无共享属性
- 空 community、min_members 阈值、缺少 id 字段、无 card 节点图、center 缺失 fallback

**Cross-function determinism (1 test):**
- related_cards 和 communities 对同一数据的一致性验证

### Performance Characterization (`tests/relations/test_graph_perf.py`)

8 个性能特征化测试：

- 100/500/1000 cards multi-hop related cards 性能基线
- 100/500/1000 cards community detection 性能基线
- 100 nodes discovery context assembly 性能基线
- 100 次重复调用的性能一致性（无内存泄漏/GC spike）

性能阈值设定为宽松上限（100 cards < 500ms, 500 cards < 2000ms, 1000 cards < 3000ms），允许未来性能回归检测。

## Changes

- `tests/relations/test_graph_golden.py` — +31 tests (NEW)
- `tests/relations/test_graph_perf.py` — +8 tests (NEW)

## Design Rationale

- **Golden tests ≠ property tests**：验证精确输出值，不是仅验证属性
- **固定 seed=42**：性能测试使用确定性的随机数据生成，确保可复现
- **宽松性能阈值**：避免 CI 环境波动导致的 flaky tests，阈值远高于实测值
- **全部 deterministic**：不调用 LLM、不做 embedding、不依赖外部服务

## Non-goals

- 不修改任何 source code
- 不引入 benchmark 框架（pytest-benchmark）
- 不设严格的性能 SLA（仅建立基线）
- 不做 stress testing（10k+ cards）

## Gates

- ruff check: exit 0 (All checks passed!)
- pytest full (~420+): exit 0, 100% pass
- npm build: exit 0
- product copy: exit 0
- git diff --check: exit 0
