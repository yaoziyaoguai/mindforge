# v0.7.21 Approve Presenter — Checkpoint

本文档是 v0.7.21 发布后的**架构治理 checkpoint**，对 ``approve_presenter``
抽取做一次独立审计与归档。它**不是**新版本说明，本身**不引入任何代码变更**。

发布说明见 ``docs/V0_7_21_APPROVE_PRESENTER_EXTRACTION.md``。

## 1. 标识

- commit: ``fefb991``
- tag: ``v0.7.21``
- 上一个 tag: ``v0.7.20`` (process_service 抽取)
- 状态：本地 commit + tag，**未 push**

## 2. 本轮目标

把 ``cli.py::approve_app`` 区域（行 373-714，27 处 ``console.print`` +
1 处 Rich Table + 1 处 ``console.print_json``）的展示职责抽到新模块
``src/mindforge/approve_presenter.py``，与 v0.7.13 ``recall_presenter``
模式保持一致。

## 3. 本轮不是什么

- **不是新功能**：approve 子命令、参数、JSON 模式开关、exit code 全部
  字节级保持。
- **不是降行数 KPI**：cli.py 4677 → 4609（-68），但同时 presenter +403、
  tests +474、docs +162；**净行数明显增加**。本轮的目标是模块边界，
  不是物理体积。
- **不是机械搬运**：``build_approval_list_json`` 把散在 CLI 的 dict 拼接
  聚合成纯函数；``render_bulk_*`` 5 个函数对应 bulk 流程的 5 个语义阶段
  （候选清单 / dry-run 尾注 / confirm 拒绝 / empty / 总结），不是逐行搬
  ``console.print``。

## 4. approve_presenter 承担

新增模块 ``src/mindforge/approve_presenter.py``（403 行，含大段中文
学习型 docstring），17 个公开 API 按 5 类展示意图组织：

| 类别 | API |
|---|---|
| format helper（纯函数） | ``format_card_created_at`` / ``format_card_source_hint`` / ``approve_next_command`` |
| approve list | ``build_approval_list_json`` / ``render_approval_list`` / ``render_approval_list_json`` |
| approve show | ``render_approval_show`` / ``render_approval_show_error`` |
| approve --all (bulk) | ``render_bulk_candidate_list`` / ``render_bulk_empty`` / ``render_bulk_dry_run_footer`` / ``render_bulk_confirm_required`` / ``render_bulk_summary`` |
| 单卡 approve 结果 | ``render_execution_failure`` / ``render_execution_success`` |
| routing / lookup error | ``render_lookup_error`` / ``render_routing_hint`` |

约定（与 ``recall_presenter`` v0.7.13 一致）：presenter **不持有全局
console**，由调用方传入 ``rich.Console`` 实例；测试时传入
``Console(file=StringIO(), force_terminal=False)`` 做 snapshot 验证。

## 5. approve_presenter 不承担

静态保证（AST 测试断言）：

- 不 ``import typer``
- 不 ``import dotenv``
- 不 ``import RunLogger``
- 不 ``import processors`` / ``sources`` / ``providers``
- 不调 ``approve_explicit_card`` / ``approve_card`` /
  ``preview_approval_card`` / ``list_approval_candidates`` /
  ``build_bulk_approval_plan`` / ``resolve_card_path_by_source_id``
- 不调 ``Path.read_text`` / ``Path.write_text`` / ``open(...)``

运行时保证：

- 不修改 card 状态 / 不写 frontmatter
- 不自动 approve
- 不调真实 LLM / 不读真实 ``.env`` / 不写正式 Obsidian notes
- 不做 RAG / embedding
- 不解析 CLI 参数（不接受 raw str 配置路径）
- 不抛 ``typer.Exit``

## 6. 三层边界

| 层 | 模块 | 职责 |
|---|---|---|
| Service | ``approval_service.py``（312 行，**本轮零修改**） | 候选筛选 / source_id 反查 / preview 字段白名单 / bulk 计划 / 显式 approve 副作用编排 |
| Domain primitive | ``approver.py``（**本轮零修改**） | ``approve_card`` 唯一执行 ``human_approved`` 状态转移 |
| Presenter | ``approve_presenter.py``（403 行，新） | Rich Table / JSON dict / Markdown 文案 / 错误展示 / 边界文案 |
| CLI adapter | ``cli.py::approve_app``（约 340 行，-68 净减） | Typer 参数 / ``--card``/``--source-id``/``--all`` routing / approval_service 调用 / RunLogger 编排 / typer.Exit |

approve 区域 ``console.print`` 数：**27 → 0**（全部下沉到 presenter）。

## 7. human_approved / explicit approve 安全边界

- ``human_approved`` 状态转移仍由 ``approver.approve_card`` **唯一执行**。
- ``approval_service`` 模块 **本轮 git diff 为空**。
- presenter 在 import 层就拒绝 ``approve_explicit_card`` /
  ``approve_card`` / ``Path.write_text`` 等所有写路径符号
  （``test_presenter_does_not_import_approver_execution_layer`` 等
  AST 静态断言）。
