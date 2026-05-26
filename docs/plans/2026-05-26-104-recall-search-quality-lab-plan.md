# Recall/Search Quality Lab Plan

**日期**: 2026-05-26
**状态**: active
**输入**: `docs/plans/2026-05-25-094-next-deepening-roadmap.md` Direction C
**授权**: Direction C — Recall/Search Quality Lab, no embedding

---

## Problem Frame

v4.9 MindForge-on-MindForge dogfood 揭示了 recall 质量的关键缺口：

1. **Fake provider 导致 recall 4/10**：fake provider 只从文件名提取关键词，真实项目文档文件名不携带完整语义，BM25 索引覆盖率不足
2. **没有 recall quality baseline**：synthetic dogfood recall 10/10 曾误导为"recall 工作良好"，但那是 sample coverage 的结果，不是索引质量
3. **没有 query explain 工具**：用户（和开发者）无法理解"为什么命中/为什么没命中"
4. **没有 recall quality gate**：每次改动后无法自动验证 recall 是否退化

本计划建立 recall quality lab，提供可复现的质量测量闭环——纯 deterministic，零 embedding/RAG/vector DB。

---

## Scope Boundary

### In Scope

- Golden recall fixtures: 固定的 approved cards + queries + expected hits
- Query explain report: `--explain` 的结构化输出和人类可读报告
- BM25 tuning: 字段权重、tokenizer 配置、小型 synonym rules
- Recall quality gate: script 输出 exit code + quality summary
- Web RecallPage 的 explain 展示

### Out of Scope

- Semantic search / embedding / vector DB
- RAG answering / LLM judge
- Graph/Sensemaking/Entity/Community expansion
- Real LLM provider activation
- Changing approval semantics
- Large dependency additions
- CLI `mindforge export` command (known limitation)

---

## Architecture Constraint

所有改动在现有 RetrievalPort 边界内进行。不新增端口/ABC，不复用 Graph 子系统。

```
recall_service.py ──→ RetrievalPort (ABC) ──→ Bm25RetrievalEngine
                                                    │
                                                    └── lexical_index (BM25)
```

Recall fixtures 和 query explain 作为独立模块挂载在 recall_service 上，不耦合到 retrieval port 内部。

---

## Implementation Units

### U1: Golden Recall Fixtures

**Goal**: 创建固定的 synthetic approved cards + query set，记录每个 query 的 expected hit IDs。

**Files**:
- CREATE `tests/fixtures/recall_benchmark.py` — golden cards + queries + expected hits
- CREATE `tests/test_recall_benchmark.py` — 验证 fixture 完整性和 golden baseline

**Approach**:
1. 定义 12 张 synthetic approved cards，覆盖不同主题（Python、架构、安全、测试、部署、中文内容）
2. 每张 card 有真实的 title、tags、body 内容（非 [fake] 占位符）
3. 定义 10 个 golden queries，每个 query 记录 expected_hit_ids（至少应命中的 card ID 集合）
4. 包含 CJK queries、英文 queries、短 queries、多词 queries
5. 包含 negative queries（预期 0 hits）

**Patterns to follow**: `tests/fixtures/retrieval_benchmark.py` 的 frozen dataclass + tuple 模式

**Test scenarios**:
- 验证 benchmark 可构建且 cards 完整
- 验证 expected hits 引用的 card IDs 都存在于 cards 中
- 验证 negative queries 的 expected_hits 为空集
- 验证 cards 有足够的字段内容（title/body/tags 非空）

**Verification**: `python -m pytest tests/test_recall_benchmark.py -q --tb=short` exit 0

---

### U2: Query Explain Report

**Goal**: 增强 `--explain` 输出，提供结构化 explain 数据和人类可读的 miss reason。

**Files**:
- MODIFY `src/mindforge/recall_service.py` — 新增 `QueryExplain` dataclass 和 `explain_misses()` 函数
- MODIFY `src/mindforge/recall_presenter.py` — 增强 explain 输出格式（若存在）
- CREATE `tests/test_recall_explain.py` — 验证 explain 输出的正确性

