# Export Page — Product Direction Spec

- **Date**: 2026-05-27
- **Status**: spec-only — 不在此 spec 内实现
- **Trigger**: Web IA audit 发现 `/export` URL 无独立页面，fallthrough 到 Home

---

## 1. 当前 Export 能力真实状态

### Backend API（已存在）

| Endpoint | Method | 行为 |
|----------|--------|------|
| `/api/library/knowledge/export` | POST | 返回 JSON 包裹的 Markdown 导出内容（含 selected card ids、format、exported_at） |
| `/api/library/knowledge/export/download` | POST | 返回 ZIP 文件下载（含 Markdown 文件 + metadata JSON） |

两个端点都接受 `ExportCardsRequest`，支持按 card ID 列表选择导出，支持 `format` 参数（默认 `markdown`）。

### Web UI（当前状态）

- 无独立 `/export` 路由 — `App.tsx` 中未注册 Export 页
- 导出触发点在 `LibraryPage` 内，通过批量选择卡片 + 导出按钮触发
- i18n keys 已定义（`library.export_selected`、`library.export_preview_title` 等）
- 用户不可通过 URL 直接访问 Export 页面

### 结论

Export **能力存在**，但**入口不清晰**。用户无独立 Export 页面来：
- 查看可导出内容概览
- 选择导出格式和范围
- 预览导出结果
- 下载导出文件

---

## 2. 产品决策：是否需要独立 Export 页面？

### 推荐：需要独立 Export 页面，但范围有限

**理由：**

1. **可发现性** — 当前用户只能在 Library 批量选择后才能触发导出，新用户无法知道 Export 存在
2. **主路径完整性** — MindForge 核心价值闭环是 Import → Review → Organize → Export。缺少 Export 页面使闭环不可见
3. **导航一致性** — Sidebar 已有 Library、Wiki、Recall、Graph 等独立页面，Export 作为同等重要的一环应有独立入口
4. **非目标** — 不做外部服务集成、不做复杂格式转换、不做 Obsidian 实时同步

### 替代方案评估

| 方案 | 优点 | 缺点 |
|------|------|------|
| A. 独立 Export 页面（推荐） | 可发现、闭环完整、导航一致 | 新增 1 个页面 + 1 个路由 |
| B. 仅保留 Library 内触发 | 零前端改动 | 不可发现、闭环断裂、IA 审计问题未解决 |
| C. Library + Card detail 双入口 | 灵活 | 复杂度高于收益，Card detail 已有自身焦点 |

**决策：方案 A — 独立 Export 页面。**

---

## 3. Export 页面 — 最小可用体验（v1）

### 页面结构

```
/export
├── 导出范围选择
│   ├── 全部已确认卡片（默认）
│   ├── 按标签筛选
│   └── 按 track 筛选
├── 导出格式选择
│   └── Markdown（唯一 MVP 格式）
├── 预览区域
│   ├── 卡片数量预览
│   ├── 卡片标题列表（可展开查看内容摘要）
│   └── 预计文件大小
├── 导出操作
│   ├── [预览 Markdown] — 在新 tab 中打开渲染预览
│   └── [下载 ZIP] — 触发 /api/library/knowledge/export/download
└── 导出历史（可选 v1.1）
    └── 最近 N 次导出记录（时间、格式、卡片数）
```

### 不需要做（v1 排除）

- 不新增导出格式（仅 Markdown）
- 不新增外部服务集成
- 不新增导出到 Obsidian vault
- 不新增定时/自动导出
- 不新增导出模板系统
- 不做增量导出（每次都全量或按筛选条件）

### 路由注册

```tsx
// App.tsx 中新增
<Route path="/export" element={<ExportPage />} />
```

### API 兼容性

- 复用现有 `/api/library/knowledge/export` 和 `/api/library/knowledge/export/download`
- 不新增 API endpoint
- 不修改现有 API contract

---

## 4. 非目标（明确排除）

- **不做**：真实 Obsidian vault 写入
- **不做**：外部服务（Notion、Google Docs 等）
- **不做**：大导出系统（1000+ 卡片批量处理管线）
- **不做**：自定义模板系统
- **不做**：定时/自动导出
- **不做**：导出格式转换（PDF、HTML、DOCX 等）— 如有需求，应单独 spec

---

## 5. 实现阶段建议

| 阶段 | 范围 | 预估复杂度 |
|------|------|-----------|
| Phase 1（本 spec 对应） | 独立 Export 页面 + 路由 + 预览 + 下载 | 小（1 页 + 1 路由） |
| Phase 2（未来） | 导出历史记录 | 中（需持久化导出记录） |
| Phase 3（未来） | 新导出格式（JSON、HTML） | 中（需扩展后端 pipeline） |

---

## 6. 与现有 IA 的关系

- Export 页面是 Web IA 闭环的最后一块拼图
- 当前 Sidebar 中 Export 已出现在工具区，但点击后无独立页面 → 用户困惑
- 本 spec 修复此 IA 断裂
- 不引入新的导航层级、不改变现有 Sidebar 结构

---

## 7. 参考

- Web IA audit: `docs/implementation-notes/2026-05-27-111-web-ia-simplification.md`
- Export API: `src/mindforge_web/routers/library.py:L90-L220`
- i18n keys: `web/src/lib/i18n.ts:L775-L790`
- Sidebar nav: `web/src/components/Sidebar.tsx`