- presenter 输入是 ``ApprovalListResult`` / ``ApprovalPreviewResult`` /
  ``ApprovalExecutionResult`` 等 **frozen dataclass**，不可变。
- CLI ``--card`` / ``--source-id`` / ``--all`` 仍由 cli.py 分发；
  presenter 不参与控制流。
- "MindForge 不会自动 approve" 边界提示文案完整保留。

## 8. 测试

新增 ``tests/test_approve_presenter.py``（474 行，26 个测试）：

| 类别 | 数量 |
|---|---|
| 渲染快照 | 6 |
| bulk 5 段输出 | 4 |
| execution 成功/失败/已批准/state_missing | 4 |
| routing / lookup error | 2 |
| AST 静态边界（不 import / 不调用） | 7 |
| approval_service 公开 API 稳定 | 1 |
| CLI 黑盒（与 v0.7.20 字节级一致） | 1 |
| frozen dataclass 不可变 | 1 |

零删除 / 零削弱已有测试。每个测试含中文学习型 docstring 解释 presenter
边界与 human_approved 保护逻辑。

## 9. 质量门 + Smoke

| 门 | 结果 |
|---|---|
| ``ruff check .`` | All checks passed |
| ``pytest`` | 534 passed / 2 skipped（v0.7.20 是 508，新增 26 项 presenter 测试） |
| ``git diff --check`` | clean |

Smoke（9 条，全部字节级一致 v0.7.20）：

1. ``mindforge commands`` ✅
2. ``mindforge --help`` ✅
3. ``mindforge approve --help`` ✅（list / show 子命令展示不变）
4. ``mindforge approve list --config configs/mindforge.yaml --limit 2`` ✅
5. ``mindforge approve --config configs/mindforge.yaml --all --dry-run --limit 1`` ✅（``approve preview`` 不存在；用 ``--all --dry-run`` 替代）
6. ``mindforge recall --config configs/mindforge.yaml --query agent --include-drafts --limit 1`` ✅
7. ``mindforge review weekly --config configs/mindforge.yaml`` ✅
8. ``mindforge process --help`` ✅
9. ``mindforge obsidian next --vault examples/demo-vault`` ✅

## 10. 安全边界确认

- ❌ 未读真实 ``.env``
- ❌ 未调真实 LLM
- ❌ 未写正式 Obsidian notes
- ❌ 未自动 approve
- ❌ 未做 RAG / embedding
- ❌ 未做 Obsidian plugin / Web UI / TUI
- ❌ 未 push
- ❌ 未改 fake provider 默认安全路径
- ❌ 未引入新依赖（pyproject.toml 仅 version 字段变化）

## 11. 真实遗留问题

1. **cli.py 仍有 298 处 ``console.print``**：approve 区域抽走 27 处仅占
   ~9%。review / process / scan / config doctor / today / start /
   backup / obsidian 等 handler 仍内嵌 Rich 渲染。
2. **cli.py ``_format_card_created_at`` / ``_format_card_source_hint`` /
   ``_approve_next_command`` 现在是薄包装委托 presenter**：缺一个明确
   的"何时彻底删除"退役计划，否则就是死代码风险。
3. **CLI 黑盒 snapshot 测试只 1 条**：理想覆盖 4-5 条
   （list 空态 / bulk 空态 / show error / single approve outcome），
   目前只验证 ``approve list`` 空态字符串。
4. **approval_service 仍承担 6 个 dataclass + 7 个公开函数（312 行）**：
   未来若继续膨胀（plan/preview/list/lookup/execution）需要内部分包。
5. **process_service 自评 5/10 (CLI 变薄程度) 仍未复评**：v0.7.20 的
   process_service 是否已变成新巨石、是否值得做 ProcessExecutor，本轮
   没有再审。
6. **review weekly handler 仍是巨石**：cli.py ~1154-1812 段约 660 行
   内嵌渲染，是下一个最清晰的内聚 use-case。
7. **``mindforge commands`` 标题写死 ``v0.7.19 — 命令地图``**：与本轮
   无关但已观察到的版本号漂移债。
8. **``ARCHITECTURE.md`` 关于 ``obsidian.py`` "仍较宽" 的注释依旧
   存在**：本轮没动这块也没让它变好。

## 12. v0.7.22 候选方向（建议，**不实现**）

- **A. review_presenter extraction**（**推荐**）
- B. top-level CLI registry cleanup
- C. backup/export service extraction
- D. process_service deeper audit / ProcessExecutor extraction
- E. config doctor / today / start presenter cleanup

详见 v0.7.22 plan（待生成）。本 checkpoint 不进入 v0.7.22 实施。

## 13. 与 safety_policy 的关系

本轮 **不修改、不扩展** ``safety_policy.py``。``approve_presenter`` 不
调用 ``safety_policy`` 做控制流判断。本文档与测试可引用
``safety_policy.boundary_statement(
"human_approved_gate" / "no_real_llm" / "no_env_read")`` 作为对齐证据。
