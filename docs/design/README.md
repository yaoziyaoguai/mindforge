# Design Documents

MindForge 设计文档索引。

---

## 目录结构

```
docs/design/
├── README.md          # 本文件
├── rfc/               # Request for Comments
│   ├── RFC_0001_SOURCE_ADAPTER_V2.md
│   ├── RFC_0002_WIKI_PRESENTATION_V2.md
│   └── RFC_0003_LEGACY_DOC_EVALUATION.md
├── sdd/               # Software Design Documents
│   ├── SDD_SOURCE_ADAPTER_V2.md
│   ├── SDD_WIKI_PRESENTATION_V2.md
│   └── SDD_WIKI_WEB_PRESENTATION_ADDENDUM.md
├── roadmap/           # Roadmap (V0_2_ROADMAP.md removed 2026-05-27 — docs cleanup batch 1)
└── adr/               # Architecture Decision Records (预留)
```

---

## RFC

| 编号 | 标题 | 说明 |
|------|------|------|
| RFC 0001 | Source Adapter V2 | 多源格式归一化方案 |
| RFC 0002 | Wiki Presentation V2 | Wiki 展示层设计 |
| RFC 0003 | Legacy Doc Evaluation | 旧文档评估与清理 |

## SDD

| 编号 | 标题 | 说明 |
|------|------|------|
| SDD Source Adapter V2 | Source Adapter 详细设计 | Adapter 接口与注册 |
| SDD Wiki Presentation V2 | Wiki 展示详细设计 | 数据模型和视图 |
| SDD Wiki Web Addendum | Wiki Web 展示补充 | 前端组件和 API 契约 |

## Roadmap

- ~~V0.2 Roadmap~~ — 已删除（docs cleanup batch 1, 2026-05-27）。当前路线参见 `docs/dev/CURRENT_PROJECT_STATE.md` §6

---

## 文档角色

- **RFC**：方案讨论和决策记录。回答"为什么这样设计"。
- **SDD**：详细设计，面向实现。回答"具体怎么做"。
- **Roadmap**：迭代规划和时间线。回答"什么时候做"。
- **ADR**：架构决策记录。回答"为什么选 A 不选 B"。

---

## 当前状态说明 (v4.6+, updated v3.7)

> **Historical/Reference Status**: 本目录下的 RFC（4 个）和 SDD（3 个）均为 2026-05-14 至 2026-05-17 期间的设计阶段产物（Draft 状态），不代表当前实现。实现可能已显著偏离设计文档的描述。这些文件作为设计讨论的历史证据保留，不应被理解为当前 canonical docs。
>
> **活跃文档**: 2026-05-26 的设计方向文档（102/104/105）和 target architecture map（100）是较新的设计决策，但其状态以 `CURRENT_PROJECT_STATE.md` 为准。
>
> **Obsidian Binding**: `obsidian-binding-design.md` 描述的功能（Obsidian vault 写入）是 MindForge 明确非目标（参见 `CURRENT_PROJECT_STATE.md` §4）。该文档保留作为早期设计讨论的历史证据。
