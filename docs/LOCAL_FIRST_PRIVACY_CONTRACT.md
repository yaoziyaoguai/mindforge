# Local-First Privacy Contract v2

> v0.13 Stage 1 引入 real-capable opt-in 路径后, 隐私契约从 fake-only
> 升级为 fake-default + real-opt-in。本文档为 MindForge 隐私边界的
> **canonical (单一权威) 来源**, 其它文档引用此文件而非复制其内容。

## 1. 默认行为 (default behaviour)

| 维度 | 默认 |
| --- | --- |
| LLM provider | `fake` (`configs/mindforge.yaml.llm.active_profile: fake`) |
| 网络调用 | 无 (fake provider 不发 HTTP) |
| 后台索引 / embedding / RAG | 无 (项目根本未引入相关依赖) |
| `.env` 处理 | `env_loader.load_dotenv_silently` 静默加载, 不打印任何 KEY 或 VALUE; env > dotfile 优先级 |
| Obsidian vault 扫描 | 无 (无 `Path.home()` 调用, 仅显式 vault 路径参数) |
| Obsidian vault 写入 | 无 (仍未启用; 见 `docs/V0_13_REAL_INGESTION_DEFERRED_GATES.md`) |
| Cubox 真实 API | 无 (仍未启用; 同上) |
| 自动 approve | 无 (`human_approved` 仅由人显式产生) |

## 2. 显式 opt-in 边界

启用真实 provider 必须 **同时满足** 以下条件, 缺一不可:

1. `mindforge.yaml.llm.active_profile` 切换到非 `fake` 的 profile;
2. 该 profile 引用的 alias 对应 `api_key` (或 env 间接值) 存在;
3. 调用方传入显式 opt-in 标志 (例如 `--allow-real`)。

仅满足条件 1 不会真正调用真实 provider — `factory.build_providers`
仍然 lazy 构建, 但调用路径必须显式 opt-in。

## 3. Real ≠ Approved 硬隔离

| 路径 | 可产生的 artifact 类型 |
| --- | --- |
| Fake provider | `preview_packet`, `ai_draft_preview` |
| Real provider opt-in | `preview_packet`, `ai_draft_preview` |
| 真实人类 approve | `human_approved` |
| 任何机器路径 | **不能** 产生 `human_approved` |

`human_approved` 在代码层面只能由 `ApprovalService` 在显式人类决策后
写入; 真实 LLM 输出无论来源, 在类型层面都是 review-only。

## 4. Secret 处理

允许:

- 用 `os.environ` 检查 env var **是否存在** (返回 `bool`);
- 把 `api_key_present: True/False` 写入 readiness 报告;
- 把 provider type / alias 名 / base_url 是否覆盖等非敏感元数据写入报告。

禁止:

- `cat .env`;
- 把 env value 打印到 stdout / log / file;
- 把 env value 写入 commit / docs / fixtures / tests;
- 把真实 provider 响应中的敏感片段写入 repo (smoke 输出在落盘前需经
  `real_smoke._scrub_excerpt` 之类的 defence-in-depth 截断/脱敏);
- 把 secret 拼接进 URL / log message。

## 5. 隐式动作禁令

MindForge 永远不:

- 在用户未显式触发的情况下读取 `Path.home()` 下任何文件;
- 启动后台进程 / 守护进程 / 定时任务;
- 自动建立 embedding / RAG / semantic merge 索引;
- 自动把 ai_draft 升级为 `human_approved`;
- 自动写入 Obsidian vault;
- 自动调用真实 Cubox API 拉取用户收藏。

## 6. Human Decision Gate Map

借鉴 LangGraph `interrupt` 与 OpenAI Agents SDK `HumanApproval`:

| Gate | 触发条件 | 默认 | 启用方式 |
| --- | --- | --- | --- |
| Enable real LLM provider | `active_profile != fake` | 关 | 显式改配置 |
| Run real LLM smoke | 上述 + `--allow-real` | 关 | CLI flag |
| Approve `human_approved` | 仅 `mindforge approve` 命令 | N/A | 人类操作 |
| Cubox real ingestion | 见 deferred gates | 关 | 未启用 |
| Obsidian vault write | 见 deferred gates | 关 | 未启用 |
| Export permanent knowledge | `mindforge backup export` 等 | 关 | 显式命令 |

## 7. 测试固化 (testable invariants)

以下断言由 `tests/test_v013_*` 系列守护:

- 默认配置 → readiness 报告 `opt_in_state == "fake_default"`;
- env 存在但 profile = fake → smoke 拒绝运行;
- profile 切换但 api_key 缺失 → smoke 拒绝运行;
- profile 切换 + api_key 存在但 `--allow-real` 未传 → smoke 拒绝运行;
- 任何 smoke 路径返回值不包含 api_key value;
- 任何 smoke 路径 `human_approved` / `written` 字段恒为 `False`;
- `provider_readiness.py` / `real_smoke.py` 不反向 import cli /
  approval / writer / cards / obsidian / cubox / scanner / dotenv /
  requests / httpx / subprocess (AST-guarded)。

## 8. 回退与审计

- 任何 opt-in 步骤随时可通过把 `active_profile` 改回 `fake` 立即回退;
- 真实 smoke 失败默认 fall-back 到 fake 描述, 不重试不放大;
- readiness 报告永远输出, 即便 smoke 拒绝运行 — 拒绝原因写入
  `blocker` 字段供审计。

## 9. 推迟项 (deferred, 非禁止)

参见:

- `docs/V0_13_REAL_INGESTION_DEFERRED_GATES.md` — Cubox / Obsidian 真实
  写入或 ingestion 的启用前置;
- `docs/PROPOSAL_REVIEWABLE_ARTIFACT.md` — 类型化 artifact 协议提案
  (proposal-only, 未授权实现)。

## 10. 文档关系

| 文档 | 角色 |
| --- | --- |
| 本文 | canonical 隐私契约 |
| `docs/V0_13_DOGFOODING_READINESS.md` §5 | 仅 cross-link 到本文, 不再复述 |
| `docs/V0_12_CAPABILITY_MATRIX.md` §8 | capability rows + artifact 类型 |
| `docs/V0_13_INDUSTRY_PATTERN_MAP.md` | 行业对照与差异化 |
| `docs/V0_13_REAL_INGESTION_DEFERRED_GATES.md` | 推迟项启用前置 |
| `docs/PROPOSAL_REVIEWABLE_ARTIFACT.md` | 未来类型化 artifact 提案 |
