---
name: distill-prompt-v2-spec
description: Specification for distill prompt v2 — restructures prompt from "faithful extraction" to "insight generation" with anti-hallucination constraints
metadata:
  type: spec
---

# Distill Prompt v2 Specification

Date: 2026-06-04
Status: Draft — awaiting human review

## 1. Current Distill Prompt v1 Problems

当前 distill prompt v1（`src/mindforge/assets/prompts/distill/v1.md`）的系统提示词：

> "把一份原始素材忠实地提炼为一张可长期阅读的知识卡片。"

**问题**：

1. **"忠实提炼"鼓励 paraphrase**：模型被要求"忠实"于原文，所以产出的是改写后的摘要，不是经过思考的洞察
2. **缺少 insight 要求**：prompt 没有要求模型识别"这条知识的核心洞察是什么"
3. **缺少 context 要求**：没有要求模型说明"适用于什么场景"
4. **缺少 limitations 要求**：没有要求模型说明"有什么限制条件"
5. **缺少 problem 要求**：没有要求模型说明"这条知识解决什么问题"
6. **Reusable Prompts/Principles 过于泛化**：prompt 没有要求原则必须"具体可操作"
7. **Review Questions 是考试题格式**：prompt 要求生成"问题和答案"，不是引导思考的问题
8. **没有 anti-hallucination 约束**：模型可以基于原文做出超出原文的推断
9. **没有 source-grounded 规则**：模型不需要将生成内容追溯到原文
10. **没有"不值得生成"的判断**：所有输入都会生成卡片，即使输入内容不值得

## 2. v2 Prompt Goals

1. **Insight > Summary**：要求模型产出真正的洞察，不是原文改写
2. **Concrete > Generalized**：要求原则具体可操作，不是泛化建议
3. **Honest > Complete**：要求模型承认不确定性，不瞎编
4. **Source-Grounded**：要求生成内容能追溯到原文
5. **Context-Aware**：要求模型说明适用场景和限制条件
6. **Problem-First**：要求模型先说"解决什么问题"，再说"怎么解决"
7. **Actionable**：要求原则能直接应用，不是空泛建议
8. **Review-Friendly**：输出的结构让审阅者容易判断价值

## 3. Anti-Hallucination Constraints

v2 prompt 包含以下 anti-hallucination 约束：

1. **不生成原文没有的事实**：所有支撑证据必须能在原文找到对应
2. **区分原文内容和模型推断**：明确标注哪些是原文说的，哪些是模型推断的
3. **承认信息不足**：如果原文不足以生成某个字段，输出"信息不足以判断"
4. **不做时间预测**：不生成"未来会怎样"的推断
5. **不生成统计数字**：不生成原文没有的具体数字、百分比、统计
6. **不引用外部来源**：不生成原文没有引用的论文、书籍、文章
7. **不编造专家观点**：不生成"专家认为"、"研究表明"等无来源说法

### 具体约束措辞（prompt 中包含）：

```
重要约束：
- 你只能基于原文生成内容，不得编造原文没有的事实
- 如果你推断出一个观点，必须在"支撑证据"中找到原文对应
- 如果原文不足以判断某个字段，请输出"信息不足以判断"
- 不要生成"专家认为"、"研究表明"等无来源说法
- 不要生成原文没有的具体数字、百分比、统计数据
- 不要引用原文没有提到的论文、书籍、文章
- 区分"原文说的"和"你推断的"——推断必须标注为推断
```

## 4. Source-Grounded Rules

v2 prompt 要求所有生成内容追溯到原文：

1. **core_insight** 必须能从原文推导出来（即使原文没有直接说）
2. **supporting_evidence** 必须包含原文的关键引述（带引用标记）
3. **applicable_context** 必须基于原文讨论的主题
4. **limitations_or_caveats** 必须基于原文的隐含限制或明确说明的限制
5. **reusable_principle** 必须能从原文推导出来
6. **one_sentence_takeaway** 必须概括原文的核心

### 证据追溯格式

