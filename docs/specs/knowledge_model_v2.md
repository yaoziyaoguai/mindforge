# 规范：知识模型 v2

## 概述

本文定义了知识卡片 YAML frontmatter 的 schema 扩展目标。目标是将卡片从"扁平文本容器"升级为个人知识网络中的类型化、语义链接节点，同时不引入重型图数据库或向量存储。

## Schema 扩展

### 1. `knowledge_type`（枚举）

定义卡片的知识论性质，即"这条知识是什么类型"。

* `concept`：定义、事实性实体或已确立的术语。（旧卡片的默认 fallback）
* `claim`：主张、观点或论点，可以被辩论、支持或反驳。
* `insight`：个人领悟、综合理解或"顿悟"时刻。
* `method`：流程、SOP 或"怎么做"。
* `evidence`：用于支撑主张的原始数据、引文或经验观察。
* `todo`：从知识中推导出的可执行行动项或下一步。
* `summary`：LLM 生成或人工编写的主题概述。（关键：LLM 摘要必须以 `ai_draft` 开始）

### 2. `relations`（对象列表）

定义指向其他卡片的显式语义链接。

**Schema：**

```yaml
relations:
  - type: supports       # 必填
    target_id: card_123  # 必填：目标卡片的 `id`
```

**允许的 `type` 值：**

* `supports`：本卡片为目标卡片提供证据或论证。
* `contradicts`：本卡片反驳目标卡片或提供反面证据。
* `expands`：本卡片为目标卡片提供更多细节或子主题。
* `example_of`：本卡片是目标卡片（通常是概念）的具体实例。
* `derived_from`：本卡片的结论从目标卡片逻辑推导而来。
* `prerequisite_of`：理解目标卡片之前必须先理解本卡片。
* `related_to`：一般性、弱关联（尽量少用）。

### 3. `human_note`（字符串，可选）

用户在审批过程中添加个人想法、上下文或注意事项的专用字段，与 `AI Summary` 保持分离。

## Fallback 与兼容规则

解析 `src/mindforge/cards.py` 中的现有 `CardSummary` 对象时：

1. **缺少 `knowledge_type`**：如果缺失或无效，默认为 `"concept"`。
2. **缺少 `relations`**：如果缺失或格式错误，默认为空元组 `()`。

## 验证约束

* `cards.py` 解析器在这些字段格式错误时**绝不能**抛出致命错误；必须在内部记录警告（或静默处理）并使用 fallback 值，确保应用程序保持健壮。
* 这些字段是元数据。关于*为什么*存在某个关系的实际推理或解释，应保留在 markdown body 中。
