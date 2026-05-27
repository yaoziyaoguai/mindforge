# mf-autopilot Skill Framework Routing

日期: 2026-05-27

## Why

上一轮 (138) 已加入 recursive remediation 和 mandatory skill gates，但对 Compound Engineering / G-stack / Superpowers 的触发规则不够硬。需要明确的 skill framework discovery 流程和强制使用规则。

## What Changed

在 `.claude/commands/mf-autopilot.md` §15 中补强:

### §15.1: Skill Framework Discovery

每次 run 选好 task entrypoint 后必须先做 discovery — 检查 Compound Engineering、G-stack、Superpowers、design skills、codex adversarial review 的可用性。无法自动列出时必须使用 known skill inventory fallback。

### §15.2: Compound Engineering / G-stack / Superpowers Mandatory Rules

按 task type 矩阵强制检查:

| Task Type | 必须检查 |
|-----------|---------|
| architecture_refactor | Compound Engineering, G-stack |
| feature_implementation (complex) | Compound Engineering, G-stack |
| quality_platform | Compound Engineering, G-stack |
| design_review | Design skills chain |
| audit_only | Codex adversarial review |

Available + applicable 但未调用 → skill_routing_failure。

### §15.3: Mandatory Skill Gate Examples

7 个具体场景示例（v3.7 Quality Platform → /plan-eng-review、Global Architecture Reset → Compound Engineering/G-stack、Web redesign → design chain 等）。

### §15.4: Selection Matrix

Framework vs best for vs overkill for 对照表。

### §15.5: Recursive Remediation Integration

architecture/plan/implementation/gate 类失败 → remediation routing 必须 re-check Compound Engineering/G-stack/Superpowers before retry。

### §16: Skill Routing Decision Format Updated

新增 "Available skill frameworks checked" 5 项检查（Compound Engineering, G-stack, Superpowers, Design skills, Codex adversarial review）。

### §20: Progress Ledger Schema Updated

新增 `Skill frameworks checked` 和 `Required skill invoked` 字段。

## Files Changed

- `.claude/commands/mf-autopilot.md` — §15 + §16 format expansion

## Remaining Risks

- Known skill inventory fallback 内容取决于 agent 的 skill 感知能力
- 框架不可用时的 fallback 路径在 §15.2 中有说明但未经实战验证