```json
{
  "supporting_evidence": "原文讨论了不可变数据在函数式编程中的重要性，特别指出'当对象在传递过程中被意外修改时，调用者无法察觉'这是最隐蔽的 bug 来源。",
  "evidence_quotes": [
    {
      "text": "当对象在传递过程中被意外修改时，调用者无法察觉",
      "context": "讨论函数间传递可变对象的风险"
    }
  ]
}
```

## 5. Output JSON Schema

v2 prompt 输出以下 JSON 结构：

```json
{
  "title": "string — 知识标题",
  "slug": "string — URL 友好的标识符",
  "knowledge_type": "enum — concept | claim | insight | method | decision | question | evidence | todo",
  "confidence": "enum — high | medium | low",
  "one_sentence_takeaway": "string — 一句话核心（50-150字）",
  "problem_it_solves": "string — 解决什么问题（50-200字）",
  "core_insight": "string — 核心洞察（100-500字）",
  "applicable_context": "string — 适用场景（50-200字）",
  "reusable_principle": "string — 可复用原则（50-200字）",
  "supporting_evidence": "string — 支撑证据（100-500字）",
  "evidence_quotes": [
    {
      "text": "string — 原文引述",
      "context": "string — 引述在原文中的上下文"
    }
  ],
  "limitations_or_caveats": "string — 限制条件（50-200字）",
  "next_actions": ["string — 下一步行动（每条 20-50 字）"],
  "related_questions": ["string — 相关问题（每条 10-50 字）"],
  "tags": ["string — 知识分类标签（3-8个）"],
  "tags_reasoning": "string — 为什么选择这些标签（简要说明）"
}
```

### Schema 约束

- 所有 string 字段不能为空字符串
- 如果某个字段无法生成（原文不足以支撑），值为 `"信息不足以判断"`
- `knowledge_type` 必须是预定义的 8 种之一
- `confidence` 必须是 high / medium / low
- `tags` 至少 1 个，最多 8 个
- `evidence_quotes` 至少 1 条，最多 5 条
- `next_actions` 可以为空数组
- `related_questions` 可以为空数组

## 6. Field Generation Requirements

| Field | 生成要求 |
|-------|---------|
| `title` | 简洁、具体、能看出知识内容。避免"关于 X 的讨论"这种泛化标题 |
| `slug` | 基于 title 生成，kebab-case，英文优先 |
| `knowledge_type` | 根据原文性质判断：讲概念→concept，讲观点→claim，讲洞察→insight，讲方法→method，讲决策→decision，讲问题→question，讲证据→evidence，讲任务→todo |
| `confidence` | 基于原文质量和模型对推断的信心判断 |
| `one_sentence_takeaway` | 一句话总结"这条知识说什么"。必须包含具体观点，不是"本文讨论了 X" |
| `problem_it_solves` | 明确说明"什么情况下会遇到这个问题"。必须具体，不是"有时候会有问题" |
| `core_insight` | 不是摘要，是经过思考后提炼的洞察。应该回答"原文最让我意外/重要/有用的观点是什么" |
| `applicable_context` | 具体说明"什么场景下这条知识有用"。必须列举具体场景，不是"各种场景" |
| `reusable_principle` | 具体可操作的原则。格式："当 [条件] 时，应该 [行动]，因为 [理由]" |
| `supporting_evidence` | 基于原文的关键引述和论述。必须包含 evidence_quotes 中的原文引述 |
| `evidence_quotes` | 直接从原文摘录的关键语句。每条附带上下文说明 |
| `limitations_or_caveats` | 基于原文的隐含限制或明确说明的限制。如果原文没有提及限制，说明"原文没有讨论限制条件" |
| `next_actions` | 从知识推导出的具体行动。每条应该可执行，不是"继续学习" |
| `related_questions` | 引导深入思考的问题。不是考试题（不含答案），是帮助用户理解的问题 |
| `tags` | 知识分类标签。应该反映知识内容，不是技术元数据 |

## 7. When to Output "Not Worth a Card"

v2 prompt 应该判断输入是否值得生成知识卡片。

### 判断标准

以下情况应该输出 `skip` 而不是卡片：

