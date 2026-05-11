"""Approval Typer adapter.

中文学习型说明：本模块只承载 ``mindforge approve`` 命令族的 CLI 适配：
参数接收、调用 approval_service、调用 approve_presenter、写 RunLogger。
真正的状态晋升规则仍在 approval_service / approver，避免把人工审批边界
散落回 root cli.py。
"""
from __future__ import annotations

from pathlib import Path

import click
import typer
from typer.core import TyperGroup

from .cli_runtime import console, load_cfg, render_active_vault_resolution_notice
from .config import MindForgeConfig
from .run_logger import RunLogger

# ---------------------------------------------------------------------------
# approve — M3 反 AI 污染闸门：显式人工把 ai_draft 卡片晋升为 human_approved
# 详见 README.md 的 explicit approval boundary。
# ---------------------------------------------------------------------------


class ApproveGroup(TyperGroup):
    """允许 ``mindforge approve <ref>`` 与子命令共存。

    Typer group 默认会把第一个非 option token 当子命令；但 approve UX 需要
    ``approve 1`` 这种短 ref。这里仅在未知子命令时把 token 解释为 pending
    ref，不改变 list/show 等真实子命令的解析。
    """

    def get_command(
        self,
        ctx: click.Context,
        cmd_name: str,
    ) -> click.Command | None:
        command = super().get_command(ctx, cmd_name)
        if command is not None or cmd_name.startswith("-"):
            return command
        return click.Command(
            name=cmd_name,
            params=[
                click.Option(
                    ["--confirm"],
                    is_flag=True,
                    default=False,
                    help="真正写入 human_approved 所需的显式确认。",
                ),
                click.Option(
                    ["--no-index"],
                    is_flag=True,
                    default=False,
                    help="approve 成功后不自动刷新 recall index（高级/排错用）。",
                ),
                click.Option(
                    ["--config", "-c"],
                    type=click.Path(path_type=Path),
                    default=Path("configs/mindforge.yaml"),
                    help="mindforge.yaml 路径",
                ),
            ],
            callback=lambda confirm, no_index, config: _approve_ref_entry(
                cmd_name,
                config=config,
                confirm=confirm,
                no_index=no_index,
            ),
            help="Approve one pending card by short ref.",
        )


approve_app = typer.Typer(
    cls=ApproveGroup,
    no_args_is_help=False,
    help=(
        "把 Knowledge Card 从 ai_draft 显式晋升为 human_approved。\n\n"
        "为什么 approve 必须是显式人工动作：\n"
        "  - long-term memory 的入口；批准的卡片会进入 recall / project context 的"
        "正式输出，会被复用到多个项目，影响后续判断。\n"
        "  - 如果允许 LLM 自动 approve，AI 误差会被无限放大；MindForge 的"
        "差异化前提之一就是 source-grounded + human-approved。\n\n"
        "常用：\n"
        "  approve list                        — 列出待确认 ai_draft（含短编号）\n"
        "  approve 1 --confirm                 — 用短编号显式晋升，并刷新 recall index\n"
        "  approve --card <path> --confirm     — 高级路径模式，继续兼容长 card path\n"
        "  approve --source-id <id> --confirm  — 基于 state.json 反查卡片再晋升\n"
        "  approve --all --dry-run             — 预览批量晋升（不写文件）\n"
    ),
)

