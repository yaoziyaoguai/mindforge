# Post-Mint4 Independent Retrospective / Lessons Learned

日期: 2026-05-28
审计类型: 全项目独立回顾（只读，无代码变更）
审计对象: MindForge v0.7.22, HEAD `cffc661`, Mint4 结项
审计人: Claude Code autonomous agent (deepseek-v4-pro)
审计方法: 治理文档全量审阅 + 代码面采样 + 产品文档交叉验证 + 3 份独立审计 triangulation

---

## 1. Executive Summary

**总体评分: 6.8/10 — Conditional Go，建议做 User Validation 后再决定是否继续投入。**

Mint4 是 MindForge 迄今最高产的工作流：Directions A (Product Main Path Deepening)、C (Recall/Search Quality Lab)、F (Structured Knowledge Workbench) 三大方向全部完成，24 项生产级能力就绪，质量闸门全部通过（~3030 pytest + 79 vitest + ruff clean + npm build clean）。

核心成果一句话：**MindForge 现在是一个功能完备、安全边界清晰、可 dogfood 的 local-first knowledge compiler。**

但 Mint4 也暴露了三个结构性风险：

1. **零真实用户验证** — 所有 dogfood 都是 synthetic/fake 数据，non-technical user adoption 完全是假设
2. **治理漂移成本** — `/mf-autopilot` 已膨胀至 1012 行，skill framework routing + recursive remediation + 9 类 failure classification 形成了一个自指涉（self-referential）的治理系统，维护成本不可忽视
3. **WebFacade 残余债** — 虽从 2163→922 行 (-57.4%)，仍是最复杂的单文件，presenter 提取不够彻底

**Verdict 缩写**: 产品做对了，工程做扎实了，但没人用。下一步唯一正确的事是 User Validation。

---

## 2. Timeline

### 2.1 Mint4 时间线总览

| 日期 | 事件 | Commits | 关键产出 |
|------|------|---------|---------|
| 2026-05-25 | Product Main Path Dogfood v1 | 多笔 | FakeProvider 补全、42 样本端到端测试、recall 10/10 |
| 2026-05-26 | v4.2 Red Team Stabilization | 多笔 | P1 修复、Graph/Sensemaking 降级、package safety |
| 2026-05-26 | v4.4 Product Main Path UX Deepening | 多笔 | FirstRunGuide, ImportPathCard, why_review 横幅 |
| 2026-05-26 | Direction C: Recall/Search Quality | `de077df`→`2d9a271` | Golden benchmark (12+18), QueryExplain, BM25 tuning, quality gate (100%), Web explain |
| 2026-05-26 | v4.7-4.8 Architecture Debt Reduction | 多笔 | schemas.py 1375→399 lines, web_facade.py 2163→922, 5 presenter submodules |
| 2026-05-27 | `/mf-autopilot` Governance v3 | 多笔 | Recursive remediation, skill framework routing, failure classification 9 类, auto-continue policy |
| 2026-05-27 | v3.7 Quality Platform | 多笔 | vitest infra, coverage config, frontend test expansion (0→50 tests, 6 files) |
| 2026-05-27 | P1 Pipeline Blocker Fix | `87453f0` | auto-fallback to fake LLM, 零配置 demo 体验 |
| 2026-05-27 | AUDIT-118 Product Debt Closure | 多笔 | Export docs, Dogfood nav fix, browser MCP smoke |
| 2026-05-27 | Docs Reset + Cleanup | 多笔 | 批量文档清理、残留引用修复 |
| 2026-05-27 | Guided Onboarding MVP (v0.7) | 多笔 | QuickStartWizard, OnboardingHint, sample workspace, 18 tests |
| 2026-05-27 | Product Main Path Dogfood v2 | 多笔 | 扩展 dogfood 脚本、recall 验证 |
| 2026-05-28 | Direction F: Structured Workbench | `5544a92`→`1e5dda9` | Saved Views, Collections, Bulk Maintenance, Card Linking, Tests, i18n |
| 2026-05-28 | Governance Truth Sync | `cffc661` | CPS + ledger reconciliation, AUTOPILOT-QUEUE 对齐, all workstreams marked done |

### 2.2 三条独立审计时间线

| 日期 | 审计 | 评分 | 结论 |
|------|------|------|------|
| 2026-05-27 | Post-Governance Global Red Team | 6.1/10 | Conditional Go |
| 2026-05-27 | Codex Independent Strategic Red Team | 6.4/10 | Conditional Go |
| 2026-05-28 | Product Innovation Review | 6.5/10 | Conditional Go — Restructuring |

