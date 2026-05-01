# v0.7.22 Review Weekly Presenter — Checkpoint

本文档是 v0.7.22 发布后的**架构治理 checkpoint**，对 ``review_presenter``
（仅 weekly 段）抽取做一次独立审计与归档。它**不是**新版本说明，本身
**不引入任何代码变更**。

发布说明见 ``docs/V0_7_22_REVIEW_WEEKLY_PRESENTER_EXTRACTION.md``。

## 1. 标识

- commit: ``1288539``
- tag: ``v0.7.22``
- 上一个 tag: ``v0.7.21`` (approve_presenter 抽取)
- 状态：本地 commit + tag，**未 push**

## 2. 本轮目标

把 ``cli.py::review_weekly`` handler（行 1588-1709，约 125 行
Markdown 拼接 + JSON dict 构造 + 1 处 ``console.print``）的**展示职责**
抽到新模块 ``src/mindforge/review_presenter.py``，与 v0.7.13
``recall_presenter`` 与 v0.7.21 ``approve_presenter`` 同构。

边界继续向"高内聚 / 低耦合 / 职责清晰"收敛：

- ``review_service`` 只负责 weekly 业务语义（聚合、统计、过滤）
- ``review_presenter`` 只负责 weekly 展示（markdown / JSON / 文案）
- ``cli.py::review_weekly`` 只负责参数解析 + 调 service + 调 presenter + IO

## 3. 本轮不是什么

- **不是新功能**：``review weekly`` 命令、参数（``--config`` /
  ``--format json`` 等）、退出码、stdout 字节级保持。byte-diff 通过
  v0.7.21 git snapshot 验证 markdown / json **完全一致**。
- **不是降行数 KPI**：cli.py 4609 → 4533（-76），但 presenter +273、
  tests +534、docs +179；**净行数明显增加**。本轮目标是模块边界，
  不是物理体积。
- **不是机械搬运**：抽出的 4 个 presenter 公开函数对应 weekly 输出的
  4 个语义阶段（learning_tasks / next_actions / json_dict /
  markdown），不是逐行搬 ``console.print``。``_safe_card_dict`` 是
  field 白名单聚合，``_list_cards_block`` 是 markdown bullet 模板，
  都是真实有内聚的 helper，不是贫血 wrapper。

## 4. 为什么本轮严格 weekly only

``review_app`` 共 6 个子命令，但 service 化程度极不均衡：

| 子命令 | 行 | service 化 | 是否走 review_service |
|---|---|---|---|
| weekly | 1588-1709 | ✅ | ``build_weekly_review`` |
| due | 1087-1180 | ❌ | inline ``iter_cards``+``filter_cards`` |
| mark | 1182-1236 | ❌ | inline 状态更新 |
| schedule | 1260-1372 | ❌ | inline ``iter_cards``+``filter_cards``+``_render_ics`` |
| backlog | 1374-1446 | ❌ | inline ``iter_cards``+``filter_cards``+``_bucket_review`` |
| stats | 1448-1524 | ❌ | inline ``iter_cards``+``filter_cards``+``_bucket_review`` |

强行把这 5 个 inline handler 的展示也搬进 review_presenter 会造成：

1. presenter 直接读卡 / 调 ``iter_cards`` —— 越界；
2. presenter 持有 ``filter_cards``+``_bucket_review`` 业务过滤 —— 污染纯展示；
3. presenter 边界变模糊，重蹈"小巨石"覆辙。

正确顺序是**先扩 review_service 接管这 5 个 handler 的业务语义**（输出
frozen dataclass），**再**做对应 presenter。本轮严格 weekly only，
是对架构边界的尊重，不是工作偷懒。

## 5. review_presenter 承担

新增模块 ``src/mindforge/review_presenter.py``（273 行），4 个公开
API + 2 个内部 helper：

| 类别 | API | 输出 |
|---|---|---|
| weekly markdown | ``render_weekly_review_markdown(result)`` | ``str`` |
| weekly JSON | ``build_weekly_review_json(result)`` | ``dict`` |
| 子段（学习任务） | ``render_weekly_learning_tasks(overdue, due, forgotten)`` | ``str`` |
| 子段（下一步） | ``render_weekly_next_actions(has_weekly_work)`` | ``str`` |
| 内部 | ``_safe_card_dict(card)`` | ``dict``（白名单字段）|
| 内部 | ``_list_cards_block(items)`` | ``str``（markdown bullet）|

