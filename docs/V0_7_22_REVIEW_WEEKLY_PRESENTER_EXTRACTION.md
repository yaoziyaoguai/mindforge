# v0.7.22 — Review Weekly Presenter Extraction

本轮把 ``cli.py::review_weekly``（行 1588-1709，125 行）的 Markdown /
JSON / Rich 展示职责抽到新模块 ``src/mindforge/review_presenter.py``。
这是 v0.7.13 ``recall_presenter`` / v0.7.21 ``approve_presenter`` 之后
第三个 presenter，按 use-case 分轮次推进 presenter 治理。

## 1. 本轮不是新功能

- 不新增 review 子命令
- 不改 ``--format markdown|json`` 选项 / 不引入新输出格式
- 不引入新依赖
- 不改变 ``review_service`` 公开 API（5 dataclass + 2 函数本轮零修改）
- 不引入 v0.8 Real LLM Opt-in / RAG / embedding / Obsidian plugin /
  Web UI / TUI

## 2. 本轮不是为了降低行数

cli.py 4609 → 4534 净减 ~75 行；同时 review_presenter.py +260（含大段
中文 docstring）+ tests +470 + docs +160 = **净行数明显增加**。本轮的
目标是模块边界清晰与展示层可独立 snapshot 测试，**不**是机械搬运。

`build_weekly_review_json` 把散在 cli.py 的字段拼接聚合成纯函数（明确
schema 责任）；`_safe_card_dict` 是 presenter 内部细节，与 cli.py 的
``_card_to_safe_dict`` **共享语义但不共享代码**——cli 的版本仍服务于其
他 5 个 review 子命令的内嵌 dict 拼接，本轮不动。

## 3. 为什么是 weekly only

``review_app`` 共 6 个子命令（due / mark / schedule / backlog / stats /
weekly），但只有 **weekly 经过 ``review_service``**：handler 调用
``build_weekly_review`` 取得 ``WeeklyReviewResult`` frozen dataclass。

其余 5 个子命令在 ``cli.py`` 内部直接调用 ``iter_cards`` +
``filter_cards`` + 自建 datetime 排序 + ``_bucket_review`` 分桶 +
``_render_ics`` 生成。它们的展示输入面是裸 ``list[CardSummary]``，
没有结构化 result。

如果把这 5 个一起 presenter 化，会等于把 inline 业务一起搬到 presenter
模块，破坏 presenter 边界、变成机械搬运。正确顺序是：先扩
``review_service`` 把这 5 个的聚合升级成 frozen dataclass，再做
presenter 抽取——这是未来一轮独立治理。

## 4. review_presenter 的职责

新增 ``src/mindforge/review_presenter.py``（约 260 行，含大段中文
docstring），4 个公开函数：

| API | 职责 |
|---|---|
| ``build_weekly_review_json(result)`` | 把 ``WeeklyReviewResult`` 转成 ``dict``（``version=1`` schema），由 CLI 调 ``json.dumps`` 序列化 |
| ``render_weekly_review_markdown(result)`` | 把 ``WeeklyReviewResult`` 渲染成 Markdown ``str``，含 7 段标题 + Workflow bridge + LLM-free 边界声明 |
| ``render_weekly_learning_tasks(overdue, due, forgotten)`` | "今天该做什么"自然语言任务列表（迁移自 ``cli._review_learning_tasks``） |
| ``render_weekly_next_actions(has_weekly_work)`` | 空状态下一步建议命令列表（迁移自 ``cli._review_next_actions``） |

约定：presenter 返回 ``str`` / ``dict``，**不**接受 ``Console`` 参数
（与 ``approve_presenter`` 不同）；尊重 ``review weekly`` 既有的
``print()`` IO 约定，不引入 Rich console 依赖。

## 5. review_presenter 不负责什么

静态保证（AST 测试断言）：

- 不 ``import typer``
- 不 ``import dotenv``
- 不 ``import RunLogger`` / ``mindforge.run_logger``
- 不 ``import processors`` / ``sources`` / ``providers`` /
  ``embedding`` / ``approver`` / ``approval_service``
- 不调 ``build_weekly_review`` / ``calculate_weekly_review_window`` /
  ``iter_cards`` / ``filter_cards``
- 不调 ``approve_card`` / ``approve_explicit_card`` /
  ``mark_review_outcome``
- 不调 ``Path.read_text`` / ``Path.write_text`` / ``open(...)``

运行时保证：

- 不修改 ``WeeklyReviewResult`` frozen dataclass
- 不读 / 不写 card 文件
- 不修改 card 状态 / 不 approve / 不 mark
- 不调真实 LLM / 不读真实 ``.env`` / 不写正式 Obsidian notes
- 不做 RAG / embedding
- 不解析 CLI 参数
- 不抛 ``typer.Exit``

## 6. review_service 与 review_presenter 的边界

