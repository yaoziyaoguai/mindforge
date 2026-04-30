# MindForge Architecture Map

本文档是当前代码分层地图，服务于 v0.7.x 架构治理。它描述真实仓库状态，不替代
协议文档，也不承诺尚未实现的模块。

## CLI / Command Layer

- `src/mindforge/cli.py`

职责：

- Typer app 和命令入口；
- CLI 参数与 exit code；
- 用户可见输出；
- RunLogger 事件；
- 调用 service / presenter / core pipeline。

边界：

- CLI 可以组合多个 service，但不应承载核心业务判断；
- CLI 可以渲染 Markdown/JSON/Rich 输出；
- CLI 不应把 LLM、approval、review、Obsidian 写入边界写散。

## Service Layer

- `src/mindforge/recall_service.py`
- `src/mindforge/approval_service.py`
- `src/mindforge/review_service.py`
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
- `obsidian_workflow.py` 负责 Obsidian dogfooding next-plan；
- `obsidian_stage.py` 负责 staged export / manifest / diff / preflight display
  plan；
- `obsidian.py` 仍较宽，包含 scan/link/stage/preflight 的领域逻辑。

注意：当前仓库还没有独立的 `obsidian_preflight.py`。preflight 领域逻辑仍在
`obsidian.py`，preflight 展示计划在 `obsidian_stage.py`。这应作为后续治理点，
不要在架构地图中假装已经完成。

## Presenter Layer

- `src/mindforge/recall_presenter.py`
- 未来可扩展 review / approval / Obsidian presenter。

职责：

- 输出表达；
- Markdown/JSON/Rich 结构选择；
- 不做业务判断；
- 不改变状态。

当前 presenter 层仍不完整：`review weekly` 和多数 Obsidian 输出仍由 `cli.py`
直接渲染。

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

职责：

- 只读扫描 Obsidian Markdown；
- 解析 wikilinks；
- staged export / manifest / diff；
- preflight readiness；
- dogfooding next-plan。

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
- Obsidian CLI handler 可能适合后续迁出；
- process/provider 命令可能适合后续 service extraction；
- presenter 层还不完整；
- `obsidian.py` 仍较宽，preflight 可考虑后续独立为专门 service；
- review/approval/presenter 需要继续观察，避免形成新的小巨石；
- 测试文件仍按历史版本聚合，短期作为保护网保留。
