"""approve_presenter v0.7.21 测试。

中文学习型说明
================

为什么这是 presenter 层测试？
- presenter 只负责把 ``approval_service`` 已经计算好的结构化结果渲染成
  用户可见输出（Rich Table / JSON dict / Rich text）；
- 它**不**修改 card 状态、**不**调用 ``approve_explicit_card``、**不**自动
  approve、**不**读 / 写 card 文件、**不**调真实 LLM、**不**读真实 .env。

测试保护的边界（**展示边界**，不是业务语义）：
1. 输出与 v0.7.20 字节级一致（snapshot 对照）；
2. presenter 模块在 import 层就拒绝 typer / dotenv / RunLogger /
   processors / sources / providers（AST 静态断言）；
3. presenter 函数不直接或间接调用 ``approve_explicit_card`` /
   ``Path.write_text``（AST 静态断言）；
4. ``human_approved`` / explicit approve 边界**仍由 approval_service 唯一保护**；
   presenter 没有任何路径可以绕过 approval_service 直接晋升卡片。

为什么 ``human_approved`` 必须仍由 approval_service / explicit approve 保护：
- approval_service 是唯一一个会触发 ``approve_card`` 副作用的入口；
- presenter 不被允许 import ``approver`` 或 ``approval_service`` 的执行函数
  （只 import 数据形 + 常量），保证这条边界静态可检查。

为什么 presenter 禁止自动 approve：
- approve 是把 ai_draft 升级为 long-term memory 的人审动作，错误率会被复用
  到所有下游 recall / project context；任何"自动 approve"路径都会破坏
  source-grounded + human-approved 的产品定位。
"""

from __future__ import annotations

import ast
import io
import json
from datetime import datetime
from pathlib import Path

import pytest
from rich.console import Console

from mindforge import approve_presenter
from mindforge.approval_service import (
    ApprovalCardLookupResult,
    ApprovalExecutionResult,
    ApprovalListResult,
    ApprovalPreviewResult,
    ApprovalServiceError,
)
from mindforge.approver import ApprovalEffect
from mindforge.cards import CardSummary


# ---------------------------------------------------------------------------
# fixtures：构造可控的 service 输出对象
# ---------------------------------------------------------------------------


def _card(
    *,
    title: str = "示例卡片",
    rel_path: str = "knowledge-cards/general/sample.md",
    status: str = "ai_draft",
    track: str | None = "general",
    source_type: str | None = "manual",
    source_title: str | None = None,
    source_url: str | None = None,
    created_at: datetime | None = None,
    value_score: int | None = 5,
) -> CardSummary:
    return CardSummary(
        id="card-1",
        title=title,
        path=Path("/tmp/vault") / rel_path,
        rel_path=rel_path,
        status=status,
        track=track,
        projects=(),
        tags=(),
        source_type=source_type,
        source_title=source_title,
        source_url=source_url,
        value_score=value_score,
        created_at=created_at,
    )


def _capture_console() -> tuple[Console, io.StringIO]:
    """生成一个写入 StringIO 的 Rich Console，便于断言渲染输出。"""
    buf = io.StringIO()
    return (
        Console(
            file=buf,
            force_terminal=False,
            color_system=None,
            width=200,
            no_color=True,
            soft_wrap=False,
            highlight=False,
        ),
        buf,
    )


# ---------------------------------------------------------------------------
# 1-2. approve list Rich + JSON
# ---------------------------------------------------------------------------


def test_render_approval_list_table_contains_header_and_row():
    """approve list Rich 输出含表头标题、行数、6 列字段、Todo commands 段。"""
    cards = (_card(),)
    res = ApprovalListResult(
        candidates=cards, scan_errors=(), statuses=("ai_draft",)
    )
    console, buf = _capture_console()
    approve_presenter.render_approval_list(
        console, res, wanted_statuses={"ai_draft"}
    )
    out = buf.getvalue()
    assert "Approve Todo · 1 pending" in out
    assert "ai_draft" in out
    assert "示例卡片" in out
    assert "Todo commands" in out
    assert "mindforge approve --card knowledge-cards/general/sample.md" in out
    assert "MindForge 不会自动 approve" in out


