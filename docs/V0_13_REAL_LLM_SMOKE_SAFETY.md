# v0.13 Stage 3 — Real LLM Smoke 安全工作流

本文档记录 `mindforge provider smoke` 真实 LLM 路径的端到端安全运行
方法, 以及 v0.13 Stage 1 → Stage 3 的修复轨迹。

## 1. 为什么 Stage 1 没有 end-to-end 跑通

Stage 1 报告中坦白:

> real-LLM smoke still not exercised end-to-end (no env in shell);
> helper coverage is stub-based via monkeypatch of factory.build_providers

Stage 3 审计发现两个真实根因, 不是 "shell 里没 env" 这么简单:

### 根因 A — provider 接口契约错配 (P1 bug)

Stage 1 的 `real_smoke.run_synthetic_real_smoke` 调用顺序是
`.complete → .chat → .generate(prompt: str)`。

但 `LLMProvider` ABC (`src/mindforge/llm/base.py`) 的真实契约是:

```python
def generate(self, request: LLMRequest) -> LLMResult: ...
```

任何真实 provider (`OpenAICompatibleProvider` /
`AnthropicCompatibleProvider`) 都只暴露这个方法, 且参数是
`LLMRequest` dataclass, 不是 `str`。

→ Stage 1 的 helper 永远走不到真实 provider 路径; 测试通过只是因为
test stub 实现了 `.complete(prompt: str)`, 与真实 provider 行为不符。

Stage 3 修复: 严格走 `provider.generate(LLMRequest(...)) -> LLMResult`,
返回值新增 `tokens_in` / `tokens_out` / `latency_ms` audit 字段;
`ProviderError` 单独捕获, 异常 message **不**回显, 避免 server 返回
信息 (例如 401 报文中的 hint) 意外泄漏。

### 根因 B — `.env` 注入未被 provider_cli 触发

`mindforge` 的标准 CLI 命令 (如 `llm ping` / `process` / `doctor`) 都
通过 `cli.py::_load_cfg` 调用 `load_dotenv_silently(Path.cwd())`, 把
仓库根 `.env` 中的 `MINDFORGE_LLM_API_KEY` 等注入 `os.environ`。

`provider_cli.py` 在 Stage 1 直接调用 `load_app_config(config)`, 跳过
了这一步。结果: 即使 `.env` 完整存在, `provider readiness` 与
`provider smoke` 也只能看到 shell `export` 的 env (通常为空)。

→ 这就是 "shell 里没 env" 的真正含义: 不是 .env 不存在, 而是
`provider_cli` 没有走标准的 .env 注入路径。

Stage 3 修复: `provider_cli` 新增 `_load_cfg_with_dotenv` 包装, 与
`cli.py::_load_cfg` 保持一致语义 (silent / non-overriding /
once-only / no third-party)。AST 守卫 `_PER_FILE_ALLOWLIST` 显式声明
`provider_cli.py` 允许 import `mindforge.env_loader` (但
`provider_readiness.py` / `real_smoke.py` 仍禁止)。

## 2. 安全工作流 (推荐顺序)

```bash
# 1) 检查当前 readiness — 不发请求, 不打印 secret value
.venv/bin/mindforge provider readiness --config configs/mindforge.yaml

# 2) 用 --profile 临时切换查看真实 profile 的 readiness
.venv/bin/mindforge provider readiness \
    --config configs/mindforge.yaml --format json
# (在 yaml 里把 active_profile 改成 anthropic_coding_plan 后再看)

# 3) 显式 opt-in 跑一次合成 smoke (会发一次真实请求, 计费!)
.venv/bin/mindforge provider smoke \
    --config configs/mindforge.yaml \
    --profile anthropic_coding_plan \
    --allow-real
```

输出永远是结构化 audit-trail, 包含:

- `ran` / `opt_in_state` / `provider_type` / `alias`
- `output_artifact = "ai_draft_preview"` (永远不是 `human_approved`)
- `human_approved = False` / `written = False` (类型契约)
- `tokens_in` / `tokens_out` / `latency_ms` (可观察 metadata, 不含
  secret)
- `output_excerpt_safe` (240 字符截断 + sk-* / Bearer * / AIza* 脱敏)

## 3. 三重 gate (任意一项不满足 → 拒绝运行)

1. `--allow-real` 必须显式传入;
2. `active_profile != "fake"` (默认是 fake, 必须显式切换);
3. 目标 alias 的 `api_key_env` 必须在 `os.environ` 中存在
   (presence-only; 永远不读取 value, value 由 provider 内部按
   `api_key_env` 自取)。

任意 gate 失败 → `ran=False` + 结构化 `blocker` 字段; 不抛异常,
不重试, 不静默 fallback。

## 4. 不会触发的事

即使 `--allow-real` smoke 真实命中:

- ❌ 不写 vault (`written=False`)
- ❌ 不写 cards
- ❌ 不进 approval queue
- ❌ 不可能变成 `human_approved` (类型契约 + 测试)
- ❌ 不调用 Cubox API
- ❌ 不读取或修改 Obsidian
- ❌ 不接受 caller-supplied prompt (`build_synthetic_prompt()` zero-arg)
- ❌ 不打印或返回 api_key value
- ❌ 不持久化 audit trail (CLI 输出即终点; 不写 jsonl / state)

## 5. 真实 smoke 实证 (Stage 3)

DashScope Coding Plan / qwen_coder_fast (anthropic_compatible),
synthetic prompt, 一次成功调用:

```
ran                   : True
opt_in_state          : ready
provider_type         : anthropic_compatible
alias                 : qwen_coder_fast
output_artifact       : ai_draft_preview
human_approved        : False
written               : False
tokens_in/out         : 44/72
latency_ms            : 1434
```

输出摘要为合成 prompt 的合规中性回答 (240 字符截断), 无 secret
泄漏, approval boundary 完整。

## 6. 局限与未来工作

- 本流程不解决"账户/计费保护": 用户必须自己确认 `.env` 中的 key
  指向自己愿意为 smoke 付费的 endpoint;
- 不持久化 audit trail: 长期 dogfooding 若需要历史回看, 后续可在
  独立 `provider_audit_store` 模块中处理 (本轮范围之外, 仍属
  proposal-only);
- 不支持 batch / 多次调用: 设计上每次 CLI 调用恰好一次 provider
  请求, 避免误循环放大;
- 真实 Cubox / Obsidian 接入仍 deferred (见
  [V0_13_REAL_INGESTION_DEFERRED_GATES.md](V0_13_REAL_INGESTION_DEFERRED_GATES.md))。
