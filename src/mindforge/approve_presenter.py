"""approve_presenter — approve 命令的展示层。

中文学习型说明
================

为什么要这一层？
----------------
v0.7.20 之前，``approve list`` / ``approve show`` / ``approve --all`` /
``approve --card`` 等所有用户可见输出都内嵌在 ``cli.py``：Rich Table 构造、
JSON dict 拼接、emoji+rich tag 文案、空态/错误态/边界提示文案，全部与 Typer
参数和 ``approval_service`` 调用混在一起。

approve 是 MindForge 的**人审安全边界**：把卡片从 ``ai_draft`` 晋升到
``human_approved`` 是显式人工动作。一旦展示层与业务层混在一起，每次改
table 表头或 emoji 都要触碰人审边界附近的代码，风险大。

本模块只负责把 ``approval_service`` 已经计算好的结构化结果渲染成
**用户可见输出**，分为五类展示意图：

1. ``render_approval_list``  —— ``approve list`` 表格 / JSON
2. ``render_approval_show``  —— ``approve show`` 字段摘要
3. ``render_bulk_preview``   —— ``approve --all`` 批量候选
4. ``render_execution_result`` —— 单卡 approve 成功 / 已批准 / 失败
5. ``render_lookup_error`` / ``render_empty_state`` / ``render_routing_hint``
   —— 错误与空态

约定（与 ``recall_presenter.py`` v0.7.13 模式一致）：
presenter **不持有全局 console**，由调用方（CLI）传入 ``Console`` 实例；
测试时可以传入 ``Console(file=StringIO(), force_terminal=False)`` 做
snapshot 验证。这样 presenter 不依赖 ``cli.console`` 模块状态，
也不引入 Typer / RunLogger / dotenv。

边界（运行时禁止）
------------------
本模块**不允许**：

1. ``import typer``；
2. 持有 ``RunLogger``；
3. 修改 card 状态 / 调用 ``approve_explicit_card``；
4. ``Path.read_text`` / ``Path.write_text``；
5. 调用 ``processor`` / ``provider`` / 真实 LLM；
6. ``import dotenv`` / 读取 ``.env``；
7. 写正式 Obsidian notes；
8. RAG / embedding；
9. 解析 CLI 参数（不接受 raw str config 路径）；
10. 改变 ``approval_service`` 公开 API；
11. 自动 approve 任何卡片（**human_approved 边界由 approval_service 唯一保护**）。

测试通过 AST 静态断言以上 import / 调用全部不出现。

与 safety_policy 的关系
------------------------
不修改 / 不扩展 ``safety_policy.py``。文档与测试可引用
``safety_policy.boundary_statement("human_approved_gate" / "no_real_llm" /
"no_env_read")`` 作为对齐证据。
"""

from __future__ import annotations

import json as _json
from typing import Any

from rich.console import Console
from rich.table import Table

from .approval_refs import (
    ApprovalRefLookupResult,
    build_pending_approval_refs_from_rows,
)
from .approval_service import (
    APPROVAL_PREVIEW_FIELDS,
    ApprovalCardLookupResult,
    ApprovalExecutionResult,
    ApprovalListResult,
    ApprovalPreviewResult,
    ApprovalServiceError,
)
from .cards import CardSummary


# ---------------------------------------------------------------------------
# 纯 helper：safe display formatters
# ---------------------------------------------------------------------------


def format_card_created_at(c: CardSummary) -> str:
    """把卡片创建时间压成 CLI 友好字符串；只读 frontmatter 安全字段。

    与 v0.7.20 之前的 ``cli._format_card_created_at`` 行为一致。
    """
    return c.created_at.isoformat(timespec="minutes") if c.created_at else "-"


def format_card_source_hint(c: CardSummary) -> str:
    """生成 approve 待办里的 source 摘要，避免读取 source 原文。

    边界：仅使用 CardSummary 已白名单化的 source_* frontmatter；
    不回读原始资料正文。与 v0.6.2 设定的 source-grounded 边界对齐。
    """
    if c.source_title:
        return c.source_title
    if c.source_url:
        return c.source_url
    return c.source_type or "-"


def approve_next_command(c: CardSummary) -> str:
    """为单张草稿给出最短下一步命令；不自动 approve。

    presenter 仅生成命令字符串，是否执行由用户复制粘贴。
    """
    return f"mindforge approve --card {c.rel_path} --confirm"


# ---------------------------------------------------------------------------
# render_approval_list —— approve list
# ---------------------------------------------------------------------------


