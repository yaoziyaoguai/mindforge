# Documentation Reset Plan

**日期**: 2026-05-27
**状态**: active — Loop 1 完成（canonical state + progress ledger），待执行 batch 1 cleanup

---

## 1. Strategy

本轮采用 **index-first, small-batch cleanup** 策略：
- 不一口气清理 100 个文档
- 每批 5-10 个文件，确认无断裂引用后执行
- 已标记 superseded 的不重复处理
- 删除/归档前必须 `rg` 确认引用

---

## 2. Current Canonical Docs (2026-05-27)

以下文件是当前 canonical，不可删除/移动：

| 文件 | 角色 |
|------|------|
| `docs/dev/CURRENT_PROJECT_STATE.md` | Agent 第一入口 |
| `docs/dev/progress-ledger.md` | 进度台账 |
| `docs/dev/architecture.md` | 架构概览 |
| `docs/dev/engineering-workflow.md` | 工程规范 |
| `docs/dev/quality-debt-ledger.md` | 质量债 |
| `docs/dev/documentation-inventory.md` | 文档清单 |
| `docs/dev/documentation-debt-ledger.md` | 文档债 |
| `docs/README.md` | 文档入口 |
| `docs/zh-CN/user-guide.md` | 中文用户指南 |
| `docs/en/user-guide.md` | 英文用户指南 |
| `README.md` | 项目入口 |
| `.claude/commands/mf-autopilot.md` | Autopilot 规则 |

---

## 3. Cleanup Batches

### Batch 1: Obvious Stale Docs (8 个)

这些文件是最明显的过时文档，由后续版本完全取代：

| # | 文件 | 原因 | 行动 |
|---|------|------|------|
| 1 | `docs/design/roadmap/V0_2_ROADMAP.md` | v0.2 路线，已被 v0.3+ 取代 | 删除 |
| 2 | `docs/design/roadmap/V0_3_KNOWLEDGE_QUALITY_AND_NAVIGATION_ROADMAP.md` | v0.3 路线，已被后续取代 | 删除 |
| 3 | `docs/design/tdd/TDD_KNOWLEDGE_QUALITY_AND_NAVIGATION.md` | 早期 TDD 文档，不再使用 | 删除 |
| 4 | `docs/design/sdd/SDD_KNOWLEDGE_QUALITY_AND_NAVIGATION.md` | v0.3 SDD，已被实现取代 | 删除 |
| 5 | `docs/internal/V0_2_DEVELOPMENT_RULES.md` | v0.2 开发规则，已被取代 | 删除 |
| 6 | `docs/internal/V0_3_DEVELOPMENT_RULES.md` | v0.3 开发规则，已被取代 | 删除 |
| 7 | `docs/plans/2026-05-21-001-feat-dogfood-readiness-plan.md` | 早期 dogfood plan，已被执行并取代 | 删除 |
| 8 | `docs/plans/2026-05-22-001-feat-real-llm-dogfood-plan.md` | 早期真实 LLM plan，已被取代 | 删除 |

### Batch 2: Archive Candidates (待下一轮)

保留不作删除，仅标记 historical。已在 documentation-inventory.md 中列出。

### Batch 3: Already Superseded (已标记，无需处理)

这些文档已有 superseded status note 或 truth reset 注释，无需额外处理。详见 `docs/dev/documentation-debt-ledger.md`。

---

## 4. Docs to Rewrite (待定)

| 文件 | 问题 | 优先级 |
|------|------|--------|
| `docs/dev/documentation-inventory.md` | 日期停在 2026-05-26，需更新 | P3 |
| `docs/dev/documentation-debt-ledger.md` | 需反映本轮 docs reset 进展 | P3 |
| `README.md` docs 导航区 | 可加入 CURRENT_PROJECT_STATE.md 引用 | P3 |

---

## 5. Execution Rules

- 删除前 `rg <文件名> docs/ README.md .claude/ --files-with-matches`
- 如果被引用，先修复引用或标记 superseded
- 每次 batch 后跑 `git diff --check` + `ruff check docs/`
- 每次 batch 后单独 commit
- 在 progress-ledger.md 记录每批结果
