# Direction C Recall/Search Quality Lab — Implementation Notes

**日期**: 2026-05-26
**输入**: `docs/plans/2026-05-26-104-recall-search-quality-lab-plan.md`
**状态**: completed

---

## 执行摘要

Direction C 在不引入 RAG/embedding/vector DB 的前提下，为 BM25 词法检索建立了可测量的质量基线。全部 5 个实现单元 (U1-U5) 已完成。

### Commits

| Unit | Commit | Description |
|------|--------|-------------|
| U1 | `de077df` | feat: U1 golden recall benchmark — 12 cards + 14 golden queries + 4 negative queries |
| U2 | `4332e66` | feat: U2 query explain — explain_zero_hits + explain_hits + QueryExplain dataclass |
| U3+U4 | `78fc4c7` | feat: U3+U4 BM25 tuning config + recall quality gate script |
| U5 | `2d9a271` | feat: U5 Web RecallPage explain panel — BM25 边界说明 + 命中字段/匹配词展示 |

---

## U1: Golden Recall Benchmark Fixtures

### 创建文件
- `tests/fixtures/recall_benchmark.py` — 黄金召回基准 fixture 模块

### 内容
- 12 张合成 approved 卡片，覆盖 architecture、security、testing、deployment、中文内容、dogfood 六个主题
- 14 条黄金查询（英文单词/多词、中文单词/多词、精确标题匹配）
- 4 条负查询（纯英文 — CJK 负查询因字符级分词限制不可行）
- 关键数据类：`GoldenCard`、`GoldenQuery`、`NegativeQuery`、`RecallBenchmark`、`build_recall_benchmark()`

### 测试
- `tests/test_recall_benchmark.py` — 27 个测试，三个测试类
- 验证：所有黄金查询召回率 ≥ 70%、3 次独立运行 deterministic、CJK 字符级分词限制文档化

---

## U2: Query Explain Diagnostics

### 修改文件
- `src/mindforge/recall_service.py` — 新增 `QueryExplain` frozen dataclass + `explain_zero_hits()` + `explain_hits()`

### QueryExplain 字段
```python
@dataclass(frozen=True)
class QueryExplain:
    query_text: str
    total_hits: int
    is_zero_hits: bool
    matched_fields_summary: dict[str, int]
    top_contributing_terms: tuple[str, ...]
    miss_reason: str | None = None
    token_count: int = 0
    boundary_note: str = ""
```

### explain_zero_hits 诊断层级
1. 空索引（无 card_rel_paths）
2. 无 approved 卡片
3. stale index（card_count != index_count）
4. track/tag/source_type filter 限制
5. 通用"关键词无匹配"

### explain_hits 聚合
- 跨所有命中聚合字段命中计数
- 收集所有词条总贡献值、排序取 top-10
- boundary_note 包含卡片数量等边界信息

### 测试
- `tests/test_recall_explain.py` — 10 个测试
- 覆盖零命中所有触发条件、命中字段聚合、term 排序、安全边界

---

## U3: BM25 Tuning Config

### 修改文件
- `src/mindforge/retrieval/bm25_engine.py` — 新增 `Bm25Config` frozen dataclass

### Bm25Config
```python
@dataclass(frozen=True)
class Bm25Config:
    field_weights: dict[str, float]
    k1: float = 1.2
    b: float = 0.75

    @classmethod
    def defaults(cls) -> "Bm25Config":
        return cls(
            field_weights={
                "title": 5.0, "source_title": 3.0, "track": 2.0,
                "tags": 3.0, "projects": 2.0, "source_type": 1.0,
                "body_summary": 1.0, "body_actions": 1.0,
                "body_principles": 1.0, "body_risks": 1.0,
            }, k1=1.2, b=0.75,
        )
```

### 测试
- `tests/test_bm25_tuning.py` — 7 个测试
- 验证默认配置、title 高权重优先级、k1=0 忽略词频、b=0 忽略文档长度、deterministic 3 次一致

---

## U4: Recall Quality Gate Script

### 创建文件
- `scripts/recall_quality_gate.py` — 独立 gate 脚本

### 功能
- 加载黄金 recall fixture → 运行 BM25 召回 → 报告召回率和每查询 pass/fail
- CLI 参数：`--threshold`（默认 0.8）、`--verbose`
- Exit code 0 = 总召回率 ≥ threshold 且所有负查询返回 0 命中
- 验证结果：14/14 黄金查询通过、4/4 负查询通过、100% 召回率 (21/21)

---

## U5: Web RecallPage Explain Display

### 修改文件
- `web/src/api/types.ts` — RecallResponse hit 类型新增 `matched_fields` 和 `matched_terms_list` 可选字段
- `web/src/lib/i18n.ts` — 新增 8 个 i18n key（zh + en）
- `web/src/pages/RecallPage.tsx` — 新增可折叠 explain 面板

### 新增 i18n keys
```
recall.explain_title: "搜索说明" / "Search Details"
recall.explain_lexical_boundary: BM25 词法检索边界说明
recall.explain_matched_fields: "命中字段分布" / "Matched Fields"
recall.explain_top_terms: "主要命中词" / "Top Matching Terms"
recall.explain_no_hits_reason: "未命中原因" / "Why No Results"
recall.explain_show: "查看搜索详情" / "Show search details"
recall.explain_hide: "收起搜索详情" / "Hide search details"
```

### Explain 面板行为
- 默认折叠，新搜索自动重置为折叠
- 展开按钮带 ▶ 箭头旋转动画（rotate-90）
- 有命中时：展示 top-3 命中字段 + top-5 卡片中唯一匹配词（top-8）
- 零命中时：展示 empty_state.description 作为未命中原因说明
- 仅在 data 存在时显示（有结果或无结果都有诊断价值）

---

## 已知限制

### CJK 字符级分词
当前 tokenizer 按单字符切分中文（"架构" → ["架","构"]），导致：
- CJK 负查询几乎不可能（单个字符太常见，"器" 匹配"装饰器"、"机器学习"）
- CJK 搜索精度低于英文
- 已通过 `test_cjk_character_tokenization_limitation` 测试文档化
- 未来改进方向：jieba/bigram tokenization

### 黄金 fixture 规模
12 张卡片、14 条黄金查询、4 条负查询 — 足以作为 baseline 和回归检测，但不是大规模 benchmark。规模扩展应在真实 dogfood 数据增长后自然发生。

---

## 非目标（未做）

- 不引入 jieba/bigram tokenization
- 不引入 semantic/embedding reranking
- 不引入 RAG answering
- 不引入 embedding/vector DB
- 不改变 BM25 参数默认值（仅暴露 Bm25Config 供 tuning）
- 不新增外部依赖

---

## Gate 结果

| Gate | Exit Code | Timeout |
|------|-----------|---------|
| `git diff --check` | 0 | No |
| `npm --prefix web run build` | 0 | No |
| `python -m pytest tests/test_web_product_copy.py -q --tb=short` | 0 | No |
| `python -m pytest tests/ -q --tb=short` | 0 | No |
| `python scripts/recall_quality_gate.py --verbose` | 0 | No |

---

## 已更新质量债台账

本次 Direction C 无新质量债。
CJK 字符级分词限制已在 U1 测试中文档化（`test_cjk_character_tokenization_limitation`），建议在方向规划中记录为 P3（已知限制，非阻塞 bug）。
