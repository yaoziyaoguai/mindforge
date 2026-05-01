"""review_presenter — review weekly 的展示层。

中文学习型说明
================

为什么要这一层？
----------------
v0.7.21 之前，``review weekly`` handler 在 ``cli.py``（行 1588-1709）里
内嵌 125 行 Markdown 拼接 + JSON dict 构造 + 1 处 Rich ``console.print``，
和 Typer 参数 / RunLogger / IO 完成提示混在一起。

review weekly 的输入面已经成熟：``review_service.build_weekly_review``
返回 ``WeeklyReviewResult`` frozen dataclass，包含 7 段结构化结果
（overdue / due_this_week / reviewed_this_week / forgotten_or_partial /
suggested_focus_tracks / project_distribution / next_week_preview）。
service 端在 ``review_service.py`` 自声明"不依赖 Typer/Rich/console，
不负责 Markdown/JSON 渲染"。

这个 presenter 把展示职责正式离开 CLI，只把 ``WeeklyReviewResult``
转成 ``str``（Markdown）或 ``dict``（JSON），不接受 ``Console`` 参数、
不持有任何副作用。

为什么本轮只做 weekly？
----------------------
``review_app`` 共 6 个子命令（due / mark / schedule / backlog / stats /
weekly），但**只有 weekly 经过 ``review_service``**；其余 5 个 handler
直接 inline 调 ``iter_cards`` + ``filter_cards`` + datetime 排序 +
``_bucket_review`` + ``_render_ics``。这 5 个的展示输入面是裸
``list[CardSummary]``，没有 frozen dataclass。如果把它们一起 presenter
化，会等于把 inline 业务一起搬到 presenter，是机械搬运 + 边界污染。

正确顺序是：先扩 ``review_service`` 把这 5 个的聚合升级成结构化
result，再做 presenter 抽取。这是未来一轮治理。

边界（运行时禁止）
------------------
本模块**不允许**：

1. ``import typer``；
2. 持有 ``RunLogger``；
3. 调用 ``iter_cards`` / ``filter_cards``；
4. 调用 ``build_weekly_review`` / ``calculate_weekly_review_window``；
5. ``Path.read_text`` / ``Path.write_text`` / ``open(...)``；
6. 修改 card 状态 / approve / mark；
7. 调用真实 LLM；
8. ``import dotenv`` / 读取 ``.env``；
9. 写正式 Obsidian notes；
10. RAG / embedding；
11. 解析 CLI 参数；
12. 改变 ``review_service`` 公开 API；
13. 改变 ``human_approved`` / ``ai_draft`` 消费边界（本模块根本不消费
    card 状态，只读 ``WeeklyReviewResult`` frozen 字段）。

测试通过 AST 静态断言以上 import / 调用全部不出现。

输出策略
--------
- JSON：``build_weekly_review_json`` 返回 ``dict``，由 CLI 调
  ``json.dumps`` 序列化并 ``print``。本模块**不**自己调
  ``json.dumps``，让 CLI 控制 ``ensure_ascii`` / ``indent`` 等。
- Markdown：``render_weekly_review_markdown`` 返回 ``str``，由 CLI 调
  ``print()`` 或写 ``--output``。
- 无 ``Console`` 参数：weekly handler 全程使用 ``print()`` 而非
  ``console.print``（与 ``approve_presenter`` 不同）；尊重既有 IO 约定。

human_approved / ai_draft 边界
-------------------------------
本模块**不消费**任何 card 状态字段。``WeeklyReviewResult.approved_cards``
等已经是 service 层用 ``human_approved`` 选择 + ``ai_draft`` 排除后的
结果；presenter 只读不判。
"""

from __future__ import annotations

from typing import Any

from .cards import CardSummary
from .review_service import WeeklyReviewResult


def render_weekly_learning_tasks(
    overdue: list[CardSummary] | tuple[CardSummary, ...],
    due_this_week: list[CardSummary] | tuple[CardSummary, ...],
    forgotten_or_partial: list[CardSummary] | tuple[CardSummary, ...],
) -> str:
    """把 weekly review 数据压成"今天该做什么"的语言。

    迁移自 ``cli.py::_review_learning_tasks``。这里**不新增**任何调度
    算法，只把已有 frontmatter 汇总转成自然语言任务列表，避免越界成
    智能推荐或 LLM 复习教练。
    """

    tasks: list[str] = []
    if overdue:
        tasks.append(f"- 先处理 {len(overdue)} 张 overdue 卡片。")
    if due_this_week:
        tasks.append(f"- 本周安排 {len(due_this_week)} 张 due card。")
    if forgotten_or_partial:
        tasks.append(
            f"- 优先回看 {len(forgotten_or_partial)} 张 forgotten/partial 卡片。"
        )
    if not tasks:
        tasks.append(
            "- 当前没有明确复习任务；先 approve 新草稿或用 recall 找主题。"
        )
    return "\n".join(tasks) + "\n"


def render_weekly_next_actions(has_weekly_work: bool) -> list[str]:
    """review 空状态的下一步建议；只返回静态命令字符串列表。

    迁移自 ``cli.py::_review_next_actions``。**不**触发任何写操作，
    **不**调用 LLM，**不**读 ``.env``。
    """

    if has_weekly_work:
        return ["运行 `mindforge review due` 聚焦今天到期项。"]
    return [
        "运行 `mindforge approve list` 查看是否有 ai_draft 待人工批准。",
        "运行 `mindforge process --profile fake --limit 1` 从 inbox 生成新的 ai_draft。",
        "运行 `mindforge recall --query <keyword>` 从已批准卡片里找学习主题。",
    ]


