"""Terminal presenter for real-data local status.

中文学习型说明：presenter 只负责把 `services.local_status` 的 plain-data
渲染成人类可读文本或 JSON；它不读文件、不加载配置、不调用 provider，也不
决定 approve/recall 的业务语义。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from ..services.local_status import FriendlyError, LocalStatusSnapshot
from ..run_logger import summarize_latest_run


def render_friendly_error(console: Console, error: FriendlyError) -> None:
    """四段式错误输出，避免普通用户看到 raw traceback。"""

    console.print("[red]What happened[/red]")
    console.print(f"  {error.what_happened}", markup=False)
    console.print("[yellow]Why it matters[/yellow]")
    console.print(f"  {error.why_it_matters}", markup=False)
    console.print("[bold]How to fix[/bold]")
    console.print(f"  {error.how_to_fix}", markup=False)
    console.print("[bold]Safe next command[/bold]")
    console.print(f"  {error.safe_next_command}", markup=False)


def render_status_json(snapshot: LocalStatusSnapshot) -> None:
    print(json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2))


def render_local_status(console: Console, snapshot: LocalStatusSnapshot) -> None:
    """渲染 Safety Bar 风格的 terminal status summary。"""

    data = snapshot.to_dict()
    safety = data["safety"]
    vault = data["vault"]
    cards = data["cards"]
    recall = data["recall"]
    console.print("[bold]MindForge local status[/bold]")
    console.print(
        "Safety: local-only · "
        f"vault={safety['vault_path']} · "
        f"model setup={_model_setup_label(data['provider'])} · "
        f"write mode={safety['write_mode']} · "
        f"pending ai_draft={safety['pending_drafts']}",
        markup=False,
    )
    console.print(
        "Recall: local lexical recall (not RAG, not embedding, no LLM call)",
        markup=False,
    )
    console.print("")
    _render_vault(console, vault)
    console.print(f"items 总数：{data['workspace']['state_item_count']}", markup=False)
    console.print(f"runs dir : {data['workspace']['runs_path']}", markup=False)
    latest = summarize_latest_run(Path(str(data["workspace"]["runs_path"])))
    if latest is None:
        console.print("最近一次 run：(无)", markup=False)
    else:
        console.print(
            f"最近一次 run · cmd={latest.command or '?'} · "
            f"run_id={latest.run_id} · events={latest.event_count}",
            markup=False,
        )
    _render_state_counts(console, data["workspace"])
    _render_cards(console, cards, recall)
    _render_warnings_and_next(console, data)


def render_workspace_status(console: Console, snapshot: LocalStatusSnapshot) -> None:
    data = snapshot.to_dict()
    console.print("[bold]Workspace status[/bold]")
    _render_vault(console, data["vault"])
    workspace = data["workspace"]
    console.print("[bold]Workspace[/bold]")
    for key in ("state_path", "state_exists", "state_item_count", "runs_path", "workdir"):
        console.print(f"  {key:<16}: {workspace[key]}", markup=False)
    if workspace.get("state_error"):
        console.print(f"  state_error      : {workspace['state_error']}", markup=False)
    table = Table(title="Sources")
    for column in ("source_type", "adapter", "file_count", "path"):
        table.add_column(column, overflow="fold")
    for item in data["sources"]:
        table.add_row(
            str(item["source_type"]),
            str(item["adapter"]),
            str(item["file_count"]),
            str(item["path"]),
        )
    console.print(table)
    _render_warnings_and_next(console, data)


def render_config_status(console: Console, snapshot: LocalStatusSnapshot) -> None:
    data = snapshot.to_dict()
    console.print("[bold]Config status[/bold]")
    console.print(f"vault.root    : {data['vault']['path']}", markup=False)
    console.print(f"model setup   : {_model_setup_label(data['provider'])}", markup=False)
    _render_warnings_and_next(console, data)


def _render_vault(console: Console, vault: dict[str, Any]) -> None:
    console.print("[bold]Vault[/bold]")
    for key in ("path", "exists", "readable", "looks_like_mindforge", "is_real_environment"):
        console.print(f"  {key:<22}: {vault[key]}", markup=False)
    resolution = vault.get("resolution") or {}
    if resolution.get("configured_differs"):
        console.print(
            f"  active vault          : {resolution.get('active_root')}",
            markup=False,
            soft_wrap=True,
        )
        console.print(
            f"  vault source          : {resolution.get('reason')}",
            markup=False,
            soft_wrap=True,
        )
        console.print(
            "  configured vault      : "
            f"fallback candidate only: {resolution.get('configured_root')}",
            markup=False,
            soft_wrap=True,
        )


def _model_setup_label(provider: dict[str, Any]) -> str:
    """把 readiness 压缩成普通用户能理解的模型配置状态。

    中文学习型说明：status/config 是用户主路径，不应把历史 provider 分组等
    开发兼容细节重新暴露为产品概念。service 层仍保留历史字段给内部调用者，
    presenter 只渲染“已配置 / 需要 Setup”这样的用户语义。
    """

    return str(provider.get("model_setup_label") or "needs setup")


def _source_type_label(source_type: str) -> str:
    """把历史 adapter 名称转换为普通用户可理解的 source 类别。"""

    if source_type in {"cubox_markdown", "webclip", "chat_export"}:
        return "imported_file"
    return source_type


def _render_cards(console: Console, cards: dict[str, Any], recall: dict[str, Any]) -> None:
    console.print("[bold]Cards[/bold]")
    console.print(f"  total         : {cards['total']}", markup=False)
    console.print(f"  items 总数：{data_count_hint(cards)}", markup=False)
    for status, count in sorted(cards["by_status"].items()):
        console.print(f"  {status:<14}: {count}", markup=False)
    console.print(f"  scan errors   : {cards['scan_error_count']}", markup=False)
    console.print("[bold]Recall[/bold]")
    console.print(f"  mode          : {recall['mode']} (not RAG, not embedding)", markup=False)
    console.print(f"  index_exists  : {recall['index_exists']}", markup=False)
    console.print(f"  human_approved: {recall['approved_card_count']}", markup=False)


def _render_state_counts(console: Console, workspace: dict[str, Any]) -> None:
    if not workspace["state_counts"] and not workspace["source_counts"]:
        return
    console.print("[bold]State[/bold]")
    for status, count in sorted(workspace["state_counts"].items()):
        console.print(f"  {status:<14}: {count}", markup=False)
    for source_type, count in sorted(workspace["source_counts"].items()):
        console.print(f"  {_source_type_label(source_type):<14}: {count}", markup=False)


def data_count_hint(cards: dict[str, Any]) -> int:
    """兼容旧 CLI 文案中的“items 总数”，这里表示 Knowledge Cards 总数。"""

    return int(cards["total"])


def _render_warnings_and_next(console: Console, data: dict[str, Any]) -> None:
    if data["warnings"]:
        console.print("[bold yellow]Warnings[/bold yellow]")
        for warning in data["warnings"]:
            console.print(f"  - {warning}", markup=False)
    console.print("[bold]Next actions[/bold]")
    for action in data["next_actions"]:
        console.print(f"  - {action}", markup=False)
