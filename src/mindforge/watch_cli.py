"""Simple watch CLI.

watch 是用户级 ingestion 入口：注册一个 file/folder，并立即处理当前内容。
本阶段不启动 daemon、不做 filesystem hook，也不提供 run/start/stop。
"""

from __future__ import annotations

from pathlib import Path

import typer

from .cli_runtime import (
    apply_provider_selection,
    console,
    load_cfg,
    render_active_vault_resolution_notice,
)
from .env_loader import load_dotenv_silently
from .process_service import FAKE_PROFILE
from .ingestion_service import watch_add_source, watch_sources_for_display
from .watch_registry import delete_watch_source, registry_path_for_vault

watch_app = typer.Typer(
    add_completion=False,
    help="管理 watched sources；第一版 watch add 只注册并立即处理当前内容。",
)


@watch_app.command("add")
def watch_add(
    target: Path = typer.Argument(..., help="要持续关注的文件或文件夹"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    profile: str | None = typer.Option(
        None,
        "--profile",
        "-p",
        help="Legacy alias for --provider；临时覆盖 provider，不修改 YAML。",
    ),
    provider: str | None = typer.Option(
        None,
        "--provider",
        help="高级临时覆盖 llm.active 指向的 provider（不修改 YAML）。",
    ),
) -> None:
    """注册 watched source，并立即生成 ai_draft 候选。"""

    cfg = load_cfg(config, read_env=False)
    cfg = apply_provider_selection(cfg, provider=provider, legacy_profile=profile)
    render_active_vault_resolution_notice(cfg)
    if cfg.llm.active_profile != FAKE_PROFILE:
        # CLI adapter 是读取 .env 的边界；service 只编排 ingestion，不持有 IO 副作用。
        load_dotenv_silently(Path.cwd())
    try:
        summary = watch_add_source(cfg, target)
    except RuntimeError as exc:
        console.print(str(exc), markup=False, soft_wrap=True)
        raise typer.Exit(code=2) from exc
    registry_result = summary.registry_result
    assert registry_result is not None
    action = "registered" if registry_result.added else "already registered"
    _print_summary(
        title=f"watch add: {action}",
        target=summary.target,
        counts=summary.counts,
    )
    console.print(f"watch id: {registry_result.source.id}", markup=False)
    console.print(f"registry: {summary.registry_path}", markup=False, soft_wrap=True)


@watch_app.command("delete")
def watch_delete(
    ref: str = typer.Argument(..., help="watched source id、文件路径或文件夹路径"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """只删除 watched source registry 记录，不删除 source 或 cards。"""

    cfg = load_cfg(config, read_env=False)
    render_active_vault_resolution_notice(cfg)
    result = delete_watch_source(cfg.vault.root, registry_path_for_vault(cfg.vault.root), ref)
    if not result.deleted:
        console.print(result.message, markup=False)
        raise typer.Exit(code=2 if "default 00-Inbox" in result.message else 0)
    console.print(f"watch delete: {result.message}", markup=False)
    assert result.source is not None
    console.print(f"removed: {result.source.id} {result.source.path}", markup=False, soft_wrap=True)
    console.print("source and cards were not deleted.", markup=False)


@watch_app.command("list")
def watch_list(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """展示 default 00-Inbox 与用户添加的 watched sources。"""

    cfg = load_cfg(config, read_env=False)
    render_active_vault_resolution_notice(cfg)
    console.print("[bold]Watched Sources[/bold]")
    for source in watch_sources_for_display(cfg):
        kind = "default" if source.is_default else "user-added"
        console.print(
            f"- {source.id} · {source.path_type} · {kind} · status={source.status} · "
            f"path={source.path} · last_seen={source.last_seen_at or '-'} · "
            f"last_processed={source.last_processed_at or '-'} · "
            f"fingerprint={source.fingerprint or '-'}",
            markup=False,
            soft_wrap=True,
        )


def _print_summary(*, title: str, target: Path, counts: dict[str, int]) -> None:
    console.print(f"[bold]{title}[/bold]")
    console.print(f"target: {target}", markup=False, soft_wrap=True)
    console.print(
        "processed={processed} skipped={skipped} failed={failed} seen={seen}".format(
            processed=counts.get("processed", 0),
            skipped=counts.get("skipped", 0),
            failed=counts.get("failed", 0),
            seen=counts.get("seen", 0),
        ),
        markup=False,
    )
    if counts.get("skipped", 0):
        console.print("skipped reasons may include already_processed or already_approved.", markup=False)
    console.print("Next: mindforge approve list", markup=False)
    console.print("Boundary: generated cards remain ai_draft until explicit approve --confirm.", markup=False)


__all__ = ["watch_app"]
