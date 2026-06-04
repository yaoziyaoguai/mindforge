# MindForge 产品边界与安全契约

> **开发者与 Agent 指令**：本文定义了 MindForge 的关键产品边界、安全规则和架构不变量。任何验证"产品定位"或"安全约束"的测试都应该对照本文档，而不是历史内部账本。

## 1. 核心工作流与状态转换

- **ai_draft 与 human_approved**：AI 只能提出草稿（`ai_draft`）。它不能直接写入永久知识库（`human_approved`）。
- **必须显式审批**：人类**必须**在每条 `ai_draft` 变为 `human_approved` 之前显式审阅和审批。不存在"自动审批"或"批量审批"绕过此审阅。

## 2. Provider 安全

- **Fake Provider 默认**：开箱即用状态下，系统使用安全的 "fake"（dogfood/mock）provider。这确保不会意外发起网络调用。
- **真实 LLM 显式 opt-in**：连接真实 LLM 需要显式 opt-in（例如在本地 secret store 中提供 API key）和用户配置。

## 3. 数据摄入与导出

- **Source Adapter 与 Provider 的职责分离**：
  - `SourceAdapter`（如 Cubox、本地文件）仅用于**读取**原始输入。
  - `Provider`（如 LLM）仅用于**处理**数据。
- **安全导出副本，不写真实 Obsidian**：MindForge 将导出 staged 为"安全副本"（例如到 `vault_template` 或隔离的 staging 目录）。它**不会**直接写入用户真实的 Obsidian vault，以防止意外数据损坏。

## 4. 架构排除项（主路径非目标）

- **不做 RAG / Embedding / 向量数据库**：当前主路径依赖直接上下文传递、词法搜索（BM25）或显式引用。RAG 和向量数据库不是当前主路径的一部分。
- **Lab / Internal 功能**：如 **Graph**、**Sensemaking**、**Entity 提取**和 **Community 共享**等功能被视为实验性（"Lab"或内部）。它们不是主路径，不应干扰核心用户旅程。

## 5. Web 界面安全

- **API key 不写 YAML、不进 Git、不进前端**：API key 存储在本地 secret store 中（`.mindforge/secrets.json`）。
- **原始 source 和 API key 不泄露到 Web 前端或 telemetry**。
- **默认不联网**：全新工作区默认不调用真实 LLM/API，也不上传 telemetry；外部模型调用必须由用户显式配置 provider/API key 并主动触发。
