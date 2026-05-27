# Docs Reset Index

**日期**: 2026-05-25
**状态**: v4.2.1 partial remediation closure

v4.2 truth reset 后，docs 被分为 canonical / superseded / lab-internal / archive-candidate。
本文档是 reset 后的索引，帮助读者快速定位正确文档。

---

## Canonical Current Docs

这些文档反映当前真实产品状态，建议优先阅读：

| 文档 | 说明 |
|------|------|
| `README.md` | 产品入口：能力、限制、安全边界、Lab/Internal 功能表 |
| `docs/zh-CN/user-guide.md` | 中文用户指南（含当前 Graph 4 NodeType 描述） |
| `docs/en/user-guide.md` | 英文用户指南 |
| `docs/dev/architecture.md` | 当前代码架构（已修正不存在的文件引用） |
| `docs/dev/quality-debt-ledger.md` | 质量债台账 + 可重现 gate baseline |
| `docs/dev/engineering-workflow.md` | 工程工作流规范 |
| `docs/dev/copy-policy.md` | UI copy 规范 |
| `docs/internal/product-contracts.md` | 产品安全契约 |
| `docs/plans/2026-05-25-087-post-stabilization-direction.md` | v4.2 后产品方向（推荐 Product Main Path Dogfood） |
| `docs/audits/2026-05-25-v4_2-post-remediation-red-team-re-audit.md` | v4.2 复审审计（score 5.5/10, No-Go for feature expansion） |
| `docs/implementation-notes/2026-05-25-086-v4_2-red-team-stabilization.md` | v4.2 稳定化实现笔记（最完整的状态记录） |
| `docs/implementation-notes/2026-05-25-088-v4_2_1-partial-remediation-closure.md` | v4.2.1 PARTIAL 闭合实现笔记 |

---

## Superseded Graph/Sensemaking Docs

这些文档包含 v4.2 truth reset 前对 Graph/Sensemaking 能力的过度声明。
已添加 "v4.2 truth reset 追记" 标记，保留为 historical planning artifacts：

| 文档 | 原声明 | 追记后状态 |
|------|--------|-----------|
| `docs/adr/2026-05-25-007-graph-backend-decision.md` | 8 NodeType workload 已验证 | 追记: 仅 4 NodeType 已实现 |
| `docs/adr/2026-05-25-006-graph-ontology-v1.md` | 8 NodeType ontology | 追记: ontology 定义有效，但仅 4 种已实现 |
| `docs/plans/2026-05-25-080-v3_7_to_v4_1-graph-view-ontology-roadmap.md` | Graph/Sensemaking 全能力路线 | 追记: 已降级为 lab/internal, historical |
| `docs/implementation-notes/2026-05-25-085-v4_1-graph-backend-decision.md` | 8 NodeType (已追记修正) | v4.2 追记已说明实际支持状态 |

---

## Lab/Internal Docs

这些文档描述的功能属于 lab/internal/experimental，不是 MindForge 主产品路径：

| 文档 | 功能 | 状态 |
|------|------|------|
| `docs/implementation-notes/2026-05-25-084-v4_0-sensemaking-workspace.md` | Sensemaking Workspace | lab, 已从主导航隐藏 |
| `docs/implementation-notes/2026-05-25-083-v3_9-entity-resolution.md` | Entity Resolution / ConceptCandidate | lab, 不支持自动升级 |
| `docs/implementation-notes/2026-05-25-082-v3_8-graph-view-mvp.md` | Graph View MVP (vis-network) | internal, 仅 Library GraphExplorer 入口 |
| `docs/implementation-notes/2026-05-25-081-v3_7-graph-ontology.md` | Graph Ontology v1 | ontology 定义, 4/8 已实现 |

---

## Future Archive Candidates

以下文档可考虑在未来 docs reset 中归档（当前保留以便历史追溯）：

- `docs/plans/2026-05-24-041-v1_1_to_v1_5-multi-stage-roadmap.md` — v1.x 路线（已过时）
- `docs/plans/2026-05-25-059-v2_0_to_v2_5-long-horizon-roadmap.md` — v2.x 路线（已过时）
- `docs/plans/2026-05-25-071-v3_0_to_v3_6-long-horizon-roadmap.md` — v3.x 路线（已过时）
- `docs/plans/2026-05-25-070-v2_0_to_v2_5-independent-delivery-audit.md` — 早期审计（已被后续审计取代）
- `docs/plans/2026-05-24-040-v1_0-gate-evidence-audit.md` — v1.0 gate audit（已被后续审计取代）

归档策略：不要大规模移动文件以避免链接炸裂。可在文件顶部添加 "archived: see docs/dev/docs-reset-index.md" 标记。

---

## What Not To Reference As Current

- 不要引用 Graph 支持 8 种 NodeType 为当前状态（实际仅 4 种）
- 不要引用 Sensemaking 为成熟产品能力（实际是 LAB/INTERNAL）
- 不要引用 Entity Resolution 为 production-ready（实际是 ConceptCandidate 检测）
- 不要引用 v4.3 / Graph expansion / Community/Topic graph 为实现中的功能
