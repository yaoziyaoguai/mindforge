---
name: knowledge-card-v2-spec
description: Specification for Knowledge Card v2 schema — restructures cards from pipeline-centric to insight-centric model
metadata:
  type: spec
---

# Knowledge Card v2 规范说明

日期：2026-06-04
状态：草稿 — 等待人工审阅

## 1. 背景与问题

MindForge 的 Knowledge Card v1 采用以下结构：

```yaml
---
title: "..."
status: ai_draft | human_approved
track: knowledge_card
tags: [tag1, tag2]
---

## Source Excerpt
...

## AI Summary
...

## AI Inference
...

## Reusable Prompts/Principles
...

## Project Hooks
...

## Review Questions
...

## Action Items
...
```

**问题**：

1. 字段以 pipeline 阶段命名（AI Summary, AI Inference, Review Questions），用户看到的是"处理过程"而不是"知识本身"
2. 缺少 `core_insight` 字段——没有要求模型提炼真正的洞察
3. 缺少 `applicable_context` 和 `limitations_or_caveats`——用户不知道什么时候适用、什么时候不适用
4. 缺少 `problem_it_solves`——用户不知道为什么要存这条知识
5. `Review Questions` 输出的是考试题（含答案），对个人知识管理无用
6. `Human Note` 是空 HTML 注释模板，CLI approve 只有 `--confirm` 没有编辑步骤
7. `tags` 没有透出到 API 响应（LibraryCardResponse 缺少 tags 字段）
8. "一句话摘要"实际取的是 body 前 150 字符（经常是 `## Source Excerpt` 的开头），不是 AI Summary

## 2. v1 为何缺乏价值

v1 卡片的设计假设是"忠实提炼原文"（faithfully extract）。这导致：

- **AI Summary** 是 paraphrase（改写），不是 insight（洞察）
- **AI Inference** 是基于原文的推测，但没有区分"原文支持"和"模型推断"
- **Reusable Prompts/Principles** 过于泛化（如"使用不可变数据"），不是具体可操作的原则
- **Review Questions** 是考试题格式，不是帮助用户理解知识的引导问题
- **Action Items** 是从原文推导的任务，但没有说明"为什么这条知识推导出这个行动"

**根本原因**：prompt 没有要求模型做判断、区分、提炼、连接。它只要求模型"总结"和"推断"。

## 3. v2 设计目标

1. **每张卡片回答一个核心问题**：这条知识为什么对我有价值？
2. **字段以用户理解为中心**，不是以 pipeline 产出为中心
3. **保持 local-first**：不引入 embedding、RAG、vector DB
4. **保持 approval 边界**：ai_draft 只能由人变成 human_approved，human_note 只能由人填写
5. **向后兼容**：v1 卡片可以在 v2 结构下正常展示
6. **可分阶段实施**：先 schema，再 prompt，再 UI

## 4. v2 不做什么

1. **不删除 v1 的任何字段** — 只增加字段，v1 字段映射到 v2 对应位置
2. **不改变 YAML frontmatter 格式** — 保持现有 frontmatter 结构，只增加字段
3. **不引入新的 approval 状态** — 保持 ai_draft / human_approved / human_rejected
4. **不改变 card ID 生成方式** — 保持 `YYYYMMDD--slug.md` 格式
5. **不改变 vault 目录结构** — 保持 `vault/20-Knowledge-Cards/{topic}/` 结构
6. **不引入 confidence score 作为展示字段** — 质量评分进入技术证据区，不影响主要阅读

## 5. 新 Schema 设计

### 5.1 Frontmatter 字段

v2 卡片的 YAML frontmatter 增加以下字段：

