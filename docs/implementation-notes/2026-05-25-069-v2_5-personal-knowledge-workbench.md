# v2.5 Personal Knowledge Workbench Productization

## 概述

v2.5 将 v2.0-v2.4 的 graph/search/import/export/approval/review/dogfood 能力整合为可长期使用的本地知识工作台。

## 实现单元

### U1: Workspace Home Enhancement
- HomePage 增加知识流转总览（按来源分组展示卡片状态分布）
- LifecycleStep 组件：可视化卡片从 Source → ai_draft → human_approved 的流转
- API: `GET /api/lifecycle` — Source-to-Card 生命周期数据

### U2: Source-to-Card Lifecycle View
- 按来源展示每个 source 下卡片在各个状态的分布
- 点击来源可展开该来源下所有卡片的详细状态

### U3: Dogfood Report Center
- API: `GET /api/dogfood` — 工作台使用报告
- DogfoodPage: 活动摘要、参与度指标、基础设施状态、改进建议
- 纯本地运行，无遥测/外部分析

### U4: Provider Readiness Center
- SetupPage 增强：Provider 就绪状态面板
- 显示哪些 alias 可用、阻塞原因、是否需要 API key
- 不返回 raw key 值

### U5: Cross-cutting UX Polish
- LoadingSkeleton 覆盖全部 10 个页面变体（wiki/library/drafts/search/sources/health/trash/setup/dogfood/default）
- App.tsx 骨架屏路由映射完善

### U6: Product Copy & Smoke
- 新增 6 个 product copy 测试函数，覆盖 v2.4-v2.5 全部新增 i18n 键
- Browser smoke: 验证 Home/Library/Wiki/Health/Dogfood/Setup/Drafts/Recall/Trash 全部页面可渲染
- 发现 LibraryPage React #310 错误为 pre-existing（git stash 验证非当前变更引入）

### U7: Documentation Polish
- 更新 architecture.md：项目结构树、路由表（6→15）、新增图谱/检索/导入导出/健康/Provider就绪章节
- 更新 user-guide.md：Web Console 页面列表、Import/Export 章节、Dogfood 章节、Provider Readiness 章节、Lifecycle 概念、Community Browser/Multi-hop Relations、Known Limitations

## 设计决策

- LoadingSkeleton 为每个页面提供专属骨架屏占位，而非通用 "Loading..." 文本 — 感知性能提升
- Dogfood 报告纯本地计算，不依赖外部服务
- Provider Readiness 只报告状态不返回 key — 安全边界
- 所有页面均通过 accessibility tree snapshot 验证渲染正确性

## 已知限制

- LibraryPage React #310 错误（pre-existing，非 v2.5 引入），根因在 LibraryPage 组件条件 hook 调用
- 未引入新依赖
- 未调用 LLM
- 未使用 embedding/vector DB
