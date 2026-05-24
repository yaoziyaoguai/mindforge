---
title: MindForge v0.5 — Next-Phase Planning Review
type: review
status: draft
date: 2026-05-24
roadmap: V0_5_PLANNING
---

# v0.5 Next-Phase Planning Review

## Current State (v0.4 complete)

v0.4 完成了"知识关系体验"层：

| Capability | Backend (v0.3) | Frontend/UX (v0.4) |
|---|---|---|
| Wiki Related Sections | Jaccard overlap engine | Section 间导航链接 |
| Card Relationship Panel | Related Cards 计算引擎 | 按 RelationReason 分组展示 |
| Provenance Trail | Source location v2 | source → sibling → wiki 面包屑 |
| Local Graph Preview | 1-hop deterministic graph | hover tooltip, 节点点击跳转, section badge |
| Knowledge Health | CLI `mindforge health` | Health Report 页面 + ?cards= 过滤探索 |
| Golden Tests | — | 11 tests, browser smoke |

## What's Working Well

- 确定性关系引擎（无 embedding/RAG 依赖）
- 从任意入口（卡片、Wiki、Health）沿关系链探索
- Fake provider test 基础设施成熟
- Autopilot auto-continue 工作流稳定

## Candidate Directions for v0.5

### Direction A: Dogfood Readiness

让用户能真正配置自己的 API key 并使用 MindForge 处理真实内容。

- Web Setup 页面完善 API key 配置 UX
- 真实 LLM dogfood 流程（scan → triage → distill → approve）
- Secrets 管理安全审计
- 真实 vault smoke tests

### Direction B: Project/Track Management

让卡片按项目/track 组织，超越"全部卡片在同一列表"的现状。

- 项目 CRUD
- 卡片归入项目
- 项目级别 Wiki 和 Health
- Track 工作流

### Direction C: Search & Discovery

升级搜索体验，从 BM25 扩展到混合搜索。

- 全文搜索 UX 增强
- Tag/Status/Source 过滤面板
- 搜索结果排序和分组
- Search index 重建 UX

### Direction D: Editing & Authoring

增强卡片编辑体验，让 MindForge 从"阅读器"变成"写作工具"。

- Rich text / Markdown 编辑器
- 双链 [[]] 语法支持
- 卡片模板
- 批量操作

### Direction E: Stability & Polish

不新增功能，打磨现有体验。

- 错误状态覆盖全页面
- a11y 审计
- Performance 优化
- E2E 测试覆盖

## Recommendation

**Direction A (Dogfood Readiness)** 是最自然的下一步：
1. v0.3-v0.4 的基础设施已经足够支撑真实使用
2. 用户体验层面已经连贯（关系探索链路完整）
3. 用户之前表达过 dogfood 意愿
4. 不需要新增大型依赖或架构变更

建议 v0.5 范围：
- Setup 页面 API key 配置完善
- 真实 LLM invoked flow 端到端验证
- Dogfood 安全边界明确
- 不做 RAG/embedding/vector DB

## Open Questions

1. 用户希望 v0.5 优先处理哪个方向？
2. Dogfood 的范围：仅 scan → approve 链路？还是包括 Wiki rebuild？
3. 是否需要真实 API key 管理 UX（masking, validation, rotation）？