三次独立审计均给出 Conditional Go，核心关切高度一致：产品方向正确、工程质量可接受，但**缺乏真实用户验证是最大风险**。

---

## 3. Capability Map

### 3.1 能力矩阵 — 当前状态

#### Production-like / Dogfoodable (24 项)

| # | 能力 | 代码位置 | 成熟度 | 备注 |
|---|------|---------|--------|------|
| 1 | Source Import (13 adapters) | `src/mindforge/sources/` | ★★★★ | MD/TXT/HTML/PDF/DOCX |
| 2 | AI Draft 五段处理 | `src/mindforge/processors/` | ★★★★ | Triage→Distill→Link→Questions→Actions |
| 3 | Human Review + Approval | `review_service.py`, `approval_service.py` | ★★★★★ | 不可绕过 |
| 4 | Knowledge Library | `library_service.py`, LibraryPage | ★★★★ | 浏览、筛选、排序 |
| 5 | BM25 Recall | `recall_service.py`, `lexical_index.py` | ★★★★ | 本地词法检索 |
| 6 | Wiki (LLM synthesis) | `wiki_service.py` | ★★★ | 需真实 LLM |
| 7 | Knowledge Health | `health/health_service.py` | ★★★★ | 8 项诊断，只读 |
| 8 | Source Provenance | `provenance/` | ★★★★ | 来源追溯 |
| 9 | Related Cards | `relations/related_cards.py` | ★★★★ | 5 种确定性关系 |
| 10 | Local Graph Preview | GraphExplorer.tsx | ★★★ | 4 NodeType |
| 11 | Export (Markdown/ZIP) | Library router + ExportPage | ★★★★ | 浏览器本地下载 |
| 12 | Provider Setup | SetupPage.tsx | ★★★★ | Web 配置模型和 API key |
| 13 | Dogfood | `dogfood/` | ★★★ | 内部工具 |
| 14 | Trash + Restore | `trash_service.py` | ★★★★ | 安全回收站 |
| 15 | Web UI (14 pages) | `web/src/pages/` | ★★★★ | React SPA + Tailwind |
| 16 | i18n (zh/en) | `web/src/lib/i18n.ts` | ★★★★ | 双语文案 |
| 17 | Frontend Tests (79 tests) | `web/src/components/__tests__/` | ★★★ | vitest + happy-dom |
| 18 | Backend Tests (~3030 tests) | `tests/` | ★★★★★ | pytest, 1 skip |
| 19 | Saved Views | `view_store.py`, ViewSwitcher | ★★★★ | local JSON store |
| 20 | Collections | `collection_store.py`, CollectionPanel | ★★★★ | CRUD + API |
| 21 | Bulk Maintenance | `card_workspace_service.py`, BulkActions | ★★★★ | YAML frontmatter 批量修改 |
| 22 | Manual Card Linking | `card_workspace_service.py`, CardWorkspace | ★★★★ | 双向 manual_links |
| 23 | Recall Benchmark | `tests/fixtures/recall_benchmark.py` | ★★★★ | 12+14+4 golden/negative |
| 24 | Query Explain | `recall_service.py` | ★★★★ | BM25 命中/未命中分析 |

#### Internal (2 项)

| # | 能力 | 说明 |
|---|------|------|
| 25 | Graph Page (`/graph`) | 独立全页，路由保留但不在主导航 |
| 26 | GraphRepository | Repository Pattern 封装，仅测试使用 |

#### Lab (4 项)

| # | 能力 | 说明 |
|---|------|------|
| 27 | Sensemaking (`/sensemaking`) | Bridge detection 等简单 heuristics |
| 28 | Entity Resolution | ConceptCandidate 确定性检测 |
| 29 | Extension Plugin | 架构预留 |
| 30 | Community/Topic Detection | 实验性 |

#### Deferred (6 项)

RAG/embedding/vector DB, Obsidian plugin, Mail storage, Auto-approve, Real provider auto-call, Graph/Sensemaking expansion

### 3.2 能力漂移追踪

从早期 roadmap 到当前状态的关键收缩：

