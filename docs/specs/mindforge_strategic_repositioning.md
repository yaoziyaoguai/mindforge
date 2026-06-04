---
name: mindforge-strategic-repositioning-sdd
description: Strategic product direction SPEC for MindForge — evaluates whether to continue as Web product, pivot to compiler/agent memory, or stop
metadata:
  type: strategic-spec
---

# MindForge Strategic Repositioning SDD

Date: 2026-06-05
Status: Draft — awaiting human review
Type: Product Direction SPEC (not implementation SPEC)

---

## 1. 当前问题

MindForge 是一个本地优先的个人 AI 知识库工具，核心链路是：

```
Source → AI Draft → Human Review → Explicit Approve → Approved Card
                                                        ├── Library
                                                        ├── Recall (BM25)
                                                        └── Topic View (runtime)
```

经过了 4 轮开发迭代（Mint1-Mint4），建成了完整的端到端知识编译管线，但：

- **零真实用户验证**（5-user test 已定义但从未执行）
- **展示体验评分 4/10，知识提取评分 3/10**（多模态审计结论）
- **Web 安装门槛极高**（git clone + pip + npm + build + start）
- **每个环节都有更强替代品**（Claude + Obsidian + NotebookLM）
- **核心产品假设从未被验证**（个人用户需要审批优先的知识加工闭环）

## 2. 为什么独立 Web 知识库方向可能不成立

### 2.1 没有不可替代的价值点

| MindForge 能力 | 替代方案 | 替代门槛 |
|---------------|---------|---------|
| 导入资料并 AI 提炼 | Claude / ChatGPT 粘贴对话 | 零 |
| 审批 AI 草稿 | 人脑判断 AI 输出 | 零 |
| 浏览知识库 | Obsidian / Notion / Apple Notes | 低 |
| 检索 | Obsidian Search / Notion Search | 低 |
| 生成 Wiki 总结 | Claude 直接生成 | 零 |
| 导出 | 复制粘贴 | 零 |

MindForge 的唯一差异化是 **approval boundary**（ai_draft → human_approved），但这个差异化对普通用户的价值未被验证。

### 2.2 Web 安装门槛是根本性 barrier

非技术用户需要：
1. 安装 Python 3.11+
2. 安装 Node.js / npm
3. `git clone`
4. `pip install -e .`
5. `npm install && npm run build`（前端）
6. `mindforge init`
7. `mindforge web --open`

这是一个开发者友好的流程，不是普通用户友好的流程。

### 2.3 复杂度远超验证过的价值

100+ Python 文件 + 13 前端页面 + 30+ 组件 + 20+ 文档 = 对于一个零用户验证的产品，这是过度工程。

### 2.4 Kill Criteria 可能已经被触发

validation-protocol.md 定义了 K2：≥3/5 用户不理解或认为 explicit approval 没有价值 → KILL。

虽然没有正式执行 5-user test，但从产品逻辑可以推断：
- 大多数人接受 AI 直接输出，不需要正式审批流程
- "审批"这个概念对非技术用户是陌生的
- 他们更习惯"AI 生成 → 我看看对不对 → 不对就改"的自然流程

## 3. 用户场景分析

### 3.1 当前定义的场景（可能不成立）

> 把阅读笔记、研究材料、项目记录、课程资料整理成可审批的知识卡片。

**问题**：这个场景的用户是谁？
- 学生？用 Notion / Apple Notes 就够了
- 研究者？用 Obsidian / Zotero 就够了
- 产品经理？用 Notion / 飞书文档就够了
- 开发者？用 Claude + Obsidian / Cursor 就够了

没有一个场景是"只有 MindForge 能做"的。

### 3.2 如果继续做，必须服务一个极其明确的场景

**候选场景**：

| 场景 | 是否足够窄 | MindForge 是否不可替代 |
|------|-----------|---------------------|
| 个人阅读笔记沉淀 | 否 | 否（Claude + Obsidian） |
| 项目文档整理 | 否 | 否（Claude + Cursor） |
| 研究者知识管理 | 否 | 否（Obsidian + Zotero） |
| Agent 长期记忆编译 | 是（待验证） | 可能是（approval boundary） |
| Obsidian 知识编译器 | 是 | 可能是（CLI + markdown） |

**结论**：只有"Agent 长期记忆编译"和"Obsidian 知识编译器"是足够窄且 MindForge 可能不可替代的场景。

## 4. 替代品分析

### 4.1 NotebookLM

- **优势**：免费、零安装、多文档理解、即时问答、AI 总结
- **劣势**：不是 local-first、不能审批、不能导出结构化笔记、不持久化知识库
- **覆盖 MindForge 的程度**：70%（多文档理解 + 总结覆盖了 import + distill）

### 4.2 Obsidian + AI Plugin

