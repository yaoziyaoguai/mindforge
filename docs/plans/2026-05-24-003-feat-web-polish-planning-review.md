---
title: MindForge Web Polish & Next Phase Planning Review
type: docs
status: draft
date: 2026-05-24
---

## Context

Milestones A-G 全部完成。Web UX 从工程原型进化为可用的知识工作台：
- Setup (步骤式配置向导)、Sources、Review/Drafts、Library (卡片网格浏览)
- Wiki (阅读模式/TOC scroll spy/print styles/排版优化)
- Home (Dashboard action guidance)、Search (Recall 文案优化)
- i18n zh/en 双语文案系统 (~200 keys)、copy policy 合同测试

当前没有明确定义的下一阶段 milestone。

## What's Left (Web-Only, No Backend Changes)

### 可立即实现的 Web 改进

1. **Loading skeleton / transition polish**
   - 页面间导航无 loading 反馈，初次加载 Wiki/Library 时有白屏闪烁
   - 可加极简 skeleton（纯 CSS，不需要新依赖）

2. **Wiki Related Sections (spec §4.5 遣留)**
   - spec 描述了但未实现。i18n key `wiki.related_sections` 已添加
   - 需要后端 `WikiSectionView.related_sections` 字段 → **超出 autopilot 范围**

3. **Sources 页面 polish**
   - 频率 combobox a11y (U12 遣留)
   - Sources 列表状态指示器完善

4. **Trash 页面 polish**
   - 空状态引导文案

### 需要 Backend 改动（超出 autopilot）

- v0.3 Roadmap M1-M6 (Card Quality, Wiki Quality, Related Cards API, Source Location, Knowledge Health, Local Graph DB)
- Wiki Related Sections (需后端加字段)
- 前端测试基础设施 (vitest + testing-library 搭建)

## Recommendation: Milestone H — Last-Mile Web Polish

做一次"最后一公里" polish pass，处理所有不再需要 backend 改动的小改进：

### H1. Loading Skeleton
- 为 Wiki、Library、Drafts 页面添加 CSS-only skeleton
- 使用 Tailwind `animate-pulse` + 圆角 div，无新依赖
- ~30 LOC CSS + ~20 LOC per page

### H2. Sources Page A11y
- Frequency combobox 加 id/name/aria-label
- ~10 LOC

### H3. Trash Empty State
- 空回收站显示引导文案
- ~5 LOC (复用 EmptyState 组件)

### H4. Regression Smoke
- Browser smoke 逐页验证
- i18n zh/en 切换验证
- Console error check

**Total: ~5 files, ~80 LOC, 纯前端，零后端改动。**

## Non-Goals

- 不改 backend API
- 不引入新依赖
- 不做 v0.3 roadmap (需 backend)
- 不新增大功能

## Decision

如果同意 H1-H4 方向，可以在同一 session 内直接实现。或者停下等待用户决定是否推进 v0.3。