| 早期声明 | 当前状态 | 收缩原因 |
|---------|---------|---------|
| 8 种 Graph NodeType | 4 种正式支持 | 产品聚焦，未实现的类型降级为 lab/internal |
| Graph/Sensemaking 全能力 | lab/internal | v4.2 red team 判断为过度声明 |
| "知识图谱"作为产品卖点 | Local Graph Preview (Library 内) | 确定性关系而非全图分析 |
| web_facade.py God Service (2163 行) | 922 行 + 5 presenter 模块 | v4.8 架构减债 |

---

## 4. Architecture Retrospective

### 4.1 架构评分: 7.2/10

**优势:**

1. **清晰的分层架构** — CLI/Web 共享服务层，SourceAdapter 归一化，策略注册模式，整体结构合理
2. **显式审批不可绕过** — `approve_card()` 只接受 `ai_draft`，类型系统强约束，不存在 bypass 路径
3. **安全边界设计良好** — API key 隔离（secret store vs YAML vs frontend）、Wiki 数据源约束、provider 日志白名单
4. **扩展点设计** — SourceAdapter (13 种格式)、RetrievalPort、GraphPort、ExtensionManifest 均为合理的抽象边界
5. **减债取得实质进展** — schemas.py 1375→399 (-63.4%), web_facade.py 2163→922 (-57.4%), 5 个 presenter 子模块提取

**问题:**

1. **WebFacade 仍是 hub** — 922 行虽然比 2163 好很多，但仍是项目中最大的 orchestration 单点。presenter 提取将其从 "God Service" 降为 "Fat Coordinator"，但 coordinator 模式本身仍有风险
2. **config.py (1296 行)** — 配置模型是第二大文件，包含了 YAML schema、validation、LLM config、wiki config、workspace config 等多种职责
3. **ingestion_service.py (1032 行)** — 第三大文件，导入处理逻辑集中
4. **模块级 helper 函数** — web_facade.py 中的 presenter 提取留下了模块级私有函数，测试摩擦仍然存在
5. **无 DI/容器** — 服务之间通过直接导入和 `WebFacade` 协调，没有依赖注入框架。对于当前规模这可以接受，但如果继续增长会成为问题

### 4.2 文件大小分布

| 范围 | 文件数 | 占比 |
|------|--------|------|
| >1000 行 | 2 (config.py 1296, ingestion_service.py 1032) | 大文件可控 |
| 500-1000 行 | ~12 | 合理 |
| 200-500 行 | ~25 | 健康 |
| <200 行 | ~30 | 健康 |

### 4.3 关键架构决策回顾

| 决策 | 当时理由 | 回顾评价 |
|------|---------|---------|
| BM25 而非 embedding/vector DB | 简单、确定性、零外部依赖 | ✅ 正确 — recall 100% 在 golden benchmark 上验证了充分性 |
| fake LLM profile 内存注入 | 零配置 demo，不污染 YAML | ✅ 正确 — P1 pipeline blocker 的关键修复 |
| local-first, 不联网 | 隐私、离线可用 | ✅ 正确 — 差异化定位清晰 |
| YAML frontmatter 作为卡片存储 | 人类可读、git-friendly | ✅ 正确 — Bulk Maintenance 直接操作 YAML |
| FastAPI + React SPA | 标准技术栈 | ✅ 正确 — 开发效率高 |
| Explicit approval 不可绕过 | 安全核心 | ✅ 正确 — 三次审计均确认此边界坚固 |
| 不做 Obsidian plugin | 避免 vault 写入风险 | ✅ 正确 — 保持独立产品身份 |
| web_facade orchestration 模式 | 避免循环导入 | ⚠️ 战术正确但债务累积 — 已改善但未根除 |

---

## 5. Product Direction

### 5.1 产品策略评分: 6.5/10

产品创新审计给出了 6.5/10 (Conditional Go — Restructuring)。回顾来看这个评分公允。

**Mint4 期间三大 Direction 的交付:**

| Direction | 描述 | 评分 | 交付完整度 | 用户感知价值 |
|-----------|------|------|-----------|------------|
| A: Product Main Path | Guided Onboarding, P1 fix, UX deepening | 7.6/10 | 高 | 高 — 直接影响 first-run 体验 |
| C: Recall/Search Quality | Benchmark, explain, tuning, quality gate | 7.1/10 | 高 | 中 — 功能完整但 BM25 的局限性决定体验上限 |
| F: Structured Workbench | Saved Views, Collections, Bulk, Linking | 6.9/10 | 高 | 中 — power user 功能，non-technical user 难以自发发现 |

