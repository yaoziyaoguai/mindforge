# mf-autopilot Skill Redesign Review

对比 FirstAgent `/auto-run` 与 MindForge `/mf-autopilot` 的 skill 设计，识别差距和低风险改进机会。

日期: 2026-05-28
参考: FirstAgent `.claude/commands/auto-run.md` (561 lines), MindForge `.claude/commands/mf-autopilot.md` (1016 lines)

---

## 1. 结构对比

| 维度 | FirstAgent auto-run | MindForge mf-autopilot |
|------|--------------------|------------------------|
| 入口文件行数 | 561 lines | 1016 lines |
| 文件分层 | 3 层: command → workflow manual → engineering constitution | 1 层: 全部在 command 文件 |
| 核心调度模型 | Skill Router Decision Table (task type → primary/secondary skill) + Workflow Stage → Skill Table | Task type entrypoint → Skill Framework Discovery → Mandatory Skill Gates → Skill Routing Decision |
| 停止规则位置 | 集中一处 §Hard Stops + 明确枚举 "不是停止条件" | 分散在 §5.7、§7、§5.8、§5.9 多处 |
| 报告格式 | 非 hard-stop 一行, hard-stop 才完整报告 | 每轮都输出完整报告 (§10, ~30 lines) |

**结论**: FirstAgent 更接近 "稳定的 auto-run skill"。MindForge 更像 "超长治理 prompt"。

---

## 2. 八个维度逐项对比

### 2.1 Auto-Continue 清晰度

| | FirstAgent | MindForge |
|---|-----------|-----------|
| 核心表述 | "只有 hard stop 才停" — 单句原则 | 分散在 §5.1 auto-continue contract、§5.7 decision table、§5.8 self-routing |
| 非停止条件 | 集中枚举 10 项（queue empty, candidate blocked, loop 完成, commit/push 完成, review 完成, 技能阶段完成...） | 分散在 §5.7 表格 + §7 底部 |
| 冗余 | 低 — 说一次，不重复 | 高 — 同一个"commit/push 不是停止点"在 §5.1、§5.3、§5.8 各说一次 |

**MindForge 问题**: auto-continue 的规则是正确的，但散布在 3-4 个 section 中，导致 agent 需要在多处交叉验证。FirstAgent 把所有非停止条件集中为一个清单，一目了然。

### 2.2 Hard-Stop 清晰度

| | FirstAgent | MindForge |
|---|-----------|-----------|
| 停止条件 | 11 项，集中列举 | 12 项在 §5.4 stop reasons + 15 项在 §7 硬红线（大量重复） |
| 一致性 | 高 | 中等 — §5.4 和 §7 有重叠但不完全一致（例如 §7 多了 "force push/tag/release" 和 "破坏性数据迁移"，§5.4 多了 "HARD_STOP_GIT_UNSAFE_STATE"） |
| 格式 | 简短描述 | 格式化的 HARD_STOP_<CODE> token（更好） |

**MindForge 做得好的**: HARD_STOP_<CODE> 标准化 token 格式比 FirstAgent 的纯文本更好。
**MindForge 问题**: §5.4（12 项）和 §7（15 项）有大量重复但不完全一致，容易造成 agent 困惑。

### 2.3 Queue/Workstream 选择清晰度

| | FirstAgent | MindForge |
|---|-----------|-----------|
| 选择机制 | PROJECT_STATUS recommended next + remediation plan next pending loop + P0→P1→P2 优先级 | AUTOPILOT-QUEUE 注释块 + CPS §6 推荐 next loops |
| 自动化程度 | Next-Loop Selection 有明确的 6 步算法 | §5.3 有 workstream 切换规则，但 queue 选择依赖人工维护的 HTML 注释 |
| Queue 格式 | 无独立 queue 格式 — 依赖 PROJECT_STATUS 的结构化字段 | HTML 注释格式 — 机器可读性差，容易漂移 |

**MindForge 问题**: AUTOPILOT-QUEUE 作为 HTML 注释嵌入 CPS，格式脆弱，容易在编辑中损坏。对比 FirstAgent 直接依赖 PROJECT_STATUS 的结构化状态字段更简洁。

### 2.4 Low-Context Handoff 清晰度

| | FirstAgent | MindForge |
|---|-----------|-----------|
| Handoff 模板 | 在 workflow doc 中定义，相对简洁 | §5.6 定义详细模板 + §21 扩展 schema（含 remediation context） |
| 触发规则 | "context 接近耗尽" — 一条规则 | §5.5 有详细的 context% → 行为映射表 |
| 恢复指令 | 在 final output 中 | 在 HANDOFF.md 中 + §21 的 `/mf-autopilot` continuation instruction |

