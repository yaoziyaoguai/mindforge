# Web UX Milestone B Implementation Notes

## 实现了什么

- **U4: Sidebar 导航分组** — 将 8 个平铺导航项分为"知识处理"（连接模型、知识源、审阅草稿、回收站）和"知识使用"（首页、知识库、Wiki、搜索）两个逻辑组，添加不可点击的分组标签
- **U5: Status Badge 图标化** — 新增 `statusIcon()`/`statusLabel()` helper，StatusCard/ConfigChecklist/CardWorkspace 的 badge 增加图标辅助辨识
- 修正 4 个因 Milestone A 中文化而过期的产品文案测试

## Plan 未覆盖但执行中必须做的决策

- `statusIcon()` 返回 `LucideIcon | null`，通过 `Inline IIFE` 在 badge 渲染处调用——避免修改 `statusTone()` 签名，现有调用方零改动
- CardWorkspace status badge 使用 `statusIcon(card.status === "human_approved" ? "ok" : "warn")` 映射，遵循组件已有的双色约定

## Deviations

- 无。Milestone B plan 中 U1-U3、U6-U7 已在前序 commit（f740573）中实现完毕，本轮仅完成 U4+U5

## 没做什么

- U1/U2/U3/U6/U7 — 已在 Milestone A 完成
- Milestone C / 后续功能
- P3 设计系统演进、P4 品牌视觉、前端测试基础设施（均为 deferred）

## 风险和 Deferred

- 无前端组件测试覆盖——依赖 npm build（tsc + vite）做类型检查，手工 smoke test 做行为验证
- Deferred 前端测试基础设施搭建后应补 StatusCard/ConfigChecklist/Sidebar 的组件快照测试

## 测试/Gate 结果

- `npm --prefix web run build`: exit code 0
- `python -m pytest -q`: exit code 0（~1200 tests passed）
- `ruff check src tests`: All checks passed
- `git diff --check`: exit code 0

## 回退记录

- 无回退
