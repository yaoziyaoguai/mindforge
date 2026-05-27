# MindForge 产品创新审计和机会地图

**日期**: 2026-05-28
**阶段**: 产品策略审计（非工程实现、非架构审计）
**任务类型**: `product_strategy`
**触发技能**: `/brainstorming` ✅, `/office-hours` ✅
**依据文档**: mf-autopilot.md, CURRENT_PROJECT_STATE.md, progress-ledger.md, engineering-workflow.md, 118-post-governance-audit, 133-codex-red-team-audit, 092-capability-map, 093-industry-benchmark, 135-dogfood-v2, 137-web-ux-deepening, 119-fake-provider-keyword

---

## 1. Executive Summary

### 核心判断: 重组式继续 (Conditional Go with Restructuring) — 得分 6.5/10

**继续理由:**

MindForge 的 `approval-first` 知识处理边界是 PKM 市场中真实且未被充分服务的差异化。现有工具分为两类：用户手动整理（Obsidian/Logseq）或 AI 直接写入知识库（Notion AI/Tana）。MindForge 的 `ai_draft → human_approved` 显式审批语义在代码、测试、dogfood 中一致执行，不存在 bypass——这是可验证的差异化，不是营销叙事。

**重组理由:**

1. **产品习惯假设未经验证**：两个独立审计给出 Conditional Go (6.1 和 6.4/10)，共同前提是"需要产品习惯证据才能继续扩张"。当前所有 dogfood 成功来自 synthetic/fake/local 数据，不等价于真实用户行为验证。
2. **主路径存在 P1 阻塞**：demo/fake 模式下仍要求显式模型配置，用户无法完成首次 Source → Draft → Review → Approval → Library → Recall → Export 循环。
3. **产品策略分散**：AUTOPILOT-QUEUE 中治理升级、UX 打磨、任务清理并列，缺乏基于用户价值的明确优先级排序。
4. **竞争护城河不存在**：approval-first 差异化需要 (a) 真实用户习惯数据证明其改变知识管理行为，(b) 足够顺滑的体验让用户愿意迁移——当前两者都不具备。

**如果继续，怎么继续:**

- **主 bet**: Direction A (Product Main Path Deepening) — 让首次用户在 15 分钟内完成完整循环
- **次 bet**: Direction F (Structured Knowledge Workbench) — 让 Library 成为真正的知识工作区
- **第三 bet**: Direction C (Recall/Search Quality Lab) — 建立检索质量测量体系
- **冻结**: Direction D (Real LLM), Direction E (Collaboration), Graph/Sensemaking 扩张
- **2 周验证假设**: 非技术用户能否在 15 分钟内完成首次完整主路径循环
- **Kill criteria**: 如果 2 周后无法让 ≥3/5 非技术用户在 ≤15 分钟内完成首次循环 → 启动归档讨论

---

## 2. 产品定位与差异化重审

### 2.1 MindForge 到底是谁

**一句话**: MindForge 是 local-first, approval-first personal knowledge compiler。

**核心工作流**:
```
Source/Import → ai_draft → Review → explicit approval → human_approved
→ Library → Recall (BM25) / Wiki (LLM synthesis) → Export
```

**MindForge 不是**（这些边界在当前代码和文档中一致执行）:
- 不是 RAG 平台
- 不是 GraphRAG
- 不是 Obsidian 插件
- 不是云端 SaaS
- 不是笔记编辑器
- 不是 read-it-later
- 不自动审批

### 2.2 与竞品的差异化矩阵

| 维度 | Obsidian | Logseq | Readwise | Tana | MindForge |
|------|----------|--------|----------|------|-----------|
| 核心输入 | 用户手写 | 用户手写 | 阅读高亮 | 结构化笔记 | 本地 source 文件 |
| AI 角色 | 可选插件 | 可选插件 | 摘要/聊天 | 结构/提取 | **仅生成草稿** |
| 知识确认 | 用户直接编辑 | 用户直接编辑 | 用户高亮 | 用户/AI 混合 | **显式人工审批** |
| 检索方式 | 文件搜索+双链 | 块搜索+查询 | 库搜索+AI 聊天 | 结构化搜索 | **BM25 词法+可解释** |
| 本地优先 | 强 | 强 | 弱(云端) | 混合 | **强(零网络 demo)** |
| 审批边界 | 无 | 无 | 无 | 弱 | **强(explicit gate)** |

### 2.3 MindForge 的独特机会

**机会陈述**: 做成 **approval-based knowledge card workflow**——现有 PKM 工具中没有人在做"AI 辅助加工但人最终确认"这个垂直场景。

**机会的独特性和可防御性**:
1. 输入是本地 source，不是手写笔记 → 服务"有大量现成资料需要加工"的用户
2. AI 只能生成 `ai_draft`，不能污染长期知识 → 解决了"AI 幻觉污染个人知识库"的信任问题
3. `human_approved` 才进入 Library/Recall/Wiki/Export → 每一条正式知识都可追溯来源和审批决策
4. 检索、Wiki、关系、导出都能解释来源和边界 → 满足"可解释性胜过便利性"的用户群体

