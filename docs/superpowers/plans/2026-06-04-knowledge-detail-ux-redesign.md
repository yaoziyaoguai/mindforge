# Knowledge Detail UX 重构 — 实现计划

> **目标：** 重构 CardWorkspace.tsx，以 4 层信息层次结构呈现知识卡片，让用户能理解"这条知识是什么"而不被内部处理细节淹没。

**技术栈：** React 18, TypeScript, Vite, vitest + @testing-library/react

---

### 任务 1：更新 i18n 字符串

**文件：**
- 修改：`web/src/lib/i18n.ts`

**变更：**
- `graph.title`："知识图谱" → "相关知识"
- `graph.related_by_source`："同源" → "来自同一来源"
- `graph.shares_tag`："同标签" → "共享标签"
- `graph.related_by_wiki_section`："同 Wiki 章节" → "同属章节"
- `library.related_group_same_source`："同源" → "来自同一来源"
- `library.related_group_same_tag`："同标签" → "共享标签"
- `library.related_group_same_wiki_section`："同 Wiki 章节" → "同属 Wiki 章节"
- `library.related_group_same_review_batch`："同批次" → "同批次审阅"
- `library.related_group_source_location_neighbor`："源位置相邻" → "来源位置相近"
- `wiki.local_graph_preview`："局部图谱预览" → "局部关系预览"
- `local_graph.title`："局部关系预览"（保持）
- `graph.no_relationships`：更新为更友好的文案
- 新增 key：`card.understanding_sections`、`card.processing_sections`、`card.key_points`、`card.no_key_points`、`card.related_knowledge`

### 任务 2：添加 KnowledgeHero 组件

**文件：**
- 修改：`web/src/components/CardWorkspace.tsx`（添加 KnowledgeHero 函数）

**变更：**
- 在 CardWorkspace.tsx 中添加 `KnowledgeHero` 组件（保持文件数低，同一领域）
- 渲染：标题、状态徽章、一句话摘要、标签、来源信息、human note 预览
- 摘要：复用 `stripMarkdown(body).slice(0, 150)` 逻辑
- 核心要点：如果存在，从 `## Key Points / 核心要点` 部分提取

### 任务 3：重构 CardSections → KnowledgeSections

**文件：**
- 修改：`web/src/components/CardWorkspace.tsx`（替换 CardSections）

**变更：**
- 将 section 分组为"理解层"（AI Summary、Human Note、Key Points）和"处理层"（Source Excerpt、AI Inference、Reusable Prompts、Principles）
- 每组为可折叠面板，默认折叠
- 所有 section 保留，仅分组

### 任务 4：合并 Graph + Related → RelatedKnowledgePanel

**文件：**
- 修改：`web/src/components/CardWorkspace.tsx`（重构）
- 修改：`web/src/components/GraphNavigationPanel.tsx`（更新 i18n 引用）
- 修改：`web/src/components/LocalGraphPreview.tsx`（更新 i18n 引用）

**变更：**
- CardWorkspace：将 GraphNavigationPanel + RelatedCardsPanel 合并为单个"相关知识"区域
- GraphNavigationPanel：`t("graph.title")` 现在返回"相关知识"
- LocalGraphPreview：i18n key 已更新
- 关系原因现在显示更新后 i18n key 的人类可读文本

### 任务 5：确保技术字段隐藏

**文件：**
- 修改：`web/src/components/CardWorkspace.tsx`

**变更：**
- 验证 source_content_hash、run_id、strategy_id、prompt_versions、stage_models 都在 `<details>` 内（已完成）
- 如果在其他地方暴露了原始 relation 证据，添加到技术细节中
- 验证默认可见区域无原始字段

### 任务 6：更新 CardWorkspace 渲染顺序

**文件：**
- 修改：`web/src/components/CardWorkspace.tsx`

**新渲染顺序：**
1. Header（标题、状态、track、来源）— 不变
2. KnowledgeHero — 新增 Layer 1
3. KnowledgeSections — 重构 Layer 2（可折叠分组）
4. RelatedKnowledgePanel — Layer 3（合并 graph + related）
5. ProvenanceTrail — 保持
6. Source/History — 保持
7. TechnicalEvidence — Layer 4（扩展 `<details>`）

### 任务 7：更新文档

**文件：**
- 修改：`docs/zh-CN/web-wiki.md`

**变更：**
- 更新知识详情页描述
- 移除"知识图谱"引用，改用"相关知识"

### 任务 8：测试

- `cd web && npm test`（vitest）
- `cd web && npm run build`
- `cd web && npm run lint`（如存在）
- `python -m pytest tests/test_api_topics.py tests/test_topic_presenter.py -q`
- `git diff --check`
- `rg "知识图谱|Same tag|Same source|sha1" web/src`

### 风险：无。所有变更仅限前端，后端语义未改变。
