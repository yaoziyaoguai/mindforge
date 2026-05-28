# Archived Documents

本目录包含历史设计文档和已归档的架构决策记录。这些文档**不代表**当前产品能力或承诺，仅作为设计讨论的历史记录保留。

---

## 已归档 ADR

| 文档 | 归档原因 |
|------|---------|
| ADR-002: Kuzu Graph Backend | Graph 是 lab/internal 功能，当前 In-Memory 方案已充分验证 |
| ADR-004: Graph Query Capability Gap | Graph 查询能力差距分析，lab 范围 |
| ADR-006: Graph Ontology v1 | 定义了 8 种 NodeType 但当前仅实现 4 种，内容可能误导 |
| ADR-007: Graph Backend Decision | Graph 后端 workload 验证，lab 范围 |

保留在主 docs/adr/ 的 ADR：001 (Retrieval Backend)、003 (Retrieval Quality Baseline)、005 (Extension Plugin Boundary)。

---

## 已归档设计文档

| 文档 | 归档原因 |
|------|---------|
| RFC 0001 + SDD Source Adapter V2 | 实施完成，历史设计记录 |
| RFC 0002 + SDD Wiki Presentation V2 | 实施完成，历史设计记录 |
| RFC 0003 Knowledge Quality & Navigation | 过期草案，包含 Graph/Sensemaking 等未实现功能的误导性声明 |
| RFC 0003 Legacy Doc Evaluation | 已解决，范围窄 |
| v2.0-v2.5 Changelog | 历史变更日志，当前为 v4.x |
| Web Design Shotgun Comparison (104) | 已被 105-final-web-design-decision 取代 |

---

## 注意

- 本目录中的文档**不作为产品承诺或 API 稳定性保证**
- 文档中描述的功能可能未实现、已移除或已重设计
- 以当前代码实现和产品主路径为准
- 主产品路径：Source/Import → ai_draft → Review → explicit approval → human_approved → Library → Recall (BM25) / Wiki (LLM synthesis) → Export