**两者相当**。MindForge 的 context% 分段策略（≥15% / <15% / <10% / <5%）更精确。FirstAgent 的模板更简洁。

### 2.5 Gate Evidence 清晰度

| | FirstAgent | MindForge |
|---|-----------|-----------|
| Gate evidence rule | 在 ENGINEERING_WORKFLOW.md 中 | §8.1 有相同的规则 + 在 engineering-workflow.md 中重复 |
| Claim-to-Evidence Gate | 有 5 级 status（RESOLVED/PARTIAL/OVERCLAIMED/NOT_FIXED/EVIDENCE_PENDING）| 无 — MindForge 没有显式的 claim-to-evidence gate |
| Status Promotion Gate | 有 6 道门禁（原始 finding 定位、修复覆盖、regression test、dogfood/harness、independent review、claim-to-evidence）| 无 — MindForge 标记 RESOLVED 没有必经的 gate 检查 |

**这是 MindForge 最大的差距**。MindForge 没有 claim-to-evidence gate 和 status promotion gate。当前 progress-ledger 中的 `Review result: PASS` 和 `Gate result: PASS` 没有经过严格的 evidence 绑定验证。

### 2.6 Skill Routing 膨胀度

| | FirstAgent | MindForge |
|---|-----------|-----------|
| Skill routing 章节 | 3 节: Skill Routing Policy + Skill Router Decision Table + When to Use Each Skill | 4 节: §14 Mandatory Skill Gates + §15 Skill Framework Discovery + §16 Skill Routing Decision Block + 部分 §11 Recursive Remediation |
| Skill 选择矩阵 | 12 行 task type 表 + 10 行 stage 表 | 9 行 task type 表 + framework 选择矩阵 |
| 强制触发规则 | 按 task type 推荐 primary/secondary，但允许 "不盲选" | §14 有 5 类 mandatory skill gates，§15.2 有 9 类 task type → framework 强绑定 |
| 输出格式 | 简短的 skill routing 声明 | §16 的 Skill Routing Decision Block 固定 11 行格式 |

**MindForge 的 skill routing 明显膨胀**。§14、§15、§16 合计 ~140 行，加上 §11 中引用的 skill 相关回退规则，skill routing 占了总长度的 ~15%。对于简单的 docs_cleanup 或 bug_fix loop，11 行的 Skill Routing Decision Block 输出是过度负担。

### 2.7 ACTION Token 稳定性

| | FirstAgent | MindForge |
|---|-----------|-----------|
| Token 类型 | 无标准化 token — 用自然语言 "Loop N COMPLETED" vs full report | 有标准化 ACTION token: `CONTINUE_NEXT_LOOP` / `HANDOFF_AND_STOP` / `HARD_STOP_<CODE>` |
| 稳定性 | N/A | 中等 — ACTION token 只在 §5.8 和 §18 定义，但 §5.9 的 banned phrases 和 §18 的规则存在重叠 |

**MindForge 的 ACTION token 设计比 FirstAgent 更好**。FirstAgent 没有等价物。但 MindForge 的 Post-Loop Self-Routing Block (§18) 和 §5.8 的 self-routing 流程有重复。

### 2.8 协议收敛潜力

能否从 "超长治理 prompt" 收敛为更稳定的 skill 协议？

**FirstAgent 的分层策略值得借鉴**:
- `.claude/commands/auto-run.md` → 调度器入口（选技能、选起点、跑 loop、输出报告）
- `docs/dev/AUTO_RUN_WORKFLOW.md` → 操作手册（loop 类型、deferred 条件、stop condition）
- `docs/dev/ENGINEERING_WORKFLOW.md` → 工程宪法（SDD→TDD→Review 纪律）

MindForge 当前把所有三层内容压在一个 1016 行的文件中。engineering-workflow.md 已经包含了很多重复内容（如 gate rules、hard red lines、autopilot 模式概述）。

**收敛路径**:
1. 把 mf-autopilot.md 中与 engineering-workflow.md 重复的内容删掉，只保留引用
2. 把 AUTOPILOT-QUEUE 从 HTML 注释改为 CPS 中的结构化 markdown 字段
3. 合并 §5.4/§7 的停止条件为单一定义
4. 合并 §5.8/§18 的 self-routing 为单一定义
5. 简化非 hard-stop 报告格式（借鉴 FirstAgent 的一行模式）

