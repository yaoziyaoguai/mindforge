# 常见问题

---

## MindForge 是什么？

一个本地优先、LLM 优先的个人 AI 知识加工工具。把本地文件变成可审批的知识卡片，通过 LLM synthesis 将已审批知识组织成结构化 Wiki。

---

## MindForge 和 Obsidian 的关系？

MindForge 不是 Obsidian 插件。两者互补：

- **Obsidian**：笔记编辑和管理
- **MindForge**：AI 驱动的知识加工和 synthesis

MindForge 不写 Obsidian 笔记，不做 Obsidian plugin。未来可能提供 Obsidian staged export 工作流。

---

## 数据安全吗？

MindForge 是 local-first、single-user 工具：

- 数据都在本地 vault
- 不联网、不上传 telemetry
- API key 只存 local secret store，不进 Git
- 不做 RAG、不做 embedding、不连向量数据库

适合非敏感资料使用。暂不建议直接处理私人/工作敏感资料。

---

## 支持哪些 LLM？

| Type | 协议 |
|------|------|
| `anthropic` | Anthropic Messages API |
| `anthropic_compatible` | 兼容 Anthropic 协议（DashScope、OpenRouter 等） |
| `openai` | OpenAI Chat Completions API |
| `openai_compatible` | 兼容 OpenAI 协议（Ollama、LM Studio、DeepSeek 等） |

本地模型（Ollama、LM Studio）通过 `openai_compatible` + `api_key_optional: true` 使用。

---

## 会花多少钱？

取决于使用的模型和 source 数量。MindForge 只在以下场景调用模型：

- 处理 source 生成 draft（import / watch add / Process now）
- 重建 Wiki（wiki rebuild / Generate Wiki）

不会自动调用模型。不会在后台偷偷调用。不会在 approve 时自动重建 Wiki（除非开启 `auto_rebuild_on_approve`）。

---

## 为什么需要显式审批？

MindForge 的设计哲学：AI 生成的内容只是参考，人的判断是最终权威。

AI 生成 `ai_draft`（草稿），必须显式审批才能成为 `human_approved`（正式知识）。没有自动审批，没有隐藏审批。

---

## 支持自动审批吗？

不支持。这是设计决策，不是缺失功能。

---

## 支持中文吗？

支持。文档和 CLI 提示支持中文。

---

## 支持哪些文件格式？

Markdown（`.md`）、TXT（`.txt`）、HTML（`.html`）、DOCX（`.docx`）、PDF 文本型（`.pdf`）。旧版 `.doc` 不支持。

---

## 会做 RAG / embedding / 向量搜索吗？

当前不做，未来也不在规划内。当前检索是 BM25 词法匹配。

---

## 如何迁移到新版本？

1. 备份 workspace 目录
2. 更新 MindForge 代码（`git pull` + `pip install -e .`）
3. 重新初始化或按 release notes 操作