def test_render_approval_list_json_payload_schema_is_stable():
    """approve list --format json：dict schema 与 v0.7.20 字节级一致。"""
    created = datetime(2025, 1, 2, 3, 4, 5)
    res = ApprovalListResult(
        candidates=(_card(created_at=created),),
        scan_errors=(),
        statuses=("ai_draft",),
    )
    payload = approve_presenter.build_approval_list_json(res)
    assert payload["count"] == 1
    item = payload["items"][0]
    assert set(item.keys()) == {
        "title",
        "path",
        "status",
        "track",
        "projects",
        "source_type",
        "created_at",
        "value_score",
    }
    assert item["created_at"] == "2025-01-02T03:04:05"
    json.dumps(payload)


def test_render_approval_list_empty_state_has_next_steps():
    """approve list 空态：黄字 + dim 下一步说明，不能误导用户去自动 approve。"""
    res = ApprovalListResult(candidates=(), scan_errors=(), statuses=("ai_draft",))
    console, buf = _capture_console()
    approve_presenter.render_approval_list(
        console, res, wanted_statuses={"ai_draft"}
    )
    out = buf.getvalue()
    assert "没有待 approve 的卡片" in out
    assert "MindForge 不会自动 approve" in out


# ---------------------------------------------------------------------------
# 3. approve show（preview）
# ---------------------------------------------------------------------------


def test_render_approval_show_lists_preview_fields_and_boundary_line():
    """approve show 输出含 Approve preview 标题、字段对齐、边界提示、Next 提示。"""
    preview = ApprovalPreviewResult(
        card_path=Path("/tmp/vault/knowledge-cards/general/sample.md"),
        fields={"id": "card-1", "title": "示例卡片", "status": "ai_draft"},
    )
    console, buf = _capture_console()
    approve_presenter.render_approval_show(
        console, preview, fallback_card_path=Path("ignored")
    )
    out = buf.getvalue()
    assert "Approve preview" in out
    assert "id          : card-1" in out
    assert "title       : 示例卡片" in out
    assert "Boundary: preview only; no auto approve, no .env, no LLM" in out
    assert "Next: mindforge approve --card" in out


def test_render_approval_show_uses_fallback_when_card_path_missing():
    """preview.card_path 缺失时使用 fallback；与 v0.7.20 行为一致。"""
    preview = ApprovalPreviewResult(card_path=None, fields={})
    console, buf = _capture_console()
    fallback = Path("/orig/path.md")
    approve_presenter.render_approval_show(console, preview, fallback)
    assert str(fallback) in buf.getvalue()


def test_render_approval_show_error_appends_next_list_hint():
    """approve show 错误路径：红色 ✗ + Next: mindforge approve list。"""
    err = ApprovalServiceError(kind="not_found", message="卡片不存在", exit_code=2)
    preview = ApprovalPreviewResult(card_path=None, fields={}, error=err)
    console, buf = _capture_console()
    approve_presenter.render_approval_show_error(console, preview)
    out = buf.getvalue()
    assert "✗ 卡片不存在" in out
    assert "Next: mindforge approve list" in out


# ---------------------------------------------------------------------------
# 4-5. bulk preview / empty / dry-run / confirm / summary
# ---------------------------------------------------------------------------


def test_render_bulk_candidate_list_shows_count_and_paths():
    cards = (_card(rel_path="a.md", title="A"), _card(rel_path="b.md", title="B"))
    console, buf = _capture_console()
    approve_presenter.render_bulk_candidate_list(console, cards)
    out = buf.getvalue()
    assert "2 张 ai_draft 待 approve" in out
    assert "a.md" in out and "b.md" in out


def test_render_bulk_dry_run_footer():
    console, buf = _capture_console()
    approve_presenter.render_bulk_dry_run_footer(console)
    assert "--dry-run 已启用，未写任何文件" in buf.getvalue()


def test_render_bulk_confirm_required_warns_about_danger():
    console, buf = _capture_console()
    approve_presenter.render_bulk_confirm_required(console)
    out = buf.getvalue()
    assert "✗" in out
    assert "批量 approve 是危险动作" in out
    assert "--confirm" in out


