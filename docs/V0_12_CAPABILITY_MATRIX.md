# MindForge v0.12 Capability Matrix

> **Status:** v0.12 closure document.
> **Audience:** contributors auditing what custom strategies can and cannot
> do at each lifecycle stage; reviewers checking that preview / approval /
> writer boundaries are intact before any v0.13 dogfooding work begins.
>
> **Inspiration:** OpenAI Agents SDK guardrails, LangGraph
> interrupt/checkpoint, Dify Knowledge Pipeline node isolation —— 行业上
> 这些产品都把"模块在每一阶段允许做什么"显式列成可审计矩阵。本文件
> 把同一思想落到 MindForge 上：custom strategy 的每个生命周期阶段必须
> 一眼看出"允许 / 禁止 / 仅未来", 避免靠口头约定。

## 1. Lifecycle stages

| # | Stage | Owning module(s) |
| --- | --- | --- |
| 1 | Definition (data) | `strategies/custom.py` |
| 2 | Loading (disk → data) | `strategies/custom_loader.py` |
| 3 | Discovery (CLI listing) | `strategies/__init__.py`, `cli.py` |
| 4 | Build / activate | `strategies/__init__.py` (build_strategy) |
| 5 | Preview (review-only) | `strategies/preview_packet.py` |
| 6 | Execution (LLM call) | _v0.13+ future_ |
| 7 | Approval | `approval_service.py` |
| 8 | Writer (vault) | `writer.py` |

## 2. Capability matrix

> Legend: ✅ allowed · ❌ forbidden by design · 🚧 future opt-in only

| Stage | Built-in strategy | Custom (declarative) | Notes |
| --- | --- | --- | --- |
| 1 Definition | ✅ Python factory | ✅ YAML/JSON dict via `parse_strategy_definition` | custom 字段白名单, status ∈ {planned, preview} |
| 2 Loading | ✅ import-time | ✅ explicit `--custom-path` only | no implicit home / vault scan |
| 3 Discovery | ✅ `available_strategies()` | ✅ `discover_strategies(custom_path=…)` with duplicate-id rejection | CLI 标记 `(custom)` |
| 4 Build | ✅ via `_build_builtin_strategy` | ❌ raises `NotYetImplementedStrategyError` ("preview", "discovery is not execution") | registry 拒绝执行 |
| 5 Preview packet | n/a | ✅ `build_custom_preview_packet` returns `{kind: preview_only, executable: false}` | review-only data; no approved-flag field |
| 6 Execution | ✅ via factory + provider | 🚧 v0.13+ opt-in only, not in v0.12 | will require explicit user opt-in |
| 7 Approval | ✅ via `ApprovalService` after explicit user approve | ❌ never reached from preview | preview packet **never** calls `ApprovalService` |
| 8 Writer | ✅ via `CardWriter` after approval | ❌ never reached from preview | preview packet **never** calls `CardWriter` |

## 3. Forbidden touchpoints (architectural invariants)

下列耦合**禁止**出现在 `strategies/preview_packet.py`、
`strategies/custom.py`、`strategies/custom_loader.py` 中。由
`tests/test_custom_strategy_import_boundaries.py` 用 AST 静态守卫；由
`tests/test_custom_preview_packet_contract.py` 与
`tests/test_custom_module_source_has_no_arbitrary_execution_imports`
等做源码 token 扫描。

- ❌ `import mindforge.cli`
- ❌ `import mindforge.approval_service` / `approver` / `approve_presenter`
- ❌ `import mindforge.writer` / `cards`
- ❌ `import mindforge.llm` (any provider)
- ❌ `import mindforge.process_service` / `review_service` / `recall_service`
- ❌ `import mindforge.obsidian*`
- ❌ `import mindforge.cubox*`
- ❌ `import mindforge.env_loader` / `dotenv` / `requests` / `httpx`
- ❌ `subprocess` / `eval` / `exec` / `__import__` / `importlib.import_module`
- ❌ `Path.home()` / `expanduser` / `.obsidian`
- ❌ packet 字段表中出现 approved-flag 字面量

## 4. Allowed cohesive collaboration

下列同包内引允许（高内聚不算耦合）：

- ✅ `preview_packet` → `custom` (StrategyDefinition / InvalidStrategyDefinitionError)
- ✅ `custom_loader` → `custom`
- ✅ `__init__` (build_strategy 包装) → `registry` + `custom_loader`
- ✅ CLI → `preview_packet` (作为 presenter 入口)

## 5. Mapping to industry guardrail patterns