**Approach**:
1. 新增 `QueryExplain` frozen dataclass：query_text、tokenized_terms、matched_fields、field_contributions、miss_reason（若 0 hits）
2. 实现 `explain_zero_hits(result: RecallSearchResult) -> QueryExplain`：分析为什么 0 hits
   - 检查是否有任何 token 匹配到索引中的 term
   - 检查 status_filter 是否过滤掉了所有结果
   - 检查索引是否为空
3. 实现 `explain_hits(result: RecallSearchResult) -> QueryExplain`：分析 hits 的匹配原因
   - 每个 hit 的 field contributions 已存在（`RecallFieldExplain`）
   - 汇总为 query-level explain
4. 在 `RecallSearchResult` 中附加 explain 数据（当 `--explain` 启用时）

**Design decisions**:
- Explain 数据直接从 BM25 索引中提取，不做 LLM 分析
- miss_reason 使用中文描述，面向用户可读
- 不做 query rewriting 或 suggestion（那是后续 loop）

**Test scenarios**:
- explain_zero_hits 对空索引返回正确的 miss_reason
- explain_zero_hits 对 status_filter 过滤返回正确的 miss_reason
- explain_hits 对已知命中返回合理的 field contributions
- explain 输出不包含 secrets/paths/内部状态

**Verification**: `python -m pytest tests/test_recall_explain.py -q --tb=short` exit 0

---

### U3: BM25 Tuning Infrastructure

**Goal**: 让 BM25 参数（字段权重、k1、b）可测试、可比较、可回退。

**Files**:
- MODIFY `src/mindforge/retrieval/bm25_engine.py` — 支持 per-field tokenization 配置
- CREATE `tests/test_bm25_tuning.py` — 参数调优的回归测试

**Approach**:
1. 定义 `Bm25Config` frozen dataclass：field_weights、k1、b、tokenizer_config
2. 在 `Bm25RetrievalEngine` 中支持传入 `Bm25Config`
3. 建立 golden tuning test：固定 cards + queries，验证特定参数组合的排序结果不变
4. 不在此 loop 中实际调参数（那是基于 fixture 数据的后续工作）

**Design decisions**:
- 所有参数变更必须有对应的 golden test 记录预期行为
- 不引入 grid search 或自动调参
- tokenizer 保持纯 Python split-based，不引入 NLP 库

**Test scenarios**:
- 不同 field_weights 产生不同排序（验证参数生效）
- 相同参数产生相同排序（确定性验证）
- k1=0 时 term frequency 不影响分数
- b=0 时 document length 不影响分数

**Verification**: `python -m pytest tests/test_bm25_tuning.py -q --tb=short` exit 0

---

### U4: Recall Quality Gate Script

**Goal**: 可独立运行的 recall quality gate，输出 exit code + structured summary。

**Files**:
- CREATE `scripts/recall_quality_gate.py` — 质量 gate 脚本
- MODIFY `docs/dev/engineering-workflow.md` — 将 recall quality gate 加入 gate 清单

**Approach**:
1. 加载 golden recall fixtures（U1）
2. 对每个 golden query 执行 recall
3. 检查 expected_hit_ids 是否都出现在结果中（recall ≥ threshold）
4. 检查 negative queries 是否返回 0 hits
5. 输出 summary：total queries、passed、failed、recall rate、failed queries detail
6. Exit code 0 当且仅当 recall rate ≥ 80%

**Design decisions**:
- 使用 fake provider 生成 cards（不需要真实 LLM）
- 独立脚本，不依赖 Web server
- 输出格式同时支持人类阅读和 CI parsing

**Verification**: `python scripts/recall_quality_gate.py` exit 0（当 benchmark 满足 ≥80% recall）

---

### U5: Web RecallPage Explain Display

**Goal**: 在 Web RecallPage 上展示 query explain 信息。

**Files**:
- MODIFY `web/src/pages/RecallPage.tsx` — 展示 explain 面板
- MODIFY `web/src/lib/i18n.ts` — 新增 explain 相关 i18n keys (zh + en)

