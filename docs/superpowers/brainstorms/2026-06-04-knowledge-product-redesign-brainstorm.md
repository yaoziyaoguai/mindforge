---
name: knowledge-product-redesign-brainstorm
description: Structured brainstorm for MindForge knowledge product redesign — addresses extraction value deficit and display UX deficit
metadata:
  type: brainstorm
---

# Knowledge Product Redesign Brainstorm

Date: 2026-06-04
Context: Post-audit (17-section audit completed). Display 4/10, Extraction 3/10. Root cause: cards lack insight value, not just poor display.

## 1. Problem Redefinition

### 根问题 A：知识提取没有价值

当前 pipeline 产出的是"原文摘录 + 摘要 + 标签 + 考试题"，不是**可复用知识**。

一张有价值的知识卡片应该回答：
- 这条知识的核心洞察是什么？（不是摘要，是 insight）
- 它解决什么实际问题？
- 适用于什么场景？不适用于什么场景？
- 用户以后为什么要回来读它？
- 它能转化为什么原则、方法、决策或行动？
- 它和已有知识发生什么关系？

**本质问题**：distill prompt v1 要求"忠实提炼"（faithfully extract），这鼓励的是 paraphrase 而不是 insight。模型没有被要求做判断、区分、提炼、连接。

### 根问题 B：知识展示没有产品体验

当前页面像调试台，7 个技术字段平铺，关系区包装成"图谱"但实际是同标签/同来源。

**本质问题**：展示层忠实反映了 pipeline 的产出结构，而不是反映用户的阅读需求。信息架构以"pipeline 产出了什么"为中心，不是以"用户需要知道什么"为中心。

### 两个问题的关系

如果只修展示（B），卡片内容本身没有价值，美化只是表面。
如果只修提取（A），展示层仍然是调试台风格，价值信息被淹没。

**必须先解决 A，再解决 B**。但 B 的 SPEC 可以并行编写，因为展示层需要知道 v2 卡片的字段才能设计布局。

---

## 2. 产品方向备选

### 方向 A：个人知识引擎（推荐）

**定位**：MindForge 是你个人的知识引擎，帮你把摄入的信息变成可复用的决策资产。

**核心价值**：
- 输入原文 → AI 提炼出真正有价值的洞察卡片
- 人工审阅确认 → 卡片变成可信知识
- 日后再遇到相关问题时，能检索到并应用这条知识

**关键特征**：
- 卡片回答"核心洞察"、"适用场景"、"限制条件"、"可复用原则"
- 标签是知识分类，不是技术元数据
- 关系区叫"相关知识"，只展示真正有语义关联的卡片
- 首页按 topic/标签组织，不是按 pipeline 阶段
- 审阅流程是确认/编辑/降级，不是 approve/reject 二选一

**优点**：
- 直接解决根因（提取价值 + 展示体验）
- 保持 local-first、no-embedding、no-RAG
- 符合用户心智模型（个人知识管理，不是企业知识库）

**缺点**：
- 需要重新设计 distill prompt（质量取决于 LLM 能力）
- 旧卡片需要 fallback 处理
- 审阅流程从 approve/reject 变为多操作，前端需要改动

**风险**：
- 如果 LLM 产出质量不够好，v2 prompt 可能产生更多垃圾
- FakeProvider 需要产出有意义的 demo 内容，否则 demo 体验更差

### 方向 B：AI 辅助笔记增强器

**定位**：MindForge 是 AI 辅助的笔记增强工具，帮你把笔记变得更结构化。

**核心价值**：自动给笔记加标签、摘要、关系、分类。

**为什么不推荐**：
- 这是 Notion/Obsidian AI 已经做的事
- 不解决"洞察价值"问题，只是自动分类 + 摘要
- 与"local-first 个人 AI 知识基座"定位不符

### 方向 C：知识图谱可视化工具

**定位**：MindForge 是知识图谱的可视化和导航工具。

**核心价值**：展示知识之间的关系网络，帮助发现知识间的隐藏连接。

