# mf-autopilot Cross-Workstream Continuation Fix — Implementation Notes

Date: 2026-05-27
Baseline HEAD: `ff3d210`
Task type: `autopilot_governance`
Source: `/mf-autopilot capability audit`

## Summary

修复 `/mf-autopilot` 在 workstream 完成→新 workstream 第一步（spec/plan 编写）时误判停止的系统性 bug。

根因审计发现: 规则定义层面完整度很高（15 个核心能力全部有明文），但 "new workstream → plan/spec" 这个组合场景落在规则盲区中，agent 保守解读为 "需要用户确认"。

## Changes

### 1. `.claude/commands/mf-autopilot.md` — §5.3 rule 5-6 优先级明确

- **Before**: "切换 workstream 需要用户明确指令或前一个 workstream 全部完成" — 两个条件无优先级
- **After**: 明确 "前一个 workstream 完成 → 自动切换，不需要等用户确认" 为默认行为；用户指令为覆盖
- 新增: rule 6 明确新 workstream 的第一步如果是 spec/plan/boundary-tests/audit，必须直接进入

### 2. `.claude/commands/mf-autopilot.md` — §5.7 auto-continue 表

新增条目:
```
| start next workstream spec/plan（前一个 workstream 已完成） | 当前 workstream 完结后，CPS §6 推荐的下一 workstream 的 spec/plan 编写 |
```

### 3. `.claude/commands/mf-autopilot.md` — §5.8 step 6 强制 ACTION token

- **Before**: "decide: auto-continue allowed → 立即进入下一步" (prose directive)
- **After**: 6 步自路由第 6 步必须输出标准化 ACTION token:
  - `ACTION: CONTINUE_NEXT_LOOP. Next: <描述>` — 且必须立即执行
  - `ACTION: HARD_STOP_<CODE>. Reason: <原因>` — 才允许停止
  - `ACTION: HANDOFF_AND_STOP. Reason: context low` — context 不足时
- 明确 "不论是否跨 workstream" 的适用范围

### 4. `.claude/commands/mf-autopilot.md` — §5.9 banned list 扩展

新增 5 个禁止表述:
- "不是 auto-continue 范围"
- "需独立 spec/plan 后执行"
- "这是新 workstream"
- "新 workstream，不是 auto-continue 范围" (组合形式)
- "需独立 spec/plan 后进入实现"

新增规则: "下一步是 X" 后面必须紧跟 `ACTION: CONTINUE_NEXT_LOOP` 并实际继续执行

### 5. `docs/dev/CURRENT_PROJECT_STATE.md` — §6 machine-readable queue

新增 HTML 注释格式的 machine-readable queue:
```
<!-- AUTOPILOT-QUEUE-START -->
<!-- AUTOPILOT-QUEUE-NEXT-ACTION: plan_spec -->
<!-- AUTOPILOT-QUEUE-TASK-TYPE: feature_implementation -->
<!-- AUTOPILOT-QUEUE-ITEM-1: ... -->
<!-- AUTOPILOT-QUEUE-END -->
```

消除 "需独立 spec/plan 后执行" 的人类语言歧义 — `NEXT-ACTION: plan_spec` 是明确的 machine-readable 指令。

### 6. `docs/dev/progress-ledger.md` — workstream 切换记录

- §1: 新增本 loop 条目
- §2: Active workstream 从 Architecture Quality Reset 切换至 Autopilot Governance

## 未修改的文件

- 未修改产品代码 (`src/`, `web/src/`)
- 未修改 tests
- 未修改 `.env` / secrets
- 未调用外部服务

## Safety

- 未修改 core approval semantics
- 未读取 .env / secrets
- 未扩展 Graph/Sensemaking
- 未引入 RAG/embedding/vector DB
- 未做架构重构
- 规则变更是 clarification（明确已有规则的适用范围），不是 expansion

## Why This Fix Is Safe

1. **不创建新能力** — 所有修改都是澄清已有规则
2. **不放松约束** — hard-stop 表未减少，auto-continue 表只加了 "start next workstream spec/plan" 一条（本质是 "plan/spec 编写" 的 sub-case）
3. **不破坏 governance** — banned list 增加 = 更严格，不是更宽松
4. **Machine-readable queue 是附加信息** — 不改变 prose 的优先级，只作为 disambiguation layer

## Design Decisions

- **Why ACTION token and not just prose?** 上次 §5.7–§5.9 的修复 (auto-continue policy hardening) 用 prose "禁止输出 X" 解决了口头停的问题，但没解决 "自路由完成后 prose 描述下一步但不执行" 的问题。ACTION token 是强制 commitment 机制 — 输出 token = 承诺执行。
- **Why machine-readable queue as HTML comments?** 不影响人类可读性（注释在 Markdown 渲染中不可见）。Agent 可以从注释中解析 `NEXT-ACTION` 而不依赖 prose 的 NLP 理解。
- **Why not split commands?** 两个命令增加认知负担，且 /mf-run-next 会遇到同样的停止问题。修复现有规则是更干净的方案。
