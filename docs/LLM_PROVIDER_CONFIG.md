# LLM Provider 配置指南

本文档解释 MindForge 的 LLM provider 抽象、三种 provider 类型的差异、
如何配置 `.env`、如何在 `configs/mindforge.yaml` 中切换 `active_profile`，
以及为什么"默认安全"和"日志/state 不记录原文"是硬约束。

> 阅读对象：本人（学习与复盘用）。所有命令默认在仓库根目录执行。

> **v0.13 Stage 1 起的安全契约升级**: 切换 `active_profile` 到非
> fake 之后, 真实 provider 路径仍然只能通过显式 opt-in 触发
> (`mindforge provider smoke --allow-real`); 真实 provider 输出永远
> 是 `ai_draft_preview`, 永远不会自动变成 `human_approved`, 永远不会
> 写入 vault。详见
> [LOCAL_FIRST_PRIVACY_CONTRACT.md](LOCAL_FIRST_PRIVACY_CONTRACT.md)
> 和 `mindforge provider readiness --help`。

---

## 1. 三种 Provider 类型

MindForge 在 `src/mindforge/llm/` 下维护三类 provider，由 `factory.build_providers()`
按 `mindforge.yaml` 中模型的 `type` 字段派发：

| type 字段 | 模块 | 协议 | 适用场景 |
|---|---|---|---|
| `fake` | `llm/fake.py` | 无（本地确定性 JSON） | **默认**：测试、CI、开发，离线、零成本、可重复 |
| `openai_compatible` | `llm/openai_compatible.py` | `POST {base_url}/chat/completions` | OpenAI、Ollama、LM Studio、vLLM、聚合网关 |
| `anthropic_compatible` | `llm/anthropic_compatible.py` | `POST {base_url}/v1/messages` | Anthropic Claude、阿里云 DashScope **Coding Plan** 等 |

**为什么三个 provider 类必须分开**：
- 协议不同（chat/completions vs messages）；
- 鉴权头不同（`Authorization: Bearer` vs `x-api-key` + `anthropic-version`）；
- 响应结构不同（`choices[0].message.content` vs `content[].text` 数组）；
- 错误脱敏粒度不同（每家服务回显的内容不同，要分别截断）。

混在一起会让"加新 provider"或"换 endpoint"反复污染同一个文件，违反 v0.1
"配置层面开放、执行层面克制"的原则。

---

## 2. 当前主路径：阿里云 DashScope Coding Plan（Anthropic-compatible）

我本地真实使用的是 **阿里云 DashScope Coding Plan**，它对外暴露 Anthropic
Messages API 协议，而**不是** OpenAI chat/completions。所以 MindForge v0.1
的真实 LLM 路径走的是 `anthropic_compatible` provider。

可用模型（仅作示例，平台支持的具体模型名以官方文档为准）：
- `qwen3-coder-plus`、`qwen3-coder-next`
- `glm-5`、`glm-4.7`
- `kimi-k2.5`
- `MiniMax-M2.5`
- 以及平台暴露的其他模型

**模型名只在 `configs/mindforge.yaml` 里出现**，业务代码里**绝不**硬编码模型名。

---

## 3. `.env` 与 `.env.example`

### 3.1 哪些变量

```bash
# ── Anthropic-compatible（v0.1 主路径）──
MINDFORGE_LLM_BASE_URL=""      # 不含末尾斜杠；provider 内部拼 /v1/messages
MINDFORGE_LLM_API_KEY=""       # 写到 x-api-key 头
MINDFORGE_LLM_VERSION="2023-06-01"  # 写到 anthropic-version 头

# ── OpenAI-compatible（备选）──
MINDFORGE_OPENAI_BASE_URL=""
MINDFORGE_OPENAI_API_KEY=""
```

### 3.2 安全约束