1. **内容不足 200 字**：原文太短，不足以生成有价值的洞察
2. **纯事实列表**：如"今天是星期一，天气很好"——没有洞察可提炼
3. **重复内容**：与已有知识卡片高度重复（需要外部判断，prompt 自身无法判断）
4. **纯个人观点无支撑**：如"我觉得 X 不好"——没有论证，没有洞察
5. **纯代码/数据**：没有论述内容的代码片段或数据表格
6. **垃圾内容**：广告、spam、无意义文本

### Skip Output Format

当判断不值得时，输出：

```json
{
  "skip": true,
  "skip_reason": "string — 为什么不值得（20-100字）",
  "suggestion": "string — 用户应该怎么做（20-50字）"
}
```

Pipeline 收到 `skip: true` 时：
1. 不生成知识卡片
2. 记录 skip 日志
3. 原文保留在 inbox 中，用户可以手动处理

## 8. When to Generate Multiple Cards

v2 prompt 应该判断输入是否包含多个独立的知识主题。

### 判断标准

以下情况应该生成多张卡片：

1. **包含多个独立概念**：如一篇文档同时讨论了"不可变数据"和"函数组合"
2. **包含多个独立方法**：如一篇文档介绍了 3 种不同的设计模式
3. **包含独立子主题**：如一篇长文档有明确分节的多个主题

### Multi-Card Output Format

```json
{
  "multi": true,
  "cards": [
    { /* card 1 JSON */ },
    { /* card 2 JSON */ }
  ],
  "multi_reason": "string — 为什么拆分为多张卡"
}
```

Pipeline 收到 `multi: true` 时：
1. 为每张卡生成独立的 ID 和文件
2. 在 `related_questions` 中互相引用
3. 记录拆分日志

## 9. Knowledge Type Classification

v2 prompt 需要区分以下 8 种知识类型：

| Type | 定义 | 示例 |
|------|------|------|
| `concept` | 解释一个概念或术语 | "不可变数据是指对象创建后不能被修改" |
| `claim` | 提出一个观点或主张 | "函数式编程比面向对象编程更适合并发" |
| `insight` | 经过思考后发现的新理解 | "不可变数据的核心价值不是安全，而是可读性" |
| `method` | 介绍一种方法或技巧 | "使用 NamedTuple 替代 dataclass 可以提升性能" |
| `decision` | 记录一个决策和理由 | "选择 PostgreSQL 而不是 MySQL，因为需要 JSON 支持" |
| `question` | 提出一个待解决的问题 | "如何在不牺牲性能的情况下实现不可变数据" |
| `evidence` | 记录一个支撑某个观点的证据 | "某实验表明不可变对象的缓存命中率提升 30%" |
| `todo` | 记录一个待执行的任务 | "重构用户认证模块，使用不可变模式" |

### Type-Specific Requirements

不同类型的卡片有不同的字段侧重：

- **concept**：侧重 `core_insight`（概念的本质）和 `applicable_context`（什么时候用这个概念）
- **claim**：侧重 `supporting_evidence`（证据）和 `limitations_or_caveats`（什么情况下不成立）
- **insight**：侧重 `core_insight`（洞察本身）和 `reusable_principle`（如何应用洞察）
- **method**：侧重 `reusable_principle`（具体步骤）和 `applicable_context`（什么时候用这个方法）
- **decision**：侧重 `problem_it_solves`（为什么做这个决策）和 `supporting_evidence`（决策依据）
- **question**：侧重 `problem_it_solves`（为什么这个问题重要），`core_insight` 可能为空
- **evidence**：侧重 `supporting_evidence`（证据本身），其他字段可能简化
- **todo**：侧重 `next_actions`（具体行动），`core_insight` 可能简化

## 10. How to Generate Valuable Fields

### 10.1 core_insight

**要求**：不是摘要，是经过思考后提炼的洞察。

**Prompt 引导**：
```
不要总结原文说了什么。思考：原文最让我意外/重要/有用的观点是什么？
如果原文只是陈述事实，提炼这个事实背后的模式或原理。
如果原文讨论了一个问题，提炼"为什么这个问题容易被忽略"或"为什么这个方案有效"。
```

