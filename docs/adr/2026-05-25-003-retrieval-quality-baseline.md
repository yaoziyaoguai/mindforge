---
title: "ADR-003: Retrieval Quality Baseline — BM25 v2.2"
date: 2026-05-25
status: active
---

# ADR-003: Retrieval Quality Baseline — BM25 v2.2

## Context

v2.2 对 BM25 词法检索做了增强（英文停用词过滤），需要建立质量基线以便未来检测回归。

## 当前架构

```
CLI / Web API
    |
    v
recall_service.run_bm25_recall()
    |
    v
RetrievalPort (ABC) ← 抽象边界
    |
    v
Bm25RetrievalEngine (adapter)
    |
    v
lexical_index.py (core BM25)
    |
    v
<workdir>/index/bm25.json
```

### 关键设计决策

1. **RetrievalPort 抽象**：recall_service 只依赖 RetrievalPort，不直接依赖 lexical_index。未来可替换为 FTS5 等后端。
2. **BM25 保持**：ADR-001 结论维护 —— 零外部依赖、性能足够、确定性可测试。
3. **停用词过滤**：v2.2 新增默认英文停用词过滤（~75 个词），可关闭。

### Tokenization v2.2

- ASCII: `[A-Za-z0-9]+` → lowercase → stopword filter
- CJK: 逐字切分
- 不做 stemming / 词形还原

### Field Weights v2.2

| Field | Weight | 理由 |
|-------|--------|------|
| title | 5.0 | 标题命中最"中要害" |
| track | 4.0 | 学习路径高信号 |
| projects | 4.0 | 项目归属高信号 |
| source_title | 3.0 | 来源文档标题中信号 |
| tags | 3.0 | 标签中信号 |
| principles | 2.0 | 原则/洞察低信号 |
| known_risks | 2.0 | 风险提示低信号 |
| body_summary | 1.0 | body 段基础信号 |
| body_actions | 1.0 | action items 基础信号 |
| body_principles | 1.0 | body 原则基础信号 |
| body_risks | 1.0 | body 风险基础信号 |
| source_type | 1.0 | 来源类型最低信号 |

### 质量特征

#### 优势

1. **确定性**：相同输入 → 相同输出（golden test 验证）
2. **可解释**：`SearchHit.field_hits` 显示每个字段的贡献
3. **快速**：纯 Python BM25，1000 cards 索引构建 < 1s
4. **安全**：索引白名单字段，绝不索引 source excerpt / human note / raw text

#### 已知trade-off

1. **CJK 逐字切分**：中文分词精度有限（如"机器学习"被拆为 4 个单字而非一个词组）。可通过引入 jieba 增强，但目前保持零依赖。
2. **无 stemming**：英文 "learning" / "learned" / "learns" 被视为 3 个不同 token。对于个人知识库规模（<1 万张卡片）影响有限。
3. **无同义词**：不处理同义词扩展。

### 测试覆盖

| 测试文件 | 数量 | 覆盖 |
|----------|------|------|
| tests/test_lexical_index.py | 27 | tokenization + field weights + BM25 indexing + search |
| tests/test_retrieval_port.py | 13 | Port contract + engine behavior + dependency inversion |
| tests/test_lexical_index.py | — | 覆盖但不单独计为 retrieval tests |

### Gate Status (v2.2)

- ruff: exit 0
- pytest: exit 0 (~460+ tests)
- npm build: exit 0
- product copy: exit 0
- git diff --check: exit 0

## Decision

保持 BM25 作为默认检索后端，继续增强 tokenization 和 field weighting。不引入 SQLite FTS5 / DuckDB FTS / embedding / vector DB 作为生产依赖。

### 何时重新评估

以下条件满足时重新打开此 ADR：
1. 知识卡片数 > 10,000 且 BM25 性能下降
2. 需要模糊搜索 / 拼写纠错
3. 需要中文词组级别分词精度
4. 需要跨语言搜索

## Consequences

- 检索质量基线已建立，可被 monitor 和比较
- `RetrievalPort` 抽象确保未来可在不破坏 API 的情况下替换检索后端
- Tokenization 增强不破坏现有索引格式（tokenizer_name 记录在索引中，格式漂移可检测）