约定（与 ``approve_presenter`` v0.7.21 **有意差异**）：weekly handler
全程使用 ``print()`` 而非 ``console.print``，因此 presenter
**不接受 ``Console`` 参数**，直接返回纯 ``str`` / ``dict``。
``json.dumps`` 由 CLI 控制（保留 ``ensure_ascii`` / ``indent`` 决策权）。

## 6. review_presenter 不承担

由 AST 静态断言强制（``tests/test_review_presenter.py`` 7 项）：

- 不 ``import typer``
- 不 ``import dotenv``
- 不 ``import RunLogger`` / ``run_logger``
- 不 ``import processors`` / ``sources`` / ``providers``
- 不 ``import approver`` / ``approval_service`` / ``embedding``
- 不调 ``build_weekly_review`` / ``calculate_weekly_review_window``
- 不调 ``iter_cards`` / ``filter_cards``
- 不调 ``approve_card`` / ``approve_explicit_card`` / ``mark_review_outcome``
- 不 ``Path.read_text`` / ``Path.write_text`` / ``open(...)``

实际 import 仅有：``__future__`` / ``typing`` / ``cards`` / ``review_service``。

## 7. review_service / review_presenter / cli.py 边界

```
                参数解析 + IO + side-effect
              ┌──────────────────────────────┐
   user ───►  │  cli.py::review_weekly       │ ────► stdout
              └─────┬─────────────────┬──────┘
                    │                 │
        业务聚合     │                 │  纯展示
                    ▼                 ▼
        ┌──────────────────┐  ┌──────────────────────┐
        │ review_service   │  │ review_presenter     │
        │ build_weekly_    │  │ render_weekly_       │
        │ review() ───────►│──┤ review_markdown()    │
        │ → WeeklyReview   │  │ build_weekly_review_ │
        │   Result (frozen)│  │ json()               │
        └──────────────────┘  └──────────────────────┘
              │                       │
              ▼                       ▼
        cards / 文件 IO          只读 dataclass，
        / status 过滤            不读卡 / 不写文件
```

关键约束：

- review_presenter **只**消费 ``WeeklyReviewResult`` frozen dataclass
- review_service 是**唯一** weekly 业务语义来源
- cli.py 不再持有 markdown / JSON 拼接，只做"取数据 → 渲染 → 输出"

## 8. human_approved / ai_draft 消费边界

人工确认边界**完全保持不变**：

- 仍由 ``review_service.build_weekly_review`` 在内部以
  ``status="human_approved"`` 过滤 ``filter_cards``
- ``ai_draft`` 不会出现在 weekly 报告
- presenter 是只读消费者，**没有任何状态判断**
- 全链路无自动 approve / 无 status mutation

## 9. 新增 / 修改测试

新增 ``tests/test_review_presenter.py``（534 行，25 项全部通过）：

| 类别 | 数量 |
|---|---|
| Markdown 渲染 | 5 |
| JSON schema | 3 |
| Helper（_safe_card_dict / _list_cards_block） | 4 |
| frozen result 兼容 | 1 |
| AST 静态边界（imports + calls） | 7 |
| review_service 公开 API 稳定性 | 1 |
| CLI 黑盒（markdown + JSON）| 2 |
| Unicode 兼容 | 1 |
| Rich/纯 print 兼容 | 1 |

无任何已有测试被弱化、跳过、xfail 或删除。

## 10. 质量门 + smoke 结果

- ``ruff check .`` ✅ All checks passed
- ``pytest`` ✅ **559 passed / 2 skipped**（v0.7.21 是 534 + 25 项 review presenter 测试）
- ``git diff --check`` ✅ 无 trailing whitespace / conflict marker
- 8 条 smoke 全绿：
  - ``commands`` / ``--help`` / ``review --help``
  - ``review weekly --config configs/mindforge.yaml``
  - ``approve list --config ... --limit 2``
  - ``recall --query agent --include-drafts --limit 1``
  - ``process --help``
  - ``obsidian next --vault examples/demo-vault``
- byte-level diff vs v0.7.21（独立 venv snapshot）：markdown
  **IDENTICAL**，``--format json`` **IDENTICAL**

## 11. 安全边界确认

| # | 项 | 状态 |
|---|---|---|
| 1 | 未读取真实 .env | ✅ |
| 2 | 未调用真实 LLM | ✅ |
| 3 | 未写正式 Obsidian notes | ✅ |
| 4 | 未自动 approve | ✅ |
| 5 | 未做 RAG / embedding | ✅ |
| 6 | 未做 Obsidian plugin | ✅ |
| 7 | 未做 Web UI / TUI | ✅ |
| 8 | 未 push | ✅ |
| 9 | 未改 fake provider 默认安全路径 | ✅ |
| 10 | 未引入新重依赖 | ✅ |
| 11 | 未改 review_service 业务语义（``git diff aa39f07..HEAD`` 0 行）| ✅ |
| 12 | 未改 human_approved / ai_draft 消费边界 | ✅ |