**核心假设未验证:**
> "Non-technical users can complete full cycle (Source → ai_draft → human_approved → Library → Recall → Export) in ≤15 minutes."

这个假设决定了产品是否 viable。目前所有 dogfood 都是用 synthetic data + fake LLM 跑的，zero real user feedback。

### 5.2 产品定位清晰度: 7/10

"local-first, approval-first personal knowledge compiler" 这个一句话定位简洁有力。NOT 列表（不是 RAG、不是 Obsidian、不是 SaaS...）有效防止了 scope creep。

但缺少一个关键问题的答案：**Who is this for and why would they switch from whatever they do today?**

### 5.3 竞争定位

| 维度 | MindForge | Obsidian | Notion | Logseq |
|------|----------|----------|--------|--------|
| Local-first | ✅ | ✅ | ❌ | ✅ |
| AI processing pipeline | ✅ (五段) | ❌ (需插件) | ✅ (Notion AI) | ❌ |
| Explicit approval | ✅ | N/A | ❌ | N/A |
| BM25 search | ✅ | ❌ (无内置) | ❌ | ✅ (Datalog) |
| Wiki synthesis | ✅ | ❌ | ❌ | ❌ |
| Open source | ✅ | ❌ | ❌ | ✅ |

差异化是存在的，但 **竞争护城河依赖于 AI pipeline + explicit approval 这对组合拳**。如果 Obsidian 出一个高质量的 AI 插件，差异化会大幅缩水。

---

## 6. User Journey

### 6.1 用户旅程评分: 6.0/10

**当前体验流:**

```
首次访问 HomePage (空 workspace)
  → QuickStartWizard (3 steps: 了解→创建→探索)
  → 点击 "Create Demo Workspace"
  → 6 张 demo 卡片直接 human_approved (approval_method: demo_sample)
  → 可立即浏览 Library / Recall / Wiki / Export
```

```
真实使用流 (需配置模型):
  → Setup → 配置模型 + API key
  → Sources → Add Source → Process Now
  → ai_draft 生成 (五个 step)
  → Review → 阅读 → Approve
  → Library 中可见
  → Recall / Wiki / Export 可用
```

**Mint4 改善:**

| 改善点 | 之前 | 之后 |
|--------|------|------|
| First-run 体验 | 空 workspace，无引导 | QuickStartWizard + OnboardingHint |
| 零配置 demo | 需要模型配置 → ConfigError | auto-fallback to fake LLM |
| 导入路径说明 | 无 | ImportPathCard 三种方式 |
| 审批语义解释 | 无 | why_review 横幅 |
| Export 安全说明 | 无 | safety_note + 格式描述 |
| 页面引导 | 无 | 8 个页面的 OnboardingHint |

**剩余问题:**

1. QuickStartWizard 创建的 demo 卡片直接 human_approved，**跳过了用户学习审批流程的机会**。用户看到了结果但不知道 `ai_draft → human_approved` 这个核心语义
2. OnboardingHint dismiss 不持久化 — 刷新后重新出现是合理行为，但可能 annoying
3. 无页面 mask/tour overlay — 用户可能不知道每个页面能做什么
4. 真实使用流（配置模型→导入→处理→审阅→审批）从未被非技术用户测试过
5. 无用户反馈收集机制 — 无法知道用户在哪里卡住

---

## 7. Web Design

### 7.1 Web 设计评分: 6.5/10

**架构评估:**

| 维度 | 评分 | 说明 |
|------|------|------|
| 组件化程度 | 7/10 | ~55 个组件 + 14 pages，结构合理 |
| API 层设计 | 8/10 | 18 个 API 模块，按 domain 清晰分离 |
| 状态管理 | 5/10 | 每页独立 fetch + local state，无全局状态管理 |
| i18n 覆盖 | 7/10 | zh/en 双语文案完整，33+33 onboarding keys |
| 测试覆盖 | 5/10 | 79 vitest tests (11 files)，UI 组件测试有代表性但覆盖率不高 |
| 可访问性 | 4/10 | 未评估过 a11y |

**技术栈:**
- React 18 + TypeScript
- Tailwind CSS
- vitest + happy-dom + @testing-library/react
- 无路由库 (手动页面切换 via state)
- 无全局状态管理库

**Web IA/UX Loop 2 审计的主要发现 (已修复):**
- HomePage 卡片分组逻辑优化
- Sidebar 分组 (Main / Lab 折叠区)
- Dogfood 从主导航移入 Lab 折叠区
- Export 页面写入 Web Console 表格