- `.env` 已在 `.gitignore` 里显式忽略（含 `.env.*` 通配，并保留 `.env.example` 例外）。
- `.env.example` 仅含变量名 + 中文注释，**不含**任何真实 key / endpoint。
- `mindforge.yaml` **不允许**直接写 `api_key` 或真实 `base_url`（必须用 `*_env` 引用）。
- `anthropic_compatible` provider 在工厂阶段强制要求 `api_key_env` 字段，
  否则启动时 fail-fast。

### 3.3 使用步骤

```bash
cp .env.example .env
# 编辑 .env，填入真实 base_url / api_key
# 不要 git add .env
```

### 3.4 自动加载（无需手动 `source .env`）

`src/mindforge/env_loader.py` 在每个 CLI 命令入口处自动加载 `.env`，
关键约束：

- **静默**：不打印任何 key/value 到 stdout/stderr；
- **`env > dotfile`**：已通过 `export` 设置的环境变量优先于 `.env`；
- **once-only**：进程内只加载一次；
- **零依赖**：不引入 `python-dotenv`，仅支持最简单的 `KEY=VALUE` 与 `KEY="quoted"` 语法；
- **路径**：从当前 cwd 向上查找最近的 `.env`，永不读 `~/.env`。

测试覆盖：`tests/test_env_loader.py` 验证不打印值、不覆盖已设 env、注释 / 空行容错。

### 3.5 模型名也可从 env 覆盖（`model_env`）

`mindforge.yaml` 中每个 model 支持可选 `model_env`：

```yaml
qwen_coder_strong:
  type: anthropic_compatible
  base_url_env: MINDFORGE_LLM_BASE_URL
  api_key_env: MINDFORGE_LLM_API_KEY
  model_env: MINDFORGE_LLM_MODEL_STRONG   # 优先级高于 model
  model: "qwen3-coder-plus"               # 兜底默认
```

用途：同一 endpoint 在 `qwen3-coder-plus` / `glm-5` / `kimi-k2.5` 等多模型间快速切，
无需改 yaml、无需 commit。

---

## 4. `configs/mindforge.yaml` 的 LLM 配置

LLM 配置是三层结构：

```
llm:
  active_profile  # 当前生效的 profile 名
  profiles        # 每个 profile = "stage → model_alias" 的静态映射
  models          # 每个 model_alias 的具体 provider/type/url/key 配置
```

### 4.1 默认 `active_profile: fake`（**安全默认**）

```yaml
llm:
  active_profile: fake
```

**为什么默认是 fake**：clone 仓库 / 安装依赖 / 第一次运行 `mindforge process` 时，
绝不应消耗真实配额、不应把私人笔记的 prompt 发往任何远端服务。fake provider
返回 schema-合规的占位 JSON，让管线跑通而不出门。

### 4.2 切换到真实主路径

```yaml
llm:
  active_profile: anthropic_coding_plan
```

切换前确认：
1. `.env` 已填写 `MINDFORGE_LLM_BASE_URL` 与 `MINDFORGE_LLM_API_KEY`；
2. 你已经 source `.env`（或用 `direnv` / `dotenv` 之类工具自动加载）；
3. 第一次执行建议加 `--file <某个测试笔记>` + `--limit 1` 做单文件 smoke test，
   而不是直接全库扫描。

### 4.3 模型路由示例

```yaml
profiles:
  anthropic_coding_plan:
    triage: qwen_coder_fast            # 低风险 / 高频 stage 用快模型
    distill: qwen_coder_strong         # 高价值 stage 用强模型
    link_suggestion: qwen_coder_fast
    review_questions: qwen_coder_strong
    action_extraction: qwen_coder_strong

models:
  qwen_coder_strong:
    provider: dashscope_coding_plan
    type: anthropic_compatible
    base_url_env: MINDFORGE_LLM_BASE_URL
    api_key_env: MINDFORGE_LLM_API_KEY
    version_env: MINDFORGE_LLM_VERSION
    model: qwen3-coder-plus
    timeout_seconds: 240
    max_retries: 2
```

