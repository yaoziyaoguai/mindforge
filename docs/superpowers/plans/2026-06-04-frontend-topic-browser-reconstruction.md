# 前端 Topic Browser 重构计划

> **供 agent 工作者使用：** REQUIRED SUB-SKILL: 使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 来逐步实现本计划。步骤使用 checkbox（`- [ ]`）语法用于跟踪。

**目标：** 用运行时 Topic Browser 替换已废弃的 LLM Wiki 重建 UI，消费 `/api/topics` 端点。

**架构：** 新建 `web/src/api/topics.ts` API 客户端从 `/api/topics` 获取数据。`WikiPage.tsx` 重写为薄适配器，组合 `TopicBrowser`，后者编排 `TopicList` + `TopicView` + `TopicContextPanel`。所有旧的 "Generate Wiki" / `/api/wiki/rebuild` 调用已移除。无新依赖。

**技术栈：** React 19, TypeScript, Tailwind CSS, Vitest + Testing Library, 自定义 i18n（LocaleProvider）

**API 契约：** `docs/specs/topic_view_api.md` — `GET /api/topics` → `TopicListResponse`，`GET /api/topics/{topic_name}` → `TopicViewResponse`（无已审批卡片时返回 404）

---

## 当前问题

1. `WikiPage.tsx` 调用 `/api/wiki/status`、`/api/wiki/page`、`/api/wiki/quality`、`/api/wiki/related-sections` — 全是遗留端点
2. "Generate Wiki" 按钮调用 `POST /api/wiki/rebuild`，返回 410
3. "Safe fallback rebuild" 调用 `POST /api/wiki/rebuild` 并带 `mode: "deterministic"`，同样返回 410
4. `docs/zh-CN/web-wiki.md` 描述的是旧的 Generate Wiki 流程
5. 导航显示 "Wiki" 但内容是 LLM 合成，而非运行时 topic 视图

## 目标体验

用户访问 `/wiki` → 看到：
- **左侧栏**：来自 `GET /api/topics` 的 topic 列表，每个 topic 名称可点击
- **中间**：来自 `GET /api/topics/{name}` 的选中 topic 卡片列表，显示卡片详情
- **右侧**：选中卡片的关系/来源上下文
- **空状态**：无 topic 时清晰提示（无已审批卡片）
- **无 Generate Wiki 按钮**，无 `/api/wiki/rebuild` 调用

## 组件树

```
WikiPage（薄适配器）
└── TopicBrowser（编排：选中 topic 状态、loading）
    ├── TopicList（左侧：topic 列表）
    ├── TopicView（中间：选中 topic 的卡片）
    │   └── TopicCard（单张卡片展示，可重复）
    └── TopicContextPanel（右侧：选中卡片的关系）
```

## 文件变更

### 新建
- `web/src/api/topics.ts` — `listTopics()`、`getTopic(name)`
- `web/src/components/wiki/TopicBrowser.tsx` — 编排层
- `web/src/components/wiki/TopicList.tsx` — topic 侧边栏
- `web/src/components/wiki/TopicView.tsx` — topic 卡片列表
- `web/src/components/wiki/TopicCard.tsx` — 单张卡片
- `web/src/components/wiki/TopicContextPanel.tsx` — 关系面板
- `web/src/pages/__tests__/WikiPage.test.tsx` — 组件测试

### 修改
- `web/src/pages/WikiPage.tsx` — 完整重写为薄适配器
- `web/src/lib/i18n.ts` — 添加 topic 相关 i18n key

### 文档
- `docs/zh-CN/web-wiki.md` — 重写为 Topic View

### 不触碰
- `web/src/components/wiki/` 下的旧 wiki 组件（保留供潜在遗留读取，不被新 WikiPage 导入）
- `web/src/api/wiki.ts`（保留类型供遗留消费者使用，不被新 WikiPage 导入）
- 后端代码（无变更）

## 自审清单

- [x] 不调用 `/api/wiki/rebuild`
- [x] 不将遗留 wiki 作为核心体验
- [x] 不破坏审批边界（仅显示 `approval_state: "human_approved"`）
- [x] 无新的大型依赖
- [x] 不过度工程化 — 5 个聚焦组件
- [x] 原样使用现有 API 契约

## 验收标准

1. `npm run build` 通过
2. WikiPage 从 API 渲染 topic 列表，选中后显示卡片
3. WikiPage 代码中无 `/api/wiki/rebuild` 调用
4. Generate Wiki 按钮已移除
5. 无 topic / 无已审批卡片的空状态已处理
6. `docs/zh-CN/web-wiki.md` 更新为 Topic View