```yaml
---
title: "不可变数据的核心价值"
slug: immutable-data-core-value
status: ai_draft
track: knowledge_card
projects: []
tags: ["functional-programming", "data-design"]

# === NEW FIELDS ===
knowledge_type: insight            # concept | claim | insight | method | decision | question | evidence | todo
one_sentence_takeaway: "不可变数据消除了一类隐蔽的 bug：当对象在传递过程中被意外修改时，调用者无法察觉。"
problem_it_solves: "在函数间传递可变对象时，调用方无法确定对象是否被中间环节修改，导致难以定位的 bug。"
applicable_context: "函数式编程风格、跨层数据传递、并发场景、状态管理"
limitations_or_caveats: "频繁创建新对象可能带来性能开销；在强可变状态依赖的场景（如游戏循环）中不适用。"
source_trace:
  url: "https://example.com/article"
  file_path: "inbox/immutable-data.md"
  excerpt_sha1: "abc123"

# === EXISTING FIELDS (unchanged) ===
value_score: 0.85
confidence: high
quality_score: 0.8
quality_level: good
prompt_versions:
  distill: v1
  triage: v1
stage_models:
  - stage: triage
    model: claude-sonnet-4-6-20250514
  - stage: distill
    model: claude-sonnet-4-6-20250514
---
```

### 5.2 正文章节

v2 卡片的 body 按以下顺序组织：

```markdown
## Core Insight
核心洞察内容（1-3 段，不是摘要，是经过思考后的提炼）

## Applicable Context
适用场景描述（什么时候这条知识有用）

## Reusable Principle
可复用原则（具体可操作的原则，不是泛化的建议）

## Supporting Evidence
支撑证据（原文中的关键引述，带引用标记）

## Limitations & Caveats
限制条件（什么时候不适用，有什么风险）

---
<!-- 以下区域仅对审阅者和高级用户可见 -->

## Related Questions
相关问题（引导思考，不是考试题）

## Next Actions
下一步行动（从知识推导出的具体行动）

## Human Note
人工备注（只能由人填写）

## Source Excerpt
原文摘录（完整的 source material）
```

## 6. 字段定义与用户价值

| Field | Type | 来源 | 为什么对用户有价值 |
|-------|------|------|-------------------|
| `title` | string | LLM 生成 | 让用户一眼看懂这条知识说什么 |
| `one_sentence_takeaway` | string | LLM 生成 | 首屏即价值——用户不需要读完全文就能判断是否值得继续 |
| `knowledge_type` | enum | LLM 生成 | 让用户知道这是什么类型的知识（概念/方法/决策/问题），决定如何使用它 |
| `problem_it_solves` | string | LLM 生成 | 回答"为什么要存这条知识"——没有问题的知识不值得存储 |
| `core_insight` | string | LLM 生成 | 卡片的核心价值所在——不是摘要，是经过思考后的提炼 |
| `applicable_context` | string | LLM 生成 | 回答"什么时候用这条知识"——避免误用 |
| `reusable_principle` | string | LLM 生成 | 回答"能直接应用什么"——知识转化为行动 |
| `supporting_evidence` | string | LLM 生成（基于原文） | 回答"凭什么相信"——提供证据追溯到原文 |
| `limitations_or_caveats` | string | LLM 生成 | 回答"什么时候不适用"——避免过度泛化 |
| `next_actions` | string[] | LLM 生成 | 回答"基于这条知识我应该做什么" |
| `related_questions` | string[] | LLM 生成 | 引导深入思考，不是考试题 |
| `tags` | string[] | LLM 生成 + 人工可编辑 | 知识分类，用于检索和组织 |
| `source_trace` | object | 系统派生 | 追溯到原始来源，确保可验证性 |
| `approval_state` | enum | 系统派生 | ai_draft / human_approved / human_rejected |
| `human_note` | string | 人工填写 | 用户对知识的个人理解、补充、反驳 |
| `value_score` | float | 系统派生 | 来自 triage 阶段，用于排序 |
| `quality_score` | float | 系统派生 | 来自 triage 阶段，用于质量过滤 |
| `prompt_versions` | object | 系统派生 | 追溯哪个 prompt 版本生成的卡片 |
| `stage_models` | object[] | 系统派生 | 追溯哪个模型在哪个阶段生成的内容 |

