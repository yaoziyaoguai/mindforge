# M5.4 — Lexical Recall (BM25) Protocol — v0.3

> ⚠️ **重要重定位**：M5 backlog 中的 "M5.4 RAG spike" 在 v0.3 被**显式重命名**
> 为 **Lexical Recall (BM25)**。MindForge **不**走 RAG / embedding / 向量库路线。
> v0.3 提供的是**纯本地词法检索**，没有任何远程调用、没有任何 LLM 调用、没有
> 任何 embedding 模型加载。

## 1. 设计目标（一句话）

让 `mindforge recall --query "..."` 从"contains 过滤"升级到"BM25 评分排序、
字段加权、可解释、可重建索引"，但严守"只索引 Knowledge Card 安全字段"的
红线，确保任何 raw source / Source Excerpt / Human Note / 私笔记永远不会被
检索命中。

## 2. 不做的事（硬约束）

- ❌ 不调用 LLM
- ❌ 不读取 `.env`
- ❌ 不联网
- ❌ 不引入 embedding / 向量库 / sentence-transformers / faiss
- ❌ 不索引 raw source 文件
- ❌ 不索引 `## Source Excerpt` 段（卡片内的原文回引）
- ❌ 不索引 `## Human Note` 段（人类私笔记）
- ❌ 不索引 prompts / completions / runs / state.json
- ❌ 不索引 `.env` / API key / 任何 secret
- ❌ 不上传索引产物
- ❌ 不写远程 telemetry

## 3. 索引白名单（可索引字段）

| 字段 | 来源 | 默认权重 |
|---|---|---|
| `title` | frontmatter | 5 |
| `track` | frontmatter | 4 |
| `projects` | frontmatter | 4 |
| `source_title` | frontmatter | 3 |
| `tags` | frontmatter | 3 |
| `principles` | frontmatter | 2 |
| `known_risks` | frontmatter | 2 |
| `source_type` | frontmatter | 1 |
| `body_summary` | body `## AI Summary` | 1 |
| `body_actions` | body `## Action Items` | 1 |
| `body_principles` | body `## Principles` | 1 |
| `body_risks` | body `## Known Risks` | 1 |

任何不在此白名单的 body section 永远**不**会进入索引。

## 4. 算法

简化版 BM25F：每个字段的 token 在虚拟文档中按 `field_weight` 重复出现，从而
得到加权 tf 与加权 doc_len，再走标准 Okapi BM25：

```
IDF(t)   = log( (N - df(t) + 0.5) / (df(t) + 0.5) + 1 )
score(d) = Σ_t  IDF(t) * tf*(k1+1) / (tf + k1*(1 - b + b*dl/avgdl))
```

其中：
- `tf`     = Σ_field  `field_weight[f]` * 出现次数 in field
- `dl`     = Σ_field  `field_weight[f]` * 字段 token 数
- `k1=1.5`, `b=0.75`（业内常用默认）
- `df(t)` 在 **过滤后** 的候选文档子集上重算（更贴近用户当前查询）

`--explain` 把总分按字段贡献近似分摊：
`field_contrib(f) = Σ_t score(t) * (w * fcount(t)) / weighted_tf(t)`

## 5. 分词器

`tokenize_v1`（保留版本号方便未来升级）：
- ASCII：`[A-Za-z0-9]+`，全部 lowercase；
- CJK：每个汉字 / 假名 / 谚文字单独一个 token；
- 其他符号忽略；
- **不**做 stemming / 停用词 / 词形还原。

理由：个人知识库索引规模小（典型 < 5000 卡），简单可解释 > 召回率极致。

## 6. 索引文件

- 路径：`<state.workdir>/index/bm25.json`（默认 `.mindforge/index/bm25.json`）
- 通过 `.mindforge/` 整目录被 `.gitignore` 挡住
- 写入策略：`.tmp` 先写后原子 `rename`
- 格式：`schema_version: 1` + `built_at` + `field_weights` + `k1/b/avgdl` + `docs[]`

`docs[i]` 仅含安全字段：`rel_path`, `id`, `title`, `status`, `track`, `projects`,
`tags`, `source_type`, `created_at`, `mtime`, `fields{name → tokens[]}`,
`doc_len`。**不**含卡片正文 / 路径之外的绝对路径 / 任何用户私数据。

## 7. 命令

```bash
# 重建索引（幂等；写整文件）
mindforge index rebuild

# 查看索引存在性 / 是否 stale / 字段权重
mindforge index status

# BM25 词法检索
mindforge recall --query "checkpoint runtime"
mindforge recall --query "agent runtime checkpoint" --explain
mindforge recall --track "agent-runtime" --query "checkpoint"
mindforge recall --project my-first-agent --query "runtime event"
mindforge recall --query "checkpoint" --include-drafts
mindforge recall --query "checkpoint" --limit 10
mindforge recall --query "checkpoint" --format markdown
mindforge recall --query "checkpoint" --format json
```

行为细节：
- `--query` 与旧版 `--keyword` **互斥** — 给 `--query` 时走 BM25 路径；不给则
  走 M4.1 规则检索（行为不变）。