**好的示例**：
> 不可变数据的核心价值不在于防止 bug（这是基本价值），而在于它让代码的阅读顺序变得线性——你不需要追踪对象在哪些地方可能被修改，只需要看数据从哪里来、到哪里去。

**坏的示例**：
> 本文讨论了不可变数据在编程中的重要性，指出不可变对象可以防止意外修改带来的 bug。

### 10.2 applicable_context

**要求**：具体场景，不是"各种场景"。

**Prompt 引导**：
```
列举 2-4 个具体场景，说明这条知识在什么情况下有用。
场景应该具体到"当你正在做 X 的时候"，不是"在编程中"。
```

**好的示例**：
> - 当你设计函数间的数据传递方式时
> - 当你在 React 中管理状态时
> - 当你在多线程环境中共享数据时

**坏的示例**：
> 在编程的多个场景中都有应用价值。

### 10.3 limitations_or_caveats

**要求**：基于原文的隐含限制或明确说明的限制。

**Prompt 引导**：
```
思考：这条知识在什么情况下不适用？原文没有讨论的限制是什么？
如果原文确实没有讨论限制，请说明"原文没有讨论限制条件"，并基于你的理解推测可能的限制。
```

**好的示例**：
> 不可变数据在频繁创建新对象时可能带来性能开销（特别是大数据集）；在强可变状态依赖的场景（如游戏循环、实时控制系统）中不适用。

**坏的示例**：
> 没有明显的限制。

### 10.4 reusable_principle

**要求**：具体可操作的原则。格式："当 [条件] 时，应该 [行动]，因为 [理由]"。

**Prompt 引导**：
```
提炼 1-3 条可复用的原则。每条原则应该能用下面的格式表达：
"当 [具体条件] 时，应该 [具体行动]，因为 [具体理由]"
原则应该具体到可以直接应用，不是"使用不可变数据"这种泛化建议。
```

**好的示例**：
> 当函数间传递数据时，应该使用不可变对象（或副本），因为调用方无法确定中间环节是否修改了对象。

**坏的示例**：
> 使用不可变数据。

### 10.5 next_actions

**要求**：从知识推导出的具体行动。每条可执行。

**Prompt 引导**：
```
基于这条知识，用户接下来应该做什么？
行动应该具体到"检查项目中 X 模块是否使用了可变对象"，不是"继续学习"。
```

**好的示例**：
> - 检查核心模块中是否有在函数间传递可变对象的模式
> - 为新模块制定不可变数据的设计规范

**坏的示例**：
> - 继续学习不可变数据
> - 了解更多函数式编程知识

## 11. How to Avoid Empty Summaries

v1 prompt 的问题之一是产出空泛摘要。v2 通过以下方式避免：

1. **不生成 `summary` 字段**：v2 没有"摘要"字段，只有"洞察"、"问题"、"原则"
2. **要求具体场景**：`applicable_context` 必须列举具体场景
3. **要求具体原则**：`reusable_principle` 必须用"当...时，应该...，因为..."格式
4. **要求证据追溯**：`supporting_evidence` 必须包含原文引述
5. **要求限制条件**：`limitations_or_caveats` 必须说明不适用的场景
6. **质量检查**：Pipeline 检查字段是否空泛（如"在多个场景中都有应用"），标记为低质量

## 12. How to Make Review Page Easier to Approve

v2 的输出结构让审阅页面更容易审批：

1. **one_sentence_takeaway** 让审阅者立刻看懂卡片价值
2. **knowledge_type** 让审阅者知道这是什么类型的知识
3. **core_insight** 是卡片的核心价值，审阅者只需要判断这个洞察是否正确
4. **supporting_evidence** 带原文引述，审阅者可以验证洞察是否有根据
5. **limitations_or_caveats** 让审阅者知道模型的自我评估
6. **evidence_quotes** 让审阅者可以直接对照原文

### Review Page 应该展示的结构

