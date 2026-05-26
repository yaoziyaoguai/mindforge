# Documentation Inventory

**日期**: 2026-05-26
**状态**: v4.6 documentation simplification
**说明**: 本文档分类 MindForge `docs/` 下所有文档目录，帮助判断哪些是 canonical、哪些是 historical/superseded/archive candidate。

---

## 文档目录分类

| Path Pattern | Count | Purpose | Current Status | Owner Area | Notes |
|-------------|-------|---------|---------------|------------|-------|
| `README.md` | 1 | 产品入口 | **canonical** | Product | 能力、限制、安全边界、Lab/Internal 表 |
| `docs/README.md` | 1 | 文档入口 | **canonical** (new) | Docs | v4.6 新增，指向所有 canonical docs |
| `docs/en/` | 5 | 英文用户文档 | **canonical** | User Docs | user-guide, getting-started, model-setup, sources, troubleshooting |
| `docs/zh-CN/` | 9 | 中文用户文档 | **canonical** | User Docs | user-guide + 8 专题文档 |
| `docs/dev/` | 11 | 开发者文档 | **canonical** (核心 7 个) + **active** (docs-reset-index, quality-baseline) | Dev | architecture, engineering-workflow, quality-debt-ledger 等 |
| `docs/internal/` | 3 | 内部规则/契约 | **canonical** | Product | product-contracts, development rules, roadmap ledger |
| `docs/audits/` | 3 | 独立审计报告 | **canonical** (current) + **historical** (v2.0-v3.6 audit) | Quality | current-capability-map 是最新 |
| `docs/plans/` | 17 | 阶段计划 | **active** (094, 089, 087) + **historical** (其余) | Planning | 仅 094/089/087 是当前活跃计划 |
| `docs/specs/` | 17 | 功能规格 | **historical** | Engineering | 实现可能已偏离，不代表当前能力 |
| `docs/implementation-notes/` | 68 | 实现记录 | **active** (最新 5 个) + **historical** (其余) | Engineering | 按日期排序；2026-05-25 之后的更接近当前状态 |
| `docs/adr/` | 7 | 架构决策记录 | **current** (001-005) + **superseded** (006-007) | Architecture | 006/007 已被 v4.2 truth reset 修正 |
| `docs/design/` | 14 | 设计文档 | **historical/reference** | Design | RFC/SDD/roadmap 是设计阶段的产物 |
| `docs/research/` | 1 | 行业研究 | **active** | Research | 093 行业对标分析 |
| `docs/dogfood*.md` | 2 | Dogfood 指南 | **active** | Quality | dogfood.md + dogfood-runbook.md |
| `docs/real-llm-dogfood.md` | 1 | 真实 LLM opt-in 指南 | **active** | User Docs | Web-first 的 opt-in 验证指南 |
| `docs/RELEASE_NOTES.md` | 1 | 发布说明 | **active** | Release | release notes |

---

## Archive Candidates

以下文档组可在未来归档（当前保留以便历史追溯，**本轮不实际移动**）：

### 早期 plans

- `docs/plans/2026-05-21-001-feat-dogfood-readiness-plan.md` — 早期 dogfood 准备计划
- `docs/plans/2026-05-22-001-feat-real-llm-dogfood-plan.md` — 早期真实 LLM dogfood 计划
- `docs/plans/2026-05-22-002-feat-web-ux-improvement-plan.md` — v0.x Web UX 改进计划
- `docs/plans/2026-05-24-003-feat-web-polish-planning-review.md` — v0.x Web 打磨
- `docs/plans/2026-05-24-004-v0_3-wrapup-v0_4-planning-review.md` — v0.3→v0.4 过渡
- `docs/plans/2026-05-24-005-v1_0-next-phase-planning-review.md` — v1.0 早期方向
- `docs/plans/2026-05-24-039-v1_0-completion-review.md` — v1.0 完成审查
- `docs/plans/2026-05-24-040-v1_0-gate-evidence-audit.md` — v1.0 gate 审计
- `docs/plans/2026-05-24-041-v1_1_to_v1_5-multi-stage-roadmap.md` — v1.x 路线（已过时）
- `docs/plans/2026-05-24-042-v1_1-quality-baseline.md` — v1.1 质量基线
- `docs/plans/2026-05-25-059-v2_0_to_v2_5-long-horizon-roadmap.md` — v2.x 路线（已过时）
- `docs/plans/2026-05-25-070-v2_0_to_v2_5-independent-delivery-audit.md` — 早期审计（已被后续取代）
- `docs/plans/2026-05-25-071-v3_0_to_v3_6-long-horizon-roadmap.md` — v3.x 路线（已过时）
- `docs/plans/2026-05-25-080-v3_7_to_v4_1-graph-view-ontology-roadmap.md` — v3.7-v4.1 Graph 路线（已被 v4.2 truth reset + superseded note）

### 早期 specs

