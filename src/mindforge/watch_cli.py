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
    resolve_source_path_for_cli,
)
from .env_loader import load_dotenv_silently
from .ingestion_diagnostics import print_ingestion_diagnostics
from .ingestion_service import watch_add_source, watch_scan_sources, watch_sources_for_display
from .process_service import FAKE_PROFILE
from .strategy_selection import StrategySelectionError, resolve_strategy_selection
from .watch_registry import (
    delete_watch_source,
    normalize_frequency,
    registry_path_for_vault,
    set_watch_status,
)

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
        hidden=True,
        help="Internal compatibility option.",
    ),
    provider: str | None = typer.Option(
        None,
        "--provider",
        hidden=True,
        help="Internal compatibility option.",
    ),
    strategy: str | None = typer.Option(
        None,
        "--strategy",
        help="为该 watched source 持久化 strategy_id；不修改 YAML。",
    ),
    every: str = typer.Option(
        "manual",
        "--every",
        "--frequency",
        help="scan frequency（--every / --frequency 等效）: manual/hourly/daily/weekly/every 1h/6h/12h/24h。",
    ),
    recursive: bool = typer.Option(
        True,
        "--recursive/--no-recursive",
        help="folder watched source 默认递归；file source 忽略此选项。",
    ),
) -> None:
    """注册 watched source，并立即生成 ai_draft 候选。"""

    cfg = load_cfg(config, read_env=False)
    cfg = apply_provider_selection(cfg, provider=provider, legacy_profile=profile)
    render_active_vault_resolution_notice(cfg)
    try:
        selected_strategy = resolve_strategy_selection(cfg, explicit_strategy=strategy)
    except StrategySelectionError as exc:
        console.print(str(exc), markup=False, soft_wrap=True)
        raise typer.Exit(code=2) from exc
    console.print(
        f"active strategy: {selected_strategy.strategy_id} ({selected_strategy.source})",
        markup=False,
    )
    try:
        frequency = normalize_frequency(every)
    except ValueError as exc:
        console.print(str(exc), markup=False)
        raise typer.Exit(code=2) from exc
    source_path = resolve_source_path_for_cli(cfg, target)
    if cfg.llm.active_profile != FAKE_PROFILE and selected_strategy.metadata.provider_mode != "deterministic":
        # CLI adapter 是读取本地 secret fallback 的边界；service 只编排 ingestion，不持有 IO 副作用。
        load_dotenv_silently(Path.cwd())
    try:
        summary = watch_add_source(
            cfg,
            source_path,
            strategy=selected_strategy,
            frequency=frequency,
            recursive=recursive if source_path.is_dir() else False,
        )
    except (ValueError, RuntimeError) as exc:
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
    print_ingestion_diagnostics(console, summary)
    console.print(f"watch id: {registry_result.source.id}", markup=False)
    console.print(f"strategy_id: {registry_result.source.strategy_id or '-'}", markup=False)
    console.print(f"frequency: {registry_result.source.frequency}", markup=False)
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


@watch_app.command("remove")
def watch_remove(
    ref: str = typer.Argument(..., help="watched source id、文件路径或文件夹路径"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """delete 的产品语义别名：只移除 registry 记录，不删除 knowledge。"""

    watch_delete(ref=ref, config=config)


@watch_app.command("scan")
def watch_scan(
    ref: str | None = typer.Argument(None, help="可选 watched source id、文件路径或文件夹路径"),
    all_sources: bool = typer.Option(False, "--all", help="扫描全部 watched sources，忽略 due 状态。"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    provider: str | None = typer.Option(None, "--provider", help="临时覆盖 provider，不修改 YAML。"),
) -> None:
    """扫描 due watched sources；--all 或指定 source 会手动触发。"""

    cfg = load_cfg(config, read_env=False)
    cfg = apply_provider_selection(cfg, provider=provider, legacy_profile=None)
    render_active_vault_resolution_notice(cfg)
    if cfg.llm.active_profile != FAKE_PROFILE:
        load_dotenv_silently(Path.cwd())
    try:
        summary = watch_scan_sources(cfg, ref=ref, all_sources=all_sources)
    except (ValueError, RuntimeError) as exc:
        console.print(str(exc), markup=False, soft_wrap=True)
        raise typer.Exit(code=2) from exc
    console.print("[bold]watch scan[/bold]")
    console.print(
        "scanned={scanned} not_due={not_due} missing={missing} processed={processed} "
        "skipped={skipped} failed={failed} seen={seen}".format(
            scanned=summary.scanned,
            not_due=summary.not_due,
            missing=summary.missing,
            processed=summary.counts.get("processed", 0),
            skipped=summary.counts.get("skipped", 0),
            failed=summary.counts.get("failed", 0),
            seen=summary.counts.get("seen", 0),
        ),
        markup=False,
    )
    console.print(
        "added={added} changed={changed} unchanged={unchanged} deleted={deleted} skipped_items={skipped_items}".format(
            added=summary.diff_counts.get("added", 0),
            changed=summary.diff_counts.get("changed", 0),
            unchanged=summary.diff_counts.get("unchanged", 0),
            deleted=summary.diff_counts.get("deleted", 0),
            skipped_items=summary.diff_counts.get("skipped", 0),
        ),
        markup=False,
    )
    if summary.missing:
        console.print("Missing watched source paths were kept; knowledge cards were not deleted.", markup=False)
    console.print("Boundary: source deletion never deletes approved knowledge.", markup=False)


@watch_app.command("status")
def watch_status(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """展示 watched source schedule/baseline 状态。"""

    watch_list(config=config)


@watch_app.command("pause")
def watch_pause(
    ref: str = typer.Argument(..., help="watched source id、文件路径或文件夹路径"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    _set_status(ref, config, "paused")


@watch_app.command("resume")
def watch_resume(
    ref: str = typer.Argument(..., help="watched source id、文件路径或文件夹路径"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    _set_status(ref, config, "active")


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
            f"frequency={source.frequency} · last_scan={source.last_scan_at or '-'} · "
            f"next_scan={source.next_scan_at or '-'} · "
            f"diff={source.diff_counts or {}} · "
            f"strategy_id={source.strategy_id or '-'} · fingerprint={source.fingerprint or '-'}",
            markup=False,
            soft_wrap=True,
        )


def _set_status(ref: str, config: Path, status: str) -> None:
    cfg = load_cfg(config, read_env=False)
    render_active_vault_resolution_notice(cfg)
    updated = set_watch_status(cfg.vault.root, registry_path_for_vault(cfg.vault.root), ref, status)  # type: ignore[arg-type]
    if updated is None:
        console.print(f"watch source not found: {ref}", markup=False)
        raise typer.Exit(code=2)
    console.print(f"watch {status}: {updated.id} {updated.path}", markup=False, soft_wrap=True)
    console.print("source and cards were not deleted.", markup=False)


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
    console.print("Next: mindforge approve list", markup=False)
    console.print("Boundary: generated cards remain ai_draft until explicit approve --confirm.", markup=False)


__all__ = ["watch_app"]