**机会的风险**:
- 这个用户群体是否存在、规模多大——完全未知
- approval 步骤是否会让用户觉得"太麻烦"而非"很安心"——未验证
- 当前产品体验是否足够顺滑让用户愿意完成这个循环——P1 阻塞表明还不够

---

## 3. 10 个战略问题回答

### Q1: MindForge 到底解决什么别人没解决的问题？

**知识摄入的"信任鸿沟"**。现有 PKM 工具分两类：(a) Obsidian/Logseq 让用户完全手动管理，信任不是问题但效率低；(b) Notion AI/Tana/Mem 让 AI 直接写入知识库，效率高但信任是黑盒。MindForge 在中间开辟了第三条路——AI 加工资料生成可审阅草稿，人确认后才进入长期知识库。这个"AI 辅助但人最终确认"的定位在 PKM 市场中是真实的空白。

**证据支撑**: `ai_draft → human_approved` 语义在 `approve_card()` 中硬编码执行（只允许 `ai_draft → human_approved` 单一路径，其他 status 拒绝），代码、测试、dogfood 三方一致，无 bypass。

### Q2: 当前版本最不可替代的差异化能力是什么？

**Explicit approval boundary**。这不是一个功能，而是一个贯穿整个系统的架构约束：
- `approve_card()` 只接受 `ai_draft → human_approved`
- `approve_explicit_card()` 不替用户选择默认卡片
- Library 默认只显示 `human_approved`
- Wiki 只从 approved cards 派生
- Recall 默认过滤到 `human_approved`

这套语义在 19 个 router、所有 service、所有 Web 页面中一致执行。它是系统级的 invariant，不是某个页面的 feature。

### Q3: 与现有 PKM 工具的竞争护城河在哪？

**当前: 没有护城河**。承认这个事实很重要。

护城河的形成需要两个条件，目前都不具备:
1. **用户习惯数据**: 需要证明 approval-first 工作流确实改变了用户的知识管理行为（留存、卡片质量、回顾频率等指标）
2. **迁移成本**: 需要让用户愿意把现有资料导入 MindForge 走审批流程，这要求导入体验足够顺滑

**潜在护城河方向**:
- 如果用户积累了足够多的 approved cards，这些卡片的质量（经人工确认）会形成数据网络效应——用户不会轻易放弃已确认的知识库
- 但当前这个网络效应为零，因为没有真实用户

### Q4: 按创新性而非可行性排序，哪个方向最有突破潜力？

**Direction C — Recall/Search Quality Lab**。

可解释的个人知识检索质量测量在 PKM 领域几乎不存在。大多数工具要么是黑盒语义搜索（你不知道为什么搜到这个），要么是简单全文搜索（你知道为什么但搜不全）。一个系统化的检索质量实验室——包含失败查询回顾、检索 fixture dashboard、BM25 tuning report、查询改写建议——是 PKM 领域被系统性忽视的创新方向。

**为什么不是其他方向**:
- Direction A (主线深化): 必要但不创新——做好审批工作流是基本功，不是突破
- Direction D (真实 LLM): 每个 PKM 工具都在做 AI，不是差异化
- Direction F (结构化工作台): Tana 已经做了，只是没做 approval-first

### Q5: MindForge 真正应该服务的目标用户画像是怎样的？

**"知识加工者"(Knowledge Processor) 而非"笔记写作者"(Note Taker)**。

具体画像:
- 有大量现成资料积累（论文、技术文档、读书笔记、项目报告、学习材料）
- 需要 AI 辅助加工成结构化知识，但不信任 AI 直接写入长期知识库
- 重视知识的可追溯性和可解释性胜过便利性
- 愿意花时间审批 AI 输出以换取更高质量的个人知识库
- 技术能力中等以上（能理解本地部署、文件导入等概念）

**明确不是目标用户**:
- 每天手写笔记的 Obsidian/Logseq 用户（MindForge 不做编辑器）
- 依赖高亮捕获的 Readwise 用户（MindForge 不做 read-it-later）
- 需要团队协作的知识管理团队（MindForge 是 personal tool）

### Q6: 用户形成使用习惯的关键路径和触发点在哪？

**关键循环**:
```
导入 source → 看到 AI draft → 审批通过 → 在 Library 看到结构化卡片 → 用 Recall 找回 → 用 Wiki 回顾
```

**最关键触发点**: 用户首次完成这个循环 ≤15 分钟。

如果用户在 15 分钟内能走完"导入一份自己的资料 → AI 生成草稿 → 自己审批 → 在 Library 看到卡片 → 搜索找到它 → 导出/分享"，习惯形成的概率大幅提升。

**当前最大障碍**: P1 管道阻塞——demo/fake 模式下仍需显式模型配置，直接打断了这个循环的第一步（source → draft）。

**次要障碍**:
- Setup 页面像基础设施配置而非产品引导
- 缺少 sample workspace 让用户零配置体验完整路径
- Review queue 缺少状态时间线和审批历史

### Q7: 如果只选 3 个最重要的 bet，应该选哪 3 个？

