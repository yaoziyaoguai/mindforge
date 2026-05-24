---
title: "v2.2 Local Lexical Search / FTS Foundation — Implementation Note"
date: 2026-05-25
status: Complete
version: v2.2
---

# v2.2 Local Lexical Search / FTS Foundation — Implementation Note

## What was done

v2.2 完成了 BM25 词法检索的边界形式化和质量增强。

### U1: RetrievalPort Formalization

- 确认现有 `RetrievalPort` ABC 抽象已正确定义（retrieval/retrieval_port.py）
- `Bm25RetrievalEngine` 正确实现 Port 接口（adapter 模式）
- `recall_service.run_bm25_recall()` 的 `engine` 参数类型为 `RetrievalPort`，只依赖抽象
- 新增 `tests/test_retrieval_port.py` — 13 个 Port contract tests：
  - 接口实现验证（isinstance、abstract 不可实例化）
  - search/hybrid_search 行为验证
  - 确定性验证
  - 可替换性验证
  - recall_service 依赖注入验证

### U2: BM25 Tokenization Enhancement

- `tokenize()` 新增 `filter_stopwords: bool = True` 参数
- 内置 75 个英文停用词（NLTK 标准停用词子集）
- 默认过滤停用词，可通过 `filter_stopwords=False` 关闭
- 向后兼容：tokenizer_name 参数保留，索引格式不变
- 新增 `tests/test_lexical_index.py` — 27 个 tokenization + BM25 tests：
  - 11 个分词测试（基础/大小写/CJK/空文本/停用词/混合/数字/确定性）
  - 7 个字段权重测试（默认值/title>body/覆盖/零权重移除/别名映射）
  - 9 个 BM25 索引测试（构建/搜索/过滤/排序/field_hits/确定性）

### U3: BM25 Ranking & Field Weighting

- 确认现有 `DEFAULT_FIELD_WEIGHTS` 设计：title(5.0) > track(4.0) > tags(3.0) > body(1.0)
- `resolve_field_weights()` 支持用户覆盖、零权重移除、别名映射
- 搜索分数排序正确（降序）、field_hits 可解释

### U4: Isolated FTS Spike

- 跳过（ADR-001 已决策保持 BM25，无触发条件）

### U5: Retrieval Quality Baseline

- 新增 `docs/adr/2026-05-25-003-retrieval-quality-baseline.md`
- 记录当前架构、field weights 设计理由、已知 trade-off
- 明确何时需重新评估（>10k cards、需要分词精度、模糊搜索等）

## Changes

- `src/mindforge/lexical_index.py` — tokenize() 增强停用词过滤 + _ENGLISH_STOP_WORDS
- `tests/test_lexical_index.py` — +27 tests (NEW)
- `tests/test_retrieval_port.py` — +13 tests (NEW)
- `docs/adr/2026-05-25-003-retrieval-quality-baseline.md` — ADR-003 (NEW)

## Design Rationale

- **不引入 jieba**：保持零外部依赖，CJK 逐字切分对个人知识库规模足够
- **停用词过滤可逆**：默认启用但可关闭，不影响索引兼容性
- **Port 契约测试不绑定实现**：测试通过抽象接口，验证可替换性而非具体行为
- **保持 BM25**：ADR-001 结论维护，纯 Python 实现零依赖

## Non-goals

- 不引入 jieba / 中文分词库
- 不做 SQLite FTS5 / DuckDB FTS spike（ADR-001 已评估）
- 不做 stemming / 词形还原
- 不做 embedding / vector DB
- 不修改 recall API contract

## Gates

- ruff check: exit 0 (All checks passed!)
- pytest full (~460+): exit 0, 100% pass
- npm build: exit 0
- product copy: exit 0
- git diff --check: exit 0
