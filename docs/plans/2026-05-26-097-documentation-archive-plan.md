# Documentation Archive Plan

**日期**: 2026-05-26
**状态**: draft
**输入**: v4.6 Documentation System Simplification
**说明**: 本计划描述 MindForge 文档系统的文件级归档策略。当前阶段不执行任何文件移动，本计划为未来归档操作提供参考。

---

## 背景

v4.6 确立了 index-first, no-moves 的文档简化策略：不移动文件、不删除历史证据、不改写历史内容，通过 `docs/README.md` 和 `docs/dev/documentation-inventory.md` 建立导航层。

当文档数量继续增长时，文件级归档（`docs/archive/` 目录）将变得必要。本计划定义了归档的触发条件、执行策略和候选清单。

---

## 归档触发条件

满足以下任一条件时考虑执行归档：

1. `docs/implementation-notes/` 超过 80 个文件
2. `docs/plans/` 中 historical plans 超过 20 个
3. 新贡献者反馈找不到正确的 canonical docs
4. 文档导航层（README + inventory）不足以消除疑惑

---

## 归档策略

### 原则

1. **最小移动** — 只移动明确标记为 archive candidate 的文件
2. **保留链接** — 在原位置留下 redirect note 或更新所有引用
3. **不改写** — 移动到 archive 的文件保持原内容不变
4. **索引导航** — archive 目录有自己的 README 解释归档原因

### 目录结构

```
docs/
├── archive/                         # 新建目录
│   ├── README.md                    # 归档说明
│   ├── plans/                       # 归档的历史 plans
│   ├── specs/                       # 归档的历史 specs
│   ├── implementation-notes/        # 归档的早期实现笔记
│   ├── design/                      # 归档的早期设计文档
│   └── adr/                         # 归档的被取代 ADR
├── README.md                        # 更新以反映新结构
├── dev/
│   ├── documentation-inventory.md   # 更新以反映移动
│   └── documentation-debt-ledger.md # 更新以记录归档操作
└── ...
```

### 迁移方法

对于每个移动的文件：
1. 在原位置创建同名 `.md` 文件，内容为 redirect note：
   ```markdown
   > **Archived**: This document has been moved to `docs/archive/<path>`. It is preserved as historical evidence and does not represent current product capabilities.
   ```
2. 将原文件移动到 `docs/archive/<path>`
3. 更新 `docs/README.md` 和 `docs/dev/documentation-inventory.md`
4. 更新 `docs/dev/documentation-debt-ledger.md` 记录操作

---

## Archive Candidates

### Priority 1: 明确过时的路线图和计划

这些文件描述的是已完全被取代的产品方向：

- ~~`docs/plans/2026-05-21-001-feat-dogfood-readiness-plan.md`~~ — 已删除（docs cleanup batch 1, 2026-05-27）
- ~~`docs/plans/2026-05-22-001-feat-real-llm-dogfood-plan.md`~~ — 已删除（docs cleanup batch 1, 2026-05-27）
- `docs/plans/2026-05-22-002-feat-web-ux-improvement-plan.md` — v0.x Web UX 改进计划
- `docs/plans/2026-05-24-003-feat-web-polish-planning-review.md` — v0.x Web 打磨
- `docs/plans/2026-05-24-004-v0_3-wrapup-v0_4-planning-review.md` — v0.3→v0.4 过渡
- `docs/plans/2026-05-24-005-v1_0-next-phase-planning-review.md` — v1.0 早期方向
- `docs/plans/2026-05-24-039-v1_0-completion-review.md` — v1.0 完成审查
- `docs/plans/2026-05-24-040-v1_0-gate-evidence-audit.md` — v1.0 gate 审计
- `docs/plans/2026-05-24-041-v1_1_to_v1_5-multi-stage-roadmap.md` — v1.x 路线
- `docs/plans/2026-05-24-042-v1_1-quality-baseline.md` — v1.1 质量基线
- `docs/plans/2026-05-25-059-v2_0_to_v2_5-long-horizon-roadmap.md` — v2.x 路线
- `docs/plans/2026-05-25-070-v2_0_to_v2_5-independent-delivery-audit.md` — 早期审计
- `docs/plans/2026-05-25-071-v3_0_to_v3_6-long-horizon-roadmap.md` — v3.x 路线
- `docs/plans/2026-05-25-080-v3_7_to_v4_1-graph-view-ontology-roadmap.md` — Graph 路线（已 superseded）

