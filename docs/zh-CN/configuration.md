# 配置参考

MindForge 配置体系说明。推荐通过 Web Setup 配置，CLI 用于高级诊断。

---

## Workspace 结构

```
<workspace>/
├── vault/                  # 本地知识库
│   └── 00-Inbox/           # Source 文件目录
├── .mindforge/             # 本地 runtime 数据（已 gitignore）
│   └── secrets.json        # API key 存储
└── configs/
    └── mindforge.yaml      # 本地 runtime config（已 gitignore）
```

---

## 模型配置

### llm.models

```yaml
llm:
  models:
    main:
      type: anthropic_compatible
      base_url: https://your-endpoint.example.com/anthropic
      model: your-model-name
      timeout_seconds: 120
      max_retries: 1
```

| 字段 | 说明 |
|------|------|
| `type` | `anthropic` / `anthropic_compatible` / `openai` / `openai_compatible` |
| `base_url` | 模型 endpoint |
| `model` | 模型名 |
| `timeout_seconds` | 单次 HTTP request timeout，默认 120s |
| `max_retries` | 单次 call 有限 retry 次数，默认 1 |

### llm.default_model

所有 workflow step 默认使用的模型。如 `main`。

### llm.routing

可选的 per-step 模型分配：

```yaml
llm:
  routing:
    triage: main
    distill: main
    link_suggestion: main
    review_questions: main
    action_extraction: main
```

缺失的 step fallback 到 default_model。

---

## Wiki 配置

```yaml
wiki:
  mode: llm                 # LLM-first synthesis（推荐）
  model: main               # 使用的 model id，必须引用 llm.models
  auto_rebuild_on_approve: false
```

| 字段 | 说明 |
|------|------|
| `mode` | `llm`（推荐）或 `deterministic`（troubleshooting 回退） |
| `model` | Wiki LLM synthesis 使用的 model id |
| `auto_rebuild_on_approve` | 默认 false。开启后 approve 时自动触发 Wiki 重建 |

---

## API Key 存储

通过 Web Setup 输入的 API key 写入本地 secret store：

- 路径：`.mindforge/secrets.json`
- 已被 `.gitignore` 覆盖
- API key 不写入 YAML config
- Web API 只返回 masked 值（如 `sk-****abcd`）

---

## 完整示例

参考 `configs/mindforge_example.yaml`。