全部 `docs/specs/` 目录（17 个文件）均为历史规格，不代表当前实现状态。实现可能已显著偏离。

### 早期 implementation notes

- 2026-05-22 至 2026-05-24 的大部分 implementation notes（~50 个文件）是早期执行记录，不代表当前 canonical docs。

### 早期 design docs

- `docs/design/roadmap/V0_2_ROADMAP.md` — v0.2 路线（已过时）
- `docs/design/roadmap/V0_3_KNOWLEDGE_QUALITY_AND_NAVIGATION_ROADMAP.md` — v0.3 路线（已过时）
- `docs/design/sdd/` 下 4 个 SDD 文档 — 设计产物，不代表当前实现
- `docs/design/rfc/RFC_0003_LEGACY_DOC_EVALUATION.md` — 历史遗留文档评估

### 早期 internal

- `docs/internal/V0_2_DEVELOPMENT_RULES.md` — v0.2 开发规则（已被更新的开发规则取代）
- `docs/internal/V0_3_DEVELOPMENT_RULES.md` — v0.3 开发规则（已被更新的开发规则取代）

---

## Superseded Docs Candidates

以下文档包含已被 v4.2 truth reset 修正的能力声明。大多数已在 `docs/dev/docs-reset-index.md` 中列出：

### 已标记 superseded (in docs-reset-index.md)

- `docs/adr/2026-05-25-007-graph-backend-decision.md` — 8 NodeType 声明已追记修正
- `docs/adr/2026-05-25-006-graph-ontology-v1.md` — ontology 仅 4/8 已实现
- `docs/plans/2026-05-25-080-v3_7_to_v4_1-graph-view-ontology-roadmap.md` — Graph/Sensemaking 全能力路线已降级
- `docs/implementation-notes/2026-05-25-085-v4_1-graph-backend-decision.md` — 8 NodeType 已追记修正

### 额外 superseded candidates（本轮可标记）

这些文档包含 Graph/Sensemaking/Community 的扩展描述，可能被误解为当前能力：

- `docs/implementation-notes/2026-05-25-082-v3_8-graph-view-mvp.md` — 描述 vis-network 图可视化（含 8 种 NodeType UI 渲染），当前仅 4 种正式支持
- `docs/implementation-notes/2026-05-25-081-v3_7-graph-ontology.md` — Graph Ontology v1 实现笔记（定义 8 种类型，仅实现 4 种）
- `docs/implementation-notes/2026-05-25-084-v4_0-sensemaking-workspace.md` — Sensemaking 描述为"知识理解工作台"，实际是 lab/internal
- `docs/implementation-notes/2026-05-25-083-v3_9-entity-resolution.md` — Entity Resolution 描述，实际仅 ConceptCandidate 检测
- `docs/implementation-notes/2026-05-25-075-v3_3-community-topic-sensemaking.md` — Community/Topic/Sensemaking 描述
- `docs/implementation-notes/2026-05-24-045-v1_2-u3-knowledge-community.md` — Knowledge Community 早期实现（实际已被收缩）
- `docs/implementation-notes/2026-05-25-049-v1_4-w2-knowledge-community-browser.md` — Community Browser 描述

---

## Lab/Internal Docs

这些文档描述 lab/internal 功能，不是主产品路径：

| 文档 | 功能 | 状态 |
|------|------|------|
| `docs/implementation-notes/2026-05-25-084-v4_0-sensemaking-workspace.md` | Sensemaking Workspace | lab |
| `docs/implementation-notes/2026-05-25-083-v3_9-entity-resolution.md` | Entity Resolution / ConceptCandidate | lab |
| `docs/implementation-notes/2026-05-25-082-v3_8-graph-view-mvp.md` | Graph View MVP (vis-network) | internal |
| `docs/implementation-notes/2026-05-25-081-v3_7-graph-ontology.md` | Graph Ontology v1 | internal (ontology 定义, 4/8 已实现) |
| `docs/implementation-notes/2026-05-25-085-v4_1-graph-backend-decision.md` | GraphRepository + ADR-007 | internal |
| `docs/implementation-notes/2026-05-25-075-v3_3-community-topic-sensemaking.md` | Community/Topic/Sensemaking | lab |
| `docs/implementation-notes/2026-05-25-078-v3_6-safe-extensibility-plugin-boundary.md` | Extension Plugin boundary | lab |
| `docs/design/sdd/SDD_WIKI_WEB_PRESENTATION_ADDENDUM.md` | Wiki web presentation (含 Graph 扩展) | reference/lab |

---

## 未在此轮移动或删除任何文件

本轮 v4.6 的文档简化策略是 **index-first, no-moves**：
- 不移动任何文件到 `archive/` 目录
- 不删除任何文件
- 不修改任何文件的 frontmatter/content（superseded notes 除外）
- 不改写历史内容
- 通过 `docs/README.md` 和本文档建立导航/分类层

未来如果需要进行文件级归档（如 `docs/archive/` 目录），建议单独 spec。
