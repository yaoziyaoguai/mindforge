# v0.7.21 — Approve Presenter Extraction

本轮是一次架构治理重构，目标是把 ``cli.py::approve_app`` 区域（行 373-714，
共 27 处 ``console.print`` + 1 处 Rich ``Table`` + 1 处 ``console.print_json``）
中的**展示职责**抽到新模块 ``src/mindforge/approve_presenter.py``，与 v0.7.13
``recall_presenter.py`` 模式保持一致。

## 1. 本轮不是新功能

- 不新增 approve 子命令
- 不新增 JSON / Markdown 输出格式（``approve list`` 已有的 JSON 模式照旧）
- 不引入新的依赖
- 不改变 ``approval_service`` 的公开 API
- 不引入 v0.8 Real LLM Opt-in / RAG / embedding / Obsidian plugin /
  Web UI / TUI

## 2. 本轮不是为了降低行数

cli.py 4677 行 → 与 v0.7.20 相比净行数 **可能持平或微增**（presenter 调用胶水
+ 中文注释抵消了被抽走的行数）。本轮的目标是 **职责边界清晰** 与 **展示层
可独立测试**，不是机械搬运 ``console.print``。

## 3. approve 为什么是 human approval safety boundary

``approve`` 是把卡片从 ``ai_draft`` 显式晋升为 ``human_approved`` 的人审动作。
``human_approved`` 卡片会进入 recall / project context / weekly review 的正式
输出，被复用到多个项目，影响后续判断；一旦允许 LLM 自动 approve，AI 误差就
会被无限放大。MindForge 的差异化前提之一就是 **source-grounded + 
human-approved**。

把展示与业务混在一起意味着每次改 emoji / table 表头都要触碰人审边界附近的
代码。把展示层下沉到 presenter 后：

- approval_service 是 ``human_approved`` 边界的**唯一执行入口**；
- presenter 在 import 层就拒绝 ``approve_explicit_card`` / ``write_text`` /
  ``approver`` 等执行符号（AST 静态断言保护）；
- 展示层的 snapshot 测试可以独立保护"输出文案不漂移"。

## 4. approve_presenter 的职责

新增 ``src/mindforge/approve_presenter.py``（约 290 行，含大段 docstring），
仅承载 5 类展示意图：

1. ``approve list``  → ``render_approval_list`` / ``render_approval_list_json``
2. ``approve show``  → ``render_approval_show`` / ``render_approval_show_error``
3. ``approve --all`` → ``render_bulk_candidate_list`` / ``render_bulk_empty`` /
   ``render_bulk_dry_run_footer`` / ``render_bulk_confirm_required`` /
   ``render_bulk_summary``
4. 单卡 approve 结果 → ``render_execution_success`` / ``render_execution_failure``
5. routing / lookup 错误 → ``render_routing_hint`` / ``render_lookup_error``

辅助纯函数：``format_card_created_at`` / ``format_card_source_hint`` /
``approve_next_command`` / ``build_approval_list_json``。

约定（与 ``recall_presenter.py`` v0.7.13 模式一致）：presenter **不持有全局
console**，由调用方传入 ``Console`` 实例；测试时传入
``Console(file=StringIO(), ...)`` 做 snapshot 验证。

## 5. approve_presenter 不负责什么

静态 + 运行时双重保证（详见 ``tests/test_approve_presenter.py``）：

- 不 ``import typer``
- 不 ``import rich.console.Console`` 之外的 IO 副作用
- 不 import ``dotenv`` / ``env_loader``
- 不 import ``run_logger``，不持有 ``RunLogger``
- 不 import ``processors`` / ``sources`` / ``providers`` / ``embedding``
- 不 ``Path.read_text`` / ``Path.write_text`` / ``open(...)``
- 不调 ``approve_explicit_card`` / ``approve_card`` / ``preview_approval_card`` /
  ``list_approval_candidates`` / ``build_bulk_approval_plan`` /
  ``resolve_card_path_by_source_id``
- 不修改 card 状态 / 不自动 approve
- 不调真实 LLM / 不读真实 ``.env`` / 不写正式 Obsidian notes
- 不做 RAG / embedding
- 不解析 CLI 参数
- 不抛 ``typer.Exit``

## 6. approval_service 与 approve_presenter 的边界

