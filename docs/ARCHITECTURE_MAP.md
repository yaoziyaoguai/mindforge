# MindForge Architecture Map

本文档是当前代码分层地图，服务于 v0.7.x 架构治理。它描述真实仓库状态，不替代
协议文档，也不承诺尚未实现的模块。治理脉络与验收标准见
[ROADMAP.md](./ROADMAP.md) 的 *v0.7.20–v0.7.23 Architecture Quality
Milestone* 段。产品形态与阶段目标见 ROADMAP.md 的
*Product Shape & Phase Plan* 段（CLI 第一产品形态、Obsidian-centered
workspace、SourceAdapter / KnowledgeStrategy 插件化等架构契约）。

## CLI / Command Layer

- `src/mindforge/cli.py`
- `src/mindforge/obsidian_cli.py`

职责：

- `cli.py`：top-level Typer app、全局选项和 command registry；
- `obsidian_cli.py`：Obsidian 子命令 adapter；
- CLI 参数与 exit code；
- 用户可见输出；
- RunLogger 事件；
- 调用 service / presenter / core pipeline。

边界：

- CLI 可以组合多个 service，但不应承载核心业务判断；
- CLI 可以渲染 Markdown/JSON/Rich 输出；
- CLI 不应把 LLM、approval、review、Obsidian 写入边界写散。
- `obsidian_cli.py` 可以依赖 Typer/Rich，因为它是 command adapter；但它不能
  承接 Obsidian 核心业务规则，也不能新增 apply/write-back。

当前说明：

- `cli.py` 已挂载 `obsidian_app`，不再承载大段 Obsidian handler；
- 其他命令仍可能留在 `cli.py`，这是后续治理点。

## Service Layer

- `src/mindforge/recall_service.py`
- `src/mindforge/approval_service.py`
- `src/mindforge/review_service.py`
- `src/mindforge/process_service.py`
- `src/mindforge/obsidian_workflow.py`
- `src/mindforge/obsidian_stage.py`
- `src/mindforge/obsidian.py`

职责：

- 业务判断；
- 结构化输入输出；
- 可独立测试的领域规则；
- 不依赖 Typer/Rich/console。

当前说明：

- `recall_service.py` 负责本地 lexical recall 结构化查询和结果；
- `approval_service.py` 负责 approve workflow 边界，单卡写入原语仍在
  `approver.py`；
- `review_service.py` 负责 weekly review 只读聚合；
- `process_service.py` 负责 process use-case 的 fake-safety provider 选择、
  prompts/tracks/template 资源解析、outcome 三分流的结构化映射、
  unsupported-provider/missing-source/malformed-input 的结构化错误；
  不读 .env、不实例化真实 provider、不依赖 Typer/Rich/RunLogger，
  实际 dotenv 加载与 console/writer/logger 副作用仍在 CLI；
- `obsidian_workflow.py` 负责 Obsidian dogfooding next-plan；
- `obsidian_stage.py` 负责 staged export / manifest / diff / preflight display
  plan；
- `obsidian.py` 仍较宽，包含 scan/link/stage/preflight 的领域逻辑。

注意：当前仓库还没有独立的 `obsidian_preflight.py`。preflight 领域逻辑仍在
`obsidian.py`，preflight 展示计划在 `obsidian_stage.py`。这应作为后续治理点，
不要在架构地图中假装已经完成。

## Presenter Layer

- `src/mindforge/recall_presenter.py`
- `src/mindforge/approve_presenter.py`
- `src/mindforge/review_presenter.py`
- 未来可扩展 process / config / Obsidian presenter。

职责：

- 输出表达；
- Markdown/JSON/Rich 结构选择；
- 不做业务判断；
- 不改变状态。

当前 presenter 层仍不完整：`process` / `scan` / `config doctor` 等命令
仍内嵌 console.print；review 子命令仅 `weekly` 已抽出 presenter，其余
`due` / `mark` / `schedule` / `backlog` / `stats` 5 个仍 inline 调
`iter_cards` + `filter_cards` + `_bucket_review`，需要先扩 review_service
再做 presenter 抽取；Obsidian 输出已迁入 `obsidian_cli.py` 这个 command
adapter，但还不是独立 presenter。v0.7.21 已抽出 `approve_presenter.py`，
v0.7.22 已抽出 `review_presenter.py`（仅 weekly）。

## Context / Policy Layer

- `src/mindforge/app_context.py`
- `src/mindforge/safety_policy.py`

职责：

- `app_context.py` 只做 config/path resolution，不做 recall/approve/review 业务；
- `safety_policy.py` 集中表达安全边界，不执行具体业务流程。

边界：

- context 层不读取 `.env`；
- policy 层不写卡片、不调 LLM、不替 service 做流程控制。

## Obsidian Integration

- `src/mindforge/obsidian.py`
- `src/mindforge/obsidian_stage.py`
- `src/mindforge/obsidian_workflow.py`
- `src/mindforge/obsidian_cli.py`

职责：

- 只读扫描 Obsidian Markdown；
- 解析 wikilinks；
- staged export / manifest / diff；
- preflight readiness；
- dogfooding next-plan。

说明：

