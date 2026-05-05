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
        f"provider={safety['provider_state']} · "
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
    _render_provider(console, data["provider"])
    _render_env(console, data["env_keys"])
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
    console.print(f"config        : {data['config_path']}", markup=False)
    console.print(f"vault.root    : {data['vault']['path']}", markup=False)
    console.print(f"active_profile: {data['provider']['active_profile']}", markup=False)
    _render_provider(console, data["provider"])
    _render_env(console, data["env_keys"])
    cubox = data["cubox"]
    console.print("[bold]Cubox[/bold]")
    console.print(f"  token_env_var  : {cubox['token_env_var']}", markup=False)
    console.print(f"  token_present  : {cubox['token_present']} (presence only)", markup=False)
    console.print(f"  opt_in_state   : {cubox['opt_in_state']}", markup=False)
    console.print(f"  network_called : {cubox['network_called']}", markup=False)
    _render_warnings_and_next(console, data)


def _render_vault(console: Console, vault: dict[str, Any]) -> None:
    console.print("[bold]Vault[/bold]")
    for key in ("path", "exists", "readable", "looks_like_mindforge", "is_real_environment"):
        console.print(f"  {key:<22}: {vault[key]}", markup=False)


def _render_provider(console: Console, provider: dict[str, Any]) -> None:
    console.print("[bold]Provider[/bold]")
    console.print(f"  active_profile : {provider['active_profile']}", markup=False)
    console.print(f"  opt_in_state   : {provider['opt_in_state']}", markup=False)
    console.print(f"  network_called : {provider['network_called']}", markup=False)


def _render_env(console: Console, env_keys: list[dict[str, Any]]) -> None:
    console.print("[bold].env / process env presence[/bold]")
    table = Table(show_header=True)
    table.add_column("key")
    table.add_column("configured")
    table.add_column("sources")
    for item in env_keys:
        table.add_row(
            str(item["name"]),
            str(item["configured"]),
            ", ".join(item["sources"]) if item["sources"] else "-",
        )
    console.print(table)
    console.print("[dim]secret values are never printed; only key names and presence are shown[/dim]")


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
        console.print(f"  {source_type:<14}: {count}", markup=False)


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
