# LLM Provider Configuration

本文档说明 MindForge 当前 LLM 模型配置体系。推荐通过 Web Setup 配置模型，
CLI 用于高级诊断。

完整示例配置参考：`configs/mindforge_example.yaml`

---

## 当前主配置格式

MindForge 使用 `llm.models` / `llm.default_model` / `llm.routing` 三层模型配置：

```yaml
llm:
  default_model: main

  models:
    main:
      type: anthropic_compatible
      base_url: https://your-endpoint.example.com/anthropic
      model: your-model-name
      timeout_seconds: 120
      max_retries: 1

  routing:
    triage: main
    distill: main
    link_suggestion: main
    review_questions: main
    action_extraction: main

wiki:
  mode: llm  # LLM-first synthesis（推荐）；Troubleshooting 回退用 deterministic
  model: main
  auto_rebuild_on_approve: false
```

### 语义

| 字段 | 说明 |
|------|------|
| `llm.models` | 用户配置的可用模型池，每个 model id 对应一个 endpoint + 协议 + 模型名 |
| `llm.default_model` | 所有 workflow step 默认使用的模型 |
| `llm.routing` | 可选，workflow step → model id。省略时全部使用 default_model |
| `timeout_seconds` | 单次 provider HTTP request timeout；省略时使用运行时默认值，不限制整个 import/watch run |
| `max_retries` | 单次 provider call 的有限 retry 次数；省略时使用运行时默认值，不做 run-level 无限重试 |
| routing 部分缺失 | 缺失 step fallback 到 default_model |
| `wiki.model` | Wiki LLM synthesis 使用的 model id；必须引用 `llm.models` |
| `wiki.auto_rebuild_on_approve` | 默认 false。开启后会在 approve 时自动触发 Wiki 重建（使用 `wiki.mode` 指定的方式，LLM synthesis 需要已配置模型和 API key）。不开启时 Wiki 需在 Web Wiki 页面或 CLI 手动触发 |

---

## 通过 Web Setup 配置（推荐）

普通用户通过 **Web Setup** 页面配置模型，不需要手写 YAML：

1. 启动 `mindforge web`，打开 Setup 页面
2. 在 **Configured models** 区域点击 **\+ Add model**
3. 填写：
   - **Model id**: 模型别名，如 `main`、`claude`
   - **Type**: `anthropic` / `anthropic_compatible` / `openai` / `openai_compatible`
   - **Base URL**: 模型 endpoint
   - **Model**: 模型名
   - **API key**: 输入你的真实 key
4. 保存

Web Setup 还支持：
- **Default model** 选择
- **Processing Workflow** 中每个 step 的模型分配
- **Wiki generation mode / Wiki model** 配置；LLM synthesis 需要用户手动触发

如果默认端口已被占用，换一个端口启动，避免误操作旧 server：

```bash
mindforge web --port 8766 --open
```

端口被占用时，CLI 会先失败并提示换端口，不会先打开浏览器。

---

## 支持的模型类型

| Type | 协议 | 适用场景 |
|------|------|---------|
| `anthropic` | 原生 Anthropic Messages API | 直接使用 Anthropic Claude |
| `anthropic_compatible` | 兼容 Anthropic 协议 | DashScope、OpenRouter 等 |
| `openai` | OpenAI 官方 Chat Completions API | 直接使用 OpenAI（默认 `https://api.openai.com/v1`） |
| `openai_compatible` | 兼容 OpenAI Chat Completions 协议 | Ollama、LM Studio、vLLM、DeepSeek、聚合网关等 |

Local 模型（Ollama、LM Studio 等）通过 `openai_compatible` + `api_key_optional: true` 配置。

---

## API Key 存储

### 推荐路径：本地 Secret Store

通过 Web Setup 输入的 API key 写入 **本地 secret store**：

- 路径：`.mindforge/secrets.json`
- 已被 `.gitignore` 中 `.mindforge/` 规则覆盖
- API key **不写入 YAML config**
- `configs/mindforge.yaml` 是本地 runtime config，已 gitignore，不应提交
- Web API **只返回 masked 值**（如 `sk-****abcd`）
- Provider runtime 优先从 secret store 取 key；部署场景可通过外部进程注入 key

### Advanced deployment fallback

普通用户不需要配置此路径。自动化部署或 CI 如需把 key 注入运行进程，应
保持 API key 不进入 YAML、不进入 Git，并以 Web Setup / local secret store
作为本地使用的默认路径。

