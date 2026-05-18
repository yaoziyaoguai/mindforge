# Library / Recall / Wiki

已审批知识卡片的浏览、检索和组织。

---

## Library

浏览已审批的知识卡片。**Library 只显示 `human_approved` 卡片**，不显示 `ai_draft`、`pending_review` 等未审批状态。审阅未审批卡片请使用 [Review](review.md)。

```bash
mindforge library list           # 列出所有已审批卡片
mindforge library show <ref>     # 查看单张卡片详情
```

也可以在 Web **Library** 页面浏览。

---

## Recall

本地 BM25 词法检索：

```bash
mindforge recall --query "关键词"
```

当前基于 BM25 词法匹配，不做语义检索。不支持 RAG、embedding、向量数据库。

---

## Knowledge Health

```bash
mindforge health
```

Knowledge Health 是只读维护报告，用于检查 review backlog、低质量卡片、缺少 provenance、重复候选、孤立卡片、stale wiki 等，并给出建议。它不会自动修改卡片、source 或 Wiki。

---

## Wiki

基于所有 `human_approved` 卡片做 LLM-first synthesis，生成结构化 topic page。

### 生成

```bash
mindforge wiki status            # 查看 Wiki 状态
mindforge wiki rebuild           # LLM synthesis 重建
mindforge wiki show              # 查看 Wiki 内容
```

也可以在 Web **Wiki** 页面点击 **Generate Wiki**。

### 工作原理

- Wiki 只从 `human_approved` cards 生成
- LLM-first synthesis：调用 LLM 对已审批卡片做综合归纳和重写
- 不会绕过审批读取 raw source
- 必须手动触发，不会自动运行
- Approved cards 是 source of truth，Wiki 不是

### 配置

```yaml
wiki:
  mode: llm                 # LLM-first synthesis
  model: main               # 使用的 model id
  auto_rebuild_on_approve: false
```

---

## 三者关系

```
Approved Cards ──→ Library (浏览)
               ├──→ Recall (BM25 检索)
               └──→ Wiki (LLM synthesis)
```

Library 和 Recall 是实时查询，Wiki 需要手动 rebuild 才会更新。当新审批的卡片数量超过 Wiki 已有卡片数时，Wiki 状态栏会显示过期提醒（"New approved knowledge is available"），提示用户重建 Wiki。

Related cards 和 Local Graph Preview 使用 source、tag、wiki section、review batch 等确定性关系展示局部导航；它们不使用 embedding、Vector DB、Graph DB，也不是 GraphRAG。
