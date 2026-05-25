# Post-Stabilization Direction Plan

**日期**: 2026-05-25  
**状态**: proposed  
**输入**: v4.2 post-remediation red team re-audit  

> **No feature expansion until chosen direction is accepted.** 不开始 v4.3，不扩张 Graph/Sensemaking/Entity/Community，不引入 RAG、embedding、vector DB、GraphRAG 或大型依赖。

---

## Recommended Next Phase

推荐下一阶段选择 **Product Main Path Dogfood**。

目标是把 MindForge 收缩到真实可用主路径，并用 50-100 个非敏感本地资料验证：

```
Source / Import → ai_draft → Review → explicit approve
→ human_approved → Library → Recall / Wiki → Export
```

这一阶段不是新增功能，而是验证产品主路径是否真实可用、哪里卡住、哪些能力应该被打磨或隐藏。

---

## Alternative Directions

### A. Product Main Path Dogfood

**目标**: 用非敏感真实资料验证端到端主路径，不继续图谱扩张。

适合现在做，因为当前最大风险不是“缺少更多功能”，而是核心路径是否能被真实用户顺畅使用。

### B. Architecture Simplification

**目标**: 拆分 `web_facade.py` / `schemas.py` 巨石，提取真实有价值的 `GraphService`、`ReviewService`、`ImportExportService` 和 schema modules。

不应先做纯架构重构。更好的顺序是先 dogfood，用用户路径暴露真实边界，再按高压路径拆分。

### C. Documentation System Reset

**目标**: 把大量旧 docs 收缩为 canonical docs + archive，修复 stale docs 和 overclaim。

适合作为 dogfood 后的第二阶段，也可与 dogfood 报告同步推进。

### D. Graph View Rebuild, Honest And Narrow

**目标**: 仅基于 `card/source/tag/wiki_section` 做 evidence graph，从 Library/Card detail 进入，解释边，不做 entity/community/sensemaking 大叙事。

当前不推荐优先做。只有主路径 dogfood 足够稳定后才值得恢复图视图探索。

### E. Safe Real Dogfood Readiness

**目标**: 不调用真实 LLM，但准备真实使用前的安全能力：redacted prompt preview、provider readiness、secret logging negative tests、manual opt-in checklist。

这适合作为后续真实 LLM 使用前的安全关，不替代产品主路径 dogfood。

---

## Why Chosen

选择 Product Main Path Dogfood 的原因：

1. v4.2 修复的是 truth 和 safety，不是产品可用性证明。
2. 最近几个版本偏向 graph/sensemaking 扩张，已经产生 overclaim 和 UI/API 不一致。
3. 主路径是 MindForge 的真实价值承诺：把本地资料变成可审阅、可检索、可导出的已审批知识。
4. Dogfood 会自然暴露 onboarding、provider setup、import、review、search、wiki、export、copy、empty state、error state 的真实问题。
5. 在真实使用证据出现前做架构拆分，容易按代码形状而不是用户路径切模块。

---

## Goals

- 用 50-100 个非敏感本地资料完成一次端到端 dogfood。
- 记录每一步的成功率、失败原因、人工操作成本和用户困惑点。
- 验证 `ai_draft → Review → explicit approve → human_approved` 不被绕过。
- 验证 Library、Recall、Wiki、Export 对已审批卡片是否有实际价值。
- 明确哪些能力应留在主导航，哪些应 internal/lab，哪些应隐藏或归档。
- 产出 dogfood report 和下一轮最小修复清单。

---

## Non-Goals

- 不实现 v4.3。
- 不新增 Graph/Sensemaking/Entity/Community 能力。
- 不调用真实 LLM、Cubox、Upstage 或外部服务，除非未来另有明确 opt-in 计划。
- 不处理私人敏感资料、公司机密资料或真实 Obsidian vault。
- 不做 RAG answering、embedding、vector DB、GraphRAG。
- 不新增大型依赖。
- 不做抽象优先的 service/schema 大拆分。
- 不修改 explicit approval / `human_approved` 安全语义。

---

## Acceptance Criteria

- 选定 50-100 个非敏感资料样本，并记录来源类别和排除规则。
- 至少完成一次完整路径：import/source processing → review → approve → library → recall/wiki/export。
- 每个失败都有可复现记录：输入类型、步骤、错误消息、用户可理解性、是否阻塞。
- 产出一份 dogfood report，按 P0/P1/P2/P3 分级。
- Graph/Sensemaking 不出现在主路径结论中，除非作为明确 lab/internal 观察项。
- 不产生任何真实 secret、API key、私人资料、Obsidian vault 写入或外部调用。
- 必要 gates 真实运行，报告 exact command、timeout、exit code。
- 结束时给出下一阶段建议：继续主路径 polish、进入 docs reset、进入 architecture simplification，或暂停。

---

## Suggested First Implementation Loop

本计划被接受后，第一轮建议是 **dogfood readiness and scenario design**，仍不做功能扩张：

1. 重新建立 repo facts：`pwd`、`git status --short`、branch、upstream、recent log。
2. 确认 workspace 使用临时非敏感目录，不接入真实私人 vault。
3. 写 dogfood runbook：样本选择规则、手动步骤、记录模板、stop conditions。
4. 准备 synthetic 或 redacted sample set；若需要真实资料，先由用户确认非敏感范围。
5. 跑 fake/dry-run 或 no-real-LLM path，记录 main path friction。
6. 只修阻塞 dogfood 的 P0/P1 bug；否则先报告，不做功能扩张。
7. 更新 dogfood report、quality debt ledger、current limitations。

---

## Stop Conditions

立即停止并报告：

- 需要读取 `.env`、secret store 或真实 API key。
- 需要调用真实 LLM、Cubox、Upstage 或外部网络服务。
- 需要处理私人敏感资料或公司机密资料。
- 需要写真实 Obsidian vault。
- 需要改变 explicit approval / `human_approved` 语义。
- 需要 RAG、embedding、vector DB、GraphRAG 或大型依赖。
- 发现 P0/P1 安全风险且无法通过小修复阻断。
- repo 不在 clean `main` 或 upstream 状态不安全。

---

## Explicit Hold

No feature expansion until this direction is accepted. 下一轮在用户接受方向前，只允许继续审计、文档 truth reset、gate 复核或计划细化；不进入 v4.3 实现。

