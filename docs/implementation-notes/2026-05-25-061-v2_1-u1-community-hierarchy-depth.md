---
title: "v2.1 U1 Community Hierarchy & Depth — Implementation Note"
date: 2026-05-25
status: Complete
version: v2.1
---

# v2.1 U1 Community Hierarchy & Depth — Implementation Note

## What was done

v2.1 U1 扩展了 `detect_communities()` 确定性知识社区检测，新增三层次增强：

### Multi-level Community Hierarchy
- `_build_hierarchy()` — 自动计算社区层级关系（source → tag → wiki_section）
- 社区 B 是 A 的子社区，当且仅当 B 的成员是 A 的子集，且类型不同
- 层级方向严格限制为 source → tag → wiki_section（最宽→最具体）
- 新增 `SubCommunityRef` dataclass 记录子社区引用

### Community Overlap Detection
- `_detect_overlaps()` — 检测跨类型社区的成员共享
- 记录共享成员 ID，便于用户理解"知识交叉关系"
- 新增 `CommunityOverlap` dataclass

### Community Quality Scoring
- `_card_quality()` — 每张卡片的确定性质量评分（0.0-1.0）
- 评分维度：provenance（0.2）+ tags（max 0.3）+ wiki_sections（max 0.3）+ body_length（0.2）+ approved（0.2）
- 社区质量分 = 成员卡片质量分的算术平均
- 纯确定性计算，不调用 LLM

## Changes

- `src/mindforge/relations/community.py` — 扩展 KnowledgeCommunity (+3 新字段)，新增 SubCommunityRef/CommunityOverlap dataclass，新增 3 个 helper
- `src/mindforge_web/schemas.py` — KnowledgeCommunityResponse 增加 sub_communities/overlap_with/quality_score
- `src/mindforge_web/services/web_facade.py` — knowledge_communities() 传递新字段
- `web/src/api/types.ts` — 新增 SubCommunityRefResponse/CommunityOverlapResponse interface，扩展 KnowledgeCommunityResponse
- `tests/relations/test_community.py` — +18 tests (27→27, 6 类新增)
- `tests/test_review_approval_boundary.py` — whitelist 增加 community.py（只读 human_approved 用于评分）

## Design Rationale

- **确定性算法**: 所有新增计算均为纯确定性（subset checking、arithmetic mean），不调用 LLM，不做 embedding
- **向后兼容**: 新字段默认值 (empty tuple/0.0)，现有 callers 无需修改
- **不可变数据**: 所有新 dataclass 采用 `frozen=True`，符合项目不变性约定
- **UI 暂不使用新字段**: 新字段仅在 API 响应中提供，UI 增强留给 v2.1 U5

## Non-goals

- 不做 LLM-based community summary
- 不做 embedding/vector-based clustering
- 不改 GraphPort 接口

## Gates

- ruff check: exit 0
- pytest full (370+): exit 0, 100% pass
- npm build: exit 0
- product copy: exit 0
- git diff --check: exit 0