Web Setup 普通保存不会写出 legacy key/base URL/model indirection 字段。

---

## Provider Types

MindForge 在 `src/mindforge/llm/` 下维护 provider：

| type 字段 | 模块 | 协议 | 适用场景 |
|---|---|---|---|
| `openai` | `llm/openai_compatible.py` | `POST /chat/completions` | OpenAI 官方 API |
| `openai_compatible` | `llm/openai_compatible.py` | `POST /chat/completions` | Ollama、vLLM、聚合网关 |
| `anthropic` | `llm/anthropic_compatible.py` | `POST /v1/messages` | Anthropic 官方 API |
| `anthropic_compatible` | `llm/anthropic_compatible.py` | `POST /v1/messages` | DashScope、OpenRouter 等 |

三个 provider 分开的原因：
- 协议不同（chat/completions vs messages）
- 鉴权头不同（`Authorization: Bearer` vs `x-api-key` + `anthropic-version`）
- 响应结构不同（`choices[0].message.content` vs `content[].text`）

---

## Model Routing 语义

`llm.routing` 是 workflow step → model id 映射：

- routing key 必须是合法 workflow step（triage / distill / link_suggestion / review_questions / action_extraction）
- routing value 必须是 `llm.models` 中已配置的 model id
- 缺失的 step fallback 到 `llm.default_model`
- routing 是第一阶段唯一用户可见的模型分配方式

---

## Processing Workflow

当前 Knowledge Card Workflow 固定五段：

| Step | 中文 | 说明 |
|------|------|------|
| Triage | 初筛 | 评估 source value，给出 track / value_score |
| Distill | 提炼 | 提取核心知识，生成卡片主体 |
| Link Suggestion | 关联建议 | 建议相关主题和链接 |
| Review Questions | 复习问题 | 生成复习和自测问题 |
| Action Extraction | 行动项提取 | 提取可跟进 action items |

每个 step 可分配不同模型。Web Setup 的 Processing Workflow 区域可查看每个 step 的 prompt 和模型配置。

---

## 安全边界

| 原则 | 实现 |
|------|------|
| API key 不进 YAML | Web 保存不写 api_key 字段；raw key 只在 secret store |
| API key 不进 Git | `.mindforge/` 已 gitignore；不要提交任何本地 secret 文件 |
| API key 不进前端 | API response 只返回 masked key |
| Provider 不打印 key | 错误消息不包含 raw key |
| 首次启动不调真实 LLM | `llm.default_model: null` / `llm.models: {}` 可启动 Web Setup |
| 真实 LLM 必须 opt-in | 需配置真实模型 + API key + 显式触发 watch/import/process 或 Wiki LLM rebuild |

---

## Safety: Logs and State

`run_logger.py` 维护白名单。每条 `llm_call` 事件**只**包含：

```
stage / model_alias / provider / provider_type / actual_model /
prompt_version / input_file_hash / status / error_message /
tokens_in / tokens_out / latency_ms
```

**绝不出现在日志中**：
- `api_key`、`Authorization` header、`x-api-key` header
- prompt 全文、completion 全文
- source raw text
- HTTP request/response body

---

## Legacy 配置兼容

旧配置仍尽量只读兼容，但普通用户不需要学习旧字段。推荐迁移路径：

1. 备份旧 `configs/mindforge.yaml`
2. 启动 Web Setup
3. 按当前 UI 保存一次模型、default model、routing 和 wiki 设置
4. 确认 API key 只进入 local secret store

---

## Common Errors

| 现象 | 原因 | 对策 |
|------|------|------|
| 模型无法生成 draft | 缺少 API key | 在 Web Setup 中为该 model 添加 API key |
| `Provider failure` | Provider 构建失败 | 检查 Web Setup 中模型的 type / base_url / model |
| `HTTP 401/403` | API key 错误/过期 | 回到对应平台检查 key 状态 |
| ruff/pytest 失败 | 环境未装好 | `pip install -e .` |

---

## Anti-Patterns

- ❌ 把 API key 写进 YAML config、commit message、issue 或聊天记录
- ❌ 在业务代码中 `if provider_type == ...` 分支 —— 协议差异必须收敛在 provider 层
- ❌ 把测试替身或历史配置兼容字段重新写成普通用户主路径
- ❌ 把 prompt 全文或 LLM 返回文本作为 `error_message`