### 字段不需要的理由

- **不增加 `confidence` 作为独立展示字段**：confidence 已在 frontmatter 中，但它是 triage 阶段的技术评分，不应该作为主要展示内容。进入技术证据区。
- **不增加 `counterarguments`**：这是学术模型的字段，个人知识管理不需要。`limitations_or_caveats` 已覆盖"这条知识可能不对"的情况。
- **不增加 `related_work`**：需要 embedding/RAG 才能做到。当前用 `suggested_links` 替代。

## 7. 字段来源

### 7.1 LLM 生成（ai_draft）

以下字段由 distill prompt v2 生成，进入 ai_draft 状态：

- `title`
- `one_sentence_takeaway`
- `knowledge_type`
- `problem_it_solves`
- `core_insight`
- `applicable_context`
- `reusable_principle`
- `supporting_evidence`（必须基于原文引述，不能瞎编）
- `limitations_or_caveats`
- `next_actions`
- `related_questions`
- `tags`

### 7.2 系统派生

以下字段由系统自动派生：

- `approval_state`：初始为 `ai_draft`，人工操作后变为 `human_approved` 或 `human_rejected`
- `source_trace`：由 pipeline 从原文元数据提取
- `value_score`：由 triage 阶段计算
- `quality_score` / `quality_level`：由 triage 阶段计算
- `prompt_versions`：由 pipeline 记录
- `stage_models`：由 pipeline 记录

### 7.3 人工提供

以下字段只能由人填写：

- `human_note`：用户在审阅时填写的个人理解、补充、反驳
- 对任何 LLM 生成字段的编辑：用户可以在审阅时修改任何字段

### 7.4 来源追溯

`source_trace` 包含：

```yaml
source_trace:
  url: "https://example.com/article"    # 原始 URL（如果有）
  file_path: "inbox/article.md"          # 本地文件路径
  excerpt_sha1: "abc123"                # 原文摘录的 SHA1（用于去重和追溯）
```

## 8. 审批边界

### 8.1 ai_draft 如何进入

1. 用户导入原文（文件、URL、剪贴板）
2. Pipeline 执行 triage → distill
3. distill 输出 JSON，组装为 YAML 卡片
4. 卡片状态为 `ai_draft`，写入 `vault/20-Knowledge-Cards/unrouted/`
5. 用户可以在审阅页面看到 ai_draft 卡片

### 8.2 human_approved 如何产生

1. 用户在审阅页面看到 ai_draft 卡片
2. 用户可以选择：
   - **Confirm**：确认卡片内容正确，状态变为 `human_approved`
   - **Edit & Confirm**：编辑任何字段后确认，状态变为 `human_approved`
   - **Downgrade to Note**：认为不值得成为知识卡片，降级为纯笔记
   - **Merge with Existing**：认为与已有卡片重复，合并到已有卡片
   - **Discard**：认为不值得保留，删除卡片
3. 只有用户主动执行 Confirm 操作后，状态才变为 `human_approved`

### 8.3 human_note 不能被 AI 伪造

- `human_note` 字段初始为空（或不存在）
- distill prompt v2 **不生成** `human_note`
- pipeline **不填充** `human_note`
- 只有用户在审阅页面手动填写 `human_note`
- CLI approve 流程需要增加 `--note` 选项（可选）

### 8.4 审批状态转换

```
                    ┌──────────────┐
                    │   imported   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  ai_draft    │ ← distill 产出
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌──▼──────┐ ┌───▼────┐
       │human_approved│ │discard  │ │downgrade│
       │ (confirmed)  │ │(deleted)│ │to note  │
       └──────────────┘ └─────────┘ └────────┘
```

## 9. v1 到 v2 的兼容策略

### 9.1 字段映射

v1 卡片字段自动映射到 v2 字段：

