# v4.9 MindForge-on-MindForge Project Knowledge Dogfood — Implementation Notes

**日期**: 2026-05-26
**状态**: complete
**基于**: `/mf-autopilot` v4.9 指令
**参考**: `docs/dogfood/2026-05-26-mindforge-on-mindforge-dogfood-report.md`

---

## 执行摘要

用 MindForge 仓库内 30 个非敏感项目文档作为 source material，通过 fake provider 完成完整主路径验证。30/30 文档成功通过 Source → ai_draft → human_approved → Library → Recall → Wiki 全路径。安全边界 intact。

**关键发现**: Fake provider 对真实项目文档的内容提取严重受限（Recall 4/10 vs synthetic dogfood 10/10），准确量化了 fake → real LLM 的质量差距。

---

## 执行步骤

### Step 1: Workspace 创建

隔离 workspace: `.tmp/mindforge_project_dogfood/`

```
.tmp/mindforge_project_dogfood/
├── dogfood.yaml          # 隔离 dogfood 配置
├── vault/
│   ├── 00-Inbox/         # 30 个 repo docs
│   └── 20-Knowledge-Cards/ # 生成的 ai_draft → human_approved cards
└── state/                # 运行时状态、索引
```

### Step 2: Source 选择

从 8 个类别选择 30 个 canonical repo docs（详见 dogfood report）。选择原则：
- 优先当前 canonical docs（README、architecture、quality-debt-ledger）
- 包含当前能力/审计/路线图
- 包含近期 implementation notes（反映当前真实状态）
- 包含中英文用户指南
- 不包含 .env、secrets、私人数据

### Step 3: Pipeline 执行

```bash
# Scan → 30 files detected, 0 failures
python -m mindforge scan --config dogfood.yaml

# Process → 30/30 ai_draft generated
python -m mindforge process --config dogfood.yaml

# Safety boundary check → library empty (no auto-approve)

# Approve → 30/30 human_approved
python -m mindforge approve --all --confirm --config dogfood.yaml

# Library → 30 cards visible
python -m mindforge library list --config dogfood.yaml

# Index rebuild → bm25.json, 30 cards
python -m mindforge index rebuild --config dogfood.yaml

# Wiki rebuild → 30 cards included
python -m mindforge wiki rebuild --config dogfood.yaml
```

### Step 4: Recall 验证

10 个 project knowledge 查询，4/10 命中 (40%)。

根因：fake provider 只从文件名提取关键词，不读取文档实际内容。

### Step 5: Export

`mindforge export` CLI 命令不存在（known limitation）。Export 通过 Web API。

---

## 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| `docs/dogfood/2026-05-26-mindforge-on-mindforge-dogfood-report.md` | NEW | v4.9 dogfood report |
| `docs/implementation-notes/2026-05-26-103-v4_9-mindforge-on-mindforge-dogfood.md` | NEW | 本笔记 |
| `.tmp/mindforge_project_dogfood/` | NEW | 隔离 dogfood workspace（不提交） |

`.tmp/` 目录在 `.gitignore` 中，运行时数据不提交。仅 report 和 notes 提交到 repo。

---

## 与 Synthetic Dogfood 的关键差异

| 维度 | Synthetic (v4.2) | Project Doc (v4.9) |
|------|------------------|--------------------|
| Source 数量 | 30-80 synthetic | 30 real repo docs |
| Source 类型 | 生成的技术笔记 | 项目文档 |
| 文件名语义 | 高（Python, Docker...） | 低（03-architecture...） |
| ai_draft 生成 | 30/30 | 30/30 |
| 卡片内容质量 | [fake] 占位符 | [fake] 占位符 |
| Recall 命中率 | 10/10 (100%) | 4/10 (40%) |
| 根因 | 文件名即关键词 | 文件名非完整关键词 |

**核心洞察**: Fake provider 的内容质量上限由源文件名决定。Synthetic samples 的文件名本身就是关键词（`python-async-io-notes.md`），而真实项目文档的文件名不携带完整语义（`03-architecture.md`）。

---

## Fake Provider 限制分析

当前 fake provider 的 `_extract_keywords()` 逻辑：
1. 从文件名提取单词（split by `-`、`_`、`.`）
2. 用这些单词填充 tags、summary、inference、principles
3. 不读取源文件实际内容

这对 pipeline 验证是足够的，但对知识提取是无意义的。

### 改进方向（非本次范围）

若要提升 fake provider 对项目文档的 recall 支持：
1. 从 markdown 标题（`#`、`##`）提取关键词
2. 从 frontmatter 提取 title/tags
3. 从文档前 500 字符提取高频词

但这些改进不应在本次 dogfood loop 中做 — fake provider 的核心价值是 pipeline 验证，不是内容理解。

---

## 安全确认

- 零网络请求 / 零 API key
- 零真实私人资料
- 零 Obsidian vault 写入
- Fake provider 确定性输出
- 不做 RAG / embedding / vector DB
- 显式审批语义 intact
- 所有数据写入 `.tmp/` 隔离目录
- 不恢复 Graph/Sensemaking/Entity/Community 扩张

---

## Gate 结果

| Gate | Command | Exit Code |
|------|---------|-----------|
| git diff --check | `git diff --check` | 0 |
| ruff | `ruff check src/ tests/ docs/` | 0 |
| npm build | `npm --prefix web run build` | 0 |
| pytest (full) | `python -m pytest tests/ -q --tb=short` | 0 (1 skip, pre-existing) |

---

## 下一步

1. **v4.9 Loop 2 (可选)**: 改进 fake provider 关键词提取，提升 project doc recall
2. **v4.10 (推荐)**: Real LLM opt-in dogfood — 同 30 个源文档，真实模型处理，对比 fake vs real
3. **v5.0**: 基于完整 dogfood evidence 规划下一阶段

---

## 不在此次范围

- 不改进 fake provider 内容提取
- 不调用真实 LLM
- 不恢复 Graph/Sensemaking/Entity/Community 扩张
- 不做 RAG/embedding/vector DB
- 不新增 CLI export 命令
- 不修改 approval 语义
