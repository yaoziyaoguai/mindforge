# v1.2 U4 Retrieval Context Composer Enhancement — Implementation Notes

> **状态: superseded (by-contraction, 2026-05-28)**
> Community/Topic Detection 已降级为 lab。参考: CPS §3 lab

## 决策

### 社区信息注入点

选择在 facade 层计算 communities 并通过 `assemble_discovery_context` 的 `communities` 参数注入，而非在 `assemble_discovery_context` 内部计算。原因：

1. `assemble_discovery_context` 保持为 `Graph` 的纯函数 — 不新增对卡片原始数据的依赖
2. `detect_communities` 需要卡片原始数据（source_id, tags, wiki_sections），这些在 `DeterministicGraphBuilder._cards` 中已缓存
3. facade 已经是编排层，适合做"计算社区 + 过滤中心卡片 + 组装"这条流水线

### 过滤策略

`detect_communities` 返回所有满足 min_members=2 的社区。`_center_card_communities` 过滤出包含当前中心卡片的社区。用户查看 card_1 的 discovery context 时只看到 card_1 所属的社区，而非全局所有社区。

### DiscoveryCommunityRef 设计

新建 `DiscoveryCommunityRef` dataclass（frozen），字段与 `KnowledgeCommunity` 高度一致但去掉了 `member_card_ids`（discovery context 中不需要完整成员列表，community API 端单独提供）。字段：
- community_type: "source" | "tag" | "wiki_section"
- shared_entity: 共享实体名
- member_count: 成员数
- description: 确定性文本描述

## 边界权衡

- **重复计算**: 每次 `get_discovery_context` 调用都会对全部 approved cards 运行 `detect_communities`。当前卡片规模（<500）下 O(n) 分组成本可忽略。未来若规模增长可缓存。
- **API contract**: `GET /api/discovery/context` response 新增 `communities` 字段（list）。前端可忽略未知字段，向后兼容。

## 已知限制

- 不在 discovery context 中返回非中心卡片所属社区（仅过滤中心卡片所属）
- 社区与 direct_matches/neighbor_cards 之间没有显式关联（平行列表，语义独立）
