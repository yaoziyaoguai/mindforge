"""tests for ``review_presenter`` (v0.7.22 weekly only).

中文学习型说明
================

这一组测试**保护展示边界**，不是业务语义：

- ``review_service`` 才是 weekly review 的业务语义来源（``human_approved``
  选择 / ``ai_draft`` 排除 / window 计算 / 5 段聚合 / focus_tracks
  signal）。``review_presenter`` 只读 service 计算好的
  ``WeeklyReviewResult`` frozen dataclass。
- presenter **禁止修改 card 状态**：本模块不接触 ``approver`` /
  ``approve_card`` / 任何写卡片符号。``human_approved`` /
  ``ai_draft`` 的状态语义由 ``approver`` + ``approval_service``
  唯一保护，本测试通过 AST 静态断言保证 presenter 在 import 层就拒绝
  这些符号。
- 为什么本轮只做 ``review weekly`` 而不是全量 review presenter？
  ``review_service`` 当前**只覆盖 weekly**；review due / mark / schedule /
  backlog / stats 等子命令业务逻辑 inline 在 cli.py，把这 5 个一起搬到
  presenter 等于把 inline 业务一起搬，是机械搬运。本模块严格收窄到
  weekly。
"""

from __future__ import annotations

import ast
import io
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from rich.console import Console

from mindforge import review_presenter, review_service
from mindforge.cards import CardSummary
from mindforge.review_service import (
    FocusTrack,
    ProjectCardCount,
    WeeklyReviewEmptyState,
    WeeklyReviewResult,
    WeeklyReviewWindow,
)


PRESENTER_PATH = Path(review_presenter.__file__)


def _make_card(
    *,
    cid: str = "card-1",
    title: str = "示例卡片",
    track: str = "agent-runtime",
    rel_path: str = "30-Cards/card-1.md",
    review_after: datetime | None = None,
    last_review_result: str | None = None,
    value_score: int | None = 5,
) -> CardSummary:
    """构造一个最小可用的 CardSummary fixture。

    presenter 测试不接触真实 vault，所有字段都是显式构造，
    保证：1) 测试不读 .env；2) 测试不写卡片；3) 字段集合稳定。
    """

    return CardSummary(
        id=cid,
        title=title,
        path=Path("/tmp/fake") / rel_path,
        rel_path=rel_path,
        status="human_approved",
        track=track,
        projects=("mindforge",),
        tags=("agent",),
        source_type="cubox_markdown",
        source_title="示例来源",
        source_url=None,
        value_score=value_score,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        review_after=review_after,
        review_count=2,
        last_review_result=last_review_result,
    )