def build_approval_list_json(result: ApprovalListResult) -> dict[str, Any]:
    """把 ``ApprovalListResult`` 转成 JSON-safe dict。

    输出 schema 与 v0.7.20 字节级一致：``{"count": N, "items": [...]}``，
    每项含 title / path / status / track / projects / source_type /
    created_at / value_score。

    注意：本函数返回 dict，**不调用 console**。CLI 端调
    ``console.print_json(json.dumps(...))`` 实际输出，与既有行为一致。
    """
    rows = list(result.candidates)
    items = [
        {
            "title": c.title,
            "path": c.rel_path,
            "status": c.status,
            "track": c.track,
            "projects": list(c.projects),
            "source_type": c.source_type,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "value_score": c.value_score,
        }
        for c in rows
    ]
    return {"count": len(items), "items": items}


def render_approval_list(
    console: Console,
    result: ApprovalListResult,
    *,
    wanted_statuses: set[str],
) -> None:
    """渲染 ``approve list`` 表格视图。

    ``wanted_statuses`` 是 CLI 已经解析过的 status 过滤集合，仅用于
    table title 文案；presenter 不重新解析 ``--status`` 参数。

    输出与 v0.7.20 字节级一致：
    - empty 态：黄字提示 + dim 下一步说明
    - 非空：带标题的 6 列 Table + 行命令清单 + dim 边界说明
    """
    rows = list(result.candidates)
    if not rows:
        console.print("[yellow]没有待 approve 的卡片。[/yellow]")
        console.print(
            "[dim]下一步：如果有新资料，运行 `mindforge watch add <file-or-folder>` "
            "或 `mindforge import <file-or-folder>` 启动后台 processing；"
            "如果暂无草稿，请用 `mindforge watch status` 或 `mindforge runs list` "
            "检查 processing 状态。模型设置未完成时，请先在 Web Setup 或本地 "
            "secret store 添加 provider key 后重试；"
            "MindForge 不会自动 approve。[/dim]",
            soft_wrap=True,
        )
        return
    refs = build_pending_approval_refs_from_rows(rows)
    table = Table(
        title=f"Approve Todo · {len(rows)} pending (status in {sorted(wanted_statuses)})"
    )
    for col in (
        "ref",
        "card id prefix",
        "title",
        "source",
        "created",
        "value score",
        "short ref",
        "risk / safety",
        "next command",
    ):
        table.add_column(col, overflow="fold")
    for c, ref in zip(rows, refs, strict=False):
        card_id_prefix = (c.id or "")[:8] if c.id else "-"
        vs = str(c.value_score) if c.value_score is not None else "-"
        table.add_row(
            f"[{ref.number}]",
            card_id_prefix,
            c.title or "?",
            format_card_source_hint(c),
            format_card_created_at(c),
            vs,
            ref.short_ref,
            "ai_draft，需要人工确认；不会自动 approve",
            f"mindforge approve {ref.number} --confirm",
        )
    console.print(table)
    console.print("[bold]Todo commands[/bold]")
    for c, ref in zip(rows, refs, strict=False):
        card_id_prefix = (c.id or "")[:8] if c.id else "-"
        vs = str(c.value_score) if c.value_score is not None else "-"
        console.print(
            f"- [{ref.number}] {c.title or '?'} · card_id_prefix={card_id_prefix} · "
            f"card_id={c.id or '-'} · short_ref={ref.short_ref} · "
            f"source={format_card_source_hint(c)} · created={format_card_created_at(c)} · "
            f"value_score={vs} · full_path={c.rel_path}",
            markup=False,
        )
        console.print(
            f"  view:    mindforge approve show --card {ref.number} --show-content",
            markup=False,
        )
        console.print(
            f"  approve: mindforge approve {ref.number} --confirm",
            markup=False,
        )
    console.print(
        "[dim]说明：数字 ref（方括号）是当前 session 的便捷编号，审批后列表刷新编号会变化。"
        "card_id_prefix（card_id 前 8 位）只是展示用短标识；完整 card_id 或 full_path 才是 canonical reference。"
        "approve 会把 ai_draft 晋升为 human_approved，之后才进入 "
        "recall / review / project context 的默认结果；MindForge 不会自动 approve。[/dim]"
    )


# ---------------------------------------------------------------------------
# render_approval_show —— approve show
# ---------------------------------------------------------------------------