**Bet 1 (主): Direction A — Product Main Path Deepening**
- 修复 P1 管道阻塞，让 demo 模式真正零配置
- 设计 guided onboarding（≤15 分钟首次循环）
- 打磨 Review queue 的 clarity 和 status timeline
- **为什么第一**: 如果用户不能完成基本循环，其他一切都是空中楼阁

**Bet 2 (次): Direction F — Structured Knowledge Workbench**
- Saved views, collections, query builder over approved cards
- Card merge/split/link 深度工作流
- Library 作为真正的主工作区而非只读浏览器
- **为什么第二**: 主路径跑通后，用户在 Library 的"停留时间"直接决定留存

**Bet 3 (第三): Direction C — Recall/Search Quality Lab**
- BM25 tuning report, failed query review, retrieval fixture dashboard
- Query explain UI（让用户理解为什么搜到这个结果）
- **为什么第三**: 检索质量是可验证的差异化，且不依赖真实 LLM

### Q8: 是否应该冻结部分方向以集中资源？

**应该立即冻结**:
1. **Direction D (Real LLM Integration)** — 等主路径用户习惯验证后再做。当前 fake provider 足以证明 pipeline 正确性。真实 LLM 引入成本、隐私、质量一致性风险，且不是差异化来源（每个 PKM 都有 AI）。
2. **Direction E (Knowledge Collaboration/Sharing)** — 个人场景未验证前做协作是本末倒置。且协作需要 auth/sharing/permissions/sync，会根本性改变架构。
3. **Graph/Sensemaking/Entity/Community 扩张** — 已标 lab/internal，维持冻结。capability map 和两个审计都明确结论：不恢复 8 NodeType / mature sensemaking 叙事。

**应该维持在 lab/internal**:
- Graph standalone page, Sensemaking Workspace, Entity Resolution, Community/Topic graph, Extension Plugin

### Q9: 如果用 2 周时间验证一个最关键假设，应该验证什么？

**核心假设**: 非技术用户能否在 15 分钟内完成首次 Source → Draft → Review → Approve → Library → Recall → Export 完整循环？

**为什么这是最关键假设**: 如果这个假设不成立，MindForge 的 approval-first 差异化就只是理论上成立但实际上不可用。用户不会为了"AI 不污染知识库"的哲学正确而忍受一个用不起来的产品。

**验证方法**:
1. 修复 P1 管道阻塞（demo 模式零配置）
2. 设计 guided onboarding 流程
3. 找 5 个非技术用户，给每人 3-5 个 Markdown 文件
4. 观察记录: 导入耗时、draft 理解度、审批决策时间、Library 浏览行为、Recall 成功率、是否愿意再次使用
5. 成功标准: ≥3/5 用户在 ≤15 分钟内完成完整循环，且 ≥3/5 表示"愿意再用"

### Q10: 基于当前证据，应该继续投资、重组还是考虑停止/归档 MindForge？

**重组式继续 (Conditional Go with Restructuring)**。

**与两个独立审计的一致性**:
- Post-governance audit (118): 6.1/10, Conditional Go — "需要产品习惯证据后才能继续扩张"
- Codex red team audit (133): 6.4/10, Conditional Go — "Product Main Path Real Dogfood v2 优先，验证产品假设后再决定"
- 本审计: 6.5/10, Conditional Go with Restructuring — "修复主路径阻塞，2 周内验证核心假设，设定明确 kill criteria"

**重组方案**:
1. 立即修复 P1 管道阻塞（允许 demo 模式零配置运行）
2. AUTOPILOT-QUEUE 重排——产品策略审计结论优先于治理升级和 UX 打磨
3. 设定 2 周验证窗口和明确 kill criteria
4. 如果 2 周后核心假设通过 → 进入 Bet 1+2+3 的 6-8 周深度执行
5. 如果 2 周后核心假设失败 → 启动归档讨论

**不建议停止/归档的理由**: approval-first 差异化是真实且独特的，代码基础已具备核心闭环，P1 阻塞是可修复的工程问题而非产品方向问题。如果核心假设验证通过，MindForge 有潜力成为 PKM 市场中一个独特且有防御力的产品。

**不建议无条件下继续的理由**: 两个独立审计和本审计都指出"需要用户习惯证据"。在没有证据的情况下继续堆功能，只会增加沉没成本。

---

## 4. 6 个候选突破方向评分 (A-F)

### 评分维度说明

| 维度 | 定义 | 评分范围 |
|------|------|---------|
| 用户痛点 (User Pain) | 目标用户当前感受到的问题严重程度 | 0(无痛点)-10(极度痛苦) |
| 差异化 (Differentiation) | 与竞品相比的独特程度 | 0(同质化)-10(完全独特) |
| 创新性 (Innovation) | 在 PKM 领域的新颖程度 | 0(已有成熟方案)-10(全新范式) |
| 构建可行性 (Build Feasibility) | 在当前架构下可实现的难易程度 | 0(需要重写)-10(开箱即用) |
| Dogfood 可行性 (Dogfood Feasibility) | 能否用 synthetic/fake 数据充分验证 | 0(必须真实用户)-10(完全可 synthetic) |
| 战略匹配 (Strategic Fit) | 与 approval-first 核心定位的一致性 | 0(偏离核心)-10(直接强化核心) |
| 风险 (Risk) | 方向失败的概率和影响 | 0(几乎零风险)-10(极高风险) |