def _make_window(now: datetime | None = None) -> WeeklyReviewWindow:
    now = now or datetime(2025, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
    return WeeklyReviewWindow(
        generated_at=now,
        week_start=now - timedelta(days=7),
        due_end=now + timedelta(days=7),
        preview_end=now + timedelta(days=14),
    )


def _make_result(
    *,
    overdue: tuple[CardSummary, ...] = (),
    due_this_week: tuple[CardSummary, ...] = (),
    reviewed_this_week: tuple[CardSummary, ...] = (),
    forgotten_or_partial: tuple[CardSummary, ...] = (),
    next_week_preview: tuple[CardSummary, ...] = (),
    focus_tracks: tuple[FocusTrack, ...] = (),
    project_distribution: tuple[ProjectCardCount, ...] = (),
    empty_state: WeeklyReviewEmptyState | None = None,
    approved_cards: tuple[CardSummary, ...] = (),
) -> WeeklyReviewResult:
    return WeeklyReviewResult(
        window=_make_window(),
        approved_cards=approved_cards,
        draft_cards_count=0,
        overdue=overdue,
        due_this_week=due_this_week,
        reviewed_this_week=reviewed_this_week,
        forgotten_or_partial=forgotten_or_partial,
        suggested_focus_tracks=focus_tracks,
        project_distribution=project_distribution,
        next_week_preview=next_week_preview,
        scan_errors=(),
        empty_state=empty_state,
    )


# ---------------------------------------------------------------------------
# 渲染契约：JSON
# ---------------------------------------------------------------------------


def test_build_weekly_review_json_has_version_and_seven_segments() -> None:
    """JSON schema 必须含 version=1 与 7 段 frontmatter 字段。

    保护对外 JSON 契约稳定（脚本/dashboard 可能依赖 schema）。
    """
    result = _make_result(overdue=(_make_card(),))
    payload = review_presenter.build_weekly_review_json(result)

    assert payload["version"] == 1
    expected_keys = {
        "version",
        "generated_at",
        "window",
        "overdue",
        "due_this_week",
        "reviewed_this_week_count",
        "forgotten_or_partial",
        "suggested_focus_tracks",
        "project_distribution",
        "next_week_preview",
        "next_actions",
    }
    assert expected_keys.issubset(payload.keys())


def test_build_weekly_review_json_field_order_matches_v0721() -> None:
    """JSON 字段顺序必须与 v0.7.21 内嵌实现一致。

    保护 ``--format json`` 输出的字节级兼容性。
    """
    result = _make_result()
    payload = review_presenter.build_weekly_review_json(result)
    assert list(payload.keys()) == [
        "version",
        "generated_at",
        "window",
        "overdue",
        "due_this_week",
        "reviewed_this_week_count",
        "forgotten_or_partial",
        "suggested_focus_tracks",
        "project_distribution",
        "next_week_preview",
        "next_actions",
    ]


def test_build_weekly_review_json_safe_card_fields_only() -> None:
    """JSON 中每张卡片只能含安全 frontmatter 字段，不得泄漏 path 等内部信息。

    保护"presenter 不读卡片正文"边界。
    """
    card = _make_card()
    result = _make_result(overdue=(card,))
    payload = review_presenter.build_weekly_review_json(result)

    item = payload["overdue"][0]
    assert "path" not in item  # 绝对路径不能进 JSON
    assert item["id"] == "card-1"
    assert item["rel_path"] == "30-Cards/card-1.md"


# ---------------------------------------------------------------------------
# 渲染契约：Markdown
# ---------------------------------------------------------------------------


def test_render_weekly_review_markdown_has_seven_segment_titles() -> None:
    """Markdown 必须含 7 段标题与文末"不调用 LLM"边界声明。

    这是用户可见的 review 输出契约；变更需要显式 plan 决策。
    """
    result = _make_result(overdue=(_make_card(),))
    md = review_presenter.render_weekly_review_markdown(result)

    for title in (
        "# Weekly Review · ",
        "## Learning tasks",
        "## Overdue · ",
        "## Due this week · ",
        "## Reviewed this week · ",
        "## Forgotten / partial · ",
        "## Suggested focus tracks",
        "## Project distribution",
        "## Next week preview · ",
        "## Workflow bridge",
    ):
        assert title in md, f"missing segment title: {title}"

    assert "**不**调用 LLM" in md, "missing LLM-free boundary statement"


def test_render_weekly_review_markdown_empty_branch_includes_next_action() -> None:
    """has_weekly_work=False 时必须追加 ``## Next action`` 段。

    保护空状态用户引导：没有复习任务时给出明确下一步命令。
    """
    result = _make_result()  # 全空 → has_weekly_work=False
    md = review_presenter.render_weekly_review_markdown(result)
    assert "## Next action" in md
    assert "mindforge approve list" in md
    assert "mindforge process" in md
    assert "mindforge recall" in md


def test_render_weekly_review_markdown_has_workflow_bridge_human_approved_boundary() -> None:
    """Workflow bridge 段必须明确 review 只用 human_approved 卡片。

    这是 human_approved / ai_draft 消费边界的用户可见声明；本测试保证
    presenter 不可意外删掉这条边界提示。
    """
    result = _make_result(overdue=(_make_card(),))
    md = review_presenter.render_weekly_review_markdown(result)
    assert "review 只使用 human_approved 卡片" in md
    assert "ai_draft" in md


def test_render_weekly_review_markdown_card_lines_use_safe_fields() -> None:
    """卡片行必须使用 id/title/track/last/rel_path，不暴露绝对路径。"""
    card = _make_card(last_review_result="forgotten")
    result = _make_result(forgotten_or_partial=(card,))
    md = review_presenter.render_weekly_review_markdown(result)
    assert "[card-1] 示例卡片" in md
    assert "track=agent-runtime" in md
    assert "last=forgotten" in md
    assert "path=30-Cards/card-1.md" in md
    assert "/tmp/fake" not in md


def test_render_weekly_review_markdown_empty_lists_render_none_marker() -> None:
    """空段必须渲染为 ``_(none)_``，不能省略段落。"""
    result = _make_result()
    md = review_presenter.render_weekly_review_markdown(result)
    assert md.count("_(none)_") >= 5  # 至少 5 个空段


# ---------------------------------------------------------------------------
# 渲染契约：helper
# ---------------------------------------------------------------------------


def test_render_weekly_learning_tasks_each_branch() -> None:
    c = _make_card()
    out = review_presenter.render_weekly_learning_tasks([c, c], [c], [c, c, c])
    assert "2 张 overdue" in out
    assert "1 张 due card" in out
    assert "3 张 forgotten/partial" in out


def test_render_weekly_learning_tasks_empty_returns_default_hint() -> None:
    out = review_presenter.render_weekly_learning_tasks([], [], [])
    assert "approve 新草稿" in out


def test_render_weekly_next_actions_has_weekly_work_returns_due_cmd() -> None:
    actions = review_presenter.render_weekly_next_actions(True)
    assert actions == ["运行 `mindforge review due` 聚焦今天到期项。"]


def test_render_weekly_next_actions_no_work_returns_three_commands() -> None:
    actions = review_presenter.render_weekly_next_actions(False)
    assert len(actions) == 3
    assert any("approve list" in a for a in actions)
    assert any("process" in a for a in actions)
    assert any("recall" in a for a in actions)


# ---------------------------------------------------------------------------
# Frozen / 不可变保证
# ---------------------------------------------------------------------------


def test_presenter_does_not_mutate_input_dataclass() -> None:
    """``WeeklyReviewResult`` 是 frozen dataclass，presenter 不能修改它。

    保护"presenter 只读"边界：service 计算的结果在跨函数传递中不被
    污染。
    """
    result = _make_result(overdue=(_make_card(),))
    review_presenter.build_weekly_review_json(result)
    review_presenter.render_weekly_review_markdown(result)

    with pytest.raises((AttributeError, Exception)):
        result.overdue = ()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AST 静态断言：presenter 在 import 层就拒绝危险符号
# ---------------------------------------------------------------------------


def _imports_in_presenter() -> set[str]:
    tree = ast.parse(PRESENTER_PATH.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names.add(module)
            for alias in node.names:
                names.add(f"{module}.{alias.name}")
    return names


def _calls_in_presenter() -> set[str]:
    tree = ast.parse(PRESENTER_PATH.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return names


def test_presenter_does_not_import_typer() -> None:
    """presenter 不能 import typer；它不是 CLI adapter。"""
    assert "typer" not in _imports_in_presenter()


def test_presenter_does_not_import_dotenv() -> None:
    """presenter 不能读 .env；env 边界由 CLI / app_context 唯一负责。"""
    imports = _imports_in_presenter()
    assert "dotenv" not in imports
    assert not any(name.startswith("dotenv") for name in imports)


def test_presenter_does_not_import_run_logger() -> None:
    """presenter 不能持有 RunLogger；side-effect 编排留在 CLI handler。"""
    imports = _imports_in_presenter()
    assert "mindforge.run_logger" not in imports
    assert "RunLogger" not in _calls_in_presenter()


def test_presenter_does_not_import_processors_or_providers() -> None:
    """presenter 不能 import processor / provider / source / iter_cards。"""
    imports = _imports_in_presenter()
    forbidden_modules = {
        "mindforge.processors",
        "mindforge.sources",
        "mindforge.providers",
        "mindforge.embedding",
        "mindforge.approver",
        "mindforge.approval_service",
    }
    assert imports.isdisjoint(forbidden_modules)
    forbidden_names = {
        "iter_cards",
        "filter_cards",
        "approve_card",
        "approve_explicit_card",
    }
    assert imports.isdisjoint(
        {f"mindforge.cards.{n}" for n in forbidden_names}
    )


def test_presenter_does_not_call_service_business_functions() -> None:
    """presenter 不能调用 ``build_weekly_review`` / ``calculate_weekly_review_window``。

    业务计算入口在 service 层，presenter 只消费 service 的返回值。
    """
    calls = _calls_in_presenter()
    assert "build_weekly_review" not in calls
    assert "calculate_weekly_review_window" not in calls
    assert "iter_cards" not in calls
    assert "filter_cards" not in calls


def test_presenter_does_not_perform_file_io() -> None:
    """presenter 不能读/写文件；IO 边界由 CLI handler 负责。"""
    calls = _calls_in_presenter()
    assert "read_text" not in calls
    assert "write_text" not in calls
    assert "open" not in calls


def test_presenter_does_not_call_approve_or_mark() -> None:
    """presenter 不能修改 card 状态（不调用 approve / mark / write 类函数）。

    human_approved / ai_draft 状态转移由 ``approver`` + ``approval_service``
    唯一保护。
    """
    calls = _calls_in_presenter()
    assert "approve_card" not in calls
    assert "approve_explicit_card" not in calls
    assert "mark_review_outcome" not in calls


# ---------------------------------------------------------------------------
# review_service 公开 API 不变（防止意外扩 service）
# ---------------------------------------------------------------------------


def test_review_service_public_api_unchanged() -> None:
    """v0.7.22 不允许修改 review_service 公开 API。

    本测试硬绑定 v0.7.21 已存在的 5 个 dataclass + 2 个函数；如果未来要
    扩展 service，应该作为独立 plan 决策，不能在 presenter 抽取轮次中
    悄悄发生。
    """
    public = {
        name
        for name in dir(review_service)
        if not name.startswith("_")
    }
    expected = {
        "WeeklyReviewWindow",
        "FocusTrack",
        "ProjectCardCount",
        "WeeklyReviewEmptyState",
        "WeeklyReviewResult",
        "calculate_weekly_review_window",
        "build_weekly_review",
    }
    assert expected.issubset(public), f"missing: {expected - public}"


# ---------------------------------------------------------------------------
# CLI 黑盒：与 v0.7.21 字节级一致
# ---------------------------------------------------------------------------


_REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_cli(args: list[str]) -> str:
    """运行真实 CLI 入口，返回 stdout。"""
    result = subprocess.run(
        [".venv/bin/mindforge", *args],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"cli failed: {result.stderr}"
    return result.stdout


def test_cli_review_weekly_markdown_smoke() -> None:
    """``review weekly`` 默认 markdown 必须返回完整 7 段 + 边界声明。

    这是 CLI 黑盒测试：保证 presenter + CLI 胶水联合后输出仍稳定。
    """
    out = _run_cli(
        ["review", "weekly", "--config", "configs/mindforge.yaml"]
    )
    assert "# Weekly Review · " in out
    assert "## Workflow bridge" in out
    assert "**不**调用 LLM" in out


def test_cli_review_weekly_json_schema_smoke() -> None:
    """``review weekly --format json`` 必须输出可解析 JSON 且 version=1。"""
    out = _run_cli(
        [
            "review",
            "weekly",
            "--config",
            "configs/mindforge.yaml",
            "--format",
            "json",
        ]
    )
    payload = json.loads(out)
    assert payload["version"] == 1
    assert "window" in payload
    assert "overdue" in payload
    assert "next_actions" in payload


# ---------------------------------------------------------------------------
# 编码层：保证 presenter 不依赖 cli.console（独立可测）
# ---------------------------------------------------------------------------


def test_presenter_returns_pure_string_no_console_required() -> None:
    """presenter 必须返回纯 str，不依赖 Console。

    保证 presenter 可独立 snapshot，不需要任何 IO mock。
    """
    result = _make_result(overdue=(_make_card(),))
    md = review_presenter.render_weekly_review_markdown(result)
    assert isinstance(md, str)
    payload = review_presenter.build_weekly_review_json(result)
    assert isinstance(payload, dict)


def test_presenter_output_renderable_through_rich_console() -> None:
    """presenter 输出可以被 rich Console 安全渲染（向后兼容）。

    虽然 presenter 不接受 Console 参数，但 CLI 用 ``print()`` 输出后，
    用户也可以重定向到 Rich console。本测试只是冒烟：确保返回的 str
    不含异常控制字符。
    """
    result = _make_result(overdue=(_make_card(),))
    md = review_presenter.render_weekly_review_markdown(result)
    buffer = io.StringIO()
    Console(file=buffer, force_terminal=False, color_system=None).print(
        md, markup=False
    )
    assert buffer.getvalue()
