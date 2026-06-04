---
name: knowledge-product-redesign-spec-review
description: Self-review of the 3 knowledge product redesign SPECs — assesses root cause resolution, feasibility, and implementation readiness
metadata:
  type: review
---

# Knowledge Product Redesign SPEC Self-Review

Date: 2026-06-04
Specs Reviewed:
- docs/specs/knowledge_card_v2.md
- docs/specs/distill_prompt_v2.md
- docs/specs/knowledge_library_ux_redesign.md

## 1. Do these SPECs really solve the root cause of "knowledge lacking value"?

**PASS — with caveats.**

Card v2 的 `core_insight`、`problem_it_solves`、`applicable_context`、`limitations_or_caveats`、`reusable_principle` 字段直接回答了审计中提出的问题：
- "这条知识的核心洞察是什么？" → `core_insight`
- "它解决什么问题？" → `problem_it_solves`
- "适用于什么场景？" → `applicable_context`
- "有什么限制条件？" → `limitations_or_caveats`
- "它能转化为什么原则/方法/决策？" → `reusable_principle` + `knowledge_type`

Prompt v2 通过 anti-hallucination 约束、source-grounded 规则、具体格式要求（"当...时，应该...，因为..."）确保模型产出真正的洞察而不是空泛摘要。

**Caveat**：SPEC 只是纸面上的设计。真正决定卡片价值的是 LLM 能否稳定产出这些字段的质量内容。如果模型不遵循 prompt 约束，卡片仍然会垃圾。这需要实施后通过实际测试验证。

## 2. Is this just adding more fields?

**PASS — no.**

v2 不是单纯增加字段数量。关键区别：

1. **字段语义变了**：`ai_summary_bullets` → `core_insight`（从摘要到洞察），`ai_inference_bullets` → `supporting_evidence`（从推断到证据追溯）
2. **增加了判断维度**：`knowledge_type` 让用户知道这是什么类型的知识，决定如何使用
3. **增加了质量约束**：anti-hallucination、source-grounded、具体格式要求
4. **字段有明确的用户价值**：每个字段都解释了"为什么用户需要这个"

如果只是为了让字段更多，不需要 `one_sentence_takeaway`（可以截断 `core_insight`）、不需要 `problem_it_solves`（可以合并到 `core_insight`）。这些字段的存在是为了回答不同的用户问题。

**V1 字段数**：~8 个核心字段
**V2 字段数**：~15 个核心字段
**增量**：7 个字段，但每个都回答了一个 v1 没回答的用户问题

## 3. Will this make the Review page more complex?

**PARTIAL — yes, but intentionally.**

Review 页面从 approve/reject 二选一变为 5 种操作：
- Confirm
- Edit & Confirm
- Downgrade to Note
- Merge with Existing
- Discard

这确实增加了复杂度。但这是必要的复杂度，因为：

1. **approve/reject 太粗糙**：有些卡片有价值但有错误，应该 Edit & Confirm 而不是 reject
2. **有些卡片不值得成为知识**：应该 Downgrade to Note 而不是 reject
3. **有些卡片重复**：应该 Merge with Existing 而不是单独存在

**风险**：5 种操作对普通用户可能太多。

**建议**：
- 第一阶段只实现 Confirm / Edit & Confirm / Discard（3 种）
- Downgrade to Note 和 Merge with Existing 后续迭代添加
- 每个操作有清晰的文字说明

**需要人工决策**：第一阶段支持几种操作？

## 4. Will this induce LLM to fabricate information not in the source?

**PASS — no, anti-hallucination constraints prevent this.**

Prompt v2 包含 7 条 anti-hallucination 约束：
1. 不生成原文没有的事实
2. 区分原文内容和模型推断
3. 承认信息不足
4. 不做时间预测
5. 不生成统计数字
6. 不引用外部来源
7. 不编造专家观点

此外：
- `supporting_evidence` 必须包含原文引述（`evidence_quotes`）
- 如果字段无法生成，输出"信息不足以判断"
- Pipeline 有质量检查：如果 `supporting_evidence` 无法追溯，标记为"证据不足"

**风险**：LLM 可能不完全遵循约束，特别是"区分原文和推断"。

**缓解**：实施后需要测试 LLM 输出的 factual accuracy。可以添加自动化检查：证据引述是否在原文中存在（字符串匹配或语义相似度）。

## 5. Does it maintain the ai_draft / human_approved boundary?

**PASS — yes.**

SPEC 1 明确定义了 approval 边界：
- ai_draft 由 distill pipeline 生成
- human_approved 只能由人主动 Confirm 产生
- human_note 只能由人填写，distill prompt 不生成，pipeline 不填充
- 审批状态转换图清晰：ai_draft → human_approved / discard / downgrade

SPEC 3 的 Review 页面设计保持了这一边界：所有操作都是用户主动触发。

**不会自动 approve**：即使在 demo 模式下，预置的 demo 卡片也应该是手动标记为 human_approved 的（在开发时预先准备好），不是运行时自动生成。

