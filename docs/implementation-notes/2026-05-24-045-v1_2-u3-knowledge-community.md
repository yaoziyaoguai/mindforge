# v1.2 U3 Knowledge Community Concept — Implementation Notes

> **Status note (v4.6 docs simplification, 2026-05-26)**: This document is historical implementation evidence. Current product truth: Knowledge Community features (source/tag/wiki_section community detection, community browser) are lab/internal. They are not part of the product main path, not exposed in main navigation, and have no API stability commitment. The deterministic community detection approach described here (no LLM, no embedding) is preserved for reference value, but the feature itself has been contracted. See docs/README.md and docs/dev/docs-reset-index.md.

## 决策

### 社区检测完全确定性

不使用 GraphRAG 的 Leiden 社区检测算法，不调用 LLM 生成社区摘要。社区定义完全由卡片元数据决定：

- **source community**: 共享 `source_id` 的卡片群
- **tag community**: 共享任一 tag 的卡片群
- **wiki_section community**: 共享任一 wiki_section 的卡片群

### 最少成员阈值 (min_members=2)

1 张卡不构成社区。阈值可配置但默认 2，与 GraphRAG 社区检测的直觉一致（一个社区至少要有内部关系）。

### 社区描述非 LLM 生成

每个社区的 `description` 是纯中文模板拼接，完全确定性、可重复。不调用任何外部 API。

### 排序规则

社区按 `member_count` 降序排列。不做二级排序（无 tie-breaking），上游可自行处理。

## 边界权衡

- **重叠成员**: 同一张卡片可以属于多个社区（source + tag + wiki_section 同时存在），不强制互斥分区。选择 flat 社区列表而非层级结构，与当前无 vector/embedding 的架构一致。
- **缺失字段**: 卡片缺少 `source_id`/`tags`/`wiki_sections` 时静默跳过对应社区类型，不做补全或推断。
- **Web API 返回结构**: 直接返回 flat list，不分组。如未来需要按 community_type 分组，由前端或上层 service 处理。

## API 设计

```
GET /api/knowledge/communities
```

返回 `KnowledgeCommunitiesResponse`，包含按 member_count 降序的所有社区。

## 已知限制

- 不做跨类型社区合并（如同一 group 既有 source 又有 tag 重叠不会合并为"复合社区"）
- 不做时间衰减（旧卡片和新卡片同一 source 计入同一社区，无权重差异）
- 不做社区层级（flat 列表，无 parent-child 关系）
