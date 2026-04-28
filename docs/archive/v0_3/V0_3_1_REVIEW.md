# v0.3.1 Review — 配置化 BM25 + Hybrid 排序

> 把 v0.3.0 的"BM25 词法检索 MVP"推进到**可调可观察的产品形态**：字段权重从硬编码迁到 `mindforge.yaml`；新增 hybrid 三路本地融合排序；索引引入 `config_hash` 配合 `index status` / `doctor` 让"配置漂移"对用户立刻可见。**仍然纯本地、无 LLM、无 .env、无 embedding。**

## 1. 范围

| 维度 | v0.3.0 | v0.3.1 |
|---|---|---|
| BM25 字段权重 | 硬编码 `DEFAULT_FIELD_WEIGHTS` | `configs/mindforge.yaml.search.bm25.fields`（用户别名 → 权重）|
| `k1` / `b` | 硬编码 1.5 / 0.75 | 可配 + 严格校验（`k1 > 0`，`b ∈ [0, 1]`）|
| 排序信号 | 仅 BM25 | `bm25` + `value_score` + `review_due` 三路加权（hybrid）|
| 索引指纹 | 无 | `config_hash`（sha256 短指纹）|
| `index status` | 仅 mtime / set-diff | + `config_hash` 比对、漂移提示 |
| `doctor` | 不查 BM25 索引 | 检查 missing / stale / 配置漂移 → 给出可执行 hint |
| telemetry | 已有白名单 | filters 内新增 `ranking_mode` / `index_stale`，**仍不**记录 query 原文 |

## 2. 实现摘要

### 2.1 配置层

`src/mindforge/config.py`：
- 新增 `BM25SearchConfig` / `HybridSearchConfig` / `SearchConfig` 三个 frozen dataclass；
- `MindForgeConfig.search: SearchConfig`，`default_factory=SearchConfig`，对老 yaml 完全兼容；
- `_parse_search()` 严格校验：负权重 / 非数 / `b ∉ [0,1]` / `k1 ≤ 0` / `default_limit ≤ 0` 全部 fail-fast `ConfigError`，附中文 actionable 提示。

### 2.2 索引层

`src/mindforge/lexical_index.py`：
- `DEFAULT_FIELD_WEIGHTS` 类型从 `int` 改 `float`；
- 新增 `USER_FIELD_ALIASES`：`learning_tracks → track`、`summary → body_summary`、`action_items → body_actions` 等；
- `resolve_field_weights(user_dict)` 把"用户别名 → 权重"翻译成"内部 field 名 → 权重"；权重 `0` = 移除（白名单语义），未知别名静默忽略；
- `compute_config_hash(field_weights, k1, b, tokenizer_name)` = sha256 短指纹（16 hex），输入做 canonical sort + round 6；
- `BM25Index` 增 `config_hash: str` 字段；`to_dict` / `from_dict` 兼容老索引（无该字段时为 `""`，被视为"未记录"）；
- 新增 `hybrid_search(index, query, weights, cards, ...)`：先调 `search()` 拿全集，再 min-max 归一 BM25 分数，叠加 `value_score / 10` 与 `review_due`（30 天衰减），按 `final_score` 排序裁剪。

### 2.3 CLI 层

`src/mindforge/cli.py`：
- `recall` 新增 `--ranking bm25|hybrid`（默认 `bm25`，向后兼容）；
- `_do_bm25_recall`：从 `cfg.search.bm25` 解析权重 + k1/b → `compute_config_hash` → 与磁盘索引比对；不一致则**自动内存重建**并提示，绝不静默用旧权重打分；
- hybrid 路径在 markdown / table / compact / json 全部输出 `final_score`，`--explain` 额外打印三路分量；
- `index rebuild`：用 cfg 解析后的 weights 构建，写入 `config_hash`，输出加 `config_hash=...`；
- `index status`：新增 "config_hash（索引）" / "config_hash（当前）" 两行，漂移时显眼提示"⚠ 配置漂移"；
- `doctor`：新增 BM25 索引检查（缺失 / stale / 漂移）→ 写入 `Action items`。

### 2.4 telemetry

`run_logger.py` 的 `filters` 子 dict 已在白名单，无需扩；
- recall 在 `filters` 内额外写 `ranking_mode` / `index_stale` 两个**元数据**键；
- query 原文继续走 `keyword_provided` / `keyword_hash` 路径，**绝不**入文件。

## 3. 测试

`tests/test_v0_3_1.py` 共 17 例，全部通过：
- 配置默认 / 用户覆盖 / 别名解析 / 0 权重移除
- 校验：负权重、`b > 1` 抛 `ConfigError`
- `config_hash` 随权重变化、`index rebuild` 写入、`index status` / `doctor` 漂移提示
- `--ranking bm25` 默认行为不变
- `--ranking hybrid` JSON 含三路分量 + `final_score`；`--explain` 文本展示
- hybrid 高 value + 已到期 review 卡片排序优先于低 value 卡片
- 缺 `value_score` / `review_after` 时不崩、分量按 0
- 非法 `--ranking neural` 退出码非 0
- recall telemetry 不写 query 原文，`ranking_mode` 元数据写入
- hybrid 路径仍不返回 `Source Excerpt` / `Human Note`

`pytest -q`：**294 passed, 2 skipped**。
`ruff check src/ tests/`：**All checks passed**。

## 4. Smoke 用例（建议手测）

```bash
mindforge init --vault /tmp/mfv
echo "..." > /tmp/mfv/20-Knowledge-Cards/x.md          # 造卡片
mindforge index rebuild                                # 写入 config_hash
mindforge index status                                 # 显示 config_hash + fresh
mindforge recall --query checkpoint                     # bm25 默认
mindforge recall --query checkpoint --ranking hybrid --explain
# 改 mindforge.yaml: search.bm25.fields.title: 9.0
mindforge index status                                 # → stale + 配置漂移
mindforge doctor                                       # → Action item: BM25 索引与配置不一致
mindforge index rebuild                                # → fresh
```

## 5. 不做的扩展（继续推迟）

- BM25F 全式（per-field IDF）
- 同义词 / 模糊匹配 / 拼写纠错
- 高亮命中片段
- 中文分词器（jieba 等）
- 索引按 track / project 分片
- 增量更新（继续保持全量 rebuild）
- embedding / RAG / 向量检索
- 自动复习调度算法（SM-2 / FSRS）

## 6. 下一步建议

两条路二选一：

1. **v0.3.2 — UX polish**：把 hybrid 三路权重做 CLI 临时覆盖（`--weight bm25=0.5 ...`）；recall 输出加"为什么这条排第一"的简短解释行；`mindforge index info --json` 给出机器可读快照。
2. **v0.4 — review scheduling**：把 `review_due` 信号反向用，做最小 SM-2 风格调度（依旧本地、可解释、不黑盒）。

推荐 **先做 v0.3.2 UX polish**：v0.3.1 已让能力完整，下一阶段更应该让"用户每天用得顺手"，而不是再扩新维度。