### Direction A: Product Main Path Deepening (主线深化)

**描述**: 修复 P1 管道阻塞，打磨 Source→Draft→Review→Approve→Library→Recall/Wiki→Export 全流程，增加 guided onboarding，让用户在 15 分钟内完成首次完整循环。

**具体包含**:
- P1: demo/fake 模式零配置 auto-fallback
- Guided onboarding: sample workspace + step-by-step 引导
- Review queue: status timeline, 审批历史, batch review guardrail
- Library: 首次空状态引导
- Export: CLI `mindforge export` 主命令
- Setup 页面: 从"基础设施配置"变为"产品引导"

| 维度 | 评分 | 说明 |
|------|------|------|
| 用户痛点 | **8** | P1 阻塞直接阻止用户完成首次循环；Setup 像工程配置而非产品引导；无 CLI export |
| 差异化 | **8** | 做好 approval-first 工作流本身就是差异化——目前没人做好 |
| 创新性 | **5** | 增量改进现有路径，非突破性创新；做好审批工作流是基本功 |
| 构建可行性 | **9** | 范围明确，现有代码基础上增量改进；P1 修复是 service 层小改动 |
| Dogfood 可行性 | **9** | 完整主路径可用 synthetic 数据充分验证；browser MCP smoke 已跑通 |
| 战略匹配 | **9** | 直接强化 approval-first 核心价值主张 |
| 风险 | **2** | 低风险，范围可控，无架构变更 |
| **加权总分** | **7.6/10** | |

**2 周验证计划**:
- Week 1: 修复 P1 阻塞 + 设计 guided onboarding + 建立 sample workspace
- Week 2: 找 5 个非技术用户走首次循环，记录时间和反馈

**Kill Criteria**:
- ≥3/5 用户无法在 15 分钟内完成首次循环
- ≥3/5 用户表示"审批步骤太麻烦，不想再用"

### Direction B: Capture/Import Expansion (捕获入口拓展)

**描述**: 浏览器扩展、移动端 share sheet、URL reader、clipboard capture，降低 source 进入 MindForge 的摩擦。

**具体包含**:
- 浏览器扩展: 一键发送网页到 MindForge
- 移动端 share sheet: iOS/Android 分享到 MindForge
- URL reader: 粘贴 URL 自动抓取内容
- Import wizard: 统一导入体验

| 维度 | 评分 | 说明 |
|------|------|------|
| 用户痛点 | **8** | 捕获摩擦是真实 PKM 用户的最大痛点之一；Readwise 的成功证明了这个需求 |
| 差异化 | **6** | 捕获本身不新鲜，但"捕获→AI draft→审批"的链条是独特的 |
| 创新性 | **6** | 捕获技术成熟（浏览器扩展、share sheet），创新在集成而非捕获本身 |
| 构建可行性 | **4** | 跨平台（iOS/Android/Chrome/Firefox/Safari）重工程；移动端需要全新 codebase |
| Dogfood 可行性 | **5** | 浏览器扩展可在本地验证；移动端 share sheet 难以 synthetic dogfood |
| 战略匹配 | **7** | 捕获是主路径的前置步骤，做好捕获能显著增加 Library 卡片数量 |
| 风险 | **7** | 平台碎片化、scope creep（容易变成"做一个 Reader"）、跨平台维护成本 |
| **加权总分** | **5.9/10** | |

**2 周验证计划**:
- Week 1: 浏览器扩展原型（Chrome only, 抓取网页正文→创建 ai_draft）
- Week 2: 5 个用户用扩展导入 10 篇网页，观察 friction 和 draft 质量

**Kill Criteria**:
- 扩展安装/使用 friction 导致 <50% 用户完成首次导入
- 用户反馈"不如直接用 Readwise/Omnivore"

### Direction C: Recall/Search Quality Lab (检索质量实验室)

**描述**: 建立系统化的个人知识检索质量测量体系——BM25 tuning report、failed query review loop、retrieval fixture dashboard、query explain UI、查询改写建议。

**具体包含**:
- Retrieval fixture dashboard: 固定查询集 + 预期结果 + 命中率趋势
- Failed query review: 用户搜索无结果/不满意的查询自动记录和回顾
- BM25 tuning report: 参数调整对召回率/精确率的影响
- Query explain UI: 展示每个搜索结果的 BM25 字段贡献
- Query rewrite suggestion: 基于失败查询建议改写

| 维度 | 评分 | 说明 |
|------|------|------|
| 用户痛点 | **6** | 当前 Recall 对 synthetic 数据可用(91.7% EN)，但真实数据检索质量未知 |
| 差异化 | **7** | 可解释的检索质量测量在 PKM 中几乎不存在；大多数工具是黑盒语义搜索 |
| 创新性 | **7** | 系统化的检索质量实验室在个人知识管理领域是新的——不是新算法，是新方法论 |
| 构建可行性 | **8** | 纯后端+Web dashboard，无外部依赖，现有 BM25 索引可直接复用 |
| Dogfood 可行性 | **9** | 可以构建 comprehensive retrieval fixtures 覆盖各种查询场景 |
| 战略匹配 | **8** | 直接提升 Library→Recall 的用户价值；可解释性与 approval-first 哲学一致 |
| 风险 | **3** | 低风险，范围可控，不需要真实 LLM 或外部服务 |
| **加权总分** | **7.1/10** | |

