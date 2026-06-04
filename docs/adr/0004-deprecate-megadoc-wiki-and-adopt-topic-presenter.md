# ADR 0004: 废弃 Megadoc Wiki 并采用 Topic Presenter

## 状态

Accepted（截至 2026-06-04 部分实现）

**实现状态：**
- `llm_rebuild_wiki`: 完全禁用（抛出 `WikiError`）— 所有入口已冻结
- `rebuild_main_wiki`: 完全禁用（抛出 `WikiError`）— 所有入口已冻结
- CLI `wiki rebuild`: 已隐藏，打印废弃通知，exit 0
- Web `POST /api/wiki/rebuild`: 返回 410 Gone
- `approval_service` 自动重建：已移除，返回废弃通知
- `TopicPresenter`: 已实现，包含真实 summary 提取和审批边界强制执行
- `GET /api/topics`: 已实现，使用稳定的 `TopicListResponse` schema
- `GET /api/topics/{topic_name}`: 已实现，使用稳定的 `TopicViewResponse` schema
- 前端重构：**尚未开始** — 阻塞于 API 契约锁定（现已完成）
- `Main-Wiki.md` 读取端点：仍可用于遗留读取访问；不再写入新内容

## 上下文

MindForge 当前的 Knowledge Experience 依赖 "Megadoc Wiki"（`30-Wiki/Main-Wiki.md`）。该文件通过拼接 `human_approved` 卡片生成，或者更危险地，通过 LLM 基于这些卡片合成章节（`llm_rebuild_wiki`）。

这种方法暴露了严重的架构和产品问题：

1. **违反审批边界**：`llm_rebuild_wiki` 生成新文本（摘要、概述），绕过了 `ai_draft` → `human_approved` 管线。它将未经验证的 LLM 幻觉呈现为 "Main Wiki" 内容，违反了核心的 local-first、approval-first 理念。
2. **可扩展性与 UX 灾难**：包含数百张卡片的单一 Markdown 文件不可读。前端（`WikiPage.tsx`）只是渲染一个手风琴列表，不提供结构层次或语义导航。
3. **贫乏的知识模型**：卡片被视为扁平文本容器。关系（"Related Sections"）使用共享卡片的 Jaccard 重叠度计算，而非显式语义链接（如 "supports"、"contradicts"）。

## 决策

我们将完全重构 Knowledge 和 Wiki 子系统：

1. **废弃 `Main-Wiki.md`**：不再写入单一 Wiki 文件。现有文件将被忽略（作为遗留产物保留）。
2. **严格执行审批边界**：`llm_rebuild_wiki` 已禁用（抛出 `WikiError`）。`rebuild_main_wiki` 也已禁用。所有 LLM 生成的合成内容**必须**以 `status: ai_draft` 和 `knowledge_type: summary` 的独立卡片身份进入系统。在人类显式审批之前，不能显示在核心知识视图中。
3. **采用 MVC/Presenter 架构**：Wiki 将从持久化文件转变为**运行时视图**。
   - **后端（`TopicPresenter`）**：查询已审批卡片，按 Topic/Track 分组，解析显式语义关系，提供 JSON。
   - **前端**：渲染三栏 "Topic Browser" 替代扁平列表。
4. **引入 Knowledge Model v2**：卡片的 YAML frontmatter 将丰富 `knowledge_type`（concept、claim、insight 等）和显式 `relations`（supports、expands 等）。

## 后果

- **正面**：恢复了 `human_approved` 边界的绝对完整性。知识库成为真正的语义网络而非文本转储。前端 UX 大幅改进。
- **负面**：前端需要大量重构。必须为缺少显式类型和关系的旧卡片实现兼容层。
- **迁移**：不需要数据迁移脚本。YAML schema 的变更纯粹是附加的，解析器会对旧卡片使用安全 fallback（`knowledge_type: concept`）。
