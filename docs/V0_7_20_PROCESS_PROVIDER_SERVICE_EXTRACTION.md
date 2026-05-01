# v0.7.20 — Process / Provider Service Extraction

本轮是一次架构治理重构，目标是把 `cli.py::process` 命令中混合在一起的
**业务判断（provider/fake-safety/资源解析/outcome 三分流）** 与
**adapter 副作用（Typer/Rich/RunLogger/CardWriter/Checkpoint）** 拆开，
形成新的 `src/mindforge/process_service.py` service 层模块。

## 1. 本轮不是为了降低行数

`cli.py` 总行数甚至轻微增加（4662 → 4677），原因是新增了 service 调用胶水
和说明性中文注释。本轮的目标是 **职责边界清晰** 与 **可独立测试**，不是
机械搬运代码以追求 LOC 下降。

## 2. process / provider 为什么是核心架构边界

`process` 是 MindForge 的核心 use-case：把 inbox 中已 scan 的文件经过
5-stage pipeline 转化为 `ai_draft` 状态的 Knowledge Card。这一过程必须严格
遵守若干安全边界：

- **fake provider 默认安全**：默认 profile 是 fake，不读 `.env`、不实例化
  真实 LLM provider，确保本地 smoke 完全离线。
- **ai_draft ≠ human_approved**：process 永远只产出 `ai_draft`，绝不
  自动 approve。
- **no real LLM by default**：只有用户显式切换到 real profile，CLI 才
  加载 `.env`。

把这些边界混在 CLI handler 里，意味着每次改 console 输出都要小心不要碰到
fake-safety 守卫。把它们下沉到 service 层后，业务边界获得独立的测试覆盖
（见 `tests/test_process_service.py` 16 项），CLI handler 退化为 adapter。

## 3. process_service 的职责

新增 `src/mindforge/process_service.py`，仅承载：

1. `ProcessRequest` —— process use-case 的结构化请求（cfg + CLI flags）
2. `ProviderSelection` —— 当前 provider/profile 选择结果，关键字段
   `requires_real_env = (active_profile != "fake")`
3. `ProcessAssets` —— prompts_dir / tracks_text / template_path | template_text
   的资源解析结果（用户显式路径优先，否则 fall back 到 package 资源）
4. `ProcessRuntime` —— 上述两者的容器
5. `resolve_process_runtime(req) -> ProcessRuntime | ProcessError`
6. `summarize_outcome(outcome, doc, adapter_name, dry_run) -> ProcessItemResult`
   （纯函数，三分流 + dry_run 语义 + source_dict 构造）
7. `ProcessError` —— 三类结构化错误码：
   - `PROCESS_ERROR_UNSUPPORTED_PROVIDER`
   - `PROCESS_ERROR_MISSING_SOURCE`
   - `PROCESS_ERROR_MALFORMED_INPUT`

## 4. process_service 不负责什么

静态 + 运行时双重保证：

- 不 import typer / rich
- 不 console.print / 不持有 RunLogger
- 不调用 `load_dotenv*`，不读真实 `.env`
- 不实例化真实 LLM provider，不调用真实 LLM
- 不自动 approve
- 不写正式 Obsidian notes，不调用 `Path.write_text`
- 不做 RAG / embedding / index 构建
- 不改变 processor 主链路 / SourceAdapter / SourceDocument 协议
- 不改变 fake provider 默认安全路径
- 不承担 Markdown / JSON / Rich 输出渲染

测试 `tests/test_process_service.py::test_static_module_does_not_import_forbidden_deps`
通过 AST 解析硬性断言模块未 import 任何禁词。

## 5. fake provider 默认路径如何保持

- `ProviderSelection.requires_real_env = (cfg.llm.active_profile != "fake")`
  是 service 唯一暴露的 fake-safety 信号。
- service 自身从不调用 `load_dotenv`，不实例化 provider。
- CLI 在收到 runtime 后，仅当 `requires_real_env` 为 True 才执行
  `load_dotenv_silently(Path.cwd())`。
- 默认 fake profile → `requires_real_env=False` → CLI 跳过 dotenv，
  与 v0.7.19 字节级一致。

## 6. no-real-LLM 边界如何保护

- service 不 import `build_providers`，不构造 `LLMClient`。
- 真实 provider 装配仍发生在 CLI 端的 `process` handler，与 v0.7.19 一致。
- 测试 `test_resolve_does_not_trigger_provider_build` 用 monkeypatch 断言
  resolve 期间不会触达 `build_providers`。

## 7. ai_draft ≠ human_approved

- `summarize_outcome` 不会改变 outcome.status；processed 的卡片仍以
  `ai_draft` 写入磁盘（CardWriter 的责任）。
- 测试 `test_process_result_is_ai_draft_not_human_approved` 显式断言
  service 不会向 outcome 添加 `human_approved` 字段。
- `approval_service` 仍是晋升 `human_approved` 的唯一入口，service 与之
  无耦合。

## 8. CLI 现在少承担什么

`cli.py::process` 中以下职责已下沉：

- `cfg.llm.active_profile != "fake"` 的硬编码判断
  → `runtime.provider.requires_real_env`
- prompts_dir / tracks_text 资源解析的 fallback 链
  → `runtime.assets.{prompts_dir, tracks_text}`
- template_path | template_text 二选一
  → `runtime.assets.{template_path, template_text}`
- `outcome.triage.parsed.get(...)` 的字段提取
  → `item_result.{track, value_score}`
- processed 分支中 `source_dict` 的字典构造
  → `item_result.source_dict`
- dry_run 与 processed 的组合判断
  → `item_result.would_write_only`

CLI 仍负责：Typer 参数 / console.print / RunLogger.emit / writer.write /
Checkpoint.upsert_seen / build_providers / LLMClient / Pipeline 装配 /
exit code / `load_dotenv_silently` 实际调用。所有 console 文案、emit
事件名/字段、退出码、命令参数 **字节级保持** 与 v0.7.19 一致。

## 9. 为什么只抽子集

只抽 `resolve_process_runtime` + `summarize_outcome` 这一最小高内聚切片：

- scanner 循环、checkpoint 写回、RunLogger.emit、writer.write 与
  outcome 处理时序耦合，强行外提会让 service 反过来依赖 RunLogger
  → 违反 "service 不依赖 Typer/Rich" 边界。
- 不新增 `provider_policy.py`，因为当前 provider 选择只是 "读
  active_profile + 计算 requires_real_env"，独立模块会变成贫血 helper。
- 不修改 `safety_policy.py`，它是边界声明常量模块，刻意克制；不要
  把业务判断塞回去。

## 10. 后续仍需治理什么

- `cli.py::process` 中 scanner/checkpoint/RunLogger 编排块（行 ~828-1010）
  仍较大，未来可考虑 `ProcessExecutor` 接受 logger/writer/checkpoint 协议。
- `obsidian.py` 仍宽，包含 scan/link/stage/preflight，可继续按
  use-case 拆 `obsidian_link_service.py` / `obsidian_preflight_service.py`。
- 真实 LLM opt-in（v0.8）的入口仍在 CLI handler，未来可加
  `ProviderRuntime` 把 `LLMClient` 装配也下沉。

## 与 safety_policy 的关系

- 本轮 **不修改、不扩展** `safety_policy.py`。
- `process_service` 不调用 `safety_policy` 做控制流判断（保持
  safety_policy 的克制）。
- 测试与本文档引用 `safety_policy.boundary_statement(
  "fake_provider_default" / "no_env_read" / "no_real_llm")` 作为
  对齐证据，证明 service 行为与已声明边界一致。