**v0.1 不做**：fallback、多模型投票、按 `value_score` 动态切换、token-aware
routing。任何"智能路由"都违反 v0.1 的"执行层面克制"原则。

---

## 5. 日志与 state 的脱敏约束

### 5.1 `runs/*.jsonl` 字段白名单

`run_logger.py` 维护一份 `_ALLOWED_FIELDS` 白名单。任何尝试写入白名单之外
字段的 emit 都会被丢弃。每条 `llm_call` 事件**只**包含：

```
stage / model_alias / provider / provider_type / actual_model /
prompt_version / input_file_hash / status / error_message /
tokens_in / tokens_out / latency_ms
```

### 5.2 严格禁止出现在日志中的内容

- `api_key`、`Authorization` header、`x-api-key` header
- `.env` 文件原文
- `raw_text`（任何源文件的原文片段）
- `prompt` 全文（即便已渲染过模板）
- `completion` 全文（LLM 返回的原始文本）
- HTTP request body 与 response body
- 任何"看起来像 token / key 的字符串"

### 5.3 实现要点

- `LLMResult.raw` 设计上永远等于 `None`，避免写卡或写日志时把响应体带出来。
- `ProviderError(network)` 只输出异常**类名**，不携带原始 message
  （某些 HTTP 库会把 url / headers / body 塞进异常 message）。
- `ProviderError(http_4xx)` 截断响应体到 300 字符并去换行。
- `tests/test_m2_hardening.py` 端到端验证：源文件含 `SECRET-PROMPT-TOKEN`、
  fake provider 输出含 `SECRET-COMPLETION-TOKEN`，二者**都**不允许出现在
  `runs/*.jsonl` 任何字符位置。

### 5.4 `state.json` 里也只存路由元数据

`ItemState.stages.<stage>` 仅含 `model_alias / provider / actual_model /
prompt_version / status / processed_at / error_message / tokens_*`，
**不含** prompt、completion、raw_text、api_key。

---

## 6. 单文件真实 smoke test 计划

### 6.1 第一步：`mindforge llm ping`（不发 HTTP，只校验 env）

```bash
mindforge llm ping --profile anthropic_coding_plan
```

该命令枚举 `active_profile` 涉及的所有 model alias，列出每个模型的：
- `provider` / `type` / `model (resolved)`（含 `model_env` 覆盖后的实际值）
- 每个所需 env 是否已 set（仅显示 `set` / `MISSING` / `unset (optional)`，**绝不**打印 value）

退出码：必填 env 全齐 → `0`；缺任一必填 → `1`。
**不发任何 HTTP 请求**，不消耗配额。`tests/test_cli_extras.py` 用 `httpx.Client.post` mock 验证。

### 6.2 第二步：`--dry-run` 跑通 pipeline 但不写卡片

```bash
mindforge process \
  --profile anthropic_coding_plan \
  --file vault/00-Inbox/ManualNotes/<test-note>.md \
  --limit 1 \
  --dry-run
```

预期：5 stage 全部调用真实 endpoint；卡片**不**写出；`state.json` **不**写入；
`runs/<run_id>.jsonl` 仍记录全部事件供审计。

### 6.3 第三步：去掉 `--dry-run`，正式落地一张卡片

预期产物：
- `vault/20-Knowledge-Cards/<track>/<date>--<slug>.md`（默认 `status: ai_draft`）
- `.mindforge/state.json`：该 item.status=processed，5 个 stage 全 ok
- `.mindforge/runs/<run_id>.jsonl`：5 条 `llm_call`，每条 `provider_type: anthropic_compatible`，**不**含 prompt/completion/key/raw_text

执行完后必须人工：
- 检查 `.mindforge/runs/<run_id>.jsonl` 没有任何敏感字段；
- 检查生成的卡片 frontmatter 字段齐全；
- 决定是否把 `status` 改为 `human_approved`（v0.1 不做自动晋升）。

### 6.4 M2.8 真实 smoke 已验证（执行记录）