## 12. 真实遗留问题

1. **review 5 个子命令业务仍 inline 在 cli.py**（due/mark/schedule/
   backlog/stats，约 412 行混合业务+展示）。它们都直接 inline 调
   ``iter_cards`` + ``filter_cards(status="human_approved")`` +
   ``_bucket_review`` —— 是 review_service 的天然下一阶段治理对象，
   但本轮严格不动。
2. ``_card_to_safe_dict``（cli.py）与 ``_safe_card_dict``（presenter）
   字段集对齐但分两处定义。本轮有意保持，因 cli 版仍服务于 5 个
   inline handler；service 化后可统一。
3. ``_review_learning_tasks`` / ``_review_next_actions`` 在 cli.py
   仍保留为薄包装委托给 presenter（向后兼容）。未来若确认无外部
   引用可删除。
4. process / scan / config doctor 等命令仍内嵌 ``console.print``，
   presenter 层在 review/approve/recall 之外仍不完整。
5. ``process_service.py`` 自 v0.7.20 抽出后已 366 行，是否累积过多
   编排职责需独立 audit；本轮无量化证据。
6. ``backup_export``（cli.py 2161-2253，约 92 行单 use-case）是
   未来 backup_service 的清晰候选，但本轮不动。
7. cli.py 仍 4533 行，``commands`` / ``today`` / ``start`` 等顶层
   命令大量堆积。是否做 top-level CLI registry cleanup 需谨慎评估
   —— 极易滑向机械搬文件。

## 13. v0.7.23 候选方向 + 推荐

| 方向 | 评估 |
|---|---|
| A. top-level CLI registry cleanup | ❌ 高风险机械搬运。无明确边界改进。 |
| B. backup/export service extraction | ⚠️ 单 use-case ~92 行，边界清晰但收益小。可作 v0.7.24 候选。 |
| C. process_service deeper audit / ProcessExecutor | ⚠️ process_service 366 行，未见明显巨石信号；先做只读 audit 更稳妥，但本身价值有限。 |
| D. review_service existing-scope hardening（接管 due/mark/schedule/backlog/stats 已存在的 inline 业务语义） | ✅ **推荐** |

**推荐 D**，理由：

1. **是治理已有逻辑，不是新功能**：5 个 handler 当前已 inline 实现
   （行 1087/1182/1260/1374/1448），都在调用 ``iter_cards`` +
   ``filter_cards(status="human_approved")`` + ``_bucket_review``。
   抽到 review_service 是**把已经存在的业务语义聚合到正确的位置**，
   不是引入任何新能力、新输出、新 CLI 命令、新参数。
2. **直接服务高内聚 / 低耦合**：``_bucket_review`` 当前在 cli.py
   1237 行，是典型的"业务函数被业务函数包围"，应属 review_service
   私有 helper；service 化后单元测试可独立覆盖 5 种 bucket 边界。
3. **解锁后续 presenter 化**：service 化后，5 个 handler 的展示
   可在未来一轮顺势进入 review_presenter，与 weekly 共享
   ``_safe_card_dict`` / ``_list_cards_block``，并消除遗留问题 2。
4. **CLI 外部行为不变**：service 化是输入面对齐，不改 stdout 字节、
   不改参数、不改退出码。byte-diff 验证策略可继续复用。
5. **不触碰真实 LLM / .env / Obsidian / RAG / plugin / Web UI**。

## 14. 对 due/schedule/backlog/stats 是否属于新功能的判断

**结论：不属于新功能。**

依据：

- 这 5 个子命令**当前都已存在于 cli.py 并对外可调用**
  （``mindforge review due/mark/schedule/backlog/stats``）
- 它们的业务逻辑（``iter_cards`` + ``filter_cards`` +
  ``_bucket_review`` + ``_render_ics``）**当前都已实现**，只是
  inline 写在 CLI handler 中
- v0.7.23 的工作是**把已有的业务语义搬到 review_service 里聚合**，
  并保持 CLI 字节级不变

如果工作变成"为 stats 增加新统计维度"、"为 schedule 增加新输出格式"、
"为 due 增加新过滤参数"，则属新功能，必须停止。v0.7.23 plan 必须
**显式禁止**任何这类扩展，并以 byte-diff 持续验证。

---

**Checkpoint 结束。本文档不引入任何代码变更，仅作为 v0.7.22 的独立
审计与归档。**
