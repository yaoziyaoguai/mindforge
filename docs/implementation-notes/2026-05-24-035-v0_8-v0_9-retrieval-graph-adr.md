# v0.8-v0.9 Retrieval & Graph Backend ADR 实现笔记

## 日期
2026-05-24

## 目标
完成 v0.8 Lexical Retrieval Foundation 和 v0.9 Local Graph Backend Spike 的架构决策。

## 产出

| 文档 | 决策 | 理由 |
|------|------|------|
| ADR-001 Retrieval Backend | 条件采用 SQLite FTS5，当前保持 BM25 | 零依赖（sqlite3 stdlib），持久化优势，BM25 当前规模足够 |
| ADR-002 Graph Backend | 暂不引入 Kuzu，保持 In-Memory | 无需编译依赖，当前规模 < 50ms，GraphPort 已就绪 |

## v0.8 完成状态

| Unit | 状态 | 产出 |
|------|------|------|
| U1 RetrievalPort | done | `src/mindforge/retrieval/` 包 + recall_service 重构 |
| U2 FTS5 Spike | deferred | ADR-001：触发条件未满足，暂不 spike |
| U3 ADR | done | `docs/adr/2026-05-24-001-retrieval-backend.md` |

## v0.9 完成状态

| Unit | 状态 | 产出 |
|------|------|------|
| U1 Kuzu Spike | deferred | ADR-002：触发条件未满足，暂不 spike |
| U2 Kuzu ADR | done | `docs/adr/2026-05-24-002-kuzu-graph-backend.md` |

## 已知限制

- FTS5/Kuzu spike 均被推迟，因为当前规模下纯 Python 实现性能足够
- 两套后端（FTS5/Kuzu）均可通过 RetrievalPort/GraphPort 插拔，架构上已预留扩展点

## 下一步

按 v0.7-v1.0 roadmap §4，下一阶段为 v1.0 Knowledge Workbench Experience。
v1.0 详细 SPEC 待制定（roadmap §4.6 标注为 v0.9 后完成）。
