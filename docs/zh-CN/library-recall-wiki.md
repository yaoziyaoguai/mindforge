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

## Wiki / Topic View

Wiki 页面已从 LLM synthesis 迁移为**运行时 Topic View**（v0.5）。按 topic 聚合 `human_approved` cards 直接展示，无需手动触发合成。

### 浏览

```bash
mindforge wiki status            # 查看 Topic View 状态
mindforge wiki show              # 查看 Topic View 内容
```

也可以直接打开 Web **Wiki** 页面浏览 Topic View。Generate Wiki 已在 v0.5 废弃。

### 工作原理

- Topic View 只展示 `human_approved` cards，按 topic 聚合
- 纯运行时视图，直接从已审批卡片构建，不调用 LLM
- 不生成合成文本，不绕过审批
- LLM-based Wiki synthesis（`llm_rebuild_wiki`）已在 v0.5 废弃

### 配置

```yaml
wiki:
  enabled: true
  auto_rebuild_on_approve: false  # 已废弃 — v0.5+ 不再使用
```

---

## 三者关系

```
Approved Cards ──→ Library (浏览)
               ├──→ Recall (BM25 检索)
               └──→ Wiki (Topic View，运行时视图)
```

Library、Recall 和 Topic View 均为实时查询，直接反映已审批卡片状态，无需手动触发更新。

Related cards 和 Local Graph Preview 使用 source、tag、wiki section、review batch 等确定性关系展示局部导航；它们不使用 embedding、Vector DB、Graph DB，也不是 GraphRAG。
