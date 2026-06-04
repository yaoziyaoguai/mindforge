# Web 知识主题页面（Topic View）

v0.5 起，Web Wiki 页面已从 LLM-based Wiki synthesis（Generate Wiki）迁移为运行时 Topic View。

---

## 页面功能

| 功能 | 说明 |
|------|------|
| **主题列表** | 左侧列出所有包含 `human_approved` 卡片的 topic 名称，来自 `GET /api/topics` |
| **主题卡片浏览** | 中间展示选中 topic 下的已审批卡片，含 title、knowledge_type、summary、tags、source 等字段 |
| **关系与来源面板** | 右侧展示选中卡片的 relations、provenance、human_note、时间信息 |
| **审批边界** | 仅展示 `human_approved` 卡片；`ai_draft` 被严格排除 |

---

## 与旧版 Wiki 的区别

| 旧版（v0.4 及之前） | 新版（v0.5+） |
|------|------|
| LLM synthesis 生成 Main-Wiki.md | 运行时 Topic View，从已审批卡片直接构建 |
| 需要手动点击 Generate Wiki 触发 LLM 调用 | 无需触发，实时反映卡片数据 |
| 生成持久化 Markdown 文件 | 无持久化文件，纯运行时视图 |
| `/api/wiki/rebuild` 可用 | `/api/wiki/rebuild` 已废弃（返回 410） |

## Generate Wiki 按钮

**Generate Wiki 按钮已移除。** LLM Wiki synthesis（`llm_rebuild_wiki`）和 deterministic template rebuild（`rebuild_main_wiki`）在 v0.5 均已废弃。Wiki 现在是运行时 Topic View，无需手动触发合成。

## 旧 Main-Wiki.md

如果旧版 MindForge 曾生成过 `Main-Wiki.md`，该文件不再更新。Wiki 页面现在展示的是 TopicPresenter 提供的实时视图，不是该文件的内容。

---

## 相关 API

| Endpoint | 用途 |
|------|------|
| `GET /api/topics` | 列出所有包含 `human_approved` 卡片的 topic |
| `GET /api/topics/{topic_name}` | 获取指定 topic 的运行时视图（仅 `human_approved` 卡片） |

详细 API contract 见 `docs/specs/topic_view_api.md`。

---

## 知识详情页信息架构

v0.5+ 的知识详情页（Library 卡片详情）采用 4 层信息架构：

| 层级 | 名称 | 说明 |
|------|------|------|
| 第一层 | 阅读层 | 一句话摘要、核心要点、标签、来源、人工备注预览 — 默认可见 |
| 第二层 | 结构化内容 | 理解内容（AI 摘要、人工备注等）与处理过程（来源摘录、推理等）分组折叠 |
| 第三层 | 相关知识 | 关联卡片，按人话关系原因分组（如"来自同一来源"、"共享标签 #xxx"） |
| 第四层 | 技术信息 | 技术字段（source_hash、run_id 等）默认折叠 |

原有"知识图谱"区域已更名为"相关知识"，关系原因从内部代码（如 `same_tag`）改为人话解释（如"共享标签"）。

## 相关命令

```bash
mindforge wiki status       # CLI 查看 Wiki 状态
mindforge wiki show         # CLI 查看 Wiki 内容（Topic View）
mindforge wiki rebuild      # 已废弃 — 退出码 0，打印废弃提示
```