- **优势**：local-first、直接编辑、双向链接、社区生态、本地搜索
- **劣势**：需要自己组织流程、没有审批边界、AI plugin 质量参差不齐
- **覆盖 MindForge 的程度**：80%（知识库管理覆盖了 Library + Recall + Wiki）

### 4.3 Claude Desktop / ChatGPT

- **优势**：零安装、即时响应、交互式提炼、可以要求结构化输出
- **劣势**：不持久化知识库、不能审批、对话历史难以检索
- **覆盖 MindForge 的程度**：60%（提炼覆盖了 distill，但不覆盖 approval + library）

### 4.4 ChatGPT Projects / Notion AI

- **优势**：多文档管理、AI 内置、零安装、协作
- **劣势**：不是 local-first、不持久化、审批概念不存在
- **覆盖 MindForge 的程度**：70%（项目管理覆盖了 import + library）

### 4.5 综合结论

所有 MindForge 的能力都被现有工具组合覆盖了 60-80%。MindForge 需要提供剩下 20-40% 的不可替代价值。当前唯一的候选是 **approval boundary + local-first + agent memory quality**。

## 5. 现有资产评估

### 5.1 高价值资产（可迁移）

| 资产 | 价值 | 可迁移到 |
|------|------|---------|
| local-first approval pipeline 思想 | 高 | 任何需要质量控制的 AI 输出场景 |
| 5 段 pipeline 架构 | 高 | 知识编译器、agent memory compiler |
| FakeProvider pattern | 高 | 任何需要 demo/测试的 LLM 项目 |
| Card YAML schema | 高 | Obsidian frontmatter、agent context 格式 |
| Export / audit log 设计 | 高 | 任何导出/审计场景 |
| SPEC / TDD / review workflow | 高 | 任何工程项目 |
| BM25 retrieval | 中 | 轻量级检索需求 |
| TopicPresenter | 中 | 从 approved 数据构建运行时视图 |

### 5.2 低价值资产（应归档）

| 资产 | 原因 |
|------|------|
| Web 前端（web/src/，13 pages，30+ components） | 如果不是 Web 产品就不需要 |
| Web 后端（mindforge_web/，20 文件） | 如果不是 Web 产品就不需要 |
| Graph / Sensemaking | 没有价值闭环的 lab 功能 |
| Extension Plugin | 架构预留，无生产价值 |
| Dogfood 工具 | 开发者工具，不是用户功能 |

## 6. 5 个战略选项对比

### Option A：继续做独立 Web 知识库产品

| 维度 | 评估 |
|------|------|
| 值得继续？ | **否**。没有不可替代价值，安装门槛高，被全面覆盖 |
| 最大竞争对手 | NotebookLM（免费多文档 AI）+ Obsidian（本地知识库） |
| 不可替代价值 | **无** |
| 开发成本 | 极高（UI 重构 + packaging + 用户验证） |
| 为什么用户会用它？ | 没有理由 |

**Verdict: KILL**

---

### Option B：降级 Web，只保留 Review / Preview / Admin

| 维度 | 评估 |
|------|------|
| 更符合 local-first / approval-first？ | 是，Web 只用于审批 |
| 减少产品复杂度？ | 是，从 13 pages 减少到 ~3 |
| 保留已有 Web 价值？ | 部分，审批 UI 是核心 |
| 需要继续做 Library UI？ | 否 |
| 为什么用 Web 审批而不是 CLI？ | **没有好答案**。CLI approve 已经够用 |

**Verdict: KILL** — 如果 Web 只用于审批，CLI 已经可以覆盖。

---

### Option C：转为 Obsidian / Markdown-first Knowledge Compiler

| 维度 | 评估 |
|------|------|
| 更适合个人工具？ | 是，用户已经在 Obsidian 里了 |
| 更容易和 coding agent 协同？ | 是，agent 可以读 markdown 文件 |
| 比独立 Web 更有价值？ | 是，解决了安装门槛问题 |
| 需要保留的模块 | Pipeline、approval CLI、card schema、export |
| 需要砍掉的模块 | 整个 Web 前端 + 后端、Graph、Sensemaking |
| 风险 | Obsidian AI plugin 可能覆盖；CLI 审阅 UX 挑战 |

**Verdict: STRONG CONTENDER**

---

### Option D：转为 Agent Memory Infrastructure

| 维度 | 评估 |
|------|------|
| 更符合 agent 发展趋势？ | 是，agent memory quality 是真实问题 |
| 更适合在 coding agent / harness 中使用？ | 是，approved knowledge 可注入 context |
| 能避免和 NotebookLM / Obsidian 竞争？ | 是，不做人用的浏览界面 |
| 需要 Web？ | 否，CLI + API 足够 |
| 和普通 long-term memory 框架的差异？ | approval boundary 确保质量 |
| 风险 | 市场太小；agent frameworks 可能内置类似能力 |

