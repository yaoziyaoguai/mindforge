# mf-autopilot Skill Redesign Review + Low-Risk Improvements

日期: 2026-05-28
Task type: autopilot_governance

## Background

对比 FirstAgent `/auto-run` (561 lines, 3 层文件) 与 MindForge `/mf-autopilot` (1016 lines, 单文件) 的 skill 设计后，识别出以下低风险改进并实施。

## What Changed

### 1. §5.4 + §7 停止条件合并
- **Before**: §5.4 列出 12 个 HARD_STOP_<CODE>，§7 列出 15 个停止条件 + 8 个非停止条件。两处有重叠但不完全一致。
- **After**: §5.4 简化为对 §7 的引用。§7 重写为 "Stop Conditions（唯一权威来源）"，包含 §7.1 Hard Stop Conditions（13 个 code 的单一表格）和 §7.2 Non-Stop Conditions（集中清单）。
- 新增 `HARD_STOP_DESTRUCTIVE` 统一 force push/tag/release/破坏性数据迁移/不可逆操作。

### 2. Non-Stop Conditions 集中清单
- **Before**: 分散在 §5.7 auto-continue 表格、§7 底部、§5.8 self-routing 规则中。
- **After**: §7.2 集中列出 20+ 个非停止条件，借鉴 FirstAgent 的 "以下不是停止条件" 模式。

### 3. Claim-to-Evidence Gate (§23)
- **新增**: 要求每个 RESOLVED/PASS 声称绑定具体证据。
- 3 级判定：RESOLVED / PARTIAL / 不得标记。
- 3 项 evidence 绑定要求：finding/issue 引用 + 文件路径/commit hash + gate exit code。
- 禁止全局声称（`all P0/P1 resolved`、`production-ready` 等）在 gate 通过前写入。

### 4. Skill Routing Decision 简化
- §16 新增低风险 task 简化输出规则：docs_cleanup、bug_fix（单文件）、autopilot_governance（小范围）、audit_only（只读）可缩写为 3 行。
- 如果 required skill 非空或风险为 medium/high，仍必须使用完整 11 行格式。

### 5. Progress Ledger 模板更新
- §20 新增 `Evidence binding` 字段。

## What Did NOT Change

- 不改产品代码（src/、web/src/、tests/）
- 不改产品功能、UI、dogfood、架构实现
- 不改 AUTOPILOT-QUEUE 格式（HTML 注释 → 结构化 markdown 留待后续）
- 不改 mf-autopilot.md 与 engineering-workflow.md 的重复内容（留待后续）
- 不引入 FirstAgent 的 Status Promotion Gate（6 道门禁）、Review Failure Routing Table、L1/L2/L3 evidence taxonomy

## Review Note

完整对比分析见: `docs/dev/mf-autopilot-skill-redesign-review.md`

## Remaining Risks

- §7 现在是唯一权威来源，其他地方（§5.7、§5.8）通过引用指向它，如果引用漂移可能导致不一致。
- Claim-to-Evidence Gate (§23) 需要在实际 loop 中验证可用性。
- 低风险 task 的简化 Skill Routing Decision 边界可能被滥用——如果 agent 把 medium-risk task 错误分类为 low-risk。