def _safe_card_dict(card: CardSummary) -> dict[str, Any]:
    """把 CardSummary 压成只含安全 frontmatter 字段的 dict。

    本函数是 presenter 内部细节：只读 CardSummary 已经存在的安全字段，
    不读 card 正文。与 ``cli._card_to_safe_dict`` 字段集对齐，保持
    ``review weekly --format json`` 的字节级兼容。
    """

    return {
        "id": card.id,
        "title": card.title,
        "track": card.track,
        "projects": list(card.projects),
        "tags": list(card.tags),
        "value_score": card.value_score,
        "review_after": (
            card.review_after.isoformat() if card.review_after else None
        ),
        "review_count": card.review_count,
        "last_review_result": card.last_review_result,
        "rel_path": card.rel_path,
        "status": card.status,
        "source_type": card.source_type,
        "source_title": card.source_title,
    }


def build_weekly_review_json(result: WeeklyReviewResult) -> dict[str, Any]:
    """把 ``WeeklyReviewResult`` 转成 ``review weekly --format json`` 的 dict。

    schema 字段顺序与 v0.7.21 ``cli.py::review_weekly`` 内嵌实现严格一致，
    保持向后兼容（``version=1``）。本函数**不**调 ``json.dumps``，
    让 CLI 控制序列化参数。
    """

    return {
        "version": 1,
        "generated_at": result.window.generated_at.isoformat(timespec="seconds"),
        "window": {
            "week_start": result.window.week_start.date().isoformat(),
            "week_end": result.window.generated_at.date().isoformat(),
        },
        "overdue": [_safe_card_dict(c) for c in result.overdue],
        "due_this_week": [_safe_card_dict(c) for c in result.due_this_week],
        "reviewed_this_week_count": len(result.reviewed_this_week),
        "forgotten_or_partial": [
            _safe_card_dict(c) for c in result.forgotten_or_partial
        ],
        "suggested_focus_tracks": [
            {"track": item.track, "score": item.score}
            for item in result.suggested_focus_tracks
        ],
        "project_distribution": [
            {"project": item.project, "card_count": item.card_count}
            for item in result.project_distribution
        ],
        "next_week_preview": [_safe_card_dict(c) for c in result.next_week_preview],
        "next_actions": render_weekly_next_actions(result.has_weekly_work),
    }


def _list_cards_block(items: list[CardSummary] | tuple[CardSummary, ...]) -> str:
    """把卡片列表压成 Markdown 段落；空列表显示 ``_(none)_``。

    与 v0.7.21 ``review_weekly`` 内嵌 ``_list`` 字节级一致。
    """

    if not items:
        return "_(none)_\n"
    lines = [
        f"- [{c.id or c.path.stem}] {c.title or '(untitled)'}  "
        f"`track={c.track or '-'}` `last={c.last_review_result or '-'}` "
        f"`path={c.rel_path}`"
        for c in items
    ]
    return "\n".join(lines) + "\n"


def render_weekly_review_markdown(result: WeeklyReviewResult) -> str:
    """把 ``WeeklyReviewResult`` 渲染成 weekly review Markdown。

    输出与 v0.7.21 ``cli.py::review_weekly`` 内嵌 Markdown 字节级一致：

    - 7 段标题（Learning tasks / Overdue / Due this week / Reviewed this
      week / Forgotten · partial / Suggested focus tracks / Project
      distribution / Next week preview）
    - has_weekly_work=False 时追加 ``## Next action`` 段
    - 文末 ``## Workflow bridge`` 段 + ``_说明：本周报由 frontmatter ...
      不调用 LLM。_`` 边界声明
    """

    overdue = list(result.overdue)
    due_this_week = list(result.due_this_week)
    reviewed_this_week = list(result.reviewed_this_week)
    forgotten_or_partial = list(result.forgotten_or_partial)
    next_week_preview = list(result.next_week_preview)

    parts = [
        f"# Weekly Review · {result.window.generated_at.date().isoformat()}\n",
        f"_window: {result.window.week_start.date().isoformat()} → "
        f"{result.window.generated_at.date().isoformat()}_\n",
        "\n## Learning tasks\n",
        render_weekly_learning_tasks(overdue, due_this_week, forgotten_or_partial),
        f"\n## Overdue · {len(overdue)} 项\n",
        _list_cards_block(overdue),
        f"\n## Due this week · {len(due_this_week)} 项\n",
        _list_cards_block(due_this_week),
        f"\n## Reviewed this week · {len(reviewed_this_week)} 项\n",
        f"\n## Forgotten / partial · {len(forgotten_or_partial)} 项\n",
        _list_cards_block(forgotten_or_partial),
        "\n## Suggested focus tracks\n",
        (
            "\n".join(
                f"- {item.track} (score={item.score})"
                for item in result.suggested_focus_tracks
            )
            + "\n"
        )
        if result.suggested_focus_tracks
        else "_(none)_\n",
        "\n## Project distribution\n",
        (
            "\n".join(
                f"- {item.project}: {item.card_count}"
                for item in result.project_distribution
            )
            + "\n"
        )
        if result.project_distribution
        else "_(none)_\n",
        f"\n## Next week preview · {len(next_week_preview)} 项\n",
        _list_cards_block(next_week_preview),
        (
            "\n## Next action\n"
            + "\n".join(
                f"- {a}" for a in render_weekly_next_actions(result.has_weekly_work)
            )
            + "\n"
            if not result.has_weekly_work
            else ""
        ),
        "\n## Workflow bridge\n",
        "- review 只使用 human_approved 卡片；新资料先 process 成 ai_draft，"
        "再由你显式 approve。\n"
        "- 找不到复习方向时，先运行 `mindforge recall --query <keyword>` 定位卡片，"
        "再回到 `mindforge review weekly`。\n",
        "\n_说明：本周报由 frontmatter 结构化汇总生成，**不**调用 LLM。_\n",
    ]
    return "".join(parts)