| MindForge invariant | 类比的行业模式 |
| --- | --- |
| Loading is not execution (Slice 2) | OpenAI Agents SDK: tool definition vs tool invocation |
| Discovery is not execution (Slice 3) | LangGraph: state inspection vs node execution |
| Preview is review-only (Slice 5) | Dify Human Input node / LangGraph `interrupt` |
| Explicit approval still required | OpenAI Agents `human_approval` guardrail |
| No arbitrary Python plugin in custom | Obsidian community plugin sandbox 反例 (MindForge 选更严格) |
| AST import-boundary tests | LangChain 早期模块化 lessons learned |

## 6. What v0.12 explicitly does **not** ship

- ❌ Custom strategy runtime execution
- ❌ Real LLM provider activation by default
- ❌ Arbitrary Python plugin / shell / script strategy
- ❌ RAG / embedding / semantic merge
- ❌ Real vault writes
- ❌ Real `.env` reads at runtime
- ❌ Auto-approval
- ❌ Cubox real-API ingestion

These belong to later milestones (v0.13 dogfooding readiness, v0.14+ real
provider opt-in) and must each pass their own boundary review before
landing.

## 7. How to extend this matrix

Adding a new lifecycle stage or new custom subsystem? Add a row to §2
**before** writing production code. If the new row would require an ❌
column to flip to ✅ for custom, raise it as an explicit RFC, not as an
incremental PR.

## 8. v0.13 Stage 1 — Real-Capable Opt-in Readiness Rows (additive)

v0.13 Stage 1 把 provider 路径从 fake-only 升级为 fake-default +
real-opt-in。本节为 capability matrix 增量, 不修改前 7 节内容。

| 能力 | 默认 | 显式 opt-in | 输出 artifact 类型 | 可成为 `human_approved`? |
| --- | --- | --- | --- | --- |
| Fake provider | ✅ 启用 | — | `preview_packet` / `ai_draft_preview` | ❌ 永远不能 |
| Real provider skeleton 存在 | ✅ (`llm/openai_compatible.py` 等) | — | — | — |
| Real provider opt-in (profile 切换) | ❌ 默认 | `mindforge.yaml.llm.active_profile` | — | — |
| Real provider 可被触发 (api_key + profile + flag) | ❌ 默认 | + `--allow-real` | `ai_draft_preview` | ❌ 永远不能 |
| Synthetic real-LLM smoke | ❌ 默认拒绝 | `mindforge provider smoke --allow-real` | `ai_draft_preview` (audit-trail dict) | ❌ 永远不能 |
| Provider readiness report | ✅ 可任意运行 (无网络) | — | `readiness_report` | ❌ 永远不能 |
| Cubox fake / dry-run | ✅ 启用 | — | `cubox_preview` | ❌ 永远不能 |
| Cubox real-API ingestion | ❌ deferred | 见 deferred gates §3 | (未实现) | — |
| Obsidian preview / dry-run | ✅ 启用 (显式 vault 路径) | — | `obsidian_preview` | ❌ 永远不能 |
| Obsidian vault 真实写入 | ❌ deferred | 见 deferred gates §4 | (未实现) | — |

### 8.1 触发者 (who-can-trigger) 矩阵

| 能力 | CLI 用户 | 自动化脚本 | 真实 LLM 输出本身 |
| --- | --- | --- | --- |
| 升格为 `human_approved` | ✅ 显式 `mindforge approve` | ❌ 不允许 | ❌ 不允许 |
| 写入 Obsidian vault | ❌ deferred | ❌ deferred | ❌ 不允许 |
| Ingest 真实 Cubox 内容 | ❌ deferred | ❌ deferred | ❌ 不允许 |
| 运行 fake / synthetic smoke | ✅ 默认允许 | ✅ 默认允许 | — |
| 运行 real synthetic smoke | ✅ `--allow-real` | ✅ `--allow-real` (在受控环境) | — |

### 8.2 与 §6 "Excluded" 列表的一致性

§6 的 ❌ 列表语义在 v0.13 Stage 1 后保持:

- ❌ Custom strategy runtime execution — 仍未启用;
- ❌ Real LLM provider activation **by default** — 仍未默认启用; opt-in
  路径出现, 但默认仍是 fake;
- ❌ Auto-approval — 仍未启用;
- ❌ Real vault writes — 仍未启用 (deferred gates 文档已记录前置条件);
- ❌ Cubox real-API ingestion — 仍未启用 (同上)。

§6 不需要修改。