**Verdict: STRONG CONTENDER**

---

### Option E：停止 MindForge，抽取通用工程资产

| 维度 | 评估 |
|------|------|
| 是否应该止损？ | 是，如果 C 和 D 都不成立 |
| 哪些资产能迁移？ | approval pipeline 思想、FakeProvider、SPEC/TDD workflow、export 设计 |
| 哪些代码应该归档？ | Web 前端 + 后端、Graph、Sensemaking、Dogfood |
| 如何写项目复盘？ | 产品假设未验证、工程过度投入、应先做用户验证 |
| 如何避免继续沉没成本？ | 停止所有新功能开发，只抽取可复用资产 |

**Verdict: FALLBACK OPTION** — 如果 C 和 D 的需求验证不成立

---

### 对比结论

| 选项 | Verdict | 优先级 |
|------|---------|--------|
| A: Web 知识库 | KILL | 5 |
| B: Web 仅审批 | KILL | 4 |
| C: Obsidian 编译器 | STRONG CONTENDER | 1 |
| D: Agent Memory | STRONG CONTENDER | 1 |
| E: 停止 | FALLBACK | 2 |

## 7. 推荐方向

**推荐：Option C + D 混合**

MindForge 转为 **Local Knowledge Compiler for Humans + Agents**：

```
Source (markdown, text, PDF, DOCX)
  → Ingestion
  → Distillation (AI提炼为结构化知识)
  → Approval (CLI 审阅 + explicit approval)
  → Export
     ├── Human output: Obsidian-compatible markdown → staged folder
     └── Agent output: Agent-readable knowledge pack → context injection
```

**关键决策**：
1. **砍掉整个 Web**：web/src/ + mindforge_web/ → 归档
2. **保留 CLI + Pipeline**：核心编译能力
3. **重写 CLI 审阅 UX**：终端中的结构化内容展示 + approve/reject/edit
4. **Obsidian Export**：导出为 Obsidian-compatible markdown
5. **（后续）Agent Export**：生成 agent-readable knowledge pack

**不做的事**：
- 不做 Web 浏览界面
- 不做知识图谱可视化
- 不做 RAG / embedding
- 不做团队协作
- 不做在线同步

## 8. 停止投资清单

以下模块应该停止投资，代码归档：

| 模块 | 原因 | 状态 |
|------|------|------|
| `web/src/` （全部 13 pages + 30+ components） | 不再是 Web 产品 | 归档 |
| `src/mindforge_web/` （全部 20 文件） | 不再是 Web 产品 | 归档 |
| Graph / Sensemaking | 没有价值闭环 | 归档 |
| Extension Plugin | 架构预留，无生产价值 | 归档 |
| Dogfood 工具 | 开发者工具 | 归档 |
| Knowledge Card v2 SPEC | 产品方向未定，schema 变更无意义 | 暂停 |
| Distill Prompt v2 SPEC | 产品方向未定，prompt 变更无意义 | 暂停 |
| Library UX Redesign SPEC | 不再有 Library 页面 | 废弃 |
| Web Design Direction docs | 不再有 Web | 归档 |

## 9. 保留资产清单

以下模块应该保留并继续投资：

| 模块 | 保留理由 |
|------|---------|
| `src/mindforge/processors/` | 核心 pipeline 逻辑 |
| `src/mindforge/cards.py` | 知识卡片数据模型 |
| `src/mindforge/approval_*.py` | 审批 workflow |
| `src/mindforge/llm/fake.py` | FakeProvider for demo/test |
| `src/mindforge/lexical_index.py` | BM25 检索（可选保留） |
| `src/mindforge/export_*.py` | 导出能力 |
| `src/mindforge/cli.py` | CLI 入口 |
| `src/mindforge/vault.py` | Vault 管理 |
| Card YAML frontmatter schema | 知识卡片格式标准 |
| SPEC / TDD / review workflow | 工程方法论 |
| docs/ 中的架构文档 | 项目理解 |

## 10. 如果转向，新的 MVP 是什么

### New MVP: MindForge CLI Knowledge Compiler

**目标**：用户能在终端中完成完整的知识编译流程。

**核心功能**（4 个命令）：

```bash
# 1. 导入并处理资料
mindforge import vault/00-Inbox/article.md

# 2. 审阅 AI 生成的草稿（终端中的结构化展示）
mindforge review
# 展示：title, takeaway, insight, context, principle, limitations
# 操作：approve / edit / reject / discard

# 3. 确认并导出到 Obsidian
mindforge approve <ref> --export-to ~/.obsidian/vault/staged/

# 4. 查看已编译知识列表
mindforge list --status approved
```

