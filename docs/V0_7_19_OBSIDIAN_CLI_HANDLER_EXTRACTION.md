# v0.7.19 Obsidian CLI Handler Extraction

## 本版本目标

v0.7.19 的目标是把 `mindforge obsidian ...` 子命令的 Typer handler 和人类可见
输出，从 `src/mindforge/cli.py` 迁移到 `src/mindforge/obsidian_cli.py`。

这不是新增 Obsidian 功能，也不是抽 service。它只是把 Obsidian command adapter
层从主 CLI 巨石里移出，让 `cli.py` 更接近 top-level app / command registry。

## 为什么这是 command adapter 边界

Obsidian 子命令有独立的 CLI 语义：`doctor`、`scan`、`links`、`stage`、
`preflight`、`next` 都围绕同一个本地 Obsidian dry-run / staged export /
manual inspection workflow。它们需要 Typer 参数、Rich table、用户下一步提示和
安全边界文案，但不应该把这些 adapter 代码混在 top-level CLI 文件里。

`obsidian_cli.py` 因此不是贫血 helper：它拥有完整的 Obsidian CLI adapter 边界，
集中承接该领域的命令注册、参数、输出和 handler 编排。

## 本轮迁移了什么

从 `cli.py` 迁移到 `obsidian_cli.py`：

- `obsidian_app`；
- `obsidian doctor`；
- `obsidian scan`；
- `obsidian links`；
- `obsidian stage`；
- `obsidian preflight`；
- `obsidian next`；
- Obsidian CLI 输出 helper；
- stage preview / staged diff / staged export manifest 的 CLI adapter glue。

`cli.py` 现在只 import 并挂载 `obsidian_app`。为兼容历史测试，`cli.py` 暂时保留
一个很薄的 `_obsidian_dogfood_command_snippets` wrapper，实际实现仍在
`obsidian_cli.py` / `obsidian_workflow.py`。

## obsidian_cli.py 的职责

`obsidian_cli.py` 负责：

- 定义并导出 `obsidian_app`；
- 定义 Obsidian 子命令 Typer handlers；
- 渲染 Obsidian 子命令的人类可见输出；
- 调用 `obsidian.py`、`obsidian_stage.py`、`obsidian_workflow.py` 和 policy/helper；
- 保持 staged export / diff / preflight / manual inspection 的现有 CLI 语义；
- 不读取 `.env`；
- 不调用 LLM；
- 不写正式 Obsidian notes。

## obsidian_cli.py 不负责什么

它不负责：

- Obsidian scan/link/stage/preflight 的核心业务规则；
- SourceAdapter / SourceDocument 主链路；
- approval / review / recall 业务；
- process/provider；
- RAG / embedding / graph DB；
- Obsidian plugin；
- apply/write-back；
- 正式 Obsidian notes 写入。

## cli.py 现在少承担什么

`cli.py` 不再承载大段 Obsidian 子命令 handler、Rich table 输出和 stage/preflight
adapter glue。它更接近：

- top-level Typer app；
- command registry；
- 仍未迁出的其他命令入口。

## 保持不变的用户行为

以下命令路径、参数和输出语义保持不变：

- `mindforge obsidian doctor`
- `mindforge obsidian scan`
- `mindforge obsidian links`
- `mindforge obsidian stage`
- `mindforge obsidian preflight`
- `mindforge obsidian next`

`stage --dry-run` 仍不写文件；`stage --staged-export --write --confirm` 仍只写 staged
export 目录和 manifest；`preflight` 仍只是 future write-gate readiness 检查。

## 被保护的 Obsidian 安全边界

本轮保持并通过测试/smoke 覆盖：

- 不读真实 `.env`；
- 不调用真实 LLM；
- 不写正式 Obsidian notes；
- 不新增 apply/write-back；
- 不做 RAG / embedding / plugin / Web UI；
- staged export 只写人工检查目录；
- preflight/manual inspection 之后仍需要人审。

## 后续治理点

Obsidian 内部模块边界仍需观察：

- `obsidian.py` 仍较宽，scan/link/stage/preflight 领域逻辑可继续拆分；
- `obsidian_cli.py` 目前集中承接 Obsidian 输出，未来可考虑 presenter 层；
- `cli.py` 仍有 process/provider/start/commands 等命令入口未治理；
- 不应在后续治理中引入 apply/write-back 或 plugin 能力。
