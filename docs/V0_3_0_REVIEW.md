# MindForge v0.3.0 Review

> v0.3.0 = **lexical recall**。让 `mindforge recall` 从"contains 过滤"升级
> 为 BM25 评分排序、字段加权、可解释、可重建索引；但严守"只索引安全字段"
> 的红线。**仍然不引入 RAG / embedding / 向量库 / 远程调用 / LLM 调用**。

## 增量

### 1. BM25 lexical recall（新）

- 新模块 `src/mindforge/lexical_index.py`：纯 Python BM25（约 350 行）
  - `tokenize` v1：ASCII word + CJK 单字
  - `BM25Index` 数据结构 + `save/load`（schema_version=1）
  - `build_index(cards)` / `search(index, query, ...)` / `diff_index`
  - 字段权重默认值见 `DEFAULT_FIELD_WEIGHTS`
  - 加权 BM25F 简化算法：每字段 token 按权重重复出现
- 新命令：
  - `mindforge index rebuild` — 全量重建到 `.mindforge/index/bm25.json`（原子写）
  - `mindforge index status` — fresh / stale 检测 + 字段权重汇总
- `mindforge recall` 增强：
  - 新增 `--query "..." [--explain]`（BM25 路径）
  - 不带 `--query` 仍走 M4.1 规则检索（向后兼容）
  - 索引不存在时自动内存即时构建并提示

### 2. 安全护栏（硬契约）

- **绝不**索引 `## Source Excerpt`、`## Human Note`、raw source、prompts、
  completions、runs、state.json、.env、API key
- **绝不**上传索引产物（`.mindforge/` 已被 `.gitignore` 挡）
- **绝不**写 query 原文进 telemetry — 只写 `keyword_provided` + `keyword_hash`
- 默认 `status=human_approved`；`--include-drafts` 才打开
- JSON 输出只暴露白名单字段（无 `doc_len` / `fields` / 原始 query）

### 3. 文档

- 新增 `docs/M5_4_LEXICAL_RECALL_PROTOCOL.md` — 完整契约（白名单 / 算法 /
  安全测试 / 不做清单）
- 更新 `README.md` / `docs/ROADMAP.md`

### 4. 测试

- 新增 `tests/test_v0_3.py` — 22 例覆盖：
  - tokenizer：ASCII 大小写、CJK 单字、空输入
  - 索引构建：**硬保证 source_excerpt / human_note 不入索引**（核心安全测试）
  - 搜索：默认 human_approved / `--include-drafts` 打开 / 字段权重排序 /
    pre-filter by track / explain 字段贡献分降序 / 空 query 返回空
  - 持久化：save/load round-trip / diff_index 检测增删改
  - CLI：index rebuild / index status（含缺失态） / recall --query 基本 /
    --explain / --include-drafts / **secret token 端到端不命中** /
    --format json schema 稳定 / --limit 生效 / 不带 --query 走旧路径
  - 索引文件落在 `.mindforge/index/` 下（被 .gitignore 挡）

## 数字

- 测试：277 passed, 2 skipped（pypdf/python-docx 未装）— v0.2.6 是 255 / v0.3 +22
- ruff：clean
- 新代码：~370 行（lexical_index.py） + ~310 行（CLI BM25 路径与 index 子命令） +
  14KB 测试

## 仍然不做

- ❌ 真实 LLM
- ❌ `.env` 内容读取
- ❌ embedding / 向量库 / RAG
- ❌ 远程检索 / 上传索引
- ❌ 索引 raw source / Source Excerpt / Human Note
- ❌ 自动 approve
- ❌ 修改原始 source 或卡片正文
- ❌ Obsidian 插件 / 浏览器插件 / GUI
- ❌ 自动复习调度
- ❌ 中文分词（jieba 等） — v0.3 故意用单字切分以避免引入分词模型

## 下一步候选

1. **v0.3.1**：把 BM25 字段权重移到 `mindforge.yaml`，让用户调
2. **v0.3.2**：`mindforge recall --hybrid` 把 BM25 和 review_after / value_score
   做加权组合（仍是规则，仍非 ML）
3. **v0.4**：复习调度算法（SM-2 / FSRS）— 但仍然纯本地、不调 LLM
4. **不**建议优先级：embedding / 向量库 / Obsidian 插件 / OCR — 极易过度工程
