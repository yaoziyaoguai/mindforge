# Handoff — 2026-05-28

> **status: resolved** — superseded by `8c62c33` (Dogfood P0/P1 Remediation). Latest state in CPS §1.

## Repo Snapshot
- HEAD: 8c62c33
- Branch: main
- Working tree: clean
- vs origin/main: 0 0

## Active Workstream
- Workstream: Quality Platform / Frontend Test Coverage
- Status: **done** — 所有低风险纯展示组件测试已覆盖

## Last Completed Loop
- Task type: feature_implementation (test expansion)
- Outcome: Breadcrumb (9 tests) + SafetyBar (16 tests) 组件测试。useLocale() i18n context provider 问题已解决。测试文件 4→6，测试 25→50。
- Commit: 7acb47e

## Completed Test Coverage

| 组件 | 测试数 | 关键挑战 |
|------|--------|---------|
| ErrorState | 2 | 无依赖，最简单 |
| LoadingSkeleton | 2 + 10 variants | 纯 CSS，无依赖 |
| EmptyState | 6 | NextAction type, href/onClick/command 分支 |
| StatusCard | 6 | status badge, detail, nextAction, section/button |
| Breadcrumb | 9 | **useLocale()** — 用 LocaleProvider 包裹解决 |
| SafetyBar | 16 | **useLocale()** + SafetySummary mock + split text node 正则 |

**renderWithLocale()** 模式已建立：`render(<LocaleProvider>{ui}</LocaleProvider>)`，后续任何使用 useLocale() 的组件测试可直接复用。

## Remaining: AUDIT-118 Product Debts

以下三项需要产品决策，不在 test expansion 范围内：

| ID | Priority | Description |
|----|----------|-------------|
| AUDIT-118-01 | P1 | Export route 已实现，但 user guides / README Web UI 表仍存在 Export 状态漂移 |
| AUDIT-118-02 | P1 | Dogfood 仍在主导航，和 internal 定位冲突 |
| AUDIT-118-04 | P1 | 缺少 fresh browser/MCP Web 主路径证据；当前 smoke 主要是 API/static |

AUDIT-118-03 (web_facade.py architecture debt) 已 resolved (v4.8+Slice 1+2)。
AUDIT-118-05 (HANDOFF.md 模板误读风险) 仍 open。

## Gates Last Run
- `git diff --check`: exit 0
- `npm --prefix web run build`: exit 0
- `npm --prefix web run test`: exit 0 (50 passed, 6 files)
- `pytest tests/test_web_product_copy.py -q --tb=short`: exit 0 (84 passed)

## Next /mf-autopilot Instruction
```
/mf-autopilot

Frontend test coverage workstream 完成（6 file/50 test）。
剩余只有 AUDIT-118 P1 产品债（Export docs, Dogfood nav, browser smoke）。
这些需要产品决策，不是低风险测试补强。
请决定下一 workstream 方向。
```

## Hard Stops / Warnings
- Context: sufficient for handoff (not context-forced — workstream-completion handoff)
- Next workstream: 等待用户产品决策（AUDIT-118 P1 items vs. 其他 roadmap 方向）