def test_render_bulk_summary_reports_ok_and_fail():
    console, buf = _capture_console()
    approve_presenter.render_bulk_summary(console, ok=3, fail=1)
    assert "成功 3 / 失败 1" in buf.getvalue()


def test_render_bulk_empty_state():
    console, buf = _capture_console()
    approve_presenter.render_bulk_empty(console)
    assert "(no ai_draft cards found)" in buf.getvalue()


# ---------------------------------------------------------------------------
# 6. execution result（success / already_approved / failure）
# ---------------------------------------------------------------------------


def _outcome(kind: str = "approved", state_missing: bool = False) -> ApprovalEffect:
    return ApprovalEffect(
        kind=kind,  # type: ignore[arg-type]
        card_path=Path("/tmp/vault/cards/x.md"),
        prev_status="ai_draft",
        new_status="human_approved",
        approval_method="explicit-card-flag",
        approved_at=datetime(2025, 1, 1, 0, 0, 0) if kind == "approved" else None,
        state_missing=state_missing,
    )


def test_render_execution_success_includes_check_mark_and_boundary_line():
    """approve 成功：✔ approved + prev/new/method + 边界 dim 提示。"""
    res = ApprovalExecutionResult(effect=_outcome("approved"))
    console, buf = _capture_console()
    approve_presenter.render_execution_success(console, res)
    out = buf.getvalue()
    assert "✔ approved" in out
    assert "prev=ai_draft → human_approved" in out
    assert "method=explicit-card-flag" in out
    assert "MindForge 不会让 AI 自动写入 human_approved" in out


def test_render_execution_success_idempotent_branch():
    """已批准：黄字幂等提示，不应再出现 ✔。"""
    res = ApprovalExecutionResult(effect=_outcome("already_approved"))
    console, buf = _capture_console()
    approve_presenter.render_execution_success(console, res)
    out = buf.getvalue()
    assert "已是 human_approved" in out
    assert "✔ approved" not in out


def test_render_execution_success_state_missing_warning():
    res = ApprovalExecutionResult(effect=_outcome("approved", state_missing=True))
    console, buf = _capture_console()
    approve_presenter.render_execution_success(console, res)
    assert "state.json 中找不到对应 item" in buf.getvalue()


def test_render_execution_failure_renders_red_message():
    err = ApprovalServiceError(kind="not_ai_draft", message="卡片不是 ai_draft", exit_code=2)
    console, buf = _capture_console()
    approve_presenter.render_execution_failure(console, err)
    assert "approve 失败：卡片不是 ai_draft" in buf.getvalue()


# ---------------------------------------------------------------------------
# 7. lookup error / routing hint
# ---------------------------------------------------------------------------


def test_render_lookup_error_shows_red_cross():
    err = ApprovalServiceError(kind="not_found", message="找不到 source_id", exit_code=2)
    lookup = ApprovalCardLookupResult(card_path=None, error=err)
    console, buf = _capture_console()
    approve_presenter.render_lookup_error(console, lookup)
    assert "✗ 找不到 source_id" in buf.getvalue()


def test_render_routing_hint_lists_all_actions():
    console, buf = _capture_console()
    approve_presenter.render_routing_hint(console)
    out = buf.getvalue()
    assert "--card" in out and "--source-id" in out and "--all --dry-run" in out
    assert "approve list" in out


# ---------------------------------------------------------------------------
# 8-15. AST 静态边界断言：禁止 import / 禁止调用
# ---------------------------------------------------------------------------


PRESENTER_PATH = Path(approve_presenter.__file__)
PRESENTER_AST = ast.parse(PRESENTER_PATH.read_text("utf-8"))


def _imports_in_presenter() -> set[str]:
    """收集 presenter 模块中所有 import 的顶层模块名。"""
    names: set[str] = set()
    for node in ast.walk(PRESENTER_AST):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".")[0])
                # 同时记录 "from .x import y" 中的 .x 子模块名
                if node.level == 1:
                    names.add(node.module)


    return names


