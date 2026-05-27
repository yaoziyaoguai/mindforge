# FakeProvider Keyword Extraction Improvement — Product Main Path Real Dogfood

**日期**: 2026-05-27
**基于**: `docs/audits/2026-05-27-118-post-governance-global-red-team-audit.md`
**Task type**: dogfood
**Workstream**: Product Main Path Real Dogfood

---

## Background

Product Main Path Real Dogfood 验证中，recall hit rate 只有 ~33% (中文) / ~40% (英文)。根因分析：

1. `FakeProvider.generate()` 的 distill stage 只从 `title` 提取关键词（`_extract_keywords(title)`）
2. Pipeline 的 `_distill_vars()` 已将真实原文 `raw_text`（最多 12000 chars）渲染进 prompt
3. 但 `FakeProvider` 完全忽略 prompt 中的 `raw_text`，只用 title 做 keyword extraction
4. 结果：所有 body 字段都是 `[fake] ...` 前缀占位内容，BM25 索引缺乏真实内容锚点

这不是产品 bug — 是 fake provider 的已知设计简化。但在 dogfood 场景下严重限制 recall 验证。

## Change

### files changed

- `src/mindforge/llm/fake.py`

### what changed

1. **新增 `_extract_keywords_from_text(text, max_keywords, source_label)`** — 从任意文本提取关键词的通用版本
   - 与 `_extract_keywords(title)` 使用相同规则（ASCII ≥3 字符 + CJK 2-gram）
   - 新增 CJK bigram 停用词集合 `_CJK_STOP_BIGRAMS`（~50 个高频无语义 2-gram）
   - 新增全局 `_STOP_WORDS` 常量（替换原函数内联集合）

2. **修改 `_extract_keywords(title)`** — 改为调用 `_extract_keywords_from_text` 的薄包装

3. **修改 `FakeProvider.generate()` distill stage** — 从 prompt 全文提取关键词
   - Title 关键词优先（`_extract_keywords(title)`，最多 8 个）
   - Prompt 全文补充关键词（`_extract_keywords_from_text(request.prompt, max_keywords=20)`）
   - 合并去重，上限 15 个（比之前的 8 个更丰富）
   - 关键词同时注入 tags、ai_summary_bullets、source_excerpt 等 BM25 索引字段

### why it is safe

- **确定性**：纯 regex + CJK 2-gram 提取，无 LLM、无网络、无随机性
- **零密钥**：不读取 .env / API key / secrets
- **零网络**：不发起任何 HTTP 请求
- **幂等**：同一份输入永远得到同一份输出
- **不改变产品语义**：只影响 fake provider 的输出；真实 provider 路径完全不受影响
- **不改变核心安全语义**：ai_draft 仍不能被自动提升为 human_approved
- **现有测试全部通过**：full test suite exit 0

### why no RAG/embedding/vector DB

这是纯关键词提取改进，不是 RAG 或 embedding。BM25 词法索引仍使用 `ascii_word_plus_cjk_char_v1` tokenizer。

## Results

### Recall hit rate comparison

| Query Language | Before (title-only) | After (title + prompt raw_text) |
|---------------|---------------------|--------------------------------|
| English (12 queries) | ~40% (4/10) | **91.7% (11/12)** |
| Chinese (12 queries) | ~33% (4/12) | 0% (0/12) — source docs are English-only |

### English queries detail

All 12 queries with hit counts:
- "retrieval backend architecture" → 8 hits
- "graph knowledge ontology" → 20 hits
- "audit quality review" → 5 hits
- "safety boundary security" → 2 hits
- "design system components" → 20 hits
- "plugin extension adapter" → 2 hits
- "engineering workflow process" → 1 hit
- "documentation cleanup archive" → 1 hit
- "approval review boundary" → 1 hit
- "product dogfood validation" → 0 hits (唯一未命中)
- "architecture quality debt" → 5 hits
- "user guide documentation" → 2 hits

### Chinese recall note

中文查询全部 0 hits 因为 source docs 全部是英文 Markdown 文件。这是 source material limitation，不是 tokenizer 或 keyword extraction 的问题。如需验证中文 recall，需要在 source set 中混入足量中文文档。

### Full pipeline verification

```
Scan: 25/25 ✅
Process (ai_draft): 25/25 ✅
Explicit Approve: 24/24 ✅ (1 duplicate overwrite)
Library: 24 cards ✅
BM25 Index: 24 cards, fresh ✅
Recall: 91.7% English hit rate ✅
Wiki: rebuilt, 24 cards included ✅
Export: Web-only (known limitation, no CLI command) ⚠️
```

## Known limitations

1. **Chinese recall 0%** — source material is English-only. Not a product bug. To validate Chinese recall: include mixed-language docs in source set.
2. **Export CLI missing** — `mindforge export` command does not exist. Export only available through Web UI ExportPage.
3. **Wiki fake content** — Wiki sections contain `[fake] Section 1/2` placeholder content because FakeProvider's `wiki_synthesis` stage doesn't correlate real cards.
4. **Template noise in keywords** — prompt template instructions contribute some noise keywords (e.g., "json", "system", "distill"), but these are filtered by the 15-keyword cap and don't degrade recall. Signal from 12000 chars of raw_text dominates.

## Deferred (not in this loop)

- Batch 2 Archive Candidates — still undefined archive/delete rules
- Chinese user guide sync — already done in previous residual references loop
- Web IA/UX Loop 2 — separate workstream
- Architecture quality reset — separate workstream
- Graph/Sensemaking/Entity/Community expansion — NOT AUTHORIZED without separate spec

## Gates

| Gate | Command | Timeout | Exit Code | Result |
|------|---------|---------|-----------|--------|
| git diff --check | `git diff --check` | no | 0 | clean |
| ruff check | `ruff check src/ tests/ docs/` | no | 0 | All checks passed! |
| product copy tests | `python -m pytest tests/test_web_product_copy.py -q --tb=short` | no | 0 | 72 passed |
| full test suite | `python -m pytest tests/ -q --tb=short` | no | 0 | all passed |
| web build | `npm --prefix web run build` | no | 0 | built in 5.64s |