**为什么不推荐**：
- 需要 embedding / vector DB / GraphRAG，违反 local-first 约束
- 当前关系数据是同标签/同来源，包装成图谱是虚假繁荣
- 4 张卡片的 vault 无法支撑有意义的图谱展示
- 不是当前用户的核心需求

---

## 3. Knowledge Card v2 结构备选

### 备选 A：最小洞察模型（推荐）

**核心思想**：卡片只保留回答"这条知识为什么有价值"的字段，其余进入折叠区。

**必需字段**：
```
title                  — 知识标题
knowledge_type         — concept / claim / insight / method / decision / question / evidence / todo
one_sentence_takeaway  — 一句话核心（用户能立刻看懂这条知识说什么）
problem_it_solves      — 解决什么问题（为什么要存这条知识）
core_insight           — 核心洞察（不是摘要，是经过思考后的提炼）
applicable_context     — 适用场景（什么时候用这条知识）
reusable_principle     — 可复用原则/方法（能直接应用的东西）
limitations_or_caveats — 限制条件（什么时候不适用）
supporting_evidence    — 支撑证据（原文中的关键引述，可追溯到 source）
tags                   — 知识分类标签
source_trace           — 来源追溯（URL、文件名、原文路径）
approval_state         — ai_draft / human_approved / human_rejected
human_note             — 人工备注（只能由人填写，不能由 AI 生成）
```

**折叠字段**（技术证据区）：
```
related_questions      — 相关问题（供审阅和后续思考）
next_actions           — 下一步行动（从知识推导出的行动项）
stage_models           — pipeline 阶段模型记录
prompt_versions        — prompt 版本记录
quality_score/level    — 质量评分
```

**优点**：
- 每个字段都有明确的用户价值
- 阅读路径清晰：takeaway → insight → context → principle → limitations
- 字段数量适中（15 个核心 + 5 个技术），不会 overwhelm
- 兼容 v1 卡片的字段映射

**缺点**：
- `one_sentence_takeaway` 和 `core_insight` 可能有重叠
- `problem_it_solves` 对某些 concept 类型卡片可能不适用
- 需要 distill prompt v2 能稳定产出这些字段

**风险**：
- LLM 可能产出空泛的 `applicable_context` 或 `limitations_or_caveats`
- `reusable_principle` 如果不是具体可操作的，就变成鸡汤

### 备选 B：完整学术模型

**核心思想**：卡片像学术论文一样完整，包含 abstract、methodology、results、discussion、references。

**字段**：20+ 个字段，包括 confidence score、evidence quality、counterarguments、related_work 等。

**为什么不推荐**：
- 字段太多，用户阅读路径不清晰
- 个人知识管理不需要学术级别的结构
- distill prompt 很难稳定产出这么多字段
- 审阅页面会变得极其复杂

### 备选 C：极简双字段模型

**核心思想**：卡片只有两个核心字段 —— "这条知识说什么"和"这条知识为什么重要"，其余全部折叠为技术证据。

**字段**：title, core_statement, why_it_matters, tags, source_trace, approval_state, human_note + 一个 raw_evidence 折叠区

**为什么不推荐**：
- 信息太少，无法指导用户"如何应用这条知识"
- 无法区分 concept / method / decision 等不同类型的知识
- `applicable_context` 和 `limitations_or_caveats` 是独立维度的信息，不应该被压缩

---

## 4. UI 信息架构备选

### 备选 A：五层阅读路径（推荐）

**Layer 1 — 价值首屏（首屏可见）**：
- 标题
- 一句话核心（one_sentence_takeaway）
- 知识类型标签
- 核心洞察（core_insight）

**Layer 2 — 应用信息（向下滚动）**：
- 适用场景
- 可复用原则
- 限制条件
- 支撑证据（带原文追溯）

**Layer 3 — 知识连接（相关区域）**：
- 相关知识（同主题/有实质关联的卡片）
- 来源追溯（原文链接、本地文件路径）

**Layer 4 — 人工协作（审阅/编辑区）**：
- 人工备注
- 相关问题
- 下一步行动
- 审阅操作（确认/编辑/降级/合并）