| 关注点 | 归属 | 备注 |
|---|---|---|
| review window 计算 | review_service | ``calculate_weekly_review_window`` |
| ``human_approved`` 选择 / ``ai_draft`` 排除 | review_service | 在 ``build_weekly_review`` 内 |
| 7 段聚合（overdue/due/reviewed/forgotten/focus/project/preview） | review_service | 返回 ``WeeklyReviewResult`` frozen 字段 |
| focus track 计数 signal | review_service | ``FocusTrack`` dataclass |
| project distribution 计数 | review_service | ``ProjectCardCount`` dataclass |
| Markdown 7 段拼接 | **review_presenter** | ``render_weekly_review_markdown`` |
| JSON dict schema | **review_presenter** | ``build_weekly_review_json``（``version=1``） |
| "今天该做什么"自然语言任务 | **review_presenter** | ``render_weekly_learning_tasks`` |
| 空状态下一步命令 | **review_presenter** | ``render_weekly_next_actions`` |
| 安全字段过滤（CardSummary → dict） | **review_presenter** 内部 | ``_safe_card_dict``，不暴露绝对 path |
| ``[green]✓[/]`` IO 完成提示 | CLI handler | 留 CLI；这是 IO 完成，非展示 |
| ``--format`` / ``--output`` 分发 | CLI handler | 留 CLI |

review_service 公开 API **本轮零变化**（测试
``test_review_service_public_api_unchanged`` 静态保护）。

## 7. CLI 现在少承担什么

cli.py::review_weekly handler 以下职责已下沉到 presenter：

- ~125 行 Markdown 拼接（7 段标题 + 卡片行 + Workflow bridge + LLM-free
  声明）
- JSON dict 字段构造（含安全字段过滤）
- 空状态 ``## Next action`` 段
- ``_review_learning_tasks`` / ``_review_next_actions`` 函数（迁移
  到 presenter；cli.py 中保留薄包装）

CLI 仍负责：

- Typer 参数（``--config`` / ``--format`` / ``--output``）
- ``_load_cfg`` 与配置解析
- ``build_weekly_review(cfg)`` 调用
- ``RunLogger`` emit
- ``--format`` 分发与 ``json.dumps`` 序列化（CLI 控制 ``ensure_ascii``
  / ``indent``）
- ``print()`` 实际 IO
- ``--output`` 文件写入 + ``[green]✓[/]`` 完成提示
- ``typer.Exit`` 与 exit code

## 8. JSON / Markdown / Rich 输出如何归属

- **JSON**：``build_weekly_review_json`` 是纯函数返回 ``dict``；
  CLI 调 ``json.dumps(payload, ensure_ascii=False, indent=2)`` 序列化
  并 ``print``。presenter 不调 ``json.dumps``，让 CLI 控制序列化参数。
- **Markdown**：``render_weekly_review_markdown`` 返回 ``str``，CLI
  直接 ``print(out)`` 或 ``output_path.write_text(out, ...)``。
- **Rich**：本 handler 唯一 Rich 输出是 ``[green]✓[/green] 已写入``
  IO 完成提示，**留在 CLI**——这是 IO 反馈不是 weekly 展示。

## 9. 为什么没有改变 review 业务语义

- ``review_service.py`` 模块本轮 git diff 为空。
- ``approver.py`` 本轮零修改。
- ``human_approved`` / ``ai_draft`` 状态转移仍由 ``approver`` +
  ``approval_service`` 唯一执行；review_presenter 在 import 层就拒绝
  这些符号。
- presenter 不消费 card 状态字段；只读 ``WeeklyReviewResult`` 已经过
  service 层 ``human_approved`` 选择 + ``ai_draft`` 排除后的结果。
- CLI 黑盒输出与 v0.7.21 字节级一致（手动 diff 验证 + 2 项
  ``test_cli_review_weekly_*_smoke``）。

## 10. 为什么没有改变 human_approved / ai_draft 消费边界

- review_service 在 ``build_weekly_review`` 内做 ``status='human_approved'``
  过滤；本轮**零修改** service。
- presenter 只读 ``WeeklyReviewResult.overdue`` 等 tuple 字段，
  里面已经是 human_approved 卡片。
- presenter Workflow bridge 段保留 v0.7.21 原文："review 只使用
  human_approved 卡片；新资料先 process 成 ai_draft，再由你显式
  approve"。这是用户可见的边界声明，本轮硬性 snapshot 保护。

## 11. 后续仍需治理什么

- **review_service 扩展**（先于其余 5 个 presenter）：把
  ``review due`` / ``review schedule`` / ``review backlog`` /
  ``review stats`` 的 inline 聚合升级成 frozen dataclass result，
  让它们具备和 weekly 同等的 shape-ready 输入面。
- **review_mark presenter / review_schedule_ics presenter**：``review
  mark`` 涉及写 frontmatter，需要先确认它经 ``approver`` 写而非
  inline 写；``--ics`` 输出有自己的格式契约。
- **process_presenter / scan_presenter / config_presenter**：cli.py 仍
  有 ~298 处 ``console.print``，按 use-case 分轮次推进。
- **``mindforge commands`` 标题写死 ``v0.7.19``**：版本号漂移债
  （v0.7.21 checkpoint 已记录）。

## 与 safety_policy 的关系

本轮 **不修改、不扩展** ``safety_policy.py``。``review_presenter`` 不
调用 ``safety_policy`` 做控制流判断。本文档与测试可引用
``safety_policy.boundary_statement(
"human_approved_gate" / "no_real_llm" / "no_env_read")`` 作为对齐证据。
