# v4.6 Documentation Debt Closure (Loop 3 补充) — Implementation Notes

**日期**: 2026-05-26
**输入**: v4.6 Documentation System Simplification Loop 3
**状态**: completed

---

## 执行摘要

在 v4.6 L1-L3 的 index-first 文档简化基础上，补完 Loop 3 的 superseded 标记覆盖范围，并补齐缺失的文档债基础设施（documentation-debt-ledger、documentation-archive-plan）。

### Commits

| Loop | Commit | Description |
|------|--------|-------------|
| L3 补充 | (pending) | docs: v4.6 docs debt closure — superseded notes + ledger + archive plan |

---

## Loop 3 补充: 额外 Superseded 标记

### 背景

v4.6 Loop 3 已为 4 个高风险 Graph/Sensemaking/Entity/GraphBackend 文档添加了 status note，另有 2 个文档已有 v4.2 truth reset 注释。但 `docs/dev/documentation-inventory.md` 中列出了 7 个额外 superseded candidates，其中 2 个 Knowledge Community 相关文档尚未标记：

- `docs/implementation-notes/2026-05-24-045-v1_2-u3-knowledge-community.md`
- `docs/implementation-notes/2026-05-25-049-v1_4-w2-knowledge-community-browser.md`

### 修改

为上述 2 个文件添加了 v4.6 status note，说明：
- 这是历史实现记录
- Knowledge Community features 是 lab/internal
- 不在主产品路径中
- 见 docs/README.md 和 docs/dev/docs-reset-index.md

### Superseded 覆盖完整性

至此，全部 11 个 Graph/Sensemaking/Entity/Community/GraphBackend 高风险旧文档均已有适当的 status 标记：

| # | 文件 | 标记来源 |
|---|------|---------|
| 1 | `adr/007-graph-backend-decision.md` | v4.2 truth reset |
| 2 | `adr/006-graph-ontology-v1.md` | v4.2 truth reset |
| 3 | `plans/080-v3_7_to_v4_1-graph-view-ontology-roadmap.md` | v4.2 truth reset |
| 4 | `impl-notes/085-v4_1-graph-backend-decision.md` | v4.6 L3 |
| 5 | `impl-notes/081-v3_7-graph-ontology.md` | v4.6 L3 |
| 6 | `impl-notes/083-v3_9-entity-resolution.md` | v4.6 L3 |
| 7 | `impl-notes/075-v3_3-community-topic-sensemaking.md` | v4.6 L3 |
| 8 | `impl-notes/082-v3_8-graph-view-mvp.md` | v4.2 truth reset (已有) |
| 9 | `impl-notes/084-v4_0-sensemaking-workspace.md` | v4.2 truth reset (已有) |
| 10 | `impl-notes/045-v1_2-u3-knowledge-community.md` | v4.6 本轮 |
| 11 | `impl-notes/049-v1_4-w2-knowledge-community-browser.md` | v4.6 本轮 |

---

## 新建: Documentation Debt Ledger

### `docs/dev/documentation-debt-ledger.md`

文档债台账，包含：

1. **文档债策略** — 重申 index-first, no-moves 五项原则
2. **Superseded 文档追踪** — 9 + 2 个已标记文档的完整表格（含标记日期和修正后状态）
3. **Historical/Archive Candidate 文档** — 按目录分类的候选清单
4. **开放文档债** — 4 个 P3 项（DOC-01~DOC-04）
5. **已解决文档债** — 5 个已解决项（DOC-R1~DOC-R5）

---

## 新建: Documentation Archive Plan

### `docs/plans/2026-05-26-097-documentation-archive-plan.md`

文档归档计划（draft），定义未来文件级归档的完整策略：

1. **触发条件** — 4 个客观条件
2. **归档策略** — 最小移动、保留链接、不改写、索引导航
3. **目录结构** — `docs/archive/` 按子目录组织
4. **迁移方法** — redirect note + git mv + 更新索引
5. **Archive Candidates** — 4 个优先级分组（14+19+50+11 个文件）
6. **不归档清单** — 10 个仍活跃的历史文件
7. **执行计划** — 5 个 Phase
8. **风险缓解** — 链接断裂、Git 历史、交叉引用、过度归档

---

## 更新: docs/README.md

在开发者文档区域新增 2 个条目：
- `docs/dev/documentation-inventory.md` — 完整文档清单 + 分类
- `docs/dev/documentation-debt-ledger.md` — 文档债台账 + superseded 追踪

在当前路线图区域新增 1 个条目：
- `docs/plans/2026-05-26-097-documentation-archive-plan.md` — 文档归档计划（draft）

---

## 更新: docs/dev/documentation-inventory.md

- 更新 `docs/dev/` 计数: 11 → 13
- 更新 `docs/plans/` 计数: 17 → 18
- 更新活动 plans: 094/089/087 → 094/089/087/097
- 标记全部 7 个额外 superseded candidates 为已标记
- 新增"本轮新增文件"和"本轮状态标记补充"子节

---

## 设计决策

- **index-first, no-moves 策略不变** — 本轮仍不移动或删除任何文件
- **archive plan 为 draft** — 明确标注为 draft，不在本轮执行文件移动
- **debt ledger 与 quality-debt-ledger 分开** — 质量债台账追踪代码/测试/性能债，文档债台账追踪文档系统债，各司其职
- **superseded note 格式一致** — 所有 status note 使用统一的 `> **Status note (v4.6 docs simplification, 2026-05-26)**:` 格式

---

## 未做事项

- 文件级归档（`docs/archive/` 创建和文件移动）
- 英文 docs/README.md 翻译
- `docs/adr/` 旧 ADR 的 "当前状态" 更新（DOC-02）
- `docs/design/` 过时设计文档清理（DOC-03）

---

## Gate Results

| Gate | Command | Exit Code | Timeout | Notes |
|------|---------|-----------|---------|-------|
| git diff | `git diff --check` | 0 | no | Clean |
| ruff (docs/) | `ruff check docs/` | 0 | no | No Python files in docs/ |

---

## 硬红线遵守

- 未移动或删除任何文件
- 未修改历史内容（仅添加 non-destructive status notes）
- 未读取 `.env` 或 secrets
- 未调用真实 LLM、Cubox、Upstage 或外部服务
- 未处理真实私人资料
- 未写真实 Obsidian vault
- 未做 RAG/embedding/vector DB
- 未新增大型依赖
- 未破坏 explicit approval / human_approved 语义
- 未恢复 Graph/Sensemaking/Entity/Community 扩张

---

## v4.6 文档系统简化 — 最终状态

| 组件 | 文件 | 状态 |
|------|------|------|
| Canonical docs 入口 | `docs/README.md` | completed (v4.6 L1) |
| 文档清单 | `docs/dev/documentation-inventory.md` | completed (v4.6 L2) |
| Superseded 标记 | 11 个高风险旧文档 | completed (v4.6 L3 + 本轮) |
| 文档债台账 | `docs/dev/documentation-debt-ledger.md` | completed (本轮) |
| 归档计划 | `docs/plans/2026-05-26-097-documentation-archive-plan.md` | completed (本轮) |
| 实现笔记 | `docs/implementation-notes/2026-05-26-096-v4_6-documentation-system-simplification.md` | completed (v4.6) |
| 本轮实现笔记 | `docs/implementation-notes/2026-05-26-107-v4_6-docs-debt-closure.md` | completed (本轮) |

v4.6 Documentation System Simplification — **全部完成**。