**2 周验证计划**:
- Week 1: 构建 retrieval fixture dashboard (50 个固定查询 + 预期结果 + 当前命中率)
- Week 2: 实现 failed query review loop（记录、分类、回顾无结果查询）

**Kill Criteria**:
- BM25 tuning 无法将 fixture 命中率提升至 ≥85%
- Failed query review 揭示系统性缺陷（如 tokenizer 无法处理某类关键查询模式）

### Direction D: Real LLM Integration (真实模型集成)

**描述**: Opt-in 真实 LLM 用于卡片生成和 Wiki synthesis 质量验证，建立真实模型下的质量基线。

**具体包含**:
- Real LLM opt-in flow (Web Setup 已有基础)
- 真实模型卡片生成质量评估报告
- Wiki synthesis 真实 LLM 质量验证
- Cost/latency/failure transparency UI
- Prompt preview 和安全 opt-in 机制

| 维度 | 评分 | 说明 |
|------|------|------|
| 用户痛点 | **5** | Fake provider 对 pipeline 验证足够；真实 LLM 是"锦上添花"而非"雪中送炭" |
| 差异化 | **4** | 每个 PKM 工具都在做 AI 集成；LLM 本身不是差异化 |
| 创新性 | **3** | LLM 集成是 table stakes，不是创新；实际上"不做默认 LLM"才是 MindForge 的创新 |
| 构建可行性 | **6** | Provider factory 已有基础；但质量评估、cost/latency tracking 需要新基础设施 |
| Dogfood 可行性 | **3** | 真实 LLM 调用需要 API key、花钱、结果不确定性高、自动化困难 |
| 战略匹配 | **5** | 长期需要，但当前不是最紧迫的；过早引入真实 LLM 可能分散对 approval-first 的专注 |
| 风险 | **8** | 成本失控、隐私泄露、质量不一致、用户过度依赖 AI 质量、安全审查负担 |
| **加权总分** | **4.3/10** | |

**2 周验证计划**:
- Week 1: 用 1 个真实模型(如 anthropic/claude)跑 10 张卡片生成，对比 fake vs real 质量
- Week 2: 建立 cost/latency 追踪，评估日常使用成本

**Kill Criteria**:
- 真实 LLM 成本使日常使用不可持续（> $5/月 per 活跃用户）
- 真实 LLM 输出质量不稳定导致 approval 工作量不减反增

### Direction E: Knowledge Collaboration/Sharing (知识协作/分享)

**描述**: 分享已审批卡片、协作审阅、团队工作区。

**具体包含**:
- Share approved card (只读链接/导出包)
- Collaborative review (多人审阅同一批 draft)
- Team workspace (共享 Library)
- Permission model (read/comment/approve)

| 维度 | 评分 | 说明 |
|------|------|------|
| 用户痛点 | **4** | MindForge 定位为 personal tool；协作需求存在但非核心场景 |
| 差异化 | **5** | 协作 PKM 有 Notion/Confluence；approval-first 协作是微弱的差异化 |
| 创新性 | **5** | 共享审批工作流在知识管理领域有边际创新 |
| 构建可行性 | **3** | Auth/sharing/permissions/sync/conflict resolution → 几乎等于重写 |
| Dogfood 可行性 | **3** | 需要多用户设置，synthetic dogfood 几乎不可能 |
| 战略匹配 | **3** | 与 local-first/personal 定位冲突；会把 MindForge 拉向 SaaS |
| 风险 | **9** | 架构根本性转变、安全风险放大、local-first 信任模型被破坏 |
| **加权总分** | **3.7/10** | |

**2 周验证计划**:
- 不推荐。个人场景未验证前做协作是本末倒置。

**Kill Criteria**:
- 不适用——当前阶段不应启动此方向。

### Direction F: Structured Knowledge Workbench (结构化知识工作台)

**描述**: Saved views, collections, query builder, card merge/split/link, curation 工具——让 Library 从"浏览已审批卡片"升级为"结构化知识工作区"。

**具体包含**:
- Saved views: 用户可保存、命名、分享 Library 筛选视图
- Collections: 手动/规则驱动的卡片分组
- Query builder: 可视化构建 card 查询（tag/project/track/status/quality 组合）
- Card merge/split: 合并重复卡片、拆分过载卡片
- Manual link: 用户手动建立卡片关系
- Bulk maintenance: 批量 tag、批量导出、批量质量评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 用户痛点 | **7** | Library 组织能力浅（只有 tag/project/track 字段，无 saved views/collections） |
| 差异化 | **7** | 对 approved cards 做结构化工作区——Tana 有结构化但无 approval gate |
| 创新性 | **6** | 结构化工作区本身不新（Tana/Notion），但在 approved-only 知识上的结构化是新的 |
| 构建可行性 | **7** | Backend query builder + Frontend views/collections，现有 card schema 可复用 |
| Dogfood 可行性 | **8** | 可用 synthetic approved cards 构建和验证各种组织场景 |
| 战略匹配 | **8** | 直接深化 Library 作为主工作区的价值；用户停留时间直接决定留存 |
| 风险 | **4** | 中等风险；scope 需要严格控制（不做 supertags，不做 meeting agent） |
| **加权总分** | **6.9/10** | |

