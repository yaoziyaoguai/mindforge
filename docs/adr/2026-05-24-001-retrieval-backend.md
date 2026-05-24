# ADR-001: Retrieval Backend — BM25 vs SQLite FTS5 vs DuckDB FTS

## 日期
2026-05-24

## 状态
Accepted (v1.3 re-evaluated 2026-05-24 — 触发条件不满足，保持 BM25)

## 背景

MindForge 当前使用纯 Python BM25 实现（`lexical_index.py`）作为全文检索引擎。v0.8 引入 `RetrievalPort` 抽象后，可以评估和替换检索后端而不影响 `recall_service.py` API 层。

## 评估维度

### 方案 A: 纯 Python BM25（现状）

| 维度 | 评价 |
|------|------|
| 依赖 | 零外部依赖 |
| 性能（100 cards） | 索引构建 < 50ms，查询 < 10ms |
| 性能（1000 cards） | 索引构建 ~200ms，查询 ~50ms（估计） |
| 持久化 | JSON 文件存储索引，重启后需校验/重建 |
| 中文支持 | CJK 逐字切分，可用但无分词 |
| 维护成本 | 完全自主可控，可随时调整 |
| 测试覆盖 | 现有 8 tests |

### 方案 B: SQLite FTS5

| 维度 | 评价 |
|------|------|
| 依赖 | **零额外依赖** — `sqlite3` 是 Python 标准库模块 |
| 性能 | 原生 C 实现，预期比纯 Python 快 3-10x |
| 持久化 | 原生 SQLite 文件，重启即用，无需重建 |
| 中文支持 | 默认 tokenizer 逐字切分（与现状相同）；可注册自定义 tokenizer |
| BM25 评分 | 内置 `bm25()` 函数，OKAPI 标准实现 |
| 高级功能 | prefix query (`*`), phrase query (`""`), `snippet()` 高亮 |
| 维护成本 | SQL schema 管理、迁移策略 |
| 测试覆盖 | 需要新增 |

### 方案 C: DuckDB FTS

| 维度 | 评价 |
|------|------|
| 依赖 | **新增依赖** — `duckdb` ~30MB wheel |
| 性能 | 列式引擎，OLAP 优化，全文检索并非其核心场景 |
| 持久化 | 原生 DuckDB 文件 |
| 中文支持 | 需额外配置 |
| 维护成本 | 学习曲线陡峭，调试工具链不成熟 |
| 适配度 | 个人知识库无需 OLAP；大材小用 |

## 决策

**条件采用方案 B（SQLite FTS5），当前保持方案 A（纯 Python BM25）为默认。**

### 触发条件

满足以下任一条件时，启动 FTS5 迁移：

1. 卡片数 > 500 且索引构建时间 > 500ms
2. 索引从磁盘加载失败率 > 5%（当前 JSON 格式的健壮性问题）
3. 用户反馈检索延迟 > 200ms

### 理由

1. **零依赖** — SQLite FTS5 是 Python 标准库的一部分，不违反"不新增依赖"红线
2. **持久化优势** — SQLite 原生文件格式比 JSON 更可靠，避免 `IndexFormatError`
3. **确定性保持** — FTS5 的 BM25 评分是确定性的、可解释的
4. **实现成本低** — `RetrievalPort` 已就绪，新增 `SqliteFts5Engine` 即可插拔
5. **回退简单** — 两套引擎可并存，通过配置切换

### 不做

- 不立即替换现有 BM25（没有触发条件满足）
- 不引入 DuckDB（不必要的重依赖）
- 不做 FTS5 中文分词增强（保持与现状相同的逐字切分）
- 不删除 `lexical_index.py`（保留作为 fallback）

## 迁移路径（当触发条件满足时）

1. 新增 `SqliteFts5Engine(RetrievalPort)` 实现
2. 新增 `SearchIndexPort` 抽象索引构建接口
3. 在 `recall_service.py` 中根据配置选择 engine
4. 新增 `SqliteFts5Engine` 的 golden tests
5. 通过 `mindforge.yaml` 配置项切换引擎
6. BM25 保留为 fallback，FTS5 索引损坏时自动回退

## v1.3 重新评估 (2026-05-24)

### 当前规模

- Demo vault: 未部署（开发环境无真实 vault）
- 测试数据: ~100 张虚拟卡片
- 实际用户卡片: 0（尚未 dogfood）

### 触发条件检查

| 条件 | 阈值 | 当前 | 满足？ |
|------|------|------|--------|
| 卡片数 | > 500 | < 100（测试） | 否 |
| 索引构建时间 | > 500ms | ~30ms（100 卡，实测） | 否 |
| 用户反馈延迟 | > 200ms | < 10ms | 否 |

### 决定

**继续使用纯 Python BM25。** 无触发条件满足。RetrievalPort 抽象保留，若未来切换只需新增 SqliteFts5Engine 适配器。

## 参考

- SQLite FTS5 文档: https://www.sqlite.org/fts5.html
- Python sqlite3 模块: https://docs.python.org/3/library/sqlite3.html
- v0.8 SPEC: `docs/specs/2026-05-24-026-v0_7-v1_0-multi-stage-roadmap.md` §2
