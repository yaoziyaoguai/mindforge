# Export Page MVP — Implementation Notes

- **Date**: 2026-05-27
- **Spec**: `docs/plans/2026-05-27-112-export-page-product-spec.md`
- **Trigger**: Web IA audit 发现 `/export` URL 无独立页面，fallthrough 到 Home

---

## 1. Implemented Scope

### Export Page (`/export`)

- **Route**: `/export` — 新增路由，不再 fallthrough 到 Home
- **Sidebar**: "导出知识" 入口，位于工具与诊断分组（健康报告 → 使用报告 → 导出知识 → 回收站）
- **Page structure**:
  - 页面标题 + 中文安全副标题
  - 导出范围选择（全部已确认 / 按标签 / 按轨道）
  - 导出格式选择（Markdown / ZIP）
  - 预览区（卡片数量 + 预计文件大小 + 卡片列表）
  - 安全说明（明确不写 Obsidian vault、不调外部服务）
  - "预览内容" 按钮（模态框查看 Markdown）
  - "下载导出" 按钮（触发浏览器本地下载）
  - 空状态（无已确认卡片时展示引导）
  - 错误/成功状态

### API 复用

- 复用现有 `POST /api/knowledge/export`（Markdown 预览 + 下载）
- 复用现有 `POST /api/knowledge/export/download`（ZIP 下载）
- 无新增 API endpoint
- 无修改 backend

---

## 2. Files Changed

| File | Change |
|------|--------|
| `web/src/pages/ExportPage.tsx` | 新增 — Export 页面 MVP 组件 |
| `web/src/App.tsx` | 新增 `/export` 路由 + ExportPage import + loading variant |
| `web/src/components/Sidebar.tsx` | 新增 "导出知识" 入口（Download 图标） |
| `web/src/lib/i18n.ts` | 新增 `nav.export` + 20 个 `export.*` i18n keys（zh/en） |

---

## 3. What Was Intentionally Not Implemented

- 不新增导出格式（仅 Markdown + ZIP，后端已支持）
- 不新增外部服务集成
- 不新增导出到 Obsidian vault
- 不新增定时/自动导出
- 不新增导出模板系统
- 不新增导出历史记录
- 不修改 backend API contract
- 不新增 backend endpoint
- JSON / OPML 格式（后端已支持但 spec 要求 MVP 仅 Markdown/ZIP）

---

## 4. Safety Constraints Preserved

- 不写真实 Obsidian vault
- 不调用外部服务
- 不调用真实 LLM/Cubox/Upstage
- 不处理真实私人资料
- 不破坏 explicit approval / human_approved 语义
- 不新增大型依赖
- 不触及 RAG/embedding/vector DB
- 不恢复 Graph/Sensemaking/Entity/Community 扩张

---

## 5. Browser/MCP Check

Chrome DevTools MCP 验证通过：

- `/export` 页面正常渲染（不再 fallthrough 到 Home）
- Sidebar "导出知识" 入口可见，位于工具与诊断分组
- 页面标题 "导出知识" + 中文安全副标题正确
- 范围选择（全部/标签/轨道）按钮交互正常
- 格式选择（Markdown/ZIP）展示正确
- 预览区显示卡片数量和预计文件大小
- 安全说明中文文案正确
- "预览内容" 模态框弹出并展示 Markdown 内容
- "下载导出" 按钮可见

---

## 6. Gates

| Gate | Command | Exit Code | Timeout |
|------|---------|-----------|---------|
| git diff --check | `git diff --check` | 0 | No |
| TypeScript build | `npm --prefix web run build` | 0 | No |
| product copy | `pytest tests/test_web_product_copy.py -q` | 0 | No |

Backend 无改动，无需 ruff/pytest backend。

---

## 7. UX States Covered

| State | Handling |
|-------|----------|
| 加载中 | App.tsx LoadingSkeleton（variant="default"） |
| 加载失败 | 错误横幅 + 中文错误消息 |
| 空已确认卡片 | EmptyState + 引导到审阅草稿 |
| 无选择（filter 后 0 结果） | "未选择卡片" 文字 |
| 导出中 | 下载按钮 disabled + "..." 文字 |
| 导出成功 | 绿色成功横幅 |
| 导出失败 | 警告色错误横幅 |
| 预览内容 | 模态框，最多显示 10000 字符 |
| 按标签筛选 | 下拉选择器 |
| 按轨道筛选 | 下拉选择器 |
