# MindForge 首次发布说明

> **范围**：v0.1 本地 MVP。本文描述了首个面向用户的本地 MVP 范围。它不是下一版本的 RFC 或 SDD，也不代表当前 v4.x 的能力。

## 已包含功能

- 通过 `mindforge init`、`mindforge start` 和 `mindforge status` 进行本地 workspace 初始化。
- Web Setup 作为主要模型配置入口。
- 面向本地 Markdown 资料的 LLM-first 知识卡片工作流。
- 生成 `ai_draft` 后由人工显式审批。
- Library、BM25 Recall 和 Wiki 仅从 `human_approved` 卡片生成。
- LLM-first Wiki 合成，保留 deterministic/template rebuild 作为高级/故障排查回退方案。
- 有界 provider 超时/重试行为，以及模型调用的可见运行进度。
- 基于 workspace 的配置和密钥查找，支持 CLI 和 Web 路径。

## 安全边界

- API key 通过 Web Setup 输入并存储在本地 secret store 中。
- API key 不得提交到版本控制、粘贴到文档或写入 YAML。
- 原始 source 文件未经显式审批不会晋升到 Library / Recall / Wiki。
- 不存在自动审批路径。
- 本版本不包含 RAG、embedding、向量数据库、语义合并、Obsidian 插件或真实的 Obsidian 正式笔记写入功能。

## 已知限制

- 请先使用非敏感资料；不要从私人或工作敏感 vault 开始。
- 长文档可能需要拆分处理，或使用更高的 `timeout_seconds`。
- 大目录处理可能需要较长时间；使用 `mindforge runs show <run_id>` 查看当前进度。
- 完整的逐 source 进度 UI、部分成功 UI 以及 source 级别重试 UX 属于未来工作。
- 高级配置文件供维护者和部署参考使用，普通用户应使用 workspace + Web Setup。

## 未来工作

- 长文档分块处理并保留来源追溯。
- 逐 source 进度元数据和更清晰的部分成功 UI。
- Source 级别重试 UX。
- 经过单独设计评审后的 RAG / embedding / 语义合并。
- 经过单独安全设计和显式授权后的 Obsidian 插件或正式笔记写入。
