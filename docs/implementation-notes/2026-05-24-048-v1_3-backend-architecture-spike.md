# v1.3 Local Backend Architecture Spike — Summary

## 日期
2026-05-24

## 状态
Complete — 无需实现变更

## 评估结论

v1.3 对三个后端方向进行了重新评估：

### 检索后端：BM25 vs SQLite FTS5 vs DuckDB FTS

| 方案 | 结论 |
|------|------|
| 纯 Python BM25（现状） | **保持**。100 卡索引构建 ~30ms，查询 < 10ms |
| SQLite FTS5 | 触发条件不满足（卡片数 < 500，索引构建 < 500ms）。RetrievalPort 已就绪，未来可直接插拔 |
| DuckDB FTS | **不采用**。重依赖（~30MB），OLAP 引擎用于全文检索是大材小用 |

### 图后端：In-Memory vs Kuzu

| 方案 | 结论 |
|------|------|
| In-Memory DeterministicGraphBuilder（现状） | **保持**。100 卡 2-hop 图构建 24.5ms，社区检测 0.1ms |
| Kuzu Embedded Graph DB | 触发条件不满足（卡片数 < 2000，查询 < 500ms）。GraphPort 已就绪，未来可直接插拔 |

### 关键指标

| 指标 | 实测值（100 卡） | 阈值 |
|------|-----------------|------|
| 2-hop 图构建 | 24.5ms | 200ms |
| 社区检测 | 0.1ms | — |
| BM25 查询 | < 10ms | 200ms |

## 更新的文档

- ADR-001: 状态 Proposed → Accepted，新增 v1.3 benchmark
- ADR-002: 状态 Proposed → Accepted，新增 v1.3 benchmark

## 决策

**不做任何后端变更。** 当前纯 Python 方案在现有规模（< 200 卡）下性能充裕。两个 ADR 均已 Accepted，定义了明确的未来触发条件和迁移路径。
