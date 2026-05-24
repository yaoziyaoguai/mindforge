---
title: "v2.1 U3 Discovery Context Composer Enhancement — Implementation Note"
date: 2026-05-25
status: Complete
version: v2.1
---

# v2.1 U3 Discovery Context Composer Enhancement — Implementation Note

## What was done

v2.1 U3 扩展了 DiscoveryContext，增加确定性可解释推理文本和粗略 token 估计。

### Reasoning: Deterministic Explainability

- 新增 `_build_reasoning()` — 纯基于计数的中文可解释文本生成
- 不调用 LLM，纯 deterministic 字符串拼接
- 格式：`中心卡片「T」通过 N 个直接关联...共享...。属于 M 个知识社区。`
- 覆盖 7 种场景的测试：全部为空、仅直接关联、含 Wiki section、含 source/tag、无共同属性但属社区、集成测试

### Token Estimation: Context Budgeting

- 新增 `_estimate_token_count()` — 粗略 token 数估计
- 启发式：总字符数 * 0.5（中英文混合折中）
- 仅统计可见文本：标题、evidence、relation_reason、community description
- 不调用 tiktoken，不调用 LLM
- 帮助 UI 判断上下文规模，不用于 token limit enforcement

### API Schema 扩展

- `DiscoveryContextResponse` 增加 `reasoning: str` 和 `estimated_token_count: int`
- facade `_discovery_context_response()` 透传新字段

## Changes

- `src/mindforge/relations/discovery_context.py` — +2 helpers +2 fields
- `src/mindforge_web/schemas.py` — +2 response fields
- `src/mindforge_web/services/web_facade.py` — 透传新字段
- `tests/relations/test_discovery_context.py` — +10 tests (31 total)

## Design Rationale

- **不调用 LLM**：reasoning 是数据描述，不需要生成式 AI
- **中文 reasoning**：面向中文用户的可读解释
- **Token 估计保守**：0.5 token/char 覆盖中英文混合场景
- **纯函数**：所有新增函数均为 deterministic pure functions

## Non-goals

- 不做 LLM-based reasoning
- 不做真实 token counting（tiktoken）
- 不做 context window enforcement
- 不做 RAG answering

## Gates

- ruff check: exit 0
- pytest full (~380+): exit 0, 100% pass
- npm build: exit 0
- product copy: exit 0
- git diff --check: exit 0