## 6. Will this introduce RAG / embedding / GraphRAG?

**PASS — no.**

三份 SPEC 都明确排除了 RAG / embedding / GraphRAG / vector DB：

- Brainstorm: "明确不做什么" → 不做 RAG / embedding / GraphRAG / vector DB
- SPEC 1: 关系区基于同标签/同主题/被提及，不需要 embedding
- SPEC 2: prompt 不要求模型搜索外部知识
- SPEC 3: 相关知识面板重命名为 RelatedKnowledgePanel，只展示 3 种关系，不做社区检测

当前 BM25  lexical search 保持不变。

## 7. Will this break local-first?

**PASS — no.**

所有变化都保持 local-first：
- 卡片存储在本地 vault
- 不引入外部服务
- 不调用真实 LLM（使用 FakeProvider 或本地配置的 LLM）
- 关系计算基于本地数据（标签、topic、标题匹配）
- 搜索使用 BM25（已有）

## 8. Can it be compatible with old cards?

**PASS — yes, through lazy migration.**

SPEC 1 定义了完整的 v1 → v2 兼容策略：

1. **不删除 v1 字段**：只增加字段
2. **字段映射表**：每个 v1 字段映射到对应的 v2 字段
3. **Fallback 规则**：v1 卡片缺失 v2 字段时有 fallback
4. **Lazy migration**：不做批量迁移，按需升级

SPEC 3 定义了前端 fallback：
- v1 卡片在 v2 前端下正常展示
- 缺失字段不展示或 fallback 到对应 v1 字段

**风险**：Fallback 规则如果有 bug，旧卡片展示异常。

**缓解**：充分的 fallback 单元测试 + 测试现有 4 张卡片。

## 9. Can it be implemented in phases?

**PASS — yes.**

三份 SPEC 设计了 6 个阶段：

| Phase | 内容 | 依赖 |
|-------|------|------|
| Phase 0 | CardSummary + presenter 添加 v2 字段 | 无 |
| Phase 1 | FakeProvider 输出有意义内容 | Phase 0 |
| Phase 2 | distill prompt v2 | Phase 0 |
| Phase 3 | Library 页面简化 + API 修复 | Phase 0 |
| Phase 4 | Detail 页面五层阅读路径 | Phase 1, 2 |
| Phase 5 | Review 页面增强 | Phase 3 |

每个阶段可以独立部署和测试。

**Phase 0** 是关键：先让后端支持 v2 字段，前端和 prompt 才能工作。

## 10. What needs human decision?

以下问题需要人工决策：

### High Priority（实施前需要决定）

1. **v2 字段是否太多？** 15 个核心字段 + 5 个技术字段。如果觉得太多，可以砍掉 `related_questions` 和 `next_actions` 到技术区。
2. **审阅页面第一阶段支持几种操作？** 建议 3 种（Confirm / Edit & Confirm / Discard），还是 5 种？
3. **knowledge_type 的 8 种枚举是否合适？** 可以砍掉 `evidence` 和 `todo`（对个人知识管理不太常用）。
4. **FakeProvider 如何产出有意义的内容？** SPEC 建议基于输入关键词生成，但具体实现方式需要确认。

### Medium Priority（实施前可以讨论）

5. **`one_sentence_takeaway` 和 `core_insight` 是否有重叠？** SPEC 认为它们回答不同问题（"说什么" vs "洞察什么"），但用户可能觉得重复。
6. **Library 页面的 sort 默认按 value_score 是否合适？** 用户可能更想按日期排序。
7. **Demo 卡片是预置还是 FakeProvider 实时生成？** 预置更容易控制质量，实时生成更灵活。

### Low Priority（可以后续迭代）

8. **Downgrade to Note 和 Merge with Existing 什么时候实施？** 建议后续迭代。
9. **Source Excerpt 是否还需要完整展示？** v2 的 `supporting_evidence` + `evidence_quotes` 可能已经足够。

## Summary

| Question | Verdict | Notes |
|----------|---------|-------|
| 1. 解决根因？ | PASS | 需要实施后验证 LLM 产出质量 |
| 2. 只是增加字段？ | PASS | 字段有明确的用户价值 |
| 3. Review 页面变复杂？ | PARTIAL | 建议分阶段实施操作数量 |
| 4. 诱导 LLM 瞎编？ | PASS | 有 anti-hallucination 约束 |
| 5. 保持 approval 边界？ | PASS | 明确定义了转换规则 |
| 6. 引入 RAG/embedding？ | PASS | 明确排除 |
| 7. 破坏 local-first？ | PASS | 全部本地化 |
| 8. 兼容旧卡片？ | PASS | 有 lazy migration 策略 |
| 9. 分阶段实施？ | PASS | 6 个阶段，可独立部署 |
| 10. 需要人工决策？ | 4 个 high-priority 问题 | 见上列表 |

**Overall Verdict: PASS with 4 high-priority decisions pending human review.**