```
┌─────────────────────────────────────────┐
│ [Title]                                 │
│ Type: [insight]  Confidence: [high]     │
│                                         │
│ One-Sentence Takeaway:                  │
│ [one_sentence_takeaway]                 │
│                                         │
│ Core Insight:                           │
│ [core_insight]                          │
│                                         │
│ Supporting Evidence:                    │
│ [supporting_evidence]                   │
│   > "[evidence_quotes[0].text]"         │
│                                         │
│ Applicable Context:                     │
│ [applicable_context]                    │
│                                         │
│ Limitations:                            │
│ [limitations_or_caveats]                │
│                                         │
│ [Confirm] [Edit & Confirm] [Downgrade]  │
│ [Discard]                               │
└─────────────────────────────────────────┘
```

## 13. FakeProvider Demo Output

当前 FakeProvider 输出 `[fake]` 占位内容，严重影响 demo 体验。

### v2 FakeProvider 应该输出

FakeProvider 应该输出有意义的 demo 内容，模拟真实 LLM 的输出格式。

#### 示例：关于"不可变数据"的 demo 卡片

```json
{
  "title": "不可变数据的核心价值是可读性",
  "slug": "immutable-data-core-value-is-readability",
  "knowledge_type": "insight",
  "confidence": "high",
  "one_sentence_takeaway": "不可变数据不仅是为了防止 bug，更重要的是让代码的阅读顺序变得线性——你不需要追踪对象在哪些地方可能被修改。",
  "problem_it_solves": "在函数间传递可变对象时，调用方无法确定对象是否被中间环节修改，导致难以定位的 bug 和调试困难。",
  "core_insight": "不可变数据的核心价值不在于防止 bug（这是基本价值），而在于它让代码的阅读顺序变得线性——你不需要追踪对象在哪些地方可能被修改，只需要看数据从哪里来、到哪里去。这大幅降低了代码的认知负担。",
  "applicable_context": "当你设计函数间的数据传递方式时；当你在 React 中管理状态时；当你在多线程环境中共享数据时；当你需要缓存计算结果时。",
  "reusable_principle": "当函数间传递数据时，应该使用不可变对象（或副本），因为调用方无法确定中间环节是否修改了对象。",
  "supporting_evidence": "原文讨论了不可变数据在函数式编程中的重要性，特别指出'当对象在传递过程中被意外修改时，调用者无法察觉'这是最隐蔽的 bug 来源。",
  "evidence_quotes": [
    {
      "text": "当对象在传递过程中被意外修改时，调用者无法察觉",
      "context": "讨论函数间传递可变对象的风险"
    }
  ],
  "limitations_or_caveats": "不可变数据在频繁创建新对象时可能带来性能开销（特别是大数据集）；在强可变状态依赖的场景（如游戏循环、实时控制系统）中不适用。",
  "next_actions": ["检查核心模块中是否有在函数间传递可变对象的模式", "为新模块制定不可变数据的设计规范"],
  "related_questions": ["在 Python 中，如何高效实现不可变对象？", "不可变数据和 CQRS 模式如何结合？"],
  "tags": ["functional-programming", "data-design", "immutability", "code-quality"],
  "tags_reasoning": "标签反映了不可变数据的主题（immutability）、所属范式（functional-programming）、应用领域（data-design）和价值目标（code-quality）"
}
```

### FakeProvider Implementation Notes

- `_extract_keywords()` 可以保留，用于生成 tags
- `distill()` 方法需要重写，产出有意义的 JSON（不是 `[fake]` 占位）
- 基于输入内容的关键词，生成合理的 title、takeaway、insight
- 不要生成随机的、无意义的占位内容
- 输出的 JSON 必须符合 v2 schema

## 14. Differences from v1

