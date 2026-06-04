# Knowledge Detail UX 重构规格

## 问题

CardWorkspace.tsx（约 630 行）扁平渲染所有 `## Heading` 段落，没有信息层次结构。用户看到 Source Excerpt、AI Summary、AI Inference、Human Note 和 Reusable Prompts 作为同等级的带边框区域，无法区分"这条知识是什么"和"内部处理细节"。

"知识图谱"区域显示原始关系类型（same_source、same_tag、sha1），普通用户无法理解。技术字段如 source_content_hash、run_id 散布各处。

## 方案：4 层信息架构

### 第 1 层 — 默认阅读（KnowledgeHero）
立即可见。用户看到：
- 卡片标题、状态徽章、track、来源类型
- 一句话摘要（正文前 150 字符，去除 markdown）
- 从 `## Key Points` 部分或正文开头提取的核心要点
- 标签列表
- 来源信息（source_title、source_type）
- human note 预览（如存在）

### 第 2 层 — 结构化内容（KnowledgeSections，默认折叠）
两个可折叠分组：
- **理解内容**（Understanding）：AI Summary、Human Note、Key Points
- **处理过程**（Processing）：Source Excerpt、AI Inference、Reusable Prompts、Principles
- 所有 section 通过 parseSections() 保留，仅分组和折叠

### 第 3 层 — 相关知识（RelatedKnowledgePanel）
替代"知识图谱"：
- `graph.title`："知识图谱" → "相关知识"
- 关系原因人性化：
  - same_source → "来自同一来源：{source_title}"
  - same_tag → "共享标签 #tag"
  - same_wiki_section → "同属章节：{section_title}"
  - similar_title_or_term → "标题或术语相似"
- 强度指示简化

### 第 4 层 — 技术证据（可折叠 `<details>`，默认关闭）
- 现有技术细节：strategy_id、source_hash、run_id、prompt_versions
- 原始关系证据
- 所有不应默认可见的技术元数据

## 组件变更

| 组件 | 操作 |
|------|------|
| KnowledgeHero | 新建 — 第 1 层渲染 |
| KnowledgeSections | 从 CardSections 重构 — 分组、可折叠 |
| RelatedKnowledgePanel | 从 GraphNavigationPanel + RelatedCardsPanel 合并重构 |
| TechnicalEvidencePanel | 扩展现有 `<details>` |
| CardWorkspace | 简化为薄编排器 |

## i18n 变更

- `graph.title`："知识图谱" → "相关知识"
- `graph.related_by_source`："同源" → "来自同一来源"
- `graph.shares_tag`："同标签" → "共享标签"
- `graph.related_by_wiki_section`："同 Wiki 章节" → "同属章节"
- `library.related_group_same_source`："同源" → "来自同一来源"
- `library.related_group_same_tag`："同标签" → "共享标签"
- `wiki.local_graph_preview`："局部图谱预览" → "局部关系预览"
- `local_graph.title`："局部关系预览" → "局部关系预览"

## 非目标

- 无 LLM 调用
- 无新依赖
- 无后端变更
- 无审批边界变更
- 无信息删除
- 无 push
