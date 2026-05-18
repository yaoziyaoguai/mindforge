# 快速入门

MindForge 安装、初始化和首次使用指南。

---

## 环境要求

- Python 3.11+
- pip
- 一个可用的 LLM API key（Anthropic、OpenAI 或兼容协议）

---

## 安装

```bash
git clone https://github.com/yaoziyaoguai/mindforge.git
cd mindforge
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

验证安装：

```bash
mindforge version
```

---

## 初始化 Workspace

Workspace 是 MindForge 的工作目录，包含 vault（知识库）和本地 runtime config。

```bash
# 创建并进入一个目录作为 workspace
mkdir -p ~/mindforge-workspace
cd ~/mindforge-workspace

# 初始化
mindforge init
```

`mindforge init` 创建 vault 骨架和本地 config。init 完成后会自动记住 workspace 路径，之后在任意目录运行 MindForge 命令都会自动找到它。

查看状态：

```bash
mindforge start     # 查看 first-run checklist
mindforge status    # workspace / vault / draft 状态
```

---

## 配置模型

MindForge 需要 LLM 模型才能生成知识卡片和 Wiki。

```bash
mindforge web --open
```

浏览器打开 `http://127.0.0.1:8765`：

1. 进入 **Setup** 页面
2. 点击 **Add model**
3. 填写：
   - **Model id**：模型别名，如 `main`
   - **Type**：`anthropic` / `anthropic_compatible` / `openai` / `openai_compatible`
   - **Base URL**：模型 endpoint
   - **Model**：模型名
   - **API key**：你的真实 API key
4. 保存

API key 存入本地 secret store（`.mindforge/secrets.json`），不进 Git、不进 YAML、不进前端。

### 支持的模型类型

| Type | 协议 | 适用场景 |
|------|------|---------|
| `anthropic` | Anthropic Messages API | 直接使用 Anthropic Claude |
| `anthropic_compatible` | 兼容 Anthropic 协议 | DashScope、OpenRouter 等 |
| `openai` | OpenAI Chat Completions API | 直接使用 OpenAI |
| `openai_compatible` | 兼容 OpenAI Chat Completions 协议 | Ollama、LM Studio、DeepSeek、聚合网关等 |

本地模型（Ollama、LM Studio 等）使用 `openai_compatible` + `api_key_optional: true`。

详细配置说明见 [模型配置](model-setup.md)。

---

## 添加第一个 Source

Source 是你想让 AI 处理的本地文件。放在 `vault/00-Inbox/` 下即可：

```bash
printf '# 第一篇笔记\n\n这是 MindForge 的测试笔记。\n' > vault/00-Inbox/first-note.md
mindforge watch add vault/00-Inbox/first-note.md
```

`watch add` 注册 source 并启动后台处理。处理完成后，AI 生成的草稿会出现在 Review 页面。

也可以一次性导入（不持续监听）：

```bash
mindforge import vault/00-Inbox/first-note.md
```

### 支持的格式

Markdown（`.md`）、TXT（`.txt`）、HTML（`.html`）、DOCX（`.docx`）、PDF 文本型（`.pdf`）。旧版 `.doc` 格式不支持。

### 路径规则

- **Web Add Source** 必须使用绝对路径
- **CLI** 支持相对路径，自动解析为绝对路径

---

## 查看处理进度

```bash
mindforge runs list                # 列出所有处理 run
mindforge runs show <run_id>       # 查看 run 详情
```

真实模型处理可能需要几分钟，`running` 不一定是卡死。

如果模型未配置，run 会失败并提示去 Web Setup 添加 API key。

---

## 审批知识卡片

AI 生成的是 `ai_draft`（草稿），必须显式审批才能成为 `human_approved`（正式知识）。

```bash
mindforge approve list                  # 列出待审批草稿
mindforge approve show --card 1 --show-content  # 查看草稿内容
mindforge approve 1 --confirm           # 显式审批
```

也可以在 Web **Review** 页面查看草稿并点击 **Approve** 审批。

**注意：审批永远是显式确认。没有自动 approve。**

---

## 浏览与检索

```bash
mindforge library list           # 浏览已审批知识库
mindforge library show <ref>     # 查看单张卡片详情
mindforge recall --query "关键词"  # BM25 词法检索
mindforge health                 # 只读生成 Knowledge Health 报告
```

Knowledge Health 会检查 review backlog、低质量卡片、缺少 provenance、重复候选、孤立卡片、stale wiki 等，只给维护建议，不自动修改内容。

---

## 生成 Wiki

Wiki 基于所有 `human_approved` 卡片做 LLM-first synthesis，生成结构化 topic page。

```bash
mindforge wiki status
mindforge wiki rebuild
mindforge wiki show
```

也可以在 Web **Wiki** 页面点击 **Generate Wiki** 触发。

Wiki 只从 approved cards 生成，不绕过审批。LLM synthesis 必须手动触发，不会自动运行。

Library / Wiki 中的 Related cards 和 Local Graph Preview 使用 source、tag、wiki section、review batch 等确定性关系展示局部导航；它不是向量数据库，也不是 GraphRAG。

---

## 下一步

- [用户指南](user-guide.md) — 完整功能说明
- [模型配置](model-setup.md) — LLM provider 配置详解
- [README](../../README.md) — 中文主入口