| 维度 | v1 | v2 |
|------|----|----|
| 系统提示词 | "忠实提炼" | "提炼洞察" |
| 输出结构 | title, slug, tags, confidence, source_excerpt, ai_summary_bullets, ai_inference_bullets, reusable_prompts_or_principles | title, slug, knowledge_type, confidence, one_sentence_takeaway, problem_it_solves, core_insight, applicable_context, reusable_principle, supporting_evidence, evidence_quotes, limitations_or_caveats, next_actions, related_questions, tags |
| 核心字段 | ai_summary_bullets（摘要） | core_insight（洞察） |
| 新增字段 | 无 | knowledge_type, one_sentence_takeaway, problem_it_solves, applicable_context, limitations_or_caveats, evidence_quotes |
| Anti-hallucination | 无 | 有（7 条约束） |
| Source-grounded | 无 | 有（证据追溯） |
| Skip 判断 | 无 | 有（6 种 skip 情况） |
| Multi-card | 无 | 有（多主题拆分） |
| Type 分类 | 无 | 8 种类型 |
| Review Questions | 考试题（含答案） | 引导问题（不含答案） |
| 原则格式 | 泛化建议 | "当...时，应该...，因为..." |
| 质量检查 | 无 | 有（8 项检查） |

## 15. Example Input & Output

### Input

```markdown
# 不可变数据的重要性

在函数式编程中，不可变数据是一个核心概念。不可变对象一旦创建就不能被修改。

当你在函数间传递一个可变对象时，你无法确定这个对象是否被中间环节修改了。这导致了一种隐蔽的 bug：

```python
def process_data(data):
    # 一些处理
    data["processed"] = True  # 修改了原对象
    return data

original = {"name": "test"}
result = process_data(original)
print(original)  # {"name": "test", "processed": True} - 被修改了！
```

这个问题的根源在于，调用方期望 `process_data` 返回结果，但不知道它同时修改了输入。

不可变数据解决了这个问题：如果 data 是不可变的，`process_data` 只能返回一个新对象，原对象保持不变。

在实践中，这意味着你的代码更容易推理和调试。你不需要追踪对象在哪些地方被修改，只需要看数据从哪里来、到哪里去。
```

### Output（见第 13 节 FakeProvider Demo Output）

## 16. Test Recommendations

### 16.1 Unit Tests

- `test_distill_v2_output_schema`：输出符合 v2 JSON schema
- `test_anti_hallucination_constraints`：不生成原文没有的事实
- `test_source_grounded_rules`：证据能追溯到原文
- `test_skip_detection`：不值得的内容返回 skip
- `test_multi_card_detection`：多主题内容返回 multi
- `test_knowledge_type_classification`：正确分类 8 种类型
- `test_principle_format`：原则符合"当...时，应该...，因为..."格式
- `test_tags_reasoning`：标签有合理的解释

### 16.2 Integration Tests

- `test_distill_pipeline_v2`：完整 pipeline 使用 v2 prompt
- `test_card_generation_from_v2_output`：卡片从 v2 输出正确组装
- `test_skip_cards_not_generated`：skip 的内容不生成卡片

### 16.3 FakeProvider Tests

- `test_fake_distill_meaningful`：输出不是 `[fake]` 占位
- `test_fake_distill_valid_schema`：输出符合 v2 schema
- `test_fake_distill_variety`：对不同输入产出不同的有意义内容

## 17. Risks & Rollback Strategy

### 17.1 Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM 不遵循 prompt 约束 | 产出质量不够 | 增加 few-shot 示例 + 质量检查 |
| Anti-hallucination 过于严格 | 模型拒绝生成有效洞察 | 放宽约束，允许基于原文的合理推断 |
| Skip 判断过于激进 | 有价值的内容被跳过 | 调整 skip 阈值，记录 skip 日志 |
| Multi-card 拆分错误 | 相关内容被拆成无关卡片 | 拆分时保留上下文引用 |
| FakeProvider 输出仍然垃圾 | demo 体验差 | 精心编写 demo 模板，基于输入关键词生成内容 |

### 17.2 Rollback Strategy

1. **Prompt 版本共存**：v1 和 v2 prompt 使用不同版本号，保留 v1 文件
2. **Pipeline 选择**：通过配置或 feature flag 选择使用 v1 还是 v2 prompt
3. **输出兼容**：v2 输出包含 v1 的所有字段（通过映射），v1 消费者能读 v2 输出
4. **回滚步骤**：
   - 切换配置回 v1 prompt
   - 新卡片使用 v1 结构
   - 已有 v2 卡片保持 v2 结构（前端兼容）
   - 不需要数据回滚