| 关注点 | 归属 |
|---|---|
| 候选筛选 / `ai_draft` 过滤 | approval_service |
| ``source_id → card_path`` 反查 | approval_service |
| approve preview 字段白名单 | approval_service（``APPROVAL_PREVIEW_FIELDS``） |
| bulk approve 候选计划 | approval_service |
| 显式 approve 副作用（写 frontmatter） | approval_service → approver |
| ``human_approved`` 状态转移 | approver（业务原语） |
| Rich Table 构造 | **approve_presenter** |
| Rich tag / emoji 文案 | **approve_presenter** |
| JSON dict 拼接 | **approve_presenter** |
| empty / error / 边界提示文案 | **approve_presenter** |
| 行命令清单 | **approve_presenter** |

approval_service 公开 API **本轮零变化**（测试
``test_approval_service_public_api_unchanged`` 静态保护）。

## 7. CLI 现在少承担什么

cli.py::approve 区域（行 373-714）以下职责已下沉到 presenter：

- Rich Table 构造（``approve list``）
- ``console.print_json(json.dumps(...))`` 的 dict 构造
- 5 处 emoji / rich tag 文案（✔/✗、`[red]/[yellow]/[green]/[dim]`）
- 6 类边界提示文案（"MindForge 不会自动 approve" 等）
- ``approve --all`` 的 5 段输出（候选清单 / dry-run 尾注 / confirm 拒绝 /
  empty / 总结）
- ``approve show`` 的字段对齐展示
- routing 友好提示
- lookup 错误展示
- ``_format_card_*`` / ``_approve_next_command`` 三个 pure helper 已迁移
  到 presenter（cli.py 中保留极薄的兼容包装，便于未来彻底删除）

CLI 仍负责：

- Typer 参数定义 / 命令注册
- ``--card`` / ``--source-id`` / ``--all`` routing 控制流
- ``approval_service`` 调用（业务）
- ``RunLogger`` 编排（``_do_single_approve`` 中的 ``with RunLogger`` 块）
- ``typer.Exit`` 与 exit code
- ``console.print_json(json.dumps(...))`` 的 ``rich.Console`` 调用本身
- ``_load_cfg`` 与配置解析

## 8. JSON / Markdown / Rich 输出如何归属

- **Rich**：presenter 接收 ``Console`` 参数，调用 ``console.print``
  渲染 Table / 文案（约定来源：``recall_presenter.py``）。
- **JSON**：``build_approval_list_json`` 是纯函数返回 dict；
  ``render_approval_list_json`` 调 ``console.print_json``。CLI 不再自己
  拼 dict。
- **Markdown**：v0.7.21 当前 approve 区域**没有** Markdown 输出格式
  （grep 已确认）；本轮**不引入**新格式，避免特性蔓延。

## 9. 为什么没有改变 approve 业务语义

- ``approval_service`` 模块本轮**零修改**（git diff 已验证）。
- ``approver.py`` 本轮**零修改**。
- ``human_approved`` 状态转移仍由 ``approver.approve_card`` 唯一执行。
- presenter 在 import 层就拒绝 ``approve_explicit_card`` / ``approve_card``
  等执行符号（``test_presenter_does_not_import_approver_execution_layer``
  静态断言）。
- presenter 不读 / 不写 card 文件（``test_presenter_does_not_call_path_*``
  静态断言）。
- CLI 黑盒输出与 v0.7.20 字节级一致（手动 smoke 验证 + snapshot test）。

## 10. 后续仍需治理什么

- **review_presenter**：``review weekly`` / ``review due`` 等命令仍在
  cli.py 内嵌 Rich 渲染（cli.py 行 1154-1812）。
- **process_presenter / scan_presenter**：``process`` / ``scan``
  handler 中仍有大量 ``console.print``，但与 RunLogger / scanner 时序
  耦合，需要先评估是否值得抽。
- **config_presenter / project_presenter**：``config doctor`` / 
  ``project list/context`` 输出散落。
- v0.7.21 之后 cli.py 仍有 ~300 处 ``console.print``；presenter 治理
  按 use-case 分轮次推进，不一次抽完。

## 与 safety_policy 的关系

- 本轮 **不修改、不扩展** ``safety_policy.py``。
- ``approve_presenter`` 不调用 ``safety_policy`` 做控制流判断。
- 测试与本文档引用 ``safety_policy.boundary_statement(
  "human_approved_gate" / "no_real_llm" / "no_env_read")`` 作为对齐证据。
