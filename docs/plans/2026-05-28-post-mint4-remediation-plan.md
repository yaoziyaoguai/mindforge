# Post-Mint4 Remediation Plan

创建日期: 2026-05-28
来源: `docs/retrospectives/2026-05-28-post-mint4-retrospective.md` (verdict 6.8/10 Conditional Go)
原则: 不做新功能、不做全局审计、不做大架构重构。只补最关键、最低风险、最高价值的不足。

---

## Scope Boundary

**In scope:**
- P1: User Validation Kit (文档和模板，不伪造真实用户)
- P2: Web UX Remediation (仅 P1/P2 阻断首次使用的 UX 问题)
- P3: Design System Foundation (轻量 token + 文档)
- P4: Autopilot Simplification (分析先行，不立即大改)
- P5: Docs Governance Cost Reduction (小 batch 清理)

**Out of scope:**
- 新功能开发
- 全局审计
- 大架构重构
- 真实用户验证执行 (HARD_STOP_PRODUCT_DECISION — 需要 5 名真实用户)
- Real LLM 集成 (Direction D)
- Graph/Sensemaking 扩张
- 响应式/移动端 (deferred per retrospective §10)
- BM25 中文分词 (deferred per retrospective §10)

---

## P1: User Validation Kit

**来源:** 复盘 §5/§6/§11 — 产品核心假设未验证, 5-user protocol defined
**优先级:** P1 (最高)
**风险:** 低 (只写文档和模板，不改产品代码)

### 交付物

1. **5-User Validation Protocol** (`docs/product/validation-protocol.md`)
   - 测试目标: 验证非技术用户能否在 ≤15 min 内完成首次完整主路径循环
   - 5 个 scenario-based tasks
   - 观察要点: 哪里卡住、什么概念不理解、什么让他们惊喜
   - Kill criteria (来自产品创新审计):
     - ≥3/5 fail full cycle → KILL
     - ≥3/5 don't understand approval → KILL
     - ≥3/5 say "wouldn't use" → KILL

2. **15-Minute First-Cycle Test Script** (`docs/product/test-script.md`)
   - 用户引导语 (非技术语言)
   - Task 1: 理解当前工作区 (自由探索 3 min)
   - Task 2: 导入一段内容 (3 min)
   - Task 3: 审阅并审批 (3 min)
   - Task 4: 使用 Recall 检索 (3 min)
   - Task 5: 使用 Wiki 生成总结 (3 min)

3. **Observer Checklist** (`docs/product/observer-checklist.md`)
   - 时间记录 (每 task 开始/结束)
   - 卡住点记录 (在哪里停顿 >30s)
   - 概念困惑记录 (用户明确提问或自言自语)
   - 情绪记录 (frustrated/neutral/delighted)
   - 不干预原则

4. **Feedback Form** (`docs/product/feedback-form.md`)
   - 5 个 Likert scale 问题 (1-5)
   - 3 个开放问题
   - NPS 问题
   - 不做真实用户 → HARD_STOP_PRODUCT_DECISION

5. **Sample Workspace Validation Path** (`docs/product/sample-workspace-validation.md`)
   - 验证 demo workspace 在 auto-fallback fake provider 下工作正常
   - 验证 6 张 demo 卡片的审批状态正确
   - 验证所有 8 个主路径页面可访问且无 console error
   - 使用 browser/MCP smoke 作为 self-check fallback

6. **CPS 更新**: 将 User Validation 从 §6 recommended next loops 提到 P0 priority

### 实现单元

| Unit | File | Description |
|------|------|-------------|
| U1 | `docs/product/validation-protocol.md` | 5-user protocol + kill criteria |
| U2 | `docs/product/test-script.md` | 15-min scenario-based test script |
| U3 | `docs/product/observer-checklist.md` | Observer recording template |
| U4 | `docs/product/feedback-form.md` | Post-test feedback form |
| U5 | `docs/product/sample-workspace-validation.md` | Browser MCP smoke validation path |
| U6 | `docs/dev/CURRENT_PROJECT_STATE.md` | Update §6 to reflect P0 validation |

### Gates
- `git diff --check`

---

## P2: Web UX Remediation

**来源:** 复盘 §6.1 — 5 个剩余 UX 问题, §7.1 — Web 设计评分 6.5/10
**优先级:** P2
**风险:** 低-中 (改 Web 代码，但只改 P1/P2 UX 问题)

### 关键问题 (从复盘提取)

1. **QuickStartWizard 跳过审批学习** (§6.1.1): demo 卡片直接 human_approved，用户看不到 ai_draft → human_approved 的核心语义
2. **OnboardingHint dismiss 不持久化** (§6.1.2): 刷新后重新出现是合理行为，但可能 annoying
3. **无用户反馈入口** (§6.1.5): 无 feedback button 或 link
4. **BulkActions/CardWorkspace YAML 直接暴露** (§7.1.5): Direction F 新增组件 UI 偏 technical

### 筛选规则

只修 P1/P2 阻断首次使用的 UX 问题:
- P1: 用户无法理解产品核心语义 → 影响 Validation
- P2: 用户体验差但可完成 → 影响 Validation 效率
- P3/P4: 不修 (deferred)

### 候选修复项 (需 browser/MCP 审计后确认)