def _do_single_approve(
    card_path: Path,
    cfg: MindForgeConfig,
    *,
    update_index: bool = True,
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
        index_result = None
        index_error = None
        if update_index and effect.kind == "approved":
            try:
                from .lexical_index import rebuild_index_for_config

                index_result = rebuild_index_for_config(cfg)
            except Exception as exc:  # pragma: no cover - 异常路径由 CLI 输出兜底
                index_error = f"{type(exc).__name__}: {exc}"

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
        if index_error is not None:
            completed_fields["index_error"] = index_error
        logger.emit("approval_completed", **completed_fields)

    render_execution_success(
        console,
        result,
        index_updated=index_result,
        index_error=index_error,
    )


def _approve_ref_entry(
    ref: str,
    *,
    config: Path,
    confirm: bool,
    no_index: bool,
) -> None:
    """``mindforge approve <ref>`` 的动态子命令入口。

    Click/Typer group 默认把 ``<ref>`` 当子命令；这里在自定义 group 中把未知
    子命令解释为 pending ref，但仍要求 ``--confirm`` 才会触发写入。
    """
    from .approval_refs import resolve_pending_approval_ref
    from .approve_presenter import render_ref_lookup_error

    cfg = load_cfg(config, read_env=False)
    render_active_vault_resolution_notice(cfg)
    lookup = resolve_pending_approval_ref(cfg, ref)
    if lookup.error is not None:
        render_ref_lookup_error(console, lookup)
        raise typer.Exit(code=lookup.error.exit_code)
    assert lookup.card_path is not None
    if not confirm:
        target = lookup.match
        label = target.short_ref if target is not None else str(lookup.card_path)
        short_ref = str(target.number) if target is not None else None
        show_arg = short_ref if short_ref is not None else str(lookup.card_path)
        console.print(
            "[red]approve requires --confirm before writing human_approved.[/red]"
        )
        console.print(
            f"Resolved target: {label} -> {lookup.card_path}\n"
            "Why: approve means ai_draft → human_approved and affects recall/project context.\n"
            f"Safe preview: mindforge approve show --card {show_arg} --config {config}",
            markup=False,
        )
        raise typer.Exit(code=2)
    _do_single_approve(lookup.card_path, cfg, update_index=not no_index)


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
        help="真正写入 human_approved 所需的显式确认（单卡 / source-id / --all 都需要）。",
    ),
    limit: int = typer.Option(
        0,
        "--limit",
        min=0,
        help="--all 时最多处理多少张（0=全部）",
    ),
    no_index: bool = typer.Option(
        False,
        "--no-index",
        help="approve 成功后不自动刷新 recall index（高级/排错用）。",
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
    render_active_vault_resolution_notice(cfg)

    # ── --card 主路径 ─────────────────────────────────────────────
    if card is not None:
        if not confirm:
            # 尝试短 ref 解析以生成友好 safe preview 命令
            from .approval_refs import resolve_pending_approval_ref as _resolve_ref
            _ref_lookup = _resolve_ref(cfg, str(card))
            _show_arg = str(_ref_lookup.match.number) if (_ref_lookup.ok and _ref_lookup.match) else str(card)
            console.print(
                "[red]approve requires --confirm before writing human_approved.[/red]"
            )
            console.print(
                f"Target: {card}\n"
                "Why: approve means ai_draft → human_approved and affects recall/project context.\n"
                f"Safe preview: mindforge approve show --card {_show_arg} --config {config}",
                markup=False,
            )
            raise typer.Exit(code=2)
        _do_single_approve(card, cfg, update_index=not no_index)
        return

    # ── --source-id：state.json 反查 card_path ───────────────────
    if source_id is not None:
        from .approval_refs import resolve_pending_approval_ref as _resolve_ref
        from .approval_service import resolve_card_path_by_source_id
        from .approve_presenter import render_lookup_error

        lookup = resolve_card_path_by_source_id(cfg, source_id)
        if lookup.error is not None:
            render_lookup_error(console, lookup)
            raise typer.Exit(code=lookup.error.exit_code)
        assert lookup.card_path is not None
        if not confirm:
            _ref_lookup = _resolve_ref(cfg, str(lookup.card_path))
            _show_arg = str(_ref_lookup.match.number) if (_ref_lookup.ok and _ref_lookup.match) else str(lookup.card_path)
            console.print(
                "[red]approve requires --confirm before writing human_approved.[/red]"
            )
            console.print(
                f"Resolved target: {lookup.card_path}\n"
                "Why: approve means ai_draft → human_approved and affects recall/project context.\n"
                f"Safe preview: mindforge approve show --card {_show_arg} --config {config}",
                markup=False,
            )
            raise typer.Exit(code=2)
        _do_single_approve(lookup.card_path, cfg, update_index=not no_index)
        return

    # ── --all 批量路径 ──────────────────────────────────────────
    if all_:
        _do_bulk_approve(cfg, dry_run=dry_run, confirm=confirm, limit=limit)
        return

    # 没给任何动作 → 安全进入 pending review 入口；只展示，不写入。
    from .approval_service import ApprovalListQuery, list_approval_candidates
    from .approve_presenter import render_approval_list

    res = list_approval_candidates(
        cfg,
        ApprovalListQuery(statuses=("ai_draft",), limit=50),
    )
    render_approval_list(console, res, wanted_statuses={"ai_draft"})


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
    if format_.lower() != "json":
        render_active_vault_resolution_notice(cfg)
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
    card: Path = typer.Option(..., "--card", help="要查看的 ai_draft / card 路径（支持数字 ref、short_ref、完整路径）"),
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"), "--config", "-c", help="mindforge.yaml 路径"
    ),
    show_content: bool = typer.Option(
        False,
        "--show-content",
        help="显式展示 draft 正文；默认只显示 frontmatter 安全摘要。",
    ),
) -> None:
    """查看待 approve 卡片的安全摘要；不读取正文、不改变状态。

    --card 支持三种引用方式：
      - 数字 ref：approve show --card 1
      - short_ref：approve show --card <slug>
      - 完整路径 / vault-relative 路径

    v0.6.5 dogfooding 需要用户在 approve 前多看一步，但这里仍守住边界：
    只读 frontmatter 白名单字段，不打印 source raw text，也不把 ai_draft 自动晋升。
    """
    from .approval_refs import resolve_pending_approval_ref
    from .approval_service import preview_approval_card
    from .approve_presenter import (
        render_approval_show,
        render_approval_show_error,
        render_ref_lookup_error,
    )

    cfg = load_cfg(config, read_env=False)
    render_active_vault_resolution_notice(cfg)

    # 先尝试短 ref 解析；失败时回退到 path 解析，保留完整 path 兼容。
    raw_ref = str(card)
    short_ref: str | None = None
    ref_lookup = resolve_pending_approval_ref(cfg, raw_ref)
    if ref_lookup.ok and ref_lookup.match is not None:
        resolved_card: Path = ref_lookup.card_path  # type: ignore[assignment]
        short_ref = str(ref_lookup.match.number)
    elif raw_ref.isdigit() and ref_lookup.error is not None:
        # 数字 ref 无法解析时直接展示友好错误，不回退到 path 解析。
        # 数字 ref 仅适用于 approve list 中的待审批项；回退 path 解析
        # 只会得到 "card path could not be resolved: 1" 这种误导性错误。
        render_ref_lookup_error(console, ref_lookup)
        raise typer.Exit(code=ref_lookup.error.exit_code)
    else:
        resolved_card = card

    preview = preview_approval_card(cfg, resolved_card)
    if preview.error is not None:
        render_approval_show_error(console, preview)
        raise typer.Exit(code=preview.error.exit_code)
    render_approval_show(console, preview, resolved_card, short_ref=short_ref)
    if show_content and preview.card_path is not None:
        from .cards import read_card_body

        console.print("[bold]Draft content (--show-content)[/bold]")
        console.print(read_card_body(preview.card_path), markup=False)