### Priority 2: 历史规格文件

全部 `docs/specs/` 目录（19 个文件）均为历史规格，不代表当前实现状态。

### Priority 3: 早期实现笔记

`docs/implementation-notes/` 中 2026-05-24 及之前的文件（~50 个）是早期执行记录。

### Priority 4: 早期设计文档

- ~~`docs/design/roadmap/V0_2_ROADMAP.md`~~ — 已删除（docs cleanup batch 1, 2026-05-27）
- ~~`docs/design/roadmap/V0_3_KNOWLEDGE_QUALITY_AND_NAVIGATION_ROADMAP.md`~~ — 已删除（docs cleanup batch 1, 2026-05-27）
- `docs/design/sdd/` 下剩余 SDD 文档（SDD_KNOWLEDGE_QUALITY 已删除）
- `docs/design/rfc/` 下 4 个 RFC 文档
- ~~`docs/design/tdd/TDD_KNOWLEDGE_QUALITY_AND_NAVIGATION.md`~~ — 已删除（docs cleanup batch 1, 2026-05-27）

---

## 不归档的文件

以下文件即使年代较早也**不归档**，因为它们在当前文档系统中承担活跃角色：

| 文件 | 原因 |
|------|------|
| `docs/audits/2026-05-25-v2.0-v3.6-independent-audit.md` | 独立审计证据，gate baseline 来源 |
| `docs/audits/2026-05-25-v4_2-post-remediation-red-team-re-audit.md` | v4.2 复审审计，当前质量基线来源 |
| `docs/adr/2026-05-24-001-retrieval-backend.md` | 当前检索后端决策仍有效 |
| `docs/adr/2026-05-24-002-kuzu-graph-backend.md` | Kùzu DB 选择决策仍有效 |
| `docs/adr/2026-05-25-003-retrieval-quality-baseline.md` | 检索质量基线仍有效 |
| `docs/adr/2026-05-25-004-graph-query-capability-gap-analysis.md` | 差距分析仍有效 |
| `docs/adr/2026-05-25-005-extension-plugin-boundary.md` | 扩展边界决策仍有效 |
| `docs/plans/2026-05-25-087-post-stabilization-direction.md` | 当前仍活跃的产品方向 |
| `docs/plans/2026-05-25-089-product-main-path-dogfood-plan.md` | 当前仍活跃的 dogfood 计划 |
| `docs/plans/2026-05-25-094-next-deepening-roadmap.md` | 当前活跃路线图 |

---

## 执行计划

| Phase | 内容 | 预估影响 |
|-------|------|---------|
| Phase 1 | 创建 `docs/archive/` 目录结构和 README | 低 |
| Phase 2 | 迁移 Priority 1 (14 early plans) | 中 — 需检查交叉引用 |
| Phase 3 | 迁移 Priority 2 (19 specs) | 中 — 需检查交叉引用 |
| Phase 4 | 迁移 Priority 3 (~50 early impl notes) | 高 — 文件数量多 |
| Phase 5 | 迁移 Priority 4 (11 design docs) | 低 |

建议 Phase 1+2 一起执行，Phase 3-5 分批执行。

---

## 风险和缓解

| 风险 | 缓解措施 |
|------|---------|
| 链接断裂 | 在原位置留 redirect note；更新 docs/README.md 和 inventory |
| Git 历史丢失 | 使用 `git mv` 保留历史 |
| 交叉引用遗漏 | 迁移前 grep 检查所有引用 |
| 过度归档 | 保留不归档文件清单，不归档仍活跃文档 |

---

## 当前状态

**本计划为 draft，不在此轮执行。** 文件移动等待单独 spec 和 review。
当前阶段（v4.6）仅执行 index-first 策略：通过 docs/README.md、documentation-inventory.md、superseded status notes 和 documentation-debt-ledger.md 建立导航层。