第一次以 `anthropic_coding_plan` profile 跑通了一份**非敏感**测试材料
（人工撰写、内容关于 ReAct loop checkpoint 设计），完整记录如下：

- **沙箱目录**：`/tmp/mindforge-smoke-m28/`（vault + `.mindforge/` 都在 /tmp，**绝不**碰真实 vault；本仓库 `.gitignore` 也保证 `.mindforge/` 不会被误提交）
- **配置**：临时 `mindforge.smoke.yaml`（基于 repo 内 `configs/mindforge.yaml`，仅改 `vault.root` 与 `state.workdir` 指到 `/tmp`），**不**入库
- **三步链路**：
  1. `mindforge llm ping --profile anthropic_coding_plan` → 所需 env 全部 set，**不发 HTTP**
  2. `mindforge process --profile anthropic_coding_plan --dry-run --limit 1 -c <smoke.yaml>` → 5 stage 全部走真实 endpoint，**不**写卡片，**不**写 state，仅 runs jsonl 留痕
  3. `mindforge process --profile anthropic_coding_plan --limit 1 -c <smoke.yaml>` → 写出 1 张 `status: ai_draft` 卡片到 `vault/20-Knowledge-Cards/agent-runtime/`
- **审计结果**：
  - source 文件 md5 前后不变（**只读**约束生效）
  - state.json 仅含路由元数据；`stages` 子结构含全部 5 个 stage
  - runs `*.jsonl` 仅 10 行，每条 `llm_call` 仅含白名单字段；grep `api_key` / `Authorization` / `x-api-key` / `Bearer` / `sk-` / `prompt_text` / `completion` / `raw_text` **全部为 0**
  - 卡片 frontmatter 完整：`source_id` / `source_type` / `adapter_name` / `prompt_version` / `profile` / `stage_models` / `run_id` / `value_score` / `confidence` 齐全

**安全边界**（M2.8 仅做单文件 smoke，不批量、不进真实 vault）：
- ✅ 测试材料是手工撰写的非敏感公开内容；
- ✅ vault 与 state 都在 `/tmp`，与个人 Obsidian vault 隔离；
- ✅ `.env` 全程未被 cat / 打印 / commit；
- ✅ 真实 endpoint 调用次数 ≤ 5（一次完整 pipeline）；
- ❌ **不要**用此流程批量处理真实 Cubox 收藏 / 工作文档 — 那是 M3+ 的事。

---

## 7. 常见错误与对策

| 现象 | 可能原因 | 对策 |
|---|---|---|
| `模型 X 必须声明 api_key_env` | yaml 写了 anthropic_compatible 但缺 `api_key_env` | 改 yaml，加 `api_key_env: MINDFORGE_LLM_API_KEY` |
| `模型 X 要求环境变量 ... 提供 api_key，但未设置或为空` | `.env` 没加载 / 变量名拼错 | 跑 `mindforge llm ping`，看哪个 env `MISSING` |
| `HTTP 401` / `HTTP 403` | api_key 错 / 过期 | 不要把 key 发给我；自己回 DashScope 后台核对 |
| `响应缺少 content[].text 文本块` | 模型返回了 tool_use 但没有 text block | v0.1 不做 tool use；换模型或在 prompt 里禁掉 tool_use |
| ruff/pytest 失败 | 环境未装好 | `pip install -e . --no-deps` 后再跑 |

---

## 8. 反模式（**不要**这样做）

- ❌ 把真实 api_key 写进 `mindforge.yaml`、`.env.example`、commit message、issue、聊天记录；
- ❌ 在业务代码（`processors/`、`writer.py`、`cli.py`）里 `if provider_type == "anthropic_compatible": ...` 这类分支 — 协议差异必须收敛在 provider 层；
- ❌ 把 `LLMResult.raw` 写进 `runs/*.jsonl`；
- ❌ 把渲染后的 prompt 或 LLM 返回文本作为 `error_message`；
- ❌ 在默认 `active_profile` 上挂真实模型 — 默认必须是 fake。