| v1 Field | v2 Field | 映射规则 |
|----------|----------|---------|
| `title` | `title` | 直接映射 |
| `ai_summary_bullets` | `core_insight` | bullets 合并为段落，标记为 v1 生成 |
| `ai_inference_bullets` | `supporting_evidence` | 作为证据保留 |
| `reusable_prompts_or_principles` | `reusable_principle` | 直接映射 |
| `review_questions` | `related_questions` | 移除答案部分，保留问题 |
| `action_items` | `next_actions` | 直接映射 |
| `tags` | `tags` | 直接映射 |
| — | `one_sentence_takeaway` | v1 无对应字段，设为 null |
| — | `knowledge_type` | v1 无对应字段，设为 "concept"（默认） |
| — | `problem_it_solves` | v1 无对应字段，设为 null |
| — | `applicable_context` | v1 无对应字段，设为 null |
| — | `limitations_or_caveats` | v1 无对应字段，设为 null |

### 9.2 正文章节映射

v1 body sections 重命名到 v2 sections：

| v1 Section | v2 Section |
|------------|------------|
| `## Source Excerpt` | `## Source Excerpt`（保持不变） |
| `## AI Summary` | `## Core Insight`（重命名，内容保留） |
| `## AI Inference` | `## Supporting Evidence`（重命名，内容保留） |
| `## Reusable Prompts/Principles` | `## Reusable Principle`（重命名） |
| `## Project Hooks` | 折叠到技术证据区 |
| `## Review Questions` | `## Related Questions`（重命名） |
| `## Action Items` | `## Next Actions`（重命名） |
| `## Human Note` | `## Human Note`（保持不变） |
| — | `## Applicable Context`（v1 无对应，为空则不展示） |
| — | `## Limitations & Caveats`（v1 无对应，为空则不展示） |

### 9.3 迁移方案

**不做批量迁移**。采用 lazy migration 策略：

1. v1 卡片保持原有 frontmatter 和 body
2. CardSummary dataclass 增加 v2 字段（可选，带默认值）
3. presenter 层检测卡片是否有 v2 字段：
   - 如果有 v2 字段，直接返回
   - 如果没有 v2 字段，按映射规则生成 v2 兼容视图
4. 新卡片直接使用 v2 结构
5. 旧卡片在用户编辑/审阅时自动升级为 v2（可选，需要用户确认）

## 10. 旧卡片回退规则

当 v2 前端组件读取 v1 卡片时：

1. `one_sentence_takeaway` 为 null → 从 `ai_summary_bullets` 的第一条生成
2. `knowledge_type` 不存在 → 默认 "concept"
3. `problem_it_solves` 为 null → 不展示该字段
4. `applicable_context` 为 null → 不展示该字段
5. `limitations_or_caveats` 为 null → 不展示该字段
6. `core_insight` 为空 → fallback 到 `ai_summary_bullets` 合并
7. `reusable_principle` 为空 → fallback 到 `reusable_prompts_or_principles`
8. `related_questions` 为空 → fallback 到 `review_questions`（移除答案）

**关键原则**：v1 卡片在 v2 前端下仍然可读，只是部分字段为空或 fallback。

## 11. 价值评分与质量标准

### 11.1 质量检查标准

distill prompt v2 生成的卡片应该通过以下质量检查：

| 检查项 | 规则 | 失败处理 |
|-------|------|---------|
| `one_sentence_takeaway` 非空 | 必须有值 | 返回错误，重新生成 |
| `core_insight` 非空 | 必须有值 | 返回错误，重新生成 |
| `core_insight` 不是原文 paraphrase | 必须包含原文没有的提炼 | 进入低质量队列 |
| `applicable_context` 非空 | 必须有值 | 警告，但不阻塞 |
| `limitations_or_caveats` 非空 | 必须有值 | 警告，但不阻塞 |
| `supporting_evidence` 基于原文 | 必须能在原文找到对应 | 标记为"证据不足" |
| `tags` 非空 | 至少有 1 个标签 | 返回错误，重新生成 |
| `knowledge_type` 是合法枚举值 | 必须是预定义的 8 种之一 | 返回错误，重新生成 |