**当前 Web 设计的问题:**

1. **无响应式设计** — 未针对移动端优化，桌面端 only
2. **组件库不统一** — Tailwind utility classes 直接写在组件中，没有提取 design token
3. **加载/空/错误状态覆盖不完整** — 有 LoadingSkeleton/EmptyState/ErrorState 组件，但不是所有页面都用了
4. **Wiki 组件族最大** — ~12 个 wiki 子组件，复杂度集中在单一功能
5. **BulkActions 和 CardWorkspace** — Direction F 新增的组件，功能强大但 UI 偏 technical (YAML frontmatter 直接暴露)

---

## 8. Autopilot Process

### 8.1 `/mf-autopilot` 评分: 7.0/10

**Mint4 期间 autopilot 演进:**

| 版本 | 关键变化 | 行数估计 |
|------|---------|---------|
| v1 (Mint4 早期) | 基础 task type routing | ~300 |
| v2 | Recursive remediation + failure classification | ~600 |
| v3 (当前) | Skill framework routing + mandatory skill gates + auto-continue policy | 1012 |

**做得好的:**

1. **Task type routing** — 7 种入口（feature/bug/docs/ui/architecture/audit/dogfood），覆盖了所有实际操作类型
2. **Recursive remediation** — 失败→分类→修复→重试的闭环设计合理
3. **Failure classification 9 类** — 覆盖了常见的失败模式，每类有明确的修复策略
4. **Auto-continue policy** — spec/doc/gate/commit/push 都不是停止点，只有 HARD_STOP 触发停止
5. **Gate rules** — 禁止 tail/head/truncated 输出作为 gate evidence，要求完整 exit code
6. **Progress ledger** — 每 loop 必更新，现已有 ~30 个 loop 的完整记录

**问题:**

1. **1012 行的命令文件** — 这本身就是一个治理债。autopilot 已经成为一个需要维护的子系统
2. **Skill framework routing 复杂度** — 强制检查 Compound Engineering / G-stack / Superpowers / Design skills / Codex，在实际执行中 agent 能否可靠地做这些检查？
3. **自指涉风险** — autopilot 治理 autopilot 的改进 → autopilot 变得更复杂 → 需要更多治理 → ...
4. **Known skill inventory fallback** — "取决于 agent 的 skill 感知能力"（引自 implementation-notes/139），这是一个真实的不确定性
5. **未经外部验证** — 所有 autopilot run 都是同一个 agent 执行的，无法知道换一个模型/agent 后行为是否一致

### 8.2 Autopilot 执行统计 (Mint4)

| 指标 | 数值 |
|------|------|
| 完成的 loops | ~30 |
| 平均 commits/loop | ~1-3 |
| Gate pass rate | 100% (所有 gate 首次通过) |
| P0 blocking bugs | 0 |
| P1 问题发现/修复 | ~3 (pipeline blocker, product debts, truth drift) |
| HARD_STOP 触发次数 | 2 (User Validation, product decisions) |

---

## 9. Lessons Learned

### 9.1 What Worked Well

#### L1: Fake Provider + Synthetic Data 策略极其高效
在零外部依赖的情况下完成了端到端验证。42 个样本 + fake LLM 证明了整个 pipeline 可以跑通。recall 从 70%→100% 的改善完全通过调整 synthetic data 覆盖实现。

**Keep doing**: synthetic dogfood 作为 CI/gate 的一部分。但不要把它和真实用户验证混为一谈。

#### L2: 显式审批边界设计是架构锚点
`approve_card()` 的类型约束（只接受 `ai_draft`）是 `ai_draft → human_approved` 语义的编译时保证。三次独立审计均确认此边界坚固。这是 MindForge 最有价值的架构决策之一。

**Keep doing**: 任何新功能必须先回答 "是否绕过审批？"

#### L3: 方向聚焦 (A+C+F) 优于广度扩张
冻结了 D (Real LLM)、E (Collaboration)、Graph/Sensemaking expansion，把资源集中在三个清晰的方向上，全部高质量交付。

**Keep doing**: 在 User Validation 之前继续冻结非核心方向。

#### L4: 质量闸门自动化
ruff + pytest + vitest + npm build + git diff --check 的五闸门体系确保了每次 commit 的质量基线。Gate pass rate 100% 证明了自动化闸门的有效性。