def render_approval_show(
    console: Console,
    preview: ApprovalPreviewResult,
    fallback_card_path: Any,
    *,
    short_ref: str | None = None,
) -> None:
    """渲染 ``approve show`` 安全字段摘要。

    presenter 假定调用方已经判断 ``preview.error is None``；如果
    ``preview.error`` 非空，请改调 ``render_lookup_error``。

    ``fallback_card_path`` 用于 preview.card_path 缺失时显示原始
    用户传入路径，与 v0.7.20 的 ``card_path = preview.card_path or card`` 一致。

    ``short_ref`` 是可选的数字 ref（如 "1"），存在时 Next 命令优先使用短命令
    ``mindforge approve <short_ref> --confirm``，不优先展示超长绝对路径。
    """
    card_path = preview.card_path or fallback_card_path
    console.print("[bold]Approve preview[/bold]")
    for key in APPROVAL_PREVIEW_FIELDS:
        console.print(f"{key:<12}: {preview.fields.get(key, '-')}")
    console.print(f"path        : {card_path}")

    # Next 命令优先短 ref，其次 short_ref slug，最后完整路径
    if short_ref is not None:
        next_cmd = f"mindforge approve {short_ref} --confirm"
        next_show = f"mindforge approve show --card {short_ref} --show-content"
    else:
        next_cmd = f"mindforge approve --card {card_path} --confirm"
        next_show = f"mindforge approve show --card {card_path} --show-content"

    console.print(
        "Boundary: preview only; no auto approve, no .env, no LLM, no source body.",
        markup=False,
    )
    console.print(f"Next (view):  {next_show}", markup=False)
    console.print(f"Next (approve): {next_cmd}", markup=False)


# ---------------------------------------------------------------------------
# render_bulk_preview —— approve --all 候选清单
# ---------------------------------------------------------------------------


def render_bulk_candidate_list(
    console: Console,
    candidates: tuple[CardSummary, ...],
) -> None:
    """渲染 ``approve --all`` 候选列表（dry-run 与真正执行前共用）。

    presenter 只渲染已就位的候选；空态由调用方在调 presenter 之前
    判断（与 v0.7.20 一致：cli.py 在 ``if not drafts`` 时直接 print
    ``(no ai_draft cards found)``）。
    """
    console.print(f"[bold]{len(candidates)} 张 ai_draft 待 approve：[/bold]")
    for c in candidates:
        console.print(f"  - {c.rel_path}  [dim]({c.title or '?'})[/dim]")


def render_bulk_empty(console: Console) -> None:
    """``approve --all`` 没有任何候选时的空态。"""
    console.print("[dim](no ai_draft cards found)[/dim]")


def render_bulk_dry_run_footer(console: Console) -> None:
    """``--dry-run`` 启用时的尾注。"""
    console.print("[dim](--dry-run 已启用，未写任何文件)[/dim]")


def render_bulk_confirm_required(console: Console) -> None:
    """缺 ``--confirm`` 时的拒绝提示。"""
    console.print(
        "[red]✗ 批量 approve 是危险动作；请加 --dry-run 预览，"
        "或确认无误后再加 --confirm[/red]"
    )


def render_bulk_summary(console: Console, *, ok: int, fail: int) -> None:
    """``approve --all --confirm`` 执行后的汇总。"""
    console.print(f"[bold]批量 approve 完成：成功 {ok} / 失败 {fail}[/bold]")


# ---------------------------------------------------------------------------
# render_execution_result —— 单卡 approve 结果
# ---------------------------------------------------------------------------


def render_execution_failure(
    console: Console,
    err: ApprovalServiceError,
) -> None:
    """渲染 ``approve_explicit_card`` 失败结果。

    presenter 不抛 typer.Exit；exit code 仍由 CLI 端按 err.exit_code 决定。
    """
    console.print(f"[red]approve 失败：{err.message}[/red]")


def render_execution_success(
    console: Console,
    result: ApprovalExecutionResult,
    *,
    index_updated: object | None = None,
    index_error: str | None = None,
) -> None:
    """渲染 ``approve_explicit_card`` 成功 / 幂等结果。

    presenter 不修改 ``result``；不调用 ``approve_explicit_card``；
    不读 / 不写 card 文件。

    包含的展示意图：成功提示 / 幂等提示 / 边界说明 / state_missing 警告。
    """
    assert result.effect is not None
    effect = result.effect
    if effect.kind == "already_approved":
        console.print(
            f"[yellow]已是 human_approved（幂等）：{effect.card_path}[/yellow]"
        )
        return
    console.print(
        f"[green]✔ approved[/green] {effect.card_path}  "
        f"(prev={effect.prev_status} → {effect.new_status}, "
        f"method={effect.approval_method})"
    )
    if index_updated is not None:
        path = getattr(index_updated, "path", None)
        count = getattr(index_updated, "card_count", None)
        console.print(
            f"approved and recall index updated (cards={count}, path={path})",
            markup=False,
        )
    elif index_error is not None:
        console.print(
            "[yellow]approved, but recall index update failed.[/yellow] "
            f"Run `mindforge index rebuild` manually. error={index_error}",
            markup=False,
        )
    console.print(
        "[dim]边界：这是一次显式人工 approve；MindForge 不会让 AI 自动写入 "
        "human_approved。下一步可直接运行 `mindforge recall --query \"...\"` "
        "或 `mindforge review weekly` 使用这张卡片。[/dim]"
    )
    if effect.state_missing:
        console.print(
            "[yellow]注意：state.json 中找不到对应 item，仅更新了卡片文件。[/yellow]"
        )
    if result.source_archive is not None:
        archive = result.source_archive
        console.print(f"source archive: {archive.kind} · {archive.message}", markup=False)
        if archive.archive_path is not None:
            console.print(f"source_archive_path: {archive.archive_path}", markup=False)