**Approach**:
1. 在 RecallPage 搜索结果区域下方新增 explain 面板
2. 显示：matched terms、top contributing fields、BM25 lexical boundary 说明
3. 当 0 hits 时显示 miss reason 和下一步建议
4. 所有文案通过 i18n 管理

**Design decisions**:
- Explain 面板默认折叠，点击展开
- 不做复杂的可视化（chart/ histogram），保持简单文本
- 安全边界：不暴露索引路径、不暴露未审批卡片内容

**Verification**: `npm --prefix web run build` exit 0 + product copy test pass

---

## Dependencies

```
U1 (Golden Fixtures)
 ├── U2 (Query Explain) ── 依赖 U1 的 fixtures 进行测试
 ├── U3 (BM25 Tuning)  ── 依赖 U1 的 fixtures 进行 golden test
 └── U4 (Quality Gate) ── 依赖 U1 的 fixtures 作为 baseline

U5 (Web Explain) ── 依赖 U2 的 explain 数据结构
```

推荐执行顺序: U1 → U2 + U3 (并行) → U4 → U5

---

## Test Strategy

| Unit | Test File | Type |
|------|-----------|------|
| U1 | `tests/test_recall_benchmark.py` | Fixture validation |
| U2 | `tests/test_recall_explain.py` | Unit + integration |
| U3 | `tests/test_bm25_tuning.py` | Golden/regression |
| U4 | `scripts/recall_quality_gate.py` | Gate script |
| U5 | `tests/test_web_product_copy.py` | Product copy |

所有测试纯 deterministic，不调用 LLM/embedding/vector DB。

---

## Gates

每个 unit 完成后运行：

- `git diff --check`
- `ruff check src/ tests/ docs/`
- `python -m pytest tests/ -q --tb=short`
- `npm --prefix web run build`（U5 及之后的 Web 改动）
- `python -m pytest tests/test_web_product_copy.py -q --tb=short`（涉及 i18n 的改动）

---

## Risks

| Risk | Mitigation |
|------|-----------|
| BM25 tuning 变成不可维护的规则泥潭 | 所有规则必须 golden test + 可解释 + 可关闭 |
| Explain 暴露内部索引状态 | 只暴露安全字段（matched_terms, field_contributions），不暴露路径/内部状态 |
| Golden fixtures 与 fake provider 输出不一致 | Fixtures 直接构造 CardSummary，绕过 fake provider |
| Recall quality gate 阈值过低失去意义 | 初始阈值 80%，基于 U1 fixtures 校准后调整 |

---

## Non-Goals

- 不做 semantic search / embedding / vector DB
- 不做 RAG answering / LLM judge
- 不做 query rewriting / auto-suggestion
- 不做 Graph/Sensemaking/Entity/Community expansion
- 不做 real LLM provider activation
- 不新增大型依赖
- 不改变 explicit approval / human_approved 语义
- 不读取 .env / secrets
- 不写真实 Obsidian vault

---

## Deferred to Implementation

1. 具体 BM25 参数调优目标值（基于 U1 fixtures 的 baseline 数据决定）
2. Synonym rules 的具体词表（基于 U1 的 CJK query 失败模式决定）
3. Explain 面板的具体 UI 布局（基于现有 RecallPage 结构决定）
4. Recall quality gate 是否加入 `./scripts/check.sh`（基于 U4 的运行速度和稳定性决定）

---

## Self-Review

| Check | Verdict | Notes |
|--------|---------|-------|
| 是否引入 embedding/RAG/vector DB？ | No | 全部基于 BM25 lexical only |
| 是否恢复 Graph/Sensemaking 扩张？ | No | 不涉及 graph/sensemaking |
| 是否改变 approval 语义？ | No | 只读 recall，不改 approval |
| 是否新增大型依赖？ | No | 全部使用现有依赖 |
| 是否有明确的实现单元？ | Yes | U1-U5，每个有 files/test/verification |
| 是否覆盖测试策略？ | Yes | 每个 unit 有对应测试文件 |
| 是否可独立验证？ | Yes | U4 作为独立 gate script |
| 是否可直接执行？ | Yes | 每个 unit 有明确的文件和修改范围 |
