# MindForge User Validation Protocol

版本: v1.0
日期: 2026-05-28
状态: ready (waiting for real users — HARD_STOP_PRODUCT_DECISION)

---

## 背景

MindForge 经过了 4 轮开发迭代 (Mint1-Mint4)，已建成完整的端到端知识编译管线，但目前**零真实用户验证**。核心产品假设（非技术用户能独立完成知识管理闭环）从未被证明。

本协议定义了验证该假设的完整流程。

---

## 验证目标

**Core Hypothesis:** 非技术用户能在首次使用 MindForge 时，在 15 分钟内独立完成完整的主路径循环（了解当前知识 → 导入一段内容 → 审阅 AI 生成的草稿 → 显式审批 → 浏览知识库 → 检索 → 生成总结 → 导出）。

**Sub-hypotheses:**
1. 用户能理解 "AI 生成草稿 → 人工审阅 → 显式审批" 的核心语义
2. 用户能独立完成所有步骤（不需要外部帮助）
3. 用户完成后的 NPS ≥ +30

---

## 测试条件

### 环境要求
- 零配置启动 (auto-fallback fake LLM — 已验证可用)
- 干净的首次运行状态（无预设工作区）
- 标准笔记本电脑，桌面浏览器 (Chrome/Firefox/Edge)
- 本地运行，无网络需求

### 参与者筛选
- **目标用户:** 非技术用户，日常有记笔记/整理信息需求
- **排除:** 开发者、AI 工程师、曾在 AI 产品团队工作过的人
- **人数:** 最低 3 人，目标 5 人
- **招募方式:** 个人社交网络、朋友推荐

### 观察者
- 1 名观察者，全程不干预
- 观察者只记录，不回答问题，不提示操作
- 用户明确求助时可回答 "请试试你觉得对的方式"

---

## Session 结构

```
总时长: 45 分钟

1. 引导 (2 min)
   - "这是一个帮助你整理知识的工具，我们希望了解第一次使用的体验"
   - "没有对错，如果卡住请说出你的想法"
   - 征得录屏同意

2. 自由探索 (5 min)
   - 用户自行打开应用，观察第一反应
   - 记录: 第一个点击是什么、在第一屏停留多久

3. Scenario Tasks (25 min)
   - 5 个任务，按顺序进行
   - 每个任务有预期时间上限
   - 超过 2 倍上限仍未完成 → 记录为 blocked，跳到下一个任务

4. 反馈 (5 min)
   - 填写 feedback form
   - 简短口头交流

5. 收尾 (3 min)
   - 感谢参与者
   - 回答参与者的问题（此时可以解释产品设计）
```

---

## Kill Criteria

以下任一条件触发，产品方向需重新评估：

| # | Criteria | 判定 |
|---|----------|------|
| K1 | ≥3/5 用户无法在 ≤15 min 内完成 tasks 2-4 (导入→审批→浏览) | KILL or MAJOR REWORK |
| K2 | ≥3/5 用户不理解或认为 explicit approval 没有价值 | KILL |
| K3 | ≥3/5 用户说 "我不会用这个工具" | KILL |
| K4 | 平均任务完成时间 > 25 min | KILL or MAJOR REWORK |

**Conditional GO:** 2 人完成但 1 人失败 → 针对性修复 → re-validate
**GO:** ≥3/5 在 ≤15 min 完成 + NPS ≥ +30

---

## 成功标准

| 指标 | 目标 | 测量方式 |
|------|------|---------|
| 任务完成率 | ≥60% (3/5) 完成全部 5 个 tasks | Observer checklist |
| 平均完成时间 | ≤15 min (tasks 2-4) | Observer time log |
| Approval 理解率 | ≥60% (3/5) 能正确解释为什么需要审批 | Feedback form Q2 + 口头 |
| NPS | ≥ +30 | Feedback form |
| 无外部帮助率 | ≥80% 的 task attempts 无 observer 介入 | Observer checklist |

---

## 数据收集

### 定量
- 每 task 的开始/结束时间
- 每 task 的成功/失败/放弃
- 点击数 (如可行)
- Feedback form Likert 评分
- NPS 评分

### 定性
- 用户自言自语/思考出声记录
- 观察者笔记：卡住点、困惑点、惊喜点
- 用户口头反馈
- 录屏回放分析

---

## 后续行动

| 结果 | 行动 |
|------|------|
| GO | P1 修复 validation 发现的问题 → 启动真实 LLM 集成 (Direction D) |
| Conditional GO | 针对性修复 → 第二轮 re-validation (新用户) |
| KILL | 写 honest post-mortem → 评估 pivot 方案 → 决定 archive 或方向调整 |

---

## 附件

- Test Script: `docs/product/test-script.md`
- Observer Checklist: `docs/product/observer-checklist.md`
- Feedback Form: `docs/product/feedback-form.md`
- Sample Workspace Validation: `docs/product/sample-workspace-validation.md`
