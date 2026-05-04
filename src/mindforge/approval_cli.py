"""Approval Typer adapter.

中文学习型说明：本模块只承载 ``mindforge approve`` 命令族的 CLI 适配：
参数接收、调用 approval_service、调用 approve_presenter、写 RunLogger。
真正的状态晋升规则仍在 approval_service / approver，避免把人工审批边界
散落回 root cli.py。
"""
from __future__ import annotations

from pathlib import Path

import typer

from .cli_runtime import console, load_cfg
from .config import MindForgeConfig
from .run_logger import RunLogger

# ---------------------------------------------------------------------------
# approve — M3 反 AI 污染闸门：显式人工把 ai_draft 卡片晋升为 human_approved
# 详见 docs/M3_HUMAN_APPROVAL_PROTOCOL.md
# ---------------------------------------------------------------------------


approve_app = typer.Typer(
    no_args_is_help=False,
    help=(
        "把 Knowledge Card 从 ai_draft 显式晋升为 human_approved。\n\n"
        "为什么 approve 必须是显式人工动作：\n"
        "  - long-term memory 的入口；批准的卡片会进入 recall / project context 的"
        "正式输出，会被复用到多个项目，影响后续判断。\n"
        "  - 如果允许 LLM 自动 approve，AI 误差会被无限放大；MindForge 的"
        "差异化前提之一就是 source-grounded + human-approved。\n\n"
        "常用：\n"
        "  approve --card <path>     — 单卡晋升（最安全主路径）\n"
        "  approve --source-id <id>  — 基于 state.json 反查卡片再晋升\n"
        "  approve list              — 列出可 approve 的 ai_draft 卡片（安全摘要）\n"
        "  approve --all --dry-run   — 预览批量晋升（不写文件）\n"
    ),
)

def _do_single_approve(
    card_path: Path,
    cfg: MindForgeConfig,
) -> None:
    """单卡晋升执行体（callback / source-id 路径共用）。"""
    from .approval_service import approve_explicit_card
    from .approve_presenter import (
        render_execution_failure,
        render_execution_success,
    )

    with RunLogger(cfg.state.runs_path, command="approve") as logger:  # type: ignore[attr-defined]
        logger.emit("approval_started", card_path=str(card_path))
        result = approve_explicit_card(cfg, card_path)
        if result.error is not None:
            logger.emit(
                "approval_failed",
                card_path=str(card_path),
                error_message=result.error.message,
                prev_status=result.error.prev_status or "",
            )
            render_execution_failure(console, result.error)
            raise typer.Exit(code=result.error.exit_code)

        assert result.effect is not None
        effect = result.effect

        completed_fields: dict[str, object] = {
            "card_path": str(effect.card_path),
            "status": effect.new_status,
            "prev_status": effect.prev_status,
            "approval_method": effect.approval_method,
            "idempotent": effect.kind == "already_approved",
        }
        if effect.approved_at is not None:
            completed_fields["approved_at"] = effect.approved_at.isoformat()
        if effect.state_missing:
            completed_fields["state_missing"] = True
        logger.emit("approval_completed", **completed_fields)

    render_execution_success(console, result)


@approve_app.callback(invoke_without_command=True)
def approve(
    ctx: typer.Context,
    card: Path | None = typer.Option(
        None,
        "--card",
        help="要晋升的 Knowledge Card 文件路径（必须是 ai_draft 状态）",
    ),
    source_id: str | None = typer.Option(
        None,
        "--source-id",
        help="按 state.json 中的 source_id 反查卡片路径再晋升（card_path 必须已记录）",
    ),
    all_: bool = typer.Option(
        False,
        "--all",
        help="批量晋升所有 ai_draft（默认拒绝；必须再加 --dry-run 预览，或 --confirm 真正执行）",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="仅打印将要 approve 的卡片，不写文件、不改 state",
    ),
    confirm: bool = typer.Option(
        False,
        "--confirm",
        help="--all 真正执行所需的显式确认（搭配可选 --limit）",
    ),
    limit: int = typer.Option(
        0,
        "--limit",
        min=0,
        help="--all 时最多处理多少张（0=全部）",
    ),
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="mindforge.yaml 路径",
    ),
) -> None:
    """显式人工 approve；默认走 --card 主路径。"""
    if ctx.invoked_subcommand is not None:
        return  # 让子命令接管
    cfg = load_cfg(config, read_env=False)

    # ── --card 主路径 ─────────────────────────────────────────────
    if card is not None:
        _do_single_approve(card, cfg)
        return

    # ── --source-id：state.json 反查 card_path ───────────────────
    if source_id is not None:
        from .approval_service import resolve_card_path_by_source_id
        from .approve_presenter import render_lookup_error

        lookup = resolve_card_path_by_source_id(cfg, source_id)
        if lookup.error is not None:
            render_lookup_error(console, lookup)
            raise typer.Exit(code=lookup.error.exit_code)
        assert lookup.card_path is not None
        _do_single_approve(lookup.card_path, cfg)
        return

    # ── --all 批量路径 ──────────────────────────────────────────
    if all_:
        _do_bulk_approve(cfg, dry_run=dry_run, confirm=confirm, limit=limit)
        return

    # 没给任何动作 → 友好提示
    from .approve_presenter import render_routing_hint

    render_routing_hint(console)
    raise typer.Exit(code=2)


