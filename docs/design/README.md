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
├── roadmap/           # Roadmap
│   └── V0_2_ROADMAP.md
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

- [V0.2 Roadmap](roadmap/V0_2_ROADMAP.md) — v0.2 迭代计划

---

## 文档角色

- **RFC**：方案讨论和决策记录。回答"为什么这样设计"。
- **SDD**：详细设计，面向实现。回答"具体怎么做"。
- **Roadmap**：迭代规划和时间线。回答"什么时候做"。
- **ADR**：架构决策记录。回答"为什么选 A 不选 B"。