**Layer 5 — 技术证据（折叠区，`<details>`）**：
- pipeline 阶段记录
- prompt 版本
- 质量评分
- 原始 body 全文

**优点**：
- 阅读路径符合人类理解习惯：先看"是什么"，再看"怎么用"，再看"还有啥"
- 普通用户只看 Layer 1-2 就能获得价值
- 高级用户和技术调试可以看到 Layer 5
- 技术字段不污染主要阅读路径

**缺点**：
- 需要前端重构 CardWorkspace.tsx
- 需要 API 返回新字段
- Layer 3 "相关知识"需要区分"真正关联"和"同标签"

### 备选 B：标签页式布局

**设计**：用标签页分组织内容——"概览"、"详情"、"关系"、"技术"。

**为什么不推荐**：
- 标签页割裂了阅读流程，用户需要在标签间跳转
- 个人知识卡片不是 SaaS 仪表盘，不需要标签页的复杂度
- 概览页会仍然信息过载，违背"首屏即价值"原则

### 备选 C：渐进展开式

**设计**：只有一个长页面，每个段落都是可折叠的，默认只展开"一句话核心"和"核心洞察"，其余手动展开。

**为什么不推荐**：
- 用户不知道哪些段落值得展开
- 没有明确的阅读优先级
- 与备选 A 相比，缺少"应用信息"的结构化分组
- 实现上更简单，但体验上不如分层明确

---

## 5. 最终推荐方向

| 维度 | 推荐 |
|------|------|
| 产品方向 | A — 个人知识引擎 |
| Card v2 结构 | A — 最小洞察模型 |
| UI 信息架构 | A — 五层阅读路径 |

**推荐组合的逻辑**：
- 三个方向 A 是互相配合的——产品方向定义了"知识引擎"，Card v2 提供了"最小洞察"结构，UI 实现了"五层阅读路径"
- 都保持 local-first，不引入 embedding/RAG/vector DB
- 字段数量可控，实施路径清晰
- 旧卡片可以 fallback 到 v2 结构

---

## 6. 明确不做什么

1. **不做 RAG / embedding / GraphRAG / vector DB** — 保持 local-first
2. **不做知识图谱可视化** — 当前关系数据不够支撑
3. **不做 Obsidian 双向同步** — 不在本轮范围
4. **不做团队协作** — 个人工具定位
5. **不做自动 approve** — 保持 ai_draft / human_approved 边界
6. **不做同标签伪装成相关知识** — 关系区只展示真正有语义关联的卡片
7. **不做"完整学术模型"卡片** — 字段过多，用户不需要
8. **不做"极简双字段"卡片** — 信息太少，无法指导应用
9. **不删除 v1 卡片的任何字段** — 只增加，不破坏
10. **不让 AI 伪造 human_note** — human_note 只能由人填写

---

## 7. 为什么不直接开始写代码

1. **Card schema 变更影响面广** — 涉及 YAML frontmatter、CardSummary dataclass、presenter、API response、前端组件、测试。没有 SPEC 直接改代码会引入不一致。
2. **distill prompt 是黑盒** — prompt 输出质量直接影响卡片价值。需要先定义输出 JSON schema 和 anti-hallucination 约束，否则实现后可能产出更差的卡片。
3. **FakeProvider 需要重新设计** — 当前 `[fake]` 占位内容严重影响 demo 体验。需要定义有意义的 demo 输出格式，否则 demo 用户看到的第一印象是垃圾。
4. **UI 重构需要明确字段映射** — 前端组件需要知道 v2 有哪些字段、哪些默认展示、哪些折叠、哪些只给高级用户。没有 SPEC 直接改 UI 会重复审计中发现的问题。
5. **approval 边界不能模糊** — human_note 只能由人填写、ai_draft 不能自动变成 human_approved、降级操作需要明确定义。这些业务规则需要在代码之前确定。
6. **分阶段实施需要计划** — Card v2、Prompt v2、UI Redesign 是三个独立但相关的变更。需要明确实施顺序和回滚策略。