- `obsidian_cli.py` 只是 CLI adapter，不是 integration core；
- `obsidian.py` / `obsidian_stage.py` / `obsidian_workflow.py` 继续承接结构化
  integration/service 逻辑。

安全边界：

- 当前版本没有 apply/write-back；
- 不写正式 Obsidian notes；
- staged export 只写 staging 目录；
- preflight/manual inspection 之后仍需人审。

## Core Pipeline

- `SourceAdapter` / `SourceDocument`：把 inbox 文件解析成统一 source；
- processors / `Pipeline`：把 source 经过 triage / distill / link / review
  questions / actions；
- `writer.py`：写 Knowledge Card，默认 `status: ai_draft`；
- `approval_service.py` + `approver.py`：显式人审后才允许
  `ai_draft -> human_approved`；
- `recall_service.py`：默认只检索 `human_approved`，显式 include-drafts 才带草稿；
- `review_service.py`：只读聚合 `human_approved`，绝不自动 approve。

## 未治理完的地方

- `cli.py` 仍然是主巨石；
- `cli.py` 仍可能承载 process/provider/start/commands 等命令入口；
- process/provider 命令可能适合后续 service extraction；
- presenter 层还不完整；
- `obsidian.py` 仍较宽，preflight 可考虑后续独立为专门 service；
- Obsidian 内部 service/presenter 仍需观察，避免 `obsidian_cli.py` 形成新的
  输出小巨石；
- review/approval/presenter 需要继续观察，避免形成新的小巨石；
- 测试文件仍按历史版本聚合，短期作为保护网保留。

## Boundary Test Layer

为防止已抽出的 service / presenter 静默退化为新巨石或悄悄突破"不依赖
CLI / 真实 LLM / .env / Obsidian write" 边界，v0.7.23 起引入分层的
AST 静态边界测试（architecture fitness functions）：

**Layer 1 — Service**（v0.7.23 + follow-up）：
- `tests/test_process_service.py`（v0.7.20 引入，混合行为 + AST）
- `tests/test_process_service_boundaries.py`（v0.7.23，**纯架构锁**）
- `tests/test_review_service_boundaries.py`（v0.7.23 follow-up）
- `tests/test_approval_service_boundaries.py`（v0.7.23 follow-up）

**Layer 2 — Presenter / CLI Adapter**（v0.7.23 second follow-up）：
- `tests/test_presenter_boundaries.py`（覆盖 approve / recall / review
  三个 presenter，parametrize 同一组检查）
- `tests/test_cli_adapter_boundaries.py`（覆盖 cli.py + obsidian_cli.py，
  parametrize 同一组检查）

三层文件结构同构（同一组 AST helper、同类断言），但每个组件的白名单 /
上限 / 禁忌不同，**有意不共享 fixture**：让每个组件的边界声明独立、显式、
可单独修改。

共同覆盖：

  - 顶层 import 封闭白名单（service/presenter）或核心负面 ban（CLI 适配器）
  - 反向依赖 ban：service / presenter 不可 import CLI；presenter 不可
    跨 use-case service；service 不可 import presenter / 其他 service
  - 真实 LLM SDK ban：openai / anthropic / litellm / cohere / ollama
  - UI 框架 ban（presenter / service 层）：typer / click / textual / prompt_toolkit
  - RAG / embedding / vector store ban
  - dotenv 直接 import ban（必须走 `mindforge.env_loader`）
  - `os.environ` / `getenv` 直接访问 ban（service / presenter 层；CLI 允许，
    用于 `MINDFORGE_*` 标志桥接）
  - `write_text` / `write_bytes` / `open()` 写盘 ban（service / presenter）
  - `__all__` 或顶层公开符号面快照锁
  - 函数 / dataclass / class 数量上限

组件特定差异：

  - **process_service**：status mutation call ban；`human_approved` 字面量
    赋值 ban；safety_policy 三条 boundary 对齐
  - **review_service**：`human_approved` 字面量**只能**作 `status=` keyword
  - **approval_service**：`human_approved` 字面量**完全不可出现**；正向断言
    必须调用 `approver.approve_card`（delegation 不可丢）；唯一允许 import
    `mindforge.approver` 的 service
  - **presenter 层**：禁止 import `approver` / `reviewer` 状态层；禁止跨 use-case
    service（每个 presenter 只可 import 自己同名 service + cards）；纯转换
    函数语义
  - **CLI 适配器**：不锁行数 / 不锁文件大小（明确反 KPI 化）；锁真实 LLM SDK
    直 import ban、真实 LLM credential 字面量（OPENAI_API_KEY 等）ban；
    正向断言：必须 import `env_loader` 并调用 `load_dotenv_silently`、必须
    import `mindforge.llm` 并调用 `build_providers`、必须调用
    `approve_explicit_card` 完成 approval delegation；`obsidian_cli` 不可
    反向 import `cli`
  - **CLI `human_approved` 字面量规则**：允许作为 keyword、collection 元素、
    Compare 右值、`in` 表达式、f-string 拼接片段；禁止作为 Assign / Return
    的写入值

后续可按同模式扩展 `recall_service` / `policy` / `context` / `workflow`，
但只在出现具体退化信号或新治理 milestone 时再加，不机械复刻。