# ---------------------------------------------------------------------------
# render_lookup_error / render_routing_hint —— routing 与错误
# ---------------------------------------------------------------------------


def render_lookup_error(
    console: Console,
    lookup: ApprovalCardLookupResult | ApprovalPreviewResult,
) -> None:
    """渲染 ``--source-id`` 反查失败 / ``approve show`` lookup 失败。

    presenter 不抛 typer.Exit；exit code 由 CLI 按 ``lookup.error.exit_code``
    决定。``approve show`` 失败路径还需要附加 ``Next:`` 提示，由
    ``render_approval_show_error`` 提供。
    """
    assert lookup.error is not None
    console.print(f"[red]✗ {lookup.error.message}[/red]")


def render_approval_show_error(
    console: Console,
    preview: ApprovalPreviewResult,
) -> None:
    """``approve show`` 错误专用版：附加 ``Next: mindforge approve list``。

    与 v0.7.20 字节级一致；与 ``--source-id`` 错误路径不同（show 给的
    next 是 list，不是 next 命令）。
    """
    assert preview.error is not None
    console.print(f"[red]✗ {preview.error.message}[/red]")
    console.print("Next: mindforge approve list", markup=False)


def render_routing_hint(console: Console) -> None:
    """``approve`` 不带任何动作时的友好提示。"""
    console.print(
        "[yellow]Pending review：先查看待确认卡片，再用短编号显式 approve。[/yellow]"
    )
    console.print(
        "Next: mindforge approve list\n"
        "Approve one: mindforge approve 1 --confirm\n"
        "Advanced path mode: mindforge approve --card <path> --confirm",
        markup=False,
    )


def render_ref_lookup_error(console: Console, lookup: ApprovalRefLookupResult) -> None:
    """渲染短 ref 解析失败；模糊时列出候选，绝不默认选择。

    v0.7.21 起针对 number_not_found 给出更友好的下一步建议，
    包括 library list（已批准卡片）和 approve list（重新获取待审批列表）。
    """
    assert lookup.error is not None
    console.print(f"[red]✗ {lookup.error.message}[/red]")
    if lookup.matches:
        console.print("[bold]Candidates[/bold]")
        for match in lookup.matches[:10]:
            console.print(
                f"- [{match.number}] {match.title or match.short_ref} · "
                f"short_ref={match.short_ref} · path={match.rel_path}",
                markup=False,
            )
    if lookup.error.kind == "number_not_found":
        console.print(
            "数字编号仅适用于当前 pending approve list 中的 ai_draft 卡片。\n"
            "如果该卡片已 approve，请使用 `mindforge library list` 查看已批准卡片。",
            markup=False,
        )
    else:
        console.print(
            "Next: mindforge approve list; then run `mindforge approve <ref> --confirm`",
            markup=False,
        )


# ---------------------------------------------------------------------------
# JSON 输出 —— CLI 直接 console.print_json(json.dumps(...))
# ---------------------------------------------------------------------------


def render_approval_list_json(
    console: Console,
    result: ApprovalListResult,
) -> None:
    """以 JSON 格式输出 ``approve list``。

    presenter 调用 ``console.print_json`` 是 ``rich.Console`` 的方法（不是
    `console.print` 之外的副作用层）；JSON payload 由
    ``build_approval_list_json`` 纯函数计算。
    """
    payload = build_approval_list_json(result)
    console.print_json(_json.dumps(payload))


__all__ = [
    "approve_next_command",
    "build_approval_list_json",
    "format_card_created_at",
    "format_card_source_hint",
    "render_approval_list",
    "render_approval_list_json",
    "render_approval_show",
    "render_approval_show_error",
    "render_bulk_candidate_list",
    "render_bulk_confirm_required",
    "render_bulk_dry_run_footer",
    "render_bulk_empty",
    "render_bulk_summary",
    "render_execution_failure",
    "render_execution_success",
    "render_lookup_error",
    "render_ref_lookup_error",
    "render_routing_hint",
]