---

## 3. 值得借鉴的 FirstAgent 设计元素

### 3.1 强烈建议采纳

| 元素 | 理由 | 风险 |
|------|------|------|
| **Claim-to-Evidence Gate（简化版）** | MindForge 当前标记 RESOLVED 无证据绑定要求。至少应要求: (1) 绑定原始 finding/issue (2) 引用具体 commit hash (3) gate exit code | 低 — 不改代码，只改 governance 规则 |
| **非停止条件集中清单** | 当前分散在 3 处，集中一处减少 agent 漏判 | 极低 — 纯文本重组 |
| **停止条件去重** | §5.4 + §7 合并为一处 | 极低 — 纯合并 |

### 3.2 可以考虑采纳

| 元素 | 理由 | 风险 |
|------|------|------|
| **非 hard-stop 报告压缩为一行** | 减少 agent 输出开销，hard-stop 才出完整报告 | 中 — 需要确保关键信息不丢失 |
| **Review Failure Routing Table** | FirstAgent 的 10 个 failure pattern → 回退目标的映射表很实用 | 低-中 — 需要 MindForge 自己的 pattern 分析 |

### 3.3 不建议照搬

| 元素 | 理由 |
|------|------|
| Workflow Stage → Skill Table | MindForge 的产品形态与 FirstAgent 的 Agent Runtime 不同，stage 切分方式不可直接移植 |
| Status Promotion Gate（完整 6 道） | MindForge 没有 FirstAgent 的 branch point / capability milestone 体系，6 道门禁过度 |
| dogfood harness evaluator 体系 | MindForge 的 dogfood 比 FirstAgent 简单，不需要 expected_events / case classification 那套 |
| 架构分层 (L1/L2/L3 evidence taxonomy) | MindForge 不做 Agent Runtime，不需要 branch point / dispatcher path 这类 evidence 分层 |

---

## 4. 低风险改进清单

以下改进可以安全执行（只改 governance 规则和文档结构，不改产品代码）:

### 4.1 立即可做（本次 loop）

1. **合并 §5.4 + §7 停止条件**: 合并为单一 `## Stop Conditions` 章节，消除重复和不一致
2. **合并 §5.8 + §18 self-routing**: 合并 post-loop self-routing 逻辑为单一章节
3. **新增集中非停止条件清单**: 借鉴 FirstAgent "以下不是停止条件" 模式
4. **简化 Skill Routing Decision 输出**: 对于低风险 task type（docs_cleanup, bug_fix, simple audit_only），允许简化为 3 行
5. **在 progress-ledger 模板中新增 evidence binding**: 要求每个 RESOLVED 声明绑定原始 issue/finding ID
6. **新增 §Claim-to-Evidence Gate（简化版）**: 3 项基础检查 — finding 绑定 + commit hash + gate exit code

### 4.2 需要更多设计（下个 loop）

1. 把 AUTOPILOT-QUEUE 从 HTML 注释迁移为结构化 markdown
2. 合并 mf-autopilot.md 与 engineering-workflow.md 中的重复内容
3. Review Failure Routing Table（需要收集 MindForge 自身的 failure pattern）

---

## 5. 不改的边界

以下 FirstAgent 设计元素**明确不引入** MindForge:

- Agent Runtime architecture / branch point 体系
- memory/tool/checkpoint 设计
- capability milestone / Anchor 体系
- L1/L2/L3/L4 evidence taxonomy（MindForge 不做 Agent Runtime）
- harness evaluator / expected_events 验证
- fake/real path split 治理
- dogfood case matrix 体系

MindForge 保持 "local-first, approval-first personal knowledge compiler" 定位不变。

---

## 6. 总结

MindForge mf-autopilot 的核心问题不是规则不够多，而是:
1. **结构扁平** — 1016 行全在一个文件，缺少 command/workflow/constitution 三层分离
2. **重复严重** — 同一规则在 §5.1/§5.3/§5.8 重复，§5.4/§7 重复
3. **缺少 evidence gate** — 没有 claim-to-evidence 绑定，RESOLVED 标记缺少证据锚点
4. **skill routing 输出过度** — 低风险 task 也要求 11 行 skill routing decision
5. **AUTOPILOT-QUEUE 格式脆弱** — HTML 注释易损坏且难以机器解析

低风险改进方向: 去重 → 合并 → 简化输出 → 补充 evidence binding。不碰架构，不新增体系。