| ID | Issue | Priority | Estimated Fix |
|----|-------|----------|---------------|
| UX-01 | QuickStartWizard demo 卡片未展示审批流程 | P1? | 在 wizard step 3 后加一个 "模拟审批" 步骤，或至少展示审批概念说明 |
| UX-02 | OnboardingHint dismiss 状态 | P2 | 添加 localStorage 持久化 dismissed hints |
| UX-03 | HomePage 无反馈入口 | P2 | 添加轻量 feedback link (不收集数据，指向 project repo issues) |
| UX-04 | 主路径页面空状态文案 | P2 | 确认 Library/Recall/Review 的空状态有引导文案 |
| UX-05 | BulkActions YAML 暴露 | P3 (deferred) | 不加 UI wrapper，技术用户受益于 YAML 直接编辑 |

### 实施策略

1. 先运行 browser/MCP audit 确认 actual UX 状态
2. 确认 P1/P2 问题列表和优先级
3. 逐个修复 (每项独立 commit)
4. 每项修复后跑 gate

### Gates
- `npm --prefix web run build`
- `python -m pytest tests/test_web_product_copy.py -q --tb=short`
- `git diff --check`

---

## P3: Design System Foundation

**来源:** 复盘 §7.1.1-§7.1.5, §10 — 无 design token, 组件库不统一
**优先级:** P3
**风险:** 低 (只加文档 + 轻量 token 提取, 不改组件实现)

### 交付物

1. **Design Tokens** (`web/src/design/tokens.ts`)
   - Colors 色板 (复用现有 Tailwind 使用模式)
   - Spacing scale
   - Typography scale
   - 不做大规模 CSS 重写

2. **Component Usage Doc** (`docs/dev/design-system.md` 或更新现有)
   - 现有组件清单
   - 每个组件的 intended usage
   - 状态覆盖要求 (loading/empty/error)
   - CTA 规则
   - 空状态规则
   - Demo badge 规则
   - Safety notice 规则

3. **Page Structure Rules** (可合并到 design-system.md)
   - 14 个页面的结构模板
   - 标题层级规则
   - 侧边栏项目规则

### 实现单元

| Unit | File | Description |
|------|------|-------------|
| U1 | `web/src/design/tokens.ts` | Design token constant definitions |
| U2 | `docs/dev/design-system.md` | Component usage doc + page structure rules |

### Gates
- `npm --prefix web run build` (if tokens.ts referenced)
- `git diff --check`

---

## P4: Autopilot Simplification

**来源:** 复盘 §8.1-§8.2, §9.2 L6 — 1012 行自指涉系统, 维护成本上升
**优先级:** P4
**风险:** 低 (只写分析文档，不改 autopilot 代码)

### 交付物

1. **Autopilot Complexity Analysis** (`docs/dev/autopilot-simplification-analysis.md`)
   - 当前 1012 行的结构分解
   - 哪些规则实际触发过 (有证据) vs 哪些从未使用
   - 冗余规则识别
   - 不必要的停止条件
   - 简化方案和风险
   - 不做实际修改，只分析

### 分析维度

| 维度 | 关注点 |
|------|--------|
| 规则冗余 | 哪些规则在实际 30 loops 中从未触发 |
| 复杂度密度 | 哪些章节可以合并/精简 |
| 自指涉风险 | 哪些规则在治理 "治理 autopilot 的 autopilot" |
| 技能依赖 | mandatory skill gates 是否实际可用 |

### Gates
- `git diff --check`

---

## P5: Docs Governance Cost Reduction

**来源:** 复盘 §9.2 L7 — 文档治理成本被低估, truth drift 多次发生
**优先级:** P5
**风险:** 低 (小 batch，每 batch 独立 commit)

### 策略

- 只清理明显的 overclaim / stale / redundant 文档
- 不改动涉及 code truth 的文档 (除非 code truth 已明确证明文档错)
- 小 batch, 每 batch 2-3 个文件

### 候选清理项

| Batch | Target | Action |
|-------|--------|--------|
| 1 | ~30 implementation notes | 归档 stale notes (状态标记) |
| 2 | user guides (zh/en) | 确认与当前 Web UI 一致 |
| 3 | design/ 目录 | 确认 design doc 状态标记 |

### Gates
- `git diff --check`
- `ruff check docs/ .claude/commands/` (if .md changed significantly)

---

## Execution Order & Auto-Continue

```
P1 (User Validation Kit)
  → gate
  → commit/push
  → P2 (Web UX Remediation)
  → gate
  → commit/push
  → P3 (Design System Foundation)
  → gate
  → commit/push
  → P4 (Autopilot Simplification Analysis)
  → gate
  → commit/push
  → P5 (Docs Governance Batch 1)
  → gate
  → commit/push
```

**Auto-continue contract:** 每个 P 完成后不停止，直接进入下一个 P，除非触发 HARD_STOP 条件。

**P1 特殊规则:** 只做 materials/tools 文档，不伪造真实用户。User Validation Kit 完成后输出 `HARD_STOP_PRODUCT_DECISION` — 文档就绪，需要真实用户。P2-P5 在 P1 后继续。

---

## Hard Constraints (all priorities)

- 不读取 .env/secrets
- 不调用真实 LLM/Cubox/Upstage
- 不处理真实私人资料
- 不写真实 Obsidian vault
- 不做 RAG/embedding/vector DB
- 不恢复 Graph/Sensemaking 扩张
- 不新增大型依赖
- 不 force push
- 不 auto approve
- 不破坏 explicit approval/human_approved 语义