**2 周验证计划**:
- Week 1: 实现 saved views + collections MVP（后端 query + 前端 UI）
- Week 2: 找 5 个用户用 20 张 approved cards 尝试组织场景（"我想按主题/项目/质量分組"）

**Kill Criteria**:
- 用户反馈"直接 folder 就够了，不需要这么复杂"
- Saved views/collections 的使用率 <20%（创建后不再使用）

---

## 5. 方向排名与推荐组合

### 综合排名

| 排名 | 方向 | 加权总分 | 推荐优先级 |
|------|------|---------|-----------|
| 1 | A — Product Main Path Deepening | **7.6** | 立即执行 |
| 2 | C — Recall/Search Quality Lab | **7.1** | 第二批次 |
| 3 | F — Structured Knowledge Workbench | **6.9** | 第二批次 |
| 4 | B — Capture/Import Expansion | **5.9** | 观察等待 |
| 5 | D — Real LLM Integration | **4.3** | 冻结 |
| 6 | E — Knowledge Collaboration | **3.7** | 冻结 |

### 推荐执行顺序

```
Phase 1 (Week 1-2): P1 阻塞修复 + Guided Onboarding + 核心假设验证
    ↓ (假设验证通过)
Phase 2 (Week 3-6): Bet 1 主线深化 + Bet 2 结构化工作台（并行）
    ↓
Phase 3 (Week 7-10): Bet 3 检索质量实验室 + 基于 Phase 2 反馈的迭代
    ↓
Phase 4 (Week 11+): 如有用户习惯证据，重新评估 Direction B 和 D
```

### 不推荐的组合

- **A+D 组合**: 主线深化同时引入真实 LLM → 风险叠加，成本不可控
- **A+E 组合**: 个人场景未验证时做协作 → 方向性错误
- **B 作为主 bet**: 捕获拓展工程量大但核心体验（审批工作流）未被验证 → 本末倒置

---

## 6. 2 周验证计划

### 验证假设

> 非技术用户能否在 15 分钟内完成首次 Source → Draft → Review → Approve → Library → Recall → Export 完整循环？

### Week 1: 修复 + 设计

| 天 | 行动 | 产出 |
|----|------|------|
| 1-2 | 修复 P1 管道阻塞：demo 模式 auto-fallback fake provider | 零配置 demo 体验可用 |
| 3-4 | 设计 guided onboarding：sample workspace + 5-step 引导 | Onboarding spec |
| 5 | 建立 sample workspace（5-10 个示例 Markdown 文件） | 开箱即用的 demo 内容 |
| 5 | 实现 CLI `mindforge export` 主命令 | 完整 CLI 主路径 |

### Week 2: 用户验证

| 天 | 行动 | 产出 |
|----|------|------|
| 1 | 找 5 个非技术用户 | 用户名单 |
| 2-3 | 每人独立完成首次循环（观察、计时、不辅助） | 观察记录 |
| 4 | 汇总数据：完成时间、friction points、是否愿意再用 | 验证报告 |
| 5 | 决策：继续执行 Phase 2 或启动归档讨论 | Go/No-Go 决策 |

### 成功标准

- 主要: ≥3/5 用户在 ≤15 分钟内完成完整循环
- 次要: ≥3/5 用户表示"愿意再用"
- 定性: 识别出 ≥3 个具体 friction points 用于 Phase 2 修复

---

## 7. Kill Criteria

### 2 周验证窗口的 Kill Criteria

以下任一条件触发 → 启动归档讨论:

1. **核心假设失败**: <3/5 用户在 15 分钟内完成首次循环
2. **用户意愿不足**: <3/5 用户表示愿意再次使用
3. **审批被感知为负担**: ≥3/5 用户主动反馈"审批步骤太麻烦"
4. **不可修复的 UX 阻塞**: P1 阻塞修复后发现 ≥2 个新的 P1 阻塞

### Phase 2-3 的 Kill Criteria

1. **无习惯形成证据**: 2 周内活跃用户的Library 回访率 <30%
2. **审批被绕过**: 用户主动寻找绕过审批的方式（如直接操作数据库）
3. **差异化被复制**: 2 个以上竞品在同期推出 approval-based workflow

### 不应触发 Kill 的场景

以下场景**不应**成为 kill 理由（它们是已知限制，不是新发现）:
- Fake provider 卡片质量不如真实 LLM（这是设计选择，不是 bug）
- 中文 Recall 命中率低（source material 是英文，不是产品缺陷）
- 缺少移动端/浏览器扩展（已知 non-goal，不是失败）

---

## 8. 机会地图

### 8.1 当前产品状态定位

