---
name: mindforge-strategic-repositioning-review
description: Self-review of MindForge strategic repositioning SDD — assesses honesty, sunk cost avoidance, and actionability
metadata:
  type: review
---

# MindForge Strategic Repositioning Self-Review

Date: 2026-06-05
SDD Reviewed: `docs/specs/mindforge_strategic_repositioning.md`

## 1. 是否过度迎合已有项目，强行证明它有价值？

**PASS — 没有。**

SDD 没有试图证明 MindForge 当前方向有。它明确说：
- 没有不可替代的价值点
- 每个环节都有更强替代品
- Kill Criteria 可能已经被触发
- Option A（Web 知识库）的 verdict 是 **KILL**

推荐方向（C+D 混合）不是基于已有代码，而是基于产品逻辑：approval boundary + local-first 在 compiler 和 agent memory 场景可能有独特价值。

## 2. 是否认真考虑了停止项目？

**PASS — 是。**

Option E（停止 MindForge，抽取通用工程资产）被完整评估：
- 哪些资产能迁移（approval pipeline 思想、FakeProvider、SPEC/TDD workflow）
- 哪些代码应该归档（Web 前端 + 后端、Graph、Sensemaking、Dogfood）
- 如何写项目复盘
- 如何避免继续沉没成本

SDD 还定义了 E 是 C 和 D 需求验证不成立时的 fallback option。

## 3. 是否诚实比较了 NotebookLM / Obsidian / coding agent / ChatGPT Projects 等替代品？

**PASS — 是。**

替代品分析覆盖了 5 个主要竞品：

| 竞品 | 覆盖 MindForge 程度 | 核心优势 |
|------|-------------------|---------|
| NotebookLM | 70% | 免费、零安装、多文档理解 |
| Obsidian + AI | 80% | local-first、直接编辑、双向链接 |
| Claude Desktop | 60% | 零安装、交互式提炼 |
| ChatGPT Projects | 70% | 多文档管理、AI 内置 |
| Notion AI | 70% | 零安装、协作 |

没有低估任何一个竞品，也没有夸大 MindForge 的差异化。

## 4. 是否指出 Web 产品路线的硬伤？

**PASS — 是。**

明确指出了：
- 安装门槛：7 步操作（git clone + pip + npm + build + init + web）
- 非技术用户不会走到这一步
- Web 维护成本高（13 pages + 30+ components + 20 backend files）
- 复杂度远超验证过的价值
- "为什么用户要打开浏览器而不是直接用 Claude"没有答案

## 5. 是否提出了足够窄、足够具体的新场景？

**PARTIAL — 需要进一步验证。**

C+D 混合场景定义为：
> "把原始资料编译成可信赖的结构化知识，供人或 agent 使用"

这比 Web 知识库窄，但仍然不够具体。需要回答：
- 谁会为这个功能付钱（或投入时间）？
- 他们现在用什么替代？
- MindForge 比替代好多少？

这些需要人工决策和真实用户验证，SPEC 本身无法回答。

## 6. 是否明确哪些模块应该停止投资？

**PASS — 是。**

停止投资清单列出了 9 个模块：
1. web/src/（13 pages + 30+ components）
2. mindforge_web/（20 文件）
3. Graph / Sensemaking
4. Extension Plugin
5. Dogfood 工具
6. Knowledge Card v2 SPEC（暂停）
7. Distill Prompt v2 SPEC（暂停）
8. Library UX Redesign SPEC（废弃）
9. Web Design Direction docs（归档）

## 7. 是否避免继续沉没成本？

**PASS — 是。**

SDD 明确指出：
- "代码量不是价值指标。保留核心 pipeline 比维护 13 个无用页面有价值"
- "用产品价值判断，不是用代码量判断"
- "继续修 UI 只会增加沉没成本，不会解决产品方向问题"
- "在验证产品方向之前，不应该继续修 UI"

## 8. 是否给出可执行的下一步？

**PASS — 是。**

未来 2 周计划：
- 第 1 周：人工决策产品方向 → 砍掉 Web → 设计 CLI 审阅 UX
- 第 2 周：重写 CLI approve → 实现 Obsidian export → 端到端测试

人工决策点（P0）：
1. 是否继续做 MindForge？（是 → C+D，否 → E）
2. 目标用户是谁？
3. 是否砍掉 Web？

## 总结

| 自审问题 | 结论 |
|----------|------|
| 1. 过度迎合已有项目？ | PASS — 没有，明确 kill 了 Option A |
| 2. 认真考虑停止？ | PASS — Option E 完整评估 |
| 3. 诚实比较竞品？ | PASS — 5 个竞品，覆盖度 60-80% |
| 4. 指出 Web 硬伤？ | PASS — 安装门槛、维护成本、复杂度 |
| 5. 提出足够窄的场景？ | PARTIAL — C+D 比 Web 窄，但仍需验证 |
| 6. 明确停止投资模块？ | PASS — 9 个模块清单 |
| 7. 避免沉没成本？ | PASS — 明确指出代码量不是价值指标 |
| 8. 给出可执行下一步？ | PASS — 2 周计划 + P0 决策点 |

**Overall Verdict: PASS** — SDD 诚实、可执行、避免了沉没成本陷阱。C+D 混合场景比 Web 窄，但仍需要人工验证需求。如果验证不成立，Option E（停止并归档）是最诚实的选择。