def _do_bulk_approve(
    cfg: MindForgeConfig, *, dry_run: bool, confirm: bool, limit: int
) -> None:
    """--all 批量晋升执行体。

    为什么默认拒绝：批量批准是把"AI 草稿"一次性升级为"长期记忆"的危险动作，
    必须显式 ``--confirm`` 才能写入。``--dry-run`` 仅展示候选列表。
    """
    from .approval_service import build_bulk_approval_plan
    from .approve_presenter import (
        render_bulk_candidate_list,
        render_bulk_confirm_required,
        render_bulk_dry_run_footer,
        render_bulk_empty,
        render_bulk_summary,
    )

    plan = build_bulk_approval_plan(cfg, limit=limit)
    drafts = tuple(plan.candidates)

    if not drafts:
        render_bulk_empty(console)
        return

    render_bulk_candidate_list(console, drafts)

    if dry_run:
        render_bulk_dry_run_footer(console)
        return
    if not confirm:
        render_bulk_confirm_required(console)
        raise typer.Exit(code=2)

    # 真正批量执行
    ok = 0
    fail = 0
    for c in drafts:
        try:
            _do_single_approve(c.path, cfg)
            ok += 1
        except typer.Exit:
            fail += 1
    render_bulk_summary(console, ok=ok, fail=fail)


def _format_card_created_at(c) -> str:
    """已迁移到 approve_presenter.format_card_created_at；保留薄包装兼容。"""
    from .approve_presenter import format_card_created_at

    return format_card_created_at(c)


def _format_card_source_hint(c) -> str:
    """已迁移到 approve_presenter.format_card_source_hint；保留薄包装兼容。"""
    from .approve_presenter import format_card_source_hint

    return format_card_source_hint(c)


def _approve_next_command(c) -> str:
    """已迁移到 approve_presenter.approve_next_command；保留薄包装兼容。"""
    from .approve_presenter import approve_next_command

    return approve_next_command(c)


@approve_app.command("list")
def approve_list(
    status: str = typer.Option(
        "ai_draft",
        "--status",
        help="按 status 过滤（默认 ai_draft）；多个用逗号分隔",
    ),
    project: str | None = typer.Option(None, "--project", help="按 projects 字段过滤"),
    track: str | None = typer.Option(
        None, "--track", help="按 learning track 过滤（精确匹配）"
    ),
    limit: int = typer.Option(50, "--limit", min=1, help="最多展示多少张"),
    format_: str = typer.Option(
        "table", "--format", help="table | json", case_sensitive=False
    ),
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"), "--config", "-c", help="mindforge.yaml 路径"
    ),
) -> None:
    """列出可 approve 的卡片（安全字段摘要；不读卡片正文）。"""
    from .approval_service import ApprovalListQuery, list_approval_candidates
    from .approve_presenter import (
        render_approval_list,
        render_approval_list_json,
    )

    cfg = load_cfg(config, read_env=False)
    wanted = {s.strip() for s in status.split(",") if s.strip()}
    res = list_approval_candidates(
        cfg,
        ApprovalListQuery(
            statuses=tuple(wanted),
            project=project,
            track=track,
            limit=limit,
        ),
    )

    if format_.lower() == "json":
        render_approval_list_json(console, res)
        return

    render_approval_list(console, res, wanted_statuses=wanted)


@approve_app.command("show")
def approve_show(
    card: Path = typer.Option(..., "--card", help="要查看的 ai_draft / card 路径"),
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"), "--config", "-c", help="mindforge.yaml 路径"
    ),
) -> None:
    """查看待 approve 卡片的安全摘要；不读取正文、不改变状态。

    v0.6.5 dogfooding 需要用户在 approve 前多看一步，但这里仍守住边界：
    只读 frontmatter 白名单字段，不打印 source raw text，也不把 ai_draft 自动晋升。
    """
    from .approval_service import preview_approval_card
    from .approve_presenter import (
        render_approval_show,
        render_approval_show_error,
    )

    cfg = load_cfg(config, read_env=False)
    preview = preview_approval_card(cfg, card)
    if preview.error is not None:
        render_approval_show_error(console, preview)
        raise typer.Exit(code=preview.error.exit_code)
    render_approval_show(console, preview, card)