**Keep doing**: 维持当前闸门标准，可以考虑增加 bundle size check (针对 P3-01)。

#### L5: 减债可量化
schemas.py 1375→399 (-63.4%), web_facade.py 2163→922 (-57.4%)。数字让人信服，比 "改善了架构" 这种模糊说法有效得多。

**Keep doing**: 减债时给出 before/after 行数。

### 9.2 What Didn't Work

#### L6: Autopilot 复杂度自举
从一个简单的 task router (300 行) 膨胀为 1012 行的治理子系统。skill framework routing + recursive remediation + 9 类 failure classification 形成了一个自指涉系统。维护 autopilot 本身开始消耗显著的 loop 时间。

**Why**: 每次遇到 edge case 就往 autopilot 加规则，而不是简化系统。没有 "autopilot 复杂度预算" 的概念。

**Fix**: 下一个 major version 应该考虑简化 autopilot，设定硬性的复杂度上限（如 500 行）。

#### L7: 文档治理成本被低估
Mint4 期间创建/更新了大量文档：CPS, progress-ledger, quality-debt-ledger, documentation-debt-ledger, HANDOFF.md, ~30 implementation notes, user guides (zh/en), architecture.md... 维护这些文档使它们之间保持 truth consistency 的成本不可忽视。发生了多次 truth drift（如 CPS HEAD 落后于实际 commit）。

**Why**: 文档分散在多个文件中，没有自动化的 cross-reference validation。

**Fix**: 考虑减少文档数量或引入自动化 cross-reference 检查。

#### L8: Web Design 缺乏设计系统基础
Tailwind utility classes 直接使用，没有 design tokens。组件视觉一致性依赖于开发者的判断力。这在小团队中可行，但在多个 feature 并行时会出现 visual inconsistency。

**Why**: 没有在早期建立 design token / component library。

**Fix**: 在下一个 UX 迭代中提取 design tokens（colors, spacing, typography）。

#### L9: User Validation 一再推迟
三次独立审计、CPS、AUTOPILOT-QUEUE 都将 User Validation 列为 "next step" 或 HARD_STOP。但它从未发生。每个 loop 都能找到 "更重要的" 事情来做。

**Why**: 写代码比找人测试容易。工程 momentum 压倒产品 discipline。

**Fix**: 在 User Validation 完成之前，HARD_STOP 所有 feature implementation。

### 9.3 Surprises

#### S1: BM25 在 synthetic data 上做到了 100% recall
没有用 embedding/vector DB，只靠 BM25 + 字段权重调优 (title=5.0, body=1.0)，就在 14 个 golden queries 上达到 100% recall。这说明对于 small-scale structured knowledge cards，BM25 足够好。

#### S2: FakeProvider keyword injection 效果有限
分析显示 body 字段的关键词注入对 BM25 的贡献有限 — title 权重 (5.0) 主导了 recall 排序。这不是 bug，而是 BM25 的 TF 饱和效应的预期行为。但团队花了时间才确认这一点。

#### S3: P1 Pipeline Blocker 修复比预期简单
`PROD-01` 看起来像一个 deep config issue，但实际上只需在两处（CLI + Web）添加 auto-fallback 逻辑，11 个测试验证。修复本身在 `87453f0` 中就已实现，只是文档 truth drift 让它看起来像 open issue。

---

## 10. Cut / Keep / Deepen / Defer Matrix

### Cut (停止 / 移除)

| 项目 | 理由 | 影响 |
|------|------|------|
| Autopilot 进一步扩张 | 1012 行已到管理上限 | 减少治理维护成本 |
| 新的 implementation notes 创建 | ~30 个已足够，新 notes 边际价值递减 | 减少文档维护负担 |
| Graph/Sensemaking 任何扩张 | 已明确冻结，必须遵守 | 防止 scope creep |
| 新 Direction 启动 | User Validation 之前不开始任何新方向 | 保持聚焦 |

### Keep (保持现状)

| 项目 | 理由 |
|------|------|
| 五闸门体系 (ruff + pytest + vitest + npm build + git diff) | 质量基线，100% pass rate |
| Explicit approval 语义 | 架构锚点，不可触碰 |
| Fake provider + synthetic dogfood | CI/CD 中持续验证 pipeline |
| i18n (zh/en) | 双语已完整，维持即可 |
| Progress ledger 更新 | 每次 loop 必做，历史记录价值高 |
| NOT 列表 (不做 RAG/Obsidian/auto-approve...) | 产品边界清晰 |

