# mf-autopilot Recursive Remediation & Mandatory Skill Gates

日期: 2026-05-27

## Why

`/mf-autopilot` 之前是 "workflow router + skill router"，缺少闭环回退能力。Review/gate/audit 失败时没有制度化的回退路径，容易停下来问用户或继续硬跑。Skill routing 只是建议性，不是强制性。

## What Changed

在 `.claude/commands/mf-autopilot.md` 新增 §11-§22，将 mf-autopilot 从 linear pipeline 升级为 recursive workflow controller。

### §11: Recursive Remediation Loop

定义 mf-autopilot 为 recursive workflow controller，非 linear pipeline。新增 4-tier remediation precedence（同阶段 fix → 上一阶段 → spec/plan → 产品决策）。

### §12: Failure Classification Table

9 类失败及对应回退目标:

| # | Class | 回退目标 |
|---|-------|---------|
| 1 | spec_failure | spec/plan stage |
| 2 | plan_failure | plan rewrite |
| 3 | design_failure | design stage |
| 4 | architecture_failure | architecture audit |
| 5 | implementation_failure | inspect/reproduce |
| 6 | gate_failure | diagnose gate |
| 7 | review_failure | earliest mismatched stage |
| 8 | docs_truth_failure | docs_cleanup entrypoint |
| 9 | skill_routing_failure | Skill Routing Decision node |

### §13: Retry / Escalation Policy

- Max 2 retries per remediation loop
- P0/P1 exceeding 2 → HARD_STOP_P0_P1_RETRY_EXCEEDED
- P2/P3 may be deferred
- Never hide failed gate / continue after failed safety gate

### §14: Mandatory Skill Gates

5 类任务的强制技能门禁:
- Product/strategy → `/brainstorming` + `/office-hours`
- Architecture/engineering → `/plan-eng-review` + boundary tests
- Web/design → 完整 design skill chain
- Audit/red-team → `/codex:adversarial-review`
- Bug fix/small fix → 直接 mf-autopilot，不强制 heavy skills

### §16: Skill Routing Decision Block

标准化输出格式，每 run 必输出。

### §17: Review Node Rules

每种 task type 对应一个 review node，review fail → 必须回退。

### §18: Post-Loop Self-Routing Block

标准化输出格式: Review/Gate result, failure class, remediation target, auto-continue allowed, ACTION token。

### §19-§21: Schema Updates

CPS AUTOPILOT-QUEUE、progress ledger、HANDOFF.md 格式升级，新增字段支持 recursive remediation 追踪。

## Files Changed

- `.claude/commands/mf-autopilot.md` — 新增 §11-§22 (~370 lines)

## Remaining Risks

- 新规则尚未在真实 loop 中实战验证
- Failure classification 的精确性取决于 agent 自我诊断能力
- Mandatory skill gates 需要 skill 实际可用；unavailable 时 fallback path 仍需完善
