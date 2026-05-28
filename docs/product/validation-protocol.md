# MindForge User Validation Protocol

版本: v1.1
日期: 2026-05-28
状态: ready (waiting for real users — HARD_STOP_PRODUCT_DECISION)

---

## 0. Validation Scope Clarification

### 已验证的启动方式

```
GitHub fresh clone
  → pip install -e '.[web]'
  → npm install && npm run build (web/)
  → python -m mindforge web --workspace <ws>
  → 用户在 Web UI (/setup) 手动配置 API key
  → real provider (qwen3.6-plus) 主路径 dogfood 通过
```

此路径已在 Dogfood v2 (2026-05-28) 中完整验证：Import → AI Draft (真实 LLM) → Explicit Approve → Library → Recall → Wiki → Export 全部 PASS。

### 尚未验证

| 项目 | 状态 | 说明 |
|------|------|------|
| packaged install (pip/brew/one-liner) | 未验证 | 无 wheel/dist 发布 |
| one-command install | 未验证 | 需多步手动操作 |
| 非技术用户自安装 | 未验证 | 当前需 GitHub clone + npm/pip |
| 非技术用户自配置 API key | 未验证 | 需知道什么是 API key / endpoint |

### 本轮 5-User Validation 范围

**本轮不要求非技术用户自己 clone/install/配置 API key。**

推荐方式：由 facilitator 预先启动 MindForge Web 服务器（demo/fake 模式，零 API key），用户**只通过浏览器**完成 MindForge 知识管理闭环。

安装/部署/onboarding 体验作为单独的 **future packaging workstream**，不混入本轮产品价值验证。

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
- **Facilitator 预先启动** Web 服务器（demo/fake 模式，零 API key 需求）
- 用户只通过桌面浏览器访问 `http://127.0.0.1:8765`
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
   - 用户打开浏览器访问已启动的 MindForge Web
   - 观察第一反应
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

---

## 附件 A: Test Script

### 参与者引导语 (观察者朗读)

> 这是一个帮助你整理个人知识的工具。我们想知道第一次使用的人能不能顺利上手。
> 接下来我会给你几个小任务。请一边操作一边说出你的想法 — 这不是考试，没有正确答案。
> 如果卡住了，告诉我你卡在哪里就好，我会记录但不会帮忙。

### Task 1: 了解当前工作区 (3 min)

引导语: "你已经打开了 MindForge 的主页。花三分钟随便看看，告诉我你看到了什么，你觉得这个工具能做什么。"

观察要点: 第一眼停留位置、是否注意到 QuickStartWizard、是否能理解卡片布局/侧边栏导航。完成判断: 用户说出至少 2 个功能或模块名称。

### Task 2: 创建自己的工作区 (3 min)

引导语: "现在点击 'Create Demo Workspace'，按照提示完成初始设置。"

期望路径: QuickStartWizard → Step 1 了解 → Step 2 创建 Demo Workspace → Step 3 探索 → 进入 Library。完成判断: 成功创建并看到 Library 中的卡片。

### Task 3: 导入一段内容并审阅 (4 min)

引导语: "现在导入一段文字让工具帮你分析。内容是: 『今天和产品团队讨论了用户反馈系统，我们决定在下一个版本中加入 NPS 评分和用户行为追踪。技术上需要前端埋点和后端存储。优先级 P1，预计两周完成。』导入后处理它，然后去 Review 页看看。"

期望路径: Sources → Add Source → 输入内容 → Process Now → Review → 查看 draft → Approve。完成判断: 成功导入 → 触发处理 → 在 Review 看到 draft → 执行审批。

### Task 4: 检索刚才的知识 (3 min)

引导语: "在 Recall 页面搜索 'NPS' 看看能找到什么。"

期望路径: Recall → 输入 "NPS" → 看到卡片 → (可选) 展开 explain 面板。完成判断: 搜索找到了审批过的卡片。

### Task 5: 生成一篇总结 (3 min)

引导语: "基于知识库生成一篇 Wiki 总结，然后导出到本地文件。"

期望路径: Wiki → 生成 Wiki → Export → 选择格式 → 下载。完成判断: Wiki 生成成功 + 导出下载了文件。

备注: 任何 task 超过 2 倍预期时间标记为 blocked。不暗示正确做法，不提示功能位置。

---

## 附件 B: Observer Checklist

### Session Info
记录 Participant ID、Date、Start/End Time、Browser、录屏同意。

### Pre-Session Check
- 应用正常启动（零配置 auto-fallback）
- 浏览器打开，首页加载完成
- 录屏已开始（如已同意）
- Observer 已就位（不干预姿态）

### 每 Task 记录项
- 开始/结束时间、持续时间
- 完成状态 (Y/N/Partial)
- Task-specific 指标（如 Task 1: 第一个点击位置、第一屏停留时间、说出的功能名称数）
- 卡住点/困惑点
- 用户引语

### 情绪记录
每 task 后标记用户情绪: Frustrated / Neutral / Engaged / Delighted。

### 总体观察
- 最大亮点
- 最大障碍
- 用户最希望改变的
- Observer 自我评价（是否有无意引导）

### Post-Session 数据汇总
Total tasks completed、Total time、外部帮助次数、是否说 "会用这个工具"、NPS。

---

## 附件 C: Feedback Form

### Likert Scale (1-5)

| # | Question |
|---|----------|
| Q1 | 我清楚地理解了这个工具能帮我做什么 |
| Q2 | "AI 生成草稿 → 我审批" 这个流程让我觉得有掌控感 |
| Q3 | 我能独立完成整个操作流程（不需要别人帮忙） |
| Q4 | 界面的引导和提示信息是清晰有用的 |
| Q5 | 我会考虑在日常生活中使用这个工具 |

### NPS
How likely are you to recommend MindForge to a friend or colleague? (0-10)

### Open Questions
- Q6: 在使用过程中，最让你困惑的是什么？
- Q7: 你觉得这个工具最有价值的功能是什么？
- Q8: 如果你可以改变一件事，你会改变什么？

### Optional Info
知识管理工具熟悉程度 (新手/有一些经验/老手)、平时用什么工具记笔记。

---

## 附件 D: Sample Workspace Validation

在 User Validation 之前验证 demo workspace 和所有主路径页面在 auto-fallback fake provider 下正常工作。

前置条件: 零配置启动 `mindforge web --port 8766 --no-open`，浏览器打开 `http://localhost:8766`。

### 验证清单

1. QuickStartWizard 流程: 首页显示向导 → Step 1/2/3 正常 → 创建 Demo Workspace 成功 → Console 无 error
2. Demo Cards: 至少 6 张卡片、status = human_approved (approval_method = demo_sample)、内容完整、不携带真实私人数据
3. 主路径页面可用性: Home/Setup/Sources/Review/Library/Recall/Wiki/Export 全部加载正常
4. Recall 功能: 搜索 "AI" 返回匹配结果、搜索不存在内容返回空状态、explain 面板可用
5. 页面引导: 8 个主路径页面 OnboardingHint 正确显示
6. Console Error: 0 errors, 无意外 warning, 无 4xx/5xx, 无 API key/secret 泄露
7. i18n: 中英文界面完整、Onboarding text zh/en key 数量匹配

### 执行方式
浏览器 MCP 自动执行，或手动浏览器验证。失败处理: P0/P1 block → 修复后重跑。
