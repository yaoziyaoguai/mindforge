# v0.4 U5 Knowledge Health 增强 实现笔记

## 日期
2026-05-24

## 目标
为 Health Report 中的每个 issue 提供跳转到相关卡片的可操作探索入口。

## 实现方案

### Backend

**新增 API endpoint**：`GET /api/knowledge/health`

**Schemas**（`schemas.py`）：
- `HealthIssueResponse` — code, severity, message, suggested_action, reason, affected_card_ids
- `HealthReportResponse` — summary, stats, issues, maintenance_suggestions

**Service**（`web_facade.py`）：
- `knowledge_health_report()` — 调用 `build_knowledge_health_report(cfg)` 并转为 API response
- 异常时返回优雅降级 fallback（summary 提示检查 vault）

**Router**（`routers/health.py`）：
- 新增 `GET /api/knowledge/health` endpoint
- 原 `/api/health` 保持为 liveness check

### Frontend

**API 层**：
- `web/src/api/health.ts` — `getKnowledgeHealth()` 函数
- `web/src/api/types.ts` — `HealthIssueResponse`、`HealthReportResponse` TypeScript 类型

**HealthPage 组件**（`web/src/pages/HealthPage.tsx`）：
- Stats 网格：显示 total_cards, approved, pending_drafts, missing_provenance, low_quality, orphans, duplicates, stale_wiki, source_warnings
- Summary banner：heart 图标 + 健康总结文字
- Issues 列表：每个 issue 卡片显示 severity icon + badge、message、reason、suggested_action
- "View affected cards" 按钮：当 issue.affected_card_ids 不为空时，导航至 `/library?cards=id1,id2,...`
- Maintenance Suggestions 列表
- Loading skeleton + error state

**LibraryPage 过滤支持**：
- 支持 `?cards=id1,id2` 查询参数过滤卡片列表
- 过滤活跃时显示 "Clear filter (N/M)" 按钮
- 过滤结果为空时显示提示信息

**i18n**：18 个新 key（zh/en）：页面标题、描述、统计标签、severity 标签、探索按钮、维护建议、空状态

**路由**：
- App.tsx：`/health` → `HealthPage`
- Sidebar.tsx：Using Knowledge 组新增 Health Report 链接（Heart 图标）

## 关键设计决策

1. **独立 endpoint**：`/api/knowledge/health` 与 `/api/health` 分离，后者保持为 liveness check
2. **affected_card_ids 上限**：导航链接只取前 10 个 ID，避免 URL 过长
3. **LibraryPage 过滤而非独立页面**：复用现有 Library 卡片网格，减少新增页面
4. **优雅降级**：health report 构建失败时返回友好提示而非 5xx

## 已知限制

- `source_warnings` issue 的 affected_card_ids 为空（源级别警告不关联特定卡片）
- `wiki_stale` issue 的 affected_card_ids 为空（需要 rebuild 而非卡片操作）
- `?cards=` 过滤在 URL query 中，不兼容 pushState 之外的路由模式

## 测试覆盖

- `tests/test_web_product_copy.py`：50/50 通过
- Browser smoke：Health 页面统计、issues、侧边栏链接正常渲染，无 console error
- Browser smoke：`?cards=` 过滤 + Clear filter 按钮正常工作