**MVP 验收标准**：
1. 导入 markdown 文件后生成 ai_draft 卡片（YAML frontmatter + markdown body）
2. `mindforge review` 在终端中以结构化方式展示卡片核心字段
3. `mindforge approve` 确认后导出 Obsidian-compatible markdown 到指定目录
4. 导出的 markdown 包含完整的 frontmatter（title, tags, knowledge_type, approval_state）
5. 整个过程不需要 Web、不需要 npm、只需要 Python

**不需要的功能**：
- Web 界面
- 知识图谱
- Wiki 生成
- 关系分析
- Health 检查
- Graph Preview

## 11. 如果停止，如何归档

如果 C + D 混合方案也不成立，执行以下归档步骤：

1. **写项目复盘**：`docs/postmortem/mindforge-postmortem.md`
   - 产品假设是什么
   - 验证了什么 / 没验证什么
   - 学到了什么
   - 下次如何避免

2. **抽取可复用资产**：
   - approval pipeline 思想 → 文档
   - FakeProvider pattern → 独立 gist / 文档
   - SPEC / TDD workflow → 已在全局 CLAUDE.md 中
   - Card YAML schema → 文档

3. **Git tag**：`git tag archive/v0.7-final`

4. **README 更新**：标注项目已归档，说明原因

5. **不再投入新代码**

## 12. 未来 2 周应该做什么

| 周 | 任务 | 产出 |
|----|------|------|
| 第 1 周 | 人工决策产品方向 | 确定选 C、D、C+D 或 E |
| 第 1 周 | 如果选 C+D：砍掉 Web（归档代码） | 仓库只有 CLI + pipeline |
| 第 1 周 | 如果选 C+D：设计 CLI 审阅 UX | 终端审阅流程 SPEC |
| 第 1 周 | 如果选 E：写项目复盘 | postmortem 文档 |
| 第 2 周 | 如果选 C+D：重写 CLI approve | 结构化审阅展示 |
| 第 2 周 | 如果选 C+D：实现 Obsidian export | 导出 Obsidian markdown |
| 第 2 周 | 如果选 C+D：端到端测试 | import → review → approve → export |
| 第 2 周 | 如果选 E：抽取可复用资产 | 文档 / gist |

## 13. 未来 1 个月应该不做什么

| 不应该做 | 原因 |
|---------|------|
| 修 Web UI | 方向可能不再做 Web |
| 实现 Knowledge Card v2 | schema 依赖产品形态 |
| 实现 Distill Prompt v2 | prompt 依赖产品形态 |
| 做 5-user validation（当前 Web 方案） | 如果方向变了，验证目标也变了 |
| 优化 Graph / Sensemaking | 没有价值闭环 |
| 增加新 Web 页面 | 同上 |
| 做 packaging / one-command install | 如果是 CLI 产品，packaging 需求不同 |
| 引入 RAG / embedding | 违反 local-first，且不是当前问题 |

## 14. 风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| C+D 混合后产品定位仍然模糊 | 用户不理解价值 | 明确一句话定位："把原始资料编译成可信赖的结构化知识，供人或 agent 使用" |
| CLI 审阅 UX 不好 | 用户宁愿用 Claude 对话 | 设计终端中的结构化展示（类似 `gh pr view` 的体验） |
| Obsidian 用户直接用 Obsidian AI | MindForge 被替代 | MindForge 的价值是 approval boundary + 批量处理 + 结构化输出 |
| Agent memory 市场需求太小 | 商业价值有限 | 先解决自己的需求（personal agent memory），再考虑外部用户 |
| 砍掉 Web 后代码量大幅减少 | 看起来"没做什么" | 代码量不是价值指标。保留核心 pipeline 比维护 13 个无用页面有价值 |
| 沉没成本情感依恋 | 不愿砍掉已写的代码 | 用产品价值判断，不是用代码量判断 |

## 15. 人工决策点

以下问题必须由你（产品决策者）回答：

### P0（本周内决定）

1. **是否继续做 MindForge？**
   - 是 → 选 C+D 混合
   - 否 → 选 E，停止并归档

2. **如果继续，目标用户是谁？**
   - 自己（personal tool）→ 最小化开发，满足自己需求
   - 开发者 / agent 用户 → C+D 混合
   - 普通用户 → A（但不推荐）

3. **是否砍掉 Web？**
   - 是 → 归档 web/src/ + mindforge_web/
   - 否 → 需要解释为什么保留 Web

### P1（两周内决定）

4. **CLI 审阅 UX 应该是什么样的？**
   - 终端内结构化展示（类似 `gh pr view`）
   - 编辑器内审阅（VS Code / Obsidian 打开草稿）
   - 其他方案

5. **Obsidian export 是必须的 MVP 功能吗？**
   - 是 → 第一周实现
   - 否 → 先做通用 markdown 导出

6. **Agent export 是 MVP 还是后续迭代？**
   - MVP → 需要定义 agent-readable 格式
   - 后续迭代 → 先做 human export
