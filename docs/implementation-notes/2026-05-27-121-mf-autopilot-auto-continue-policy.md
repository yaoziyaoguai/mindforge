# mf-autopilot Auto-Continue Policy — Implementation Notes

Date: 2026-05-27
Baseline HEAD: `3c829da`
Task type: `autopilot_governance`
Active workstream: Autopilot Governance

## Summary

修复 `/mf-autopilot` 在 Web IA/UX Loop 2 完成后未自动继续的治理 bug：autopilot 正确识别了下一步（Architecture Quality Reset plan），但输出"是否继续？"后停止，违反了 auto-continue contract。

本轮新增 3 个治理规则章节（§5.7–§5.9），明确 auto-continue 决策边界、自路由流程和软停止禁令。

## Changes

### 1. `.claude/commands/mf-autopilot.md` — §5.7 Auto-Continue Decision Table

新增明确的 auto-continue 决策表，分三个子表：

**Auto-continue without asking user（12 项）：**
- audit、plan/spec 编写、implementation notes 编写
- docs cleanup（在已批准规则内）
- browser/MCP QA
- targeted P1/P2 fix
- tests/gates
- small safe implementation slice（已由 plan 授权）
- architecture_refactor plan/spec only
- architecture boundary tests
- low-risk schema/service cleanup（plan 已覆盖）
- 更新 CURRENT_PROJECT_STATE / progress-ledger / HANDOFF

**Must ask user / HARD_STOP_PRODUCT_DECISION（10 项）：**
- real API key needed
- real LLM/Cubox/Upstage required
- real private user data needed
- real Obsidian vault write needed
- large archive/delete batch without exact rules
- large architecture implementation without plan/review
- new heavy dependency
- product direction conflict
- restoring Graph/Sensemaking/Entity/Community expansion
- irreversible or destructive action

**Low-context override：** 与 §5.5 一致，但明确 plan/spec/docs/handoff 在 context < 15% 仍可继续（边界小且清晰时）。

### 2. `.claude/commands/mf-autopilot.md` — §5.8 Self-routing after final report

定义 6 步自路由流程：
1. parse own completed loop outcome
2. identify next recommended loop
3. classify next loop task type
4. check hard-stop table
5. check context policy
6. decide: auto-continue → 立即执行 / not allowed → HARD_STOP_*

明确 4 类"不得询问用户"的行动：写 plan/spec、review output and choose next loop、更新 state 文件、跑 gates 和 commit/push。

### 3. `.claude/commands/mf-autopilot.md` — §5.9 Banned soft-stop phrases

列出 8 个禁止的软停止表述：
- "是否继续？"、"等待用户指令"、"建议下一步是 X"、"可以进入 X"
- "是否要我继续？"、"需要我继续吗？"、"要不要我…"、"准备好了就告诉我"

规则：如果报告写了"下一步是 X"且 X 在 auto-continue 范围内，必须立即执行 X。

### 4. Task type 注册

- §3 新增 `autopilot_governance` task type 及其 loop 入口
- §5.2 进度模板新增 `autopilot_governance`

## 未修改的文件

- 未改产品代码（`src/`、`web/src/`）
- 未进入 Architecture Quality Reset 实现
- 未读 `.env` / secrets
- 未调用外部服务

## Gates

| Gate | Command | Exit Code |
|------|---------|-----------|
| git diff --check | `git diff --check` | 0 |
| ruff check | `ruff check docs/ .claude/commands/` | 0 |
| product copy tests | `python -m pytest tests/test_web_product_copy.py -q --tb=short` | 0 |

## Remaining Debt

- Architecture Quality Reset plan 尚未编写（现在通过 auto-continue 规则可在下一轮自动进入）
- HANDOFF.md 仍为模板（当前 context 充足，不需要 pollute）

## Safety

- 未修改 core approval semantics
- 未读取 .env / secrets
- 未修改 real provider activation
- 未扩展 Graph/Sensemaking/Entity/Community
- 未引入 RAG/embedding/vector DB
- 未做架构大重构
- 未调用外部服务