```
                审批强度
                    ↑
                    │
            MindForge ●────── 高审批强度 + 低 AI 自动化
                    │        （approval-first 差异化区域）
                    │
                    │     Notion AI ●────── 低审批强度 + 高 AI 自动化
                    │     Tana AI   ●       （AI 直接写入知识库）
                    │
                    │  Obsidian ●────────── 零 AI + 零审批
                    │  Logseq   ●           （纯手动知识管理）
                    │
                    └──────────────────────────→ AI 自动化程度
```

MindForge 当前占据"高审批强度 + AI 辅助但非自动"的位置——这是 PKM 市场中的空白区域。问题是这个位置是否有足够的需求。

### 8.2 机会热力图

| 机会区域 | 用户价值 | 差异化 | 可行性 | 时机 | 优先级 |
|---------|---------|--------|--------|------|--------|
| 审批工作流 polish | 高 | 高 | 高 | 现在 | **P0** |
| Onboarding/首次体验 | 高 | 中 | 高 | 现在 | **P0** |
| Library 组织深度 | 高 | 中高 | 中高 | 2-4 周后 | **P1** |
| 检索质量测量 | 中高 | 高 | 高 | 4-6 周后 | **P1** |
| 捕获入口拓展 | 高 | 中 | 低 | 6-8 周后(条件) | P2 |
| 真实 LLM 集成 | 中 | 低 | 中 | 8 周后(条件) | P2 |
| 协作/分享 | 中低 | 低 | 低 | 不做 | P4 |
| Graph/Sensemaking 扩张 | 低 | 低 | 中 | 不做 | P4 |

### 8.3 不做地图

| 方向 | 为什么不现在做 | 什么条件下重新评估 |
|------|--------------|-----------------|
| 真实 LLM | 差异化不在此，风险高，成本不可控 | 主路径用户习惯验证通过 + 用户主动要求更好卡片质量 |
| 捕获拓展 | 工程量大，核心循环未验证先做捕获可能白费 | 核心循环验证通过 + 用户最大痛点是"找不到东西可导" |
| 协作 | 个人场景未验证，且与 local-first 定位冲突 | 个人用户数 >100 + 明确团队使用需求 |
| Graph/Sensemaking | 两个审计结论一致：不恢复扩张 | 主路径稳定 + 用户明确需要知识关系分析 |
| 移动端 | 工程巨大，先验证桌面端需求 | 桌面端 DAU >500 + 移动端使用场景数据 |

---

## 9. 风险与不确定性

### 9.1 产品风险 (Product Risk)

| 风险 | 严重度 | 可能性 | 缓解措施 |
|------|--------|--------|---------|
| approval-first 没有足够用户需求 | 致命 | 中高 | 2 周验证窗口直接测试 |
| 审批被视为负担而非价值 | 高 | 中 | Onboarding 中解释 why approval matters |
| 用户宁愿用 Obsidian + AI 插件 | 中 | 中 | 差异化在"系统级 invariant"而非"功能" |
| PKM 市场已饱和，新工具难以获客 | 中 | 高 | 聚焦垂直场景（知识加工者）而非通用 PKM |

### 9.2 技术风险 (Technical Risk)

| 风险 | 严重度 | 可能性 | 缓解措施 |
|------|--------|--------|---------|
| WebFacade 仍是架构瓶颈(922 行) | 中 | 中 | Phase 2 中安排 targeted refactor,不做大重写 |
| Fake provider 无法模拟真实 LLM 质量问题 | 低 | 中 | 明确 fake provider 的测试边界 |

### 9.3 执行风险 (Execution Risk)

| 风险 | 严重度 | 可能性 | 缓解措施 |
|------|--------|--------|---------|
| AUTOPILOT-QUEUE 优先级与产品策略不一致 | 中 | 中 | 本次审计后重排 QUEUE |
| 持续治理升级消耗过多工程资源 | 中 | 低 | 治理稳定后 freeze，不持续迭代 |
| docs 数量过大导致 agent 方向漂移 | 低 | 中 | 归档旧 docs，保持 canonical docs 精简 |

### 9.4 不确定性

- 目标用户群体("知识加工者")的规模未知——没有市场数据支撑
- approval-first 的"aha moment"是什么——当前只有假设，没有证据
- 用户愿意为 approval-first 容忍多大的 UX friction——未知
- 中文用户群体的需求和英文用户是否有差异——未验证

---

## 10. 建议下一步行动

### 10.1 立即执行 (本周)

1. **修复 P1 管道阻塞** — `mindforge import` 在 demo 模式应自动 fallback fake provider
2. **重排 AUTOPILOT-QUEUE** — 产品策略审计结论应优先于治理升级和 P3 UX 打磨
3. **本产品创新审计文档 commit + push**

### 10.2 2 周验证窗口 (Week 1-2)

4. 设计并实现 guided onboarding (sample workspace + step-by-step)
5. 实现 CLI `mindforge export` 主命令
6. 执行用户验证 (5 个非技术用户, 首次循环)
7. 决策: Go/No-Go Phase 2

### 10.3 如果 Go (Week 3-10)

8. **Bet 1** (主线深化): Review queue polish, export CLI, setup simplification
9. **Bet 2** (结构化工作台): Saved views, collections, query builder
10. **Bet 3** (检索质量实验室): Retrieval fixtures, failed query review, query explain UI

