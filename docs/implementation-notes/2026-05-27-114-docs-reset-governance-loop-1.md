# Docs Reset & Governance — Loop 1 Implementation Notes

- **Date**: 2026-05-27
- **Trigger**: `/mf-autopilot` — Documentation Reset Big Loop
- **Status**: Loop 1 (canonical state + progress ledger + autopilot upgrade)

---

## 1. Scope

本轮不是产品功能、UI polish、架构重构。本轮是项目治理、文档重置、进度账本、`/mf-autopilot` 升级。

### 本轮完成

1. **`docs/dev/CURRENT_PROJECT_STATE.md`** — 新增。项目当前状态文件，所有 agent 的第一入口。包含 7 个必需 section: repo snapshot, product identity, real capabilities (4 tiers), non-goals, open debts, recommended next loops, autopilot entry rules。
2. **`docs/dev/progress-ledger.md`** — 新增。进度台账，追踪所有 completed loops、active workstream、next recommended loop、update rules。
3. **`.claude/commands/mf-autopilot.md`** — 更新。新增: mandatory initial reads (§2)、task-type-based entry point selection (§3, 8 种 task type 各有对应入口序列)、auto-continue 强化 (§5.1)、progress update rule (§5.2)。
4. **`docs/README.md`** — 更新。Start Here 表格加入 CURRENT_PROJECT_STATE.md 和 progress-ledger.md；开发者文档表格加入新文件。

### 本轮未做

- 未删除/归档 stale docs（下一轮 batch）
- 未修改产品代码
- 未修改测试

---

## 2. Files Changed

| File | Change |
|------|--------|
| `docs/dev/CURRENT_PROJECT_STATE.md` | 新增 — 项目当前状态文件 |
| `docs/dev/progress-ledger.md` | 新增 — 进度台账 |
| `.claude/commands/mf-autopilot.md` | 更新 — task-type-based 入口 + 必读文件 + progress update rule |
| `docs/README.md` | 更新 — 加入新 canonical 文件引用 |
| `docs/implementation-notes/2026-05-27-114-docs-reset-governance-loop-1.md` | 新增 — 本文件 |

---

## 3. Safety Constraints Preserved

- 不读取 `.env` / secrets
- 不调用真实 LLM / Cubox / Upstage
- 不处理真实私人资料
- 不写真实 Obsidian vault
- 不做 RAG / embedding / vector DB
- 不恢复 Graph/Sensemaking 扩张
- 不新增大型依赖
- 不 force push
- 不破坏 explicit approval / human_approved 语义

---

## 4. Gates

Docs-only 改动，gate plan:

| Gate | Command | Expected |
|------|---------|----------|
| git diff --check | `git diff --check` | exit 0 |
| ruff (docs) | `ruff check docs/ .claude/commands/` | exit 0 |
| product copy | `python -m pytest tests/test_web_product_copy.py -q --tb=short` | exit 0 |

---

## 5. Next Steps

1. 继续 documentation reset batch 1 — 清理最明显的 stale/superseded docs (~10-20 个)
2. 更新 documentation-inventory.md 和 documentation-debt-ledger.md
3. 如 context 不足，写 handoff 后继续