### Deepen (深化投入)

| 项目 | 理由 | 优先级 |
|------|------|--------|
| **User Validation** | 三次审计一致结论，最高优先级 | P0 |
| Web 响应式基础 | 至少 mobile-friendly，当前桌面端 only | P2 |
| Design tokens 提取 | 减少 visual inconsistency | P3 |
| Onboarding 体验迭代 | 基于 user feedback 改进 | P1 (post-validation) |
| BM25 中文分词 | 当前 analyzer 未针对中文优化 | P2 |

### Defer (继续冻结)

| 项目 | 理由 |
|------|------|
| Real LLM integration (Direction D) | User Validation 后决定 |
| Collaboration (Direction E) | 需求未验证 |
| Embedding / Vector DB | 明确不做，BM25 当前充分 |
| Obsidian plugin | 明确不做 |
| Mobile app | 响应式设计先做 |
| Graph/Sensemaking 全能力 | 已降级 lab/internal |

---

## 11. 2-Week Plan

### 原则: 停止 feature development，聚焦 User Validation

```
Week 1: Preparation + Recruitment
├── Day 1-2: 准备 User Validation 测试脚本和观察指南
│   - 5 个 scenario-based tasks（非 "test case" 语言）
│   - 观察要点: 在哪里卡住、什么概念不理解、什么让他们惊喜
│   - 招募标准: 非技术用户、日常有记笔记/整理信息需求、未见过 MindForge
├── Day 3-4: 招募 5 名测试用户
│   - 最低要求: 3 名完成完整测试
│   - 备选: 如招募困难，至少 2 名 + 1 名技术用户对照
└── Day 5: 环境准备 + dry run
    - 确保零配置启动 (auto-fallback to fake LLM)
    - 准备 demo workspace 但不主动展示
    - Dry run 观察脚本

Week 2: Testing + Analysis
├── Day 6-8: 执行 5 场 User Validation sessions
│   - 每场 45 分钟: 15 min 自由探索 + 25 min scenario tasks + 5 min 反馈
│   - 全程录屏 (需用户同意)
│   - 观察者记录但不干预
├── Day 9-10: 分析 + Kill Criteria 判定
│   - ≥3/5 用户在 ≤15 min 内完成 full cycle → GO
│   - <3/5 完成 或 平均 >25 min → KILL or MAJOR REWORK
│   - 中间情况 → Conditional GO with specific fixes
└── Day 11+: 根据结果决定:
    ├── GO → P1 修复 user validation 发现的问题 → 真实 LLM 集成
    ├── Conditional GO → 针对性修复 → re-validate
    └── KILL → 写 honest post-mortem → archive project
```

### Kill Criteria (来自产品创新审计)

1. **Core Hypothesis Fails**: ≥3/5 non-technical users cannot complete full cycle in ≤15 minutes
2. **Approval Concept Rejected**: ≥3/5 users don't understand or don't value explicit approval
3. **No Compelling Reason**: ≥3/5 users say "I wouldn't use this" after completing the cycle

### Pre-validation HARD_STOPs

- 不做新功能
- 不重构
- 不写新文档 (除了 validation 脚本)
- 不改进 autopilot
- 所有 engineering effort 仅用于修复阻碍 user validation 的 P0/P1 bug

---

## 12. Final Verdict

### 综合评分

| 维度 | 评分 | 权重 | 加权 |
|------|------|------|------|
| 产品方向 | 6.5/10 | 25% | 1.63 |
| 工程架构 | 7.2/10 | 20% | 1.44 |
| 代码质量 | 7.5/10 | 15% | 1.13 |
| 测试覆盖 | 7.0/10 | 10% | 0.70 |
| 用户体验 | 6.0/10 | 15% | 0.90 |
| 治理流程 | 7.0/10 | 10% | 0.70 |
| 文档质量 | 6.5/10 | 5% | 0.33 |
| **加权总分** | | | **6.83/10** |

### 一句话总结

**MindForge 在 Mint4 建成了一个工程扎实、安全边界清晰、能力完备的知识编译器 — 但还没人用过。**

### 最大风险 (Top 5)

1. 🔴 **零真实用户验证** — 核心假设未证明，整个产品可能建立在错误前提上
2. 🟡 **Autopilot 治理膨胀** — 1012 行自指涉系统，维护成本上升
3. 🟡 **WebFacade 残余债** — 922 行仍是最大单文件，coordinator 模式脆弱
4. 🟡 **竞争窗口** — AI-first knowledge management 赛道正在变热，时不我待
5. 🟢 **文档 truth drift** — 已知问题，影响限于开发者体验