### 10.4 如果 No-Go

11. 归档 MindForge 代码和文档
12. 写入归档原因和经验总结
13. 保留 approval-first 概念模型作为未来参考

---

## 11. 对 CURRENT_PROJECT_STATE.md 的更新建议

以下内容应反映在更新后的 `docs/dev/CURRENT_PROJECT_STATE.md` 中:

1. **标题版本**: v3.9 → v4.0（产品策略审计完成，方向重组）
2. **AUTOPILOT-QUEUE 重排**: 本产品策略审计结论应替换当前 ITEM-1/2/3
3. **推荐下一 loop**: Product Main Path P1 Fix → Guided Onboarding → 用户验证
4. **新增引用**: 本产品创新审计文档路径
5. **开放债更新**: P1 管道阻塞(新发现)应列入 §5

---

## 12. 推荐下一 /mf-autopilot Queue Item

```html
<!-- AUTOPILOT-QUEUE-START -->
<!-- AUTOPILOT-QUEUE-NEXT-ACTION: fix_p1_pipeline_blocker -->
<!-- AUTOPILOT-QUEUE-TASK-TYPE: bug_fix -->
<!-- AUTOPILOT-QUEUE-ITEM-1:
workstream=Product Main Path P1 Pipeline Blocker Fix
task_type=bug_fix
current_node=pending
next_action=auto_configure_fake_provider_when_no_real_model_demo_mode
required_skill=none
frameworks_checked=product_strategy_audit_2026-05-28
review_node=browser_mcp_smoke
failure_class=pipeline_blocker
remediation_target=zero_config_demo_experience
auto_continue_allowed=true
hard_stop_required=false
-->
<!-- AUTOPILOT-QUEUE-ITEM-2:
workstream=Guided Onboarding Design
task_type=feature_implementation
current_node=pending
next_action=design_sample_workspace_and_step_by_step_onboarding
required_skill=/brainstorming
frameworks_checked=product_strategy_audit_2026-05-28
review_node=user_validation
failure_class=none
remediation_target=none
auto_continue_allowed=false
hard_stop_required=true
hard_stop_reason=requires_user_validation_before_proceeding
-->
<!-- AUTOPILOT-QUEUE-ITEM-3:
workstream=User Validation — Core Hypothesis Test
task_type=dogfood
current_node=pending
next_action=recruit_5_non_technical_users_and_run_first_cycle_test
required_skill=none
frameworks_checked=product_strategy_audit_2026-05-28
review_node=go_no_go_decision
failure_class=none
remediation_target=none
auto_continue_allowed=false
hard_stop_required=true
hard_stop_reason=requires_go_no_go_product_decision
-->
<!-- AUTOPILOT-QUEUE-END -->
```

---

## 附录

### A. 审计方法说明

本产品创新审计基于以下输入:
- 7 份核心文档的完整阅读和交叉验证
- 2 份独立红队审计(118 和 133)的结论对照
- 1 份行业对标分析(093)的竞争格局参考
- 1 份能力地图(092)的当前真实能力基准
- 3 份最新 dogfood/实现笔记(135/137/119)的产品现状证据
- 6 个候选方向的 7 维度量化评分
- 10 个战略问题的系统回答

### B. 与现有审计的一致性检查

| 审计 | 日期 | 评分 | 结论 | 本审计一致性 |
|------|------|------|------|------------|
| Post-governance (118) | 2026-05-27 | 6.1/10 | Conditional Go, 需产品习惯证据 | 一致 |
| Codex red team (133) | 2026-05-27 | 6.4/10 | Conditional Go, 主路径 dogfood 优先 | 一致 |
| 本审计 | 2026-05-28 | 6.5/10 | Conditional Go with Restructuring, 2周验证 | — |

### C. Skill Execution Report

- `/brainstorming`: 已触发 ✅ — 用于产品策略探索和方向评估
- `/office-hours`: 已触发 ✅ — 用于产品策略咨询框架
- 本审计遵循 brainstorming skill 的 checklist: explore project context ✅, propose approaches ✅, present design ✅, write design doc ✅

### D. 最终报告清单

- [x] 产品创新审计执行完成
- [x] 10 个战略问题全部回答
- [x] 6 个候选方向全部评分(A-F)
- [x] 2 周验证计划制定
- [x] Kill criteria 明确设定
- [x] 输出文档路径: `docs/product/2026-05-28-001-mindforge-product-innovation-review.md`
- [x] 主 bet: Direction A — Product Main Path Deepening
- [x] 次 bet: Direction F — Structured Knowledge Workbench
- [x] Kill criteria: 核心假设验证失败 → 启动归档讨论
- [x] 下一 AUTOPILOT-QUEUE item: fix_p1_pipeline_blocker
- [x] `/brainstorming` triggered: yes
- [x] `/office-hours` triggered: yes
- [ ] Gates 待运行
- [ ] CURRENT_PROJECT_STATE.md 待更新
- [ ] progress-ledger.md 待更新
- [ ] Commit 待执行

**ACTION TOKEN: CONTINUE_TO_GATES**
