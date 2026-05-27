# mf-autopilot Reliability Upgrade — Implementation Notes

- **Date**: 2026-05-27
- **Trigger**: `/mf-autopilot` — harden loop governance rules
- **Status**: Loop complete

---

## 1. Scope

本轮是 `/mf-autopilot` 规则自身的治理补强。不做产品功能、UI、架构、docs 大清理。

### 4 类优化

**1. Active Workstream / Loop Queue Rules**
- 每次 run 必须识别 current active workstream
- 默认单 workstream，多个候选按 priority 选一个
- CURRENT_PROJECT_STATE.md 和 progress-ledger.md 不一致时以 CURRENT_PROJECT_STATE.md 为准
- 切换 workstream 需要明确依据

**2. Stale Window / Old Commit Reconciliation Rules**
- 旧窗口 commit 不得直接当作当前主线事实
- 必须用当前 repo git log --all 重新验证
- 不得 cherry-pick 不可见 commit
- 不得改 remote/proxy/global git config

**3. Progress Update Template**
- progress-ledger.md 使用固定模板 (Date, Commit, Workstream, Task type, Outcome, Docs, Gates, Next, Workstream changed)
- Minor fix 至少追加一行

**4. Low-Context Handoff Protocol**
- context < 15%: 不开启新 loop
- context < 10%: 只完成当前变更
- context < 5%: 立即写 handoff
- Handoff 固定位置: `docs/dev/HANDOFF.md`
- HANDOFF.md 已加入 `/mf-autopilot` §2 必读列表

---

## 2. Files Changed

| File | Change |
|------|--------|
| `.claude/commands/mf-autopilot.md` | 新增 §1.1 (stale window rules), §5.3 (active workstream rules), §5.6 (handoff protocol); 更新 §2 (add HANDOFF.md to reads), §5.2 (progress template); 重编号 |
| `docs/dev/CURRENT_PROJECT_STATE.md` | 修复 HEAD → `0248755`; 新增 §8 (handoff protocol); 更新 §6 (next loops) |
| `docs/dev/progress-ledger.md` | 更新 §4 (update template); §2 (active workstream); §1 (add governance loop 1) |
| `docs/dev/HANDOFF.md` | 新增 — 低 context handoff 模板 |
| `docs/implementation-notes/2026-05-27-115-mf-autopilot-reliability-upgrade.md` | 新增 — 本文件 |

---

## 3. Safety Constraints

- 不读取 `.env` / secrets
- 不调用真实 LLM
- 不修改产品代码
- 不删除文件
- 不破坏 explicit approval 语义

---

## 4. Gates

| Gate | Command | Expected |
|------|---------|----------|
| git diff --check | `git diff --check` | exit 0 |
| ruff (docs) | `ruff check docs/ .claude/commands/` | exit 0 |
| product copy | `python -m pytest tests/test_web_product_copy.py -q --tb=short` | exit 0 |
