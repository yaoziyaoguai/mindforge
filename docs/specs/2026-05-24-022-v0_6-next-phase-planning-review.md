---
title: MindForge v0.6 — Next-Phase Planning Review
type: review
status: draft
date: 2026-05-24
roadmap: V0_6_PLANNING
parent: 2026-05-24-010-v0_5-next-phase-planning-review.md
---

# v0.6 Next-Phase Planning Review

## Current State (v0.5 complete)

v0.5 完成了 Dogfood Readiness：

| Unit | Capability | Status |
|------|-----------|--------|
| U1 | Setup UX Polish — 模型快速模板、Key 格式验证、Key 可见性切换 | done |
| U2 | Safety Confirmation Gate — 模式感知安全横幅、激活确认对话框、provider_mode 持久化 | done |
| U3 | Fake Dogfood Automation — `scripts/fake_dogfood.sh` 端到端验证 | done |
| U4 | Dogfood Runbook — 统一操作手册 `docs/dogfood-runbook.md` | done |
| U5 | Web Smoke & Product Copy — Setup 页面 i18n 覆盖、browser smoke | done |
| U6 | Safety Hardening Audit — 5 维度审计全部 PASS，无 P0/P1 | done |

**当前产品能力**: 用户能通过 Web UI 配置真实 API key、通过安全检查清单激活真实模式，`fake_dogfood.sh` 提供一键自动化验证。关系体验层（v0.4）和知识质量层（v0.3）完整。

## Remaining Candidate Directions (from v0.5 review)

| Direction | Theme | Status |
|-----------|-------|--------|
| A | Dogfood Readiness | **done (v0.5)** |
| B | Project/Track Management | pending |
| C | Search & Discovery | pending |
| D | Editing & Authoring | pending |
| E | Stability & Polish | pending |

## Recommendation: Direction C — Search & Discovery

**v0.6 推荐主题：Search & Discovery**

### Rationale

1. **当前搜索体验是 BM25-only**，无过滤、无分组、无排序选项。Library 中的卡片数增长后，线性浏览不可持续。
2. **v0.3-v0.5 积累了丰富的卡片元数据**（status、source、tags、quality scores、relations）但搜索没有利用这些维度。
3. **Search 是连接 Library 和 Wiki 的桥梁** — 用户在 Library 中搜索卡片，在 Wiki 中搜索 section，但目前两者是独立体验。
4. **不需要大依赖** — 可在现有 BM25 基础上叠加过滤、分组、排序，不引入向量 DB 或 embedding。
5. **立即提升日常使用价值** — 搜索是最高频的导航操作。

### v0.6 Draft Scope

| Unit | Capability | Priority |
|------|-----------|----------|
| S1 | Search Filter Panel — status/source/tag 过滤 + 组合 | P0 |
| S2 | Search Results Grouping — 按 status/source 分组展示 | P1 |
| S3 | Search Sorting — relevance/date/quality 排序选项 | P1 |
| S4 | Wiki Search Integration — 在 Wiki 页面内搜索 section | P2 |
| S5 | Search UX Polish — 空状态、loading、error states | P1 |

### Non-Goals

- 不做向量搜索 / semantic search / embedding
- 不做 Elasticsearch / Meilisearch 等外部搜索引擎
- 不做 RAG / vector DB
- 不引入新的大型依赖

### Alternatives Considered

**Direction B (Project/Track Management)**: 有价值的组织功能，但需要新的数据模型（projects 表/文件），比搜索更大的 scope。搜索增强可以在不改变数据模型的前提下交付。

**Direction E (Stability & Polish)**: 错误状态、a11y、性能优化可以编织进 v0.6 的每个 unit 中（每个 S-unit 覆盖对应的 error/empty/loading states），而不是单独做一个 stabilization milestone。

## Open Questions

1. 用户是否同意 Search & Discovery 为 v0.6 方向？
2. Search 过滤是否需要 URL query params 持久化（支持分享/书签搜索 URL）？
3. Wiki 内搜索 section 是否应该复用 Library 搜索组件？