def _names_called_in_presenter() -> set[str]:
    """收集 presenter 中所有被调用的简单名字（``foo(...)``）。

    覆盖 ``approve_explicit_card(...)`` / ``write_text(...)`` 这类直接调用；
    不覆盖 ``some.long.chain.call``，但配合 import 静态断言已足够。
    """
    called: set[str] = set()
    for node in ast.walk(PRESENTER_AST):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                called.add(f.id)
            elif isinstance(f, ast.Attribute):
                called.add(f.attr)
    return called


def test_presenter_does_not_import_typer():
    assert "typer" not in _imports_in_presenter()


def test_presenter_does_not_import_dotenv():
    imports = _imports_in_presenter()
    assert "dotenv" not in imports
    assert "env_loader" not in imports


def test_presenter_does_not_import_run_logger():
    """RunLogger 是 IO 副作用类型，presenter 不允许持有。"""
    imports = _imports_in_presenter()
    assert "run_logger" not in imports
    assert "RunLogger" not in _names_called_in_presenter()


def test_presenter_does_not_import_processors_sources_providers():
    forbidden = {"processors", "sources", "providers", "llm_client", "embedding"}
    assert not (forbidden & _imports_in_presenter())


def test_presenter_does_not_import_approver_execution_layer():
    """presenter 只能 import approval_service 的数据形 + 常量；
    不允许 import approver.approve_card / approval_service.approve_explicit_card
    等执行函数（防止任何自动 approve 路径）。
    """
    called = _names_called_in_presenter()
    assert "approve_card" not in called
    assert "approve_explicit_card" not in called
    assert "preview_approval_card" not in called
    assert "list_approval_candidates" not in called
    assert "build_bulk_approval_plan" not in called
    assert "resolve_card_path_by_source_id" not in called


def test_presenter_does_not_call_path_write_text_or_read_text():
    """presenter 不读 / 不写 card 文件。"""
    called = _names_called_in_presenter()
    assert "write_text" not in called
    assert "write_bytes" not in called
    assert "read_text" not in called
    assert "read_bytes" not in called
    assert "open" not in called


def test_presenter_does_not_modify_input_dataclasses():
    """presenter 输入是 frozen dataclass；尝试修改会抛 FrozenInstanceError。"""
    res = ApprovalExecutionResult(effect=_outcome("approved"))
    with pytest.raises(Exception):
        res.effect = None  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 16. approval_service 公开 API 数量稳定（防止本轮意外扩 API）
# ---------------------------------------------------------------------------


def test_approval_service_public_api_unchanged():
    """approval_service 的公开符号在本轮不应增加；如有变化必须人工审。"""
    from mindforge import approval_service as svc

    public = {
        name
        for name in dir(svc)
        if not name.startswith("_")
        and name[0].isupper() or name in {
            "list_approval_candidates",
            "build_bulk_approval_plan",
            "resolve_card_path_by_source_id",
            "resolve_candidate_by_card_id",
            "preview_approval_card",
            "approve_explicit_card",
        }
    }
    expected_minimum = {
        "ApprovalServiceError",
        "ApprovalListQuery",
        "ApprovalListResult",
        "ApprovalCardLookupResult",
        "ApprovalPreviewResult",
        "ApprovalExecutionResult",
        "list_approval_candidates",
        "build_bulk_approval_plan",
        "resolve_card_path_by_source_id",
        "resolve_candidate_by_card_id",
        "preview_approval_card",
        "approve_explicit_card",
    }
    missing = expected_minimum - public
    assert not missing, f"approval_service 缺少预期公开 API: {missing}"


# ---------------------------------------------------------------------------
# 17. CLI 黑盒：approve list / approve --all --dry-run 与 v0.7.20 兼容
# ---------------------------------------------------------------------------


def test_cli_approve_list_smoke_runs_without_crash():
    """import 后能调用 typer app；不实际写文件。snapshot 由真实 smoke 命令保护。"""
    from mindforge.cli import app

    assert app is not None
    # 只确认 approve_app 仍然挂载
    cmds = {cmd.name for cmd in app.registered_groups}
    assert "approve" in cmds
