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

  routing:
    triage: main
    distill: main
    link_suggestion: main
    review_questions: main
    action_extraction: main
```

### 语义

| 字段 | 说明 |
|------|------|
| `llm.models` | 用户配置的可用模型池，每个 model id 对应一个 endpoint + 协议 + 模型名 |
| `llm.default_model` | 所有 workflow step 默认使用的模型 |
| `llm.routing` | 可选，workflow step → model id。省略时全部使用 default_model |
| routing 部分缺失 | 缺失 step fallback 到 default_model |

---

## 通过 Web Setup 配置（推荐）

普通用户通过 **Web Setup** 页面配置模型，不需要手写 YAML：

1. 启动 `mindforge web`，打开 Setup 页面
2. 在 **Configured models** 区域点击 **\+ Add model**
3. 填写：
   - **Model id**: 模型别名，如 `main`、`claude`
   - **Type**: `anthropic` / `anthropic_compatible` / `openai_compatible`
   - **Base URL**: 模型 endpoint
   - **Model**: 模型名
   - **API key**: 输入你的真实 key
4. 保存

Web Setup 还支持：
- **Default model** 选择
- **Processing Workflow** 中每个 step 的模型分配

---

## 支持的模型类型

| Type | 协议 | 适用场景 |
|------|------|---------|
| `anthropic` | 原生 Anthropic Messages API | 直接使用 Anthropic Claude |
| `anthropic_compatible` | 兼容 Anthropic 协议 | DashScope、OpenRouter 等 |
| `openai_compatible` | 兼容 OpenAI Chat Completions 协议 | OpenAI、Ollama、LM Studio、vLLM、DeepSeek 等 |

Local 模型（Ollama、LM Studio 等）通过 `openai_compatible` + `api_key_optional: true` 配置。

---

## API Key 存储

### 推荐路径：本地 Secret Store

通过 Web Setup 输入的 API key 写入 **本地 secret store**：

- 路径：`.mindforge/secrets.json`
- 已被 `.gitignore` 中 `.mindforge/` 规则覆盖
- API key **不写入 YAML config**
- Web API **只返回 masked 值**（如 `sk-****abcd`）
- Provider runtime 优先从 secret store 取 key，其次从环境变量 fallback

### 环境变量模式（Advanced / Legacy Compatible）

如果必须使用环境变量：

```bash
export MINDFORGE_LLM_API_KEY="<your-key>"
```

并在 YAML 中声明：

```yaml
models:
  main:
    type: anthropic_compatible
    base_url: https://example.com/anthropic
    model: your-model
    api_key_env: MINDFORGE_LLM_API_KEY   # env var name
```

**环境变量模式是 advanced/deployment 路径，不是普通用户推荐路径。**
Web Setup 普通保存不会写出 `api_key_env`、`base_url_env`、`model_env` 字段。

### 优先级

Provider runtime 解析 API key 的优先级：**env var > local secret store > missing**

---

## Provider Types

MindForge 在 `src/mindforge/llm/` 下维护三类 provider：

| type 字段 | 模块 | 协议 | 适用场景 |
|---|---|---|---|
| `fake` | `llm/fake.py` | 本地确定性 JSON | 测试、CI、开发（离线、零成本） |
| `openai_compatible` | `llm/openai_compatible.py` | `POST /chat/completions` | OpenAI、Ollama、vLLM、聚合网关 |
| `anthropic_compatible` | `llm/anthropic_compatible.py` | `POST /v1/messages` | Anthropic、DashScope 等 |

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
- routing 不叫 `stage_models`，不使用旧 `active_profile` / `profiles` 概念

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
| API key 不进 Git | `.env` + `.mindforge/` 均 gitignore |
| API key 不进前端 | API response 只返回 masked key |
| Provider 不打印 key | 错误消息不包含 raw key |
| 默认不调真实 LLM | fake provider 是默认（零成本、零网络） |
| 真实 LLM 必须 opt-in | 需配置真实模型 + API key + 显式触发 watch/import/process |

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

### 旧格式：active_profile / profiles

```yaml
llm:
  active_profile: my_profile
  profiles:
    my_profile:
      triage: alias_a
      distill: alias_a
```

此格式仍可**读取加载**，但新配置和新卡片使用 `llm.models` / `llm.default_model` / `llm.routing`。

### 迁移建议

1. 备份旧 `configs/mindforge.yaml`
2. 通过 Web Setup 保存一次配置 → 自动迁移为新格式
3. 或手动将 `profiles` + `models` 改为 `llm.models` + `llm.default_model` + 可选 `llm.routing`
4. 移除 `active_profile` 和 `profiles` 字段

### 旧字段对照

| 旧字段 | 新语义 |
|--------|--------|
| `llm.active_profile` | `llm.default_model`（default model id） |
| `llm.profiles` | 不再需要；改为 `llm.default_model` + `llm.routing` |
| `api_key_env` | 改为 local secret store |
| `base_url_env` | 改为直接在 model 中配置 `base_url` |
| `model_env` | 改为直接在 model 中配置 `model` |
| `stage_models` | replaced by `model_routing` in card provenance |

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
- ❌ 把 API key 写进 `.env.example`
- ❌ 在业务代码中 `if provider_type == ...` 分支 —— 协议差异必须收敛在 provider 层
- ❌ 默认 `active_profile` 挂真实模型 —— 默认应是 fake，真实模型需用户显式配置
- ❌ 把 prompt 全文或 LLM 返回文本作为 `error_message`