- 默认 `status=human_approved`；`--include-drafts` 才打开 `ai_draft`。
- 索引文件不存在时，`recall --query` 会**内存即时构建**并提示一次。
- 不传 `--query` 仍可使用所有 M4.1 过滤器（`--track` / `--project` / `--tag` /
  `--keyword` / `--sort` 等），向后兼容。

## 8. Staleness 检测

`index status` 比对索引内 doc 与当前 vault 卡片：
- `added`：磁盘上有但索引里没有
- `removed`：索引里有但磁盘上没有了
- `changed`：mtime 漂移（容差 1 秒）
- `fresh = ¬(added ∨ removed ∨ changed)`

只显示前 5 项，避免 stdout 爆炸。

## 9. 可观察性

每次 `recall --query` 都通过 `RunLogger` 写一条 `recall_bm25_executed` 事件：
- 复用白名单字段 `keyword_provided` / `keyword_hash` 记录"是否给了 query +
  query 的 hash 指纹"；**绝不**写 query 原文
- `count` / `filters` / `output_format`
- `filters.used_disk_index` 标记本次是否用了磁盘索引

## 10. 安全测试（必须存在）

`tests/test_v0_3.py` 中**硬保证**：
- `test_build_index_excludes_source_excerpt_and_human_note`
- `test_cli_recall_query_secret_token_never_matches`

只要回归这两条，BM25 安全契约就视为破裂，必须修复才能合并。

## 11. 不做的扩展（明确推迟）

- BM25F 全式（per-field IDF / per-field length normalization）
- 同义词 / 拼写纠错 / 模糊匹配
- 高亮命中片段（会触发"打印卡片正文"风险，需要单独审计）
- 多语言分词器（中文分词器 jieba 等）
- 索引按 track / project 分片
- 实时增量更新（v0.3 只支持全量 rebuild；个人库规模无需增量）

## 12. v0.3.1 — 配置化字段权重 + hybrid 排序

> v0.3.1 在不破坏 v0.3.0 安全契约的前提下，把 BM25 从"硬编码权重"升级为"用户可配 + 多信号融合"。**仍然是纯本地规则，不是 RAG / embedding。**

### 12.1 `configs/mindforge.yaml`

```yaml
search:
  bm25:
    enabled: true
    k1: 1.5
    b: 0.75
    default_limit: 10
    fields:
      title: 5.0
      learning_tracks: 4.0   # 别名 → 内部 track
      projects: 4.0
      tags: 3.0
      summary: 1.0           # 别名 → body_summary
      action_items: 1.0      # 别名 → body_actions
  hybrid:
    enabled: true
    weights:
      bm25: 0.75
      value_score: 0.15
      review_due: 0.10
```

- `bm25.fields` 用"用户友好别名 → 权重"，由 `lexical_index.USER_FIELD_ALIASES` 解析。
- 权重 `0` = **从该字段移除索引**（白名单语义）。
- 未声明的字段使用 `DEFAULT_FIELD_WEIGHTS`。
- `b` 必须在 `[0, 1]`；`k1` > 0；任何字段权重 < 0 都会 fail-fast `ConfigError`。

### 12.2 `config_hash` 与 stale 检测

- `BM25Index.config_hash` = sha256 前 16 位，覆盖：`schema_version` / tokenizer 名 / 排序后的字段权重 / `k1` / `b` / 索引 body sections 列表。
- `mindforge index status`、`mindforge doctor` 都会比对索引内 `config_hash` 与当前 `mindforge.yaml` 的 hash；不一致 → **stale**，提示 `mindforge index rebuild`。
- recall 路径若发现 `config_hash` 漂移，自动用内存按当前配置重建（一次性提示），结果总是用"当前配置"打分，**绝不**用旧权重静默返回结果。

### 12.3 hybrid 排序

- 三路信号都先归一到 `[0, 1]`，再按 `weights` 加权求和：
  - `bm25_norm` = `(bm25 - min) / (max - min)`，对当前命中集做 min-max 归一；
  - `value_norm` = `clamp(value_score / 10, 0, 1)`；
  - `review_due_norm` = `1.0`（已到期）/ `1 - days_remaining/30`（30 天内）/ `0`（缺失或 >30 天）。
- 缺失 `value_score` / `review_after` → 对应分量按 `0`，**不报错**。
- `--ranking hybrid --explain` 会打印每条命中的三路分量与 `final_score`。

### 12.4 telemetry 新增字段

仍然在 `filters` 子 dict 内（已在白名单），新增两个**元数据** key：
- `ranking_mode`：`"bm25"` / `"hybrid"`；
- `index_stale`：`bool`，是否触发了配置漂移导致的内存重建。

**绝不**记录 query 原文 / hybrid 三路具体分量 / 卡片正文。

### 12.5 测试硬保证（`tests/test_v0_3_1.py`）

- `test_search_config_rejects_negative_weight` / `test_search_config_rejects_bad_b`：配置校验
- `test_index_status_shows_stale_on_config_drift`：漂移检测
- `test_recall_hybrid_promotes_high_value_card`：hybrid 排序行为
- `test_recall_hybrid_safe_when_value_score_missing`：缺字段不崩
- `test_recall_telemetry_no_query_plaintext`：query 永不入 telemetry
- `test_no_source_excerpt_in_hybrid_results`：hybrid 路径仍满足 v0.3 安全契约