### 11.2 价值评分

保留现有 `value_score` 和 `quality_score`，但增加一个用户可见的质量标识：

```
quality_level: excellent | good | fair | poor
```

- `excellent`: value_score >= 0.9，且通过所有质量检查
- `good`: value_score >= 0.7，且通过核心检查
- `fair`: value_score >= 0.5，或有警告
- `poor`: value_score < 0.5，或检查失败

质量标识进入技术证据区，不在主要阅读路径展示。

## 12. 验收标准

1. CardSummary dataclass 包含所有 v2 字段（可选，带默认值）
2. LibraryCardResponse API 包含 tags 字段
3. LibraryCardResponse API 包含 one_sentence_takeaway 字段
4. 前端组件能正确展示 v2 卡片的全部核心字段
5. v1 卡片在 v2 前端下正常展示（fallback 规则生效）
6. 审阅页面支持 Confirm / Edit & Confirm / Downgrade / Merge / Discard 操作
7. human_note 只能由人填写，AI 不生成
8. distill prompt v2 输出 JSON 符合 v2 schema
9. FakeProvider 输出有意义的 demo 内容（不是 `[fake]` 占位）
10. 所有新字段有对应的单元测试

## 13. 测试建议

### 13.1 单元测试

- `test_card_summary_v2_fields`：CardSummary 包含 v2 字段
- `test_v1_to_v2_field_mapping`：v1 卡片正确映射到 v2
- `test_fallback_rules`：v1 卡片缺失 v2 字段时 fallback 正确
- `test_approval_boundary`：ai_draft 不能自动变为 human_approved
- `test_human_note_not_generated_by_ai`：distill 不生成 human_note

### 13.2 集成测试

- `test_distill_prompt_v2_output`：prompt v2 输出符合 JSON schema
- `test_library_card_response_includes_tags`：API 返回 tags
- `test_library_card_response_includes_takeaway`：API 返回 one_sentence_takeaway

### 13.3 FakeProvider 测试

- `test_fake_distill_output_meaningful`：FakeProvider 输出不是 `[fake]` 占位
- `test_fake_distill_output_valid_schema`：FakeProvider 输出符合 v2 schema

## 14. 风险与回滚策略

### 14.1 风险

| 风险 | 影响 | 缓解措施 |
|------|--------|------------|
| LLM 产出质量不够 | 卡片仍然没有价值 | prompt v2 增加 anti-hallucination 约束 + 质量检查 |
| 旧卡片 fallback 有 bug | 旧卡片展示异常 | 充分的 fallback 单元测试 + 灰度发布 |
| 前端重构引入回归 | 现有页面损坏 | 充分的 UI 测试 + 分阶段部署 |
| FakeProvider 输出仍然垃圾 | demo 体验差 | 重新设计 FakeProvider，产出有意义的 demo 卡片 |

### 14.2 回滚策略

1. **CardSummary 兼容性**：新字段都是可选的，带默认值，回滚时旧代码不受影响
2. **Frontmatter 兼容性**：不删除 v1 字段，只增加 v2 字段，回滚时旧代码仍然能读
3. **API 兼容性**：新字段添加到响应中，客户端忽略未知字段
4. **Prompt 兼容性**：保留 v1 prompt，v2 prompt 使用新的版本号，回滚时切换回 v1
5. **UI 兼容性**：前端组件通过 feature flag 控制 v2 布局，回滚时切换回 v1

**回滚步骤**：
1. 切换 distill prompt 版本回 v1
2. 切换前端组件 feature flag 回 v1 布局
3. CardSummary 新字段保持不变（旧代码忽略它们）
4. 新卡片仍然使用 v2 frontmatter（旧代码忽略未知字段）
5. 不需要数据库迁移或数据回滚