### 最大优势 (Top 5)

1. 🟢 **Explicit approval 架构锚点** — 类型系统强约束，三次审计确认不可绕过
2. 🟢 **完整的端到端 pipeline** — 13 adapters → 五段处理 → 审批 → Library/Recall/Wiki/Export
3. 🟢 **工程质量闸门** — 五闸门体系 100% pass rate，~3100 tests
4. 🟢 **清晰的产品边界** — NOT 列表有效防止 scope creep
5. 🟢 **可量化的减债成果** — schemas -63%, facade -57%

### Go / No-Go 建议

**Conditional Go — 附加条件:**

1. ✅ 立即启动 User Validation (2-week plan above)
2. ✅ 冻结所有 feature development 直到 validation 完成
3. ✅ 不启动新的 Direction
4. ✅ 不扩张 autopilot 治理规则
5. ✅ 如 Kill Criteria 触发，诚实评估是否 pivot 或 archive

---

## 13. Appendices

### A. 审计方法论

本次审计不依赖单一来源，而是通过以下方式 triangulate:

1. **治理文档全量审阅**: CPS (315 lines), progress-ledger (589 lines), HANDOFF.md, quality-debt-ledger, engineering-workflow.md
2. **产品文档交叉验证**: 产品创新审计 (733 lines), Codex red team audit (1275 lines), post-governance audit (948 lines)
3. **用户文档一致性检查**: user-guide.md (en, 461 lines) vs user-guide.md (zh-CN, 470 lines) vs README.md (359 lines)
4. **代码面采样**: 目录结构、文件大小分布、关键模块行数、测试文件行数
5. **3 份独立审计 triangulation**: 寻找共识和不一致

### B. 文档一致性检查

| 检查项 | 结果 |
|--------|------|
| CPS Web UI 表 vs 实际 pages | ✅ 一致 (14 pages) |
| CPS capabilities vs 代码实际存在 | ✅ 一致 |
| en user guide vs zh-CN user guide | ✅ 一致 (结构对等) |
| architecture.md 引用 vs 实际文件 | ✅ 一致 (v4.8 修复了旧引用) |
| progress-ledger 最新 loop vs CPS HEAD | ✅ 一致 (`cffc661`) |
| quality-debt-ledger vs CPS open debts | ✅ 一致 |

### C. Gate Baseline (2026-05-28)

> 以下为最后一次全量 gate run 的基线数据 (来自 quality-debt-ledger + CPS，非本次重新执行):

| Gate | Exit Code | Detail |
|------|-----------|--------|
| ruff | 0 | All checks passed |
| git diff --check | 0 | — |
| npm build | 0 | built in ~2.5s |
| product copy tests | 0 | ~84 passed |
| approval boundary | 0 | 102 passed |
| package safety | 0 | passed |
| full pytest | 0 | ~3030 passed, 1 skip |
| expanded dogfood | 0 | 13 steps PASS, recall 10/10 |

### D. 关键文件索引

| 文件 | 行数 | 角色 |
|------|------|------|
| `.claude/commands/mf-autopilot.md` | 1012 | Autopilot 治理规范 |
| `docs/dev/CURRENT_PROJECT_STATE.md` | 315 | 项目状态入口 |
| `docs/dev/progress-ledger.md` | 589 | 进度台账 |
| `docs/dev/architecture.md` | 232 | 架构概览 |
| `docs/dev/quality-debt-ledger.md` | 91 | 质量债台账 |
| `docs/en/user-guide.md` | 461 | 英文用户指南 |
| `docs/zh-CN/user-guide.md` | 470 | 中文用户指南 |
| `src/mindforge/config.py` | 1296 | 配置模型 (最大 Python 文件) |
| `src/mindforge_web/services/web_facade.py` | 922 | Web 编排层 (曾 2163 行) |
| `tests/test_web_api.py` | 5453 | 最大测试文件 |

### E. 致谢

本审计基于 3 份先前的独立审计成果:
- Post-Governance Global Red Team Audit (2026-05-27)
- Codex Independent Strategic Red Team Audit (2026-05-27)
- Product Innovation Review (2026-05-28)

这些审计提供了互补的分析视角，本回顾整合了它们的共同发现。
