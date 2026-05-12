"""Simple watch CLI.

watch 是用户级 ingestion 入口：注册一个 file/folder，并启动后台 processing。
watch scan 扫描 due watched sources，发现 added/changed 文件时创建 background
processing run。ai_draft 只有后台 run 成功后才会出现在 approve list。
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
from .ingestion_service import watch_scan_sources, watch_sources_for_display
from .cli_processing_runtime import config_path_from_cfg, start_cli_processing_run
from .process_service import FAKE_PROFILE
from .strategy_selection import StrategySelectionError, resolve_strategy_selection
from .watch_registry import (
    add_watch_source,
    delete_watch_source,
    normalize_frequency,
    registry_path_for_vault,
    set_watch_status,
)

watch_app = typer.Typer(
    add_completion=False,
    help="管理 watched sources；watch add 注册 source 并启动后台 processing。",
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
    """注册 watched source，并启动后台 processing。"""

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
    try:
        registry_result = add_watch_source(
            cfg.vault.root,
            registry_path_for_vault(cfg.vault.root),
            source_path,
            strategy_id=selected_strategy.strategy_id,
            frequency=frequency,
            recursive=recursive if source_path.is_dir() else False,
        )
    except (ValueError, RuntimeError) as exc:
        console.print(str(exc), markup=False, soft_wrap=True)
        raise typer.Exit(code=2) from exc
    action = "registered" if registry_result.added else "already registered"
    run = start_cli_processing_run(
        cfg,
        config_path=config_path_from_cfg(cfg, config),
        source_ref=registry_result.source.id,
        source_path=registry_result.source.path,
        mode="watch_scan",
        worker_args=[
            "--mode",
            "watch_scan",
            "--ref",
            registry_result.source.id,
            *(["--provider", provider] if provider else []),
            *(["--profile", profile] if profile else []),
            *([] if selected_strategy.strategy_id is None else ["--strategy", selected_strategy.strategy_id]),
        ],
    )
    _print_registered_source(action=action, target=registry_result.source.path)
    console.print(f"watch id: {registry_result.source.id}", markup=False)
    console.print(f"strategy_id: {registry_result.source.strategy_id or '-'}", markup=False)
    console.print(f"frequency: {registry_result.source.frequency}", markup=False)
    console.print(f"registry: {registry_path_for_vault(cfg.vault.root)}", markup=False, soft_wrap=True)
    _print_background_run_hint(run.record.run_id, reused_existing=run.reused_existing)


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
    """扫描 due watched sources，发现 added/changed 文件时启动后台 processing。

    中文学习型说明：watch scan 是 frequency scan 的产品入口。它先做只读 scan
    找到 added/changed 文件，再为有变更的每个 source 创建独立的 background
    ProcessingRun。用户通过 runs show 观察后台进度。没有常驻 daemon，
    可配合 cron/launchd/外部调度定期运行。
    """

    cfg = load_cfg(config, read_env=False)
    cfg = apply_provider_selection(cfg, provider=provider, legacy_profile=None)
    render_active_vault_resolution_notice(cfg)
    if cfg.llm.active_profile != FAKE_PROFILE:
        load_dotenv_silently(Path.cwd())

    # process_changes=False：只做 scan + diff，不调用 _ingest_targets_summary()。
    # CLI 负责为有变更的 source 创建 background ProcessingRun。
    try:
        summary = watch_scan_sources(cfg, ref=ref, all_sources=all_sources, process_changes=False)
    except (ValueError, RuntimeError) as exc:
        console.print(str(exc), markup=False, soft_wrap=True)
        raise typer.Exit(code=2) from exc

    console.print("[bold]watch scan[/bold]")
    console.print(
        "scanned={scanned} not_due={not_due} missing={missing} "
        "processed={processed} skipped={skipped} failed={failed} seen={seen}".format(
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

    # 为有 added/changed 的 source 创建 background processing run
    launched_count = 0
    for detail in summary.source_details:
        if not detail.has_changes:
            continue
        if not detail.path.exists():
            continue
        run = start_cli_processing_run(
            cfg,
            config_path=config_path_from_cfg(cfg, config),
            source_ref=detail.source_id,
            source_path=detail.path,
            mode="watch_scan",
            worker_args=[
                "--mode",
                "watch_scan",
                "--ref",
                detail.source_id,
                *(["--provider", provider] if provider else []),
            ],
        )
        launched_count += 1
        console.print(
            f"  Background processing started for {detail.source_id}: run_id={run.record.run_id}",
            markup=False,
        )

    if summary.missing:
        console.print("Missing watched source paths were kept; knowledge cards were not deleted.", markup=False)
    console.print("Boundary: source deletion never deletes approved knowledge.", markup=False)

    # 打印产品主路径提示
    if launched_count > 0:
        console.print(
            "Background processing started when changes were found; "
            "use runs show <run_id> to track progress.",
            markup=False,
        )
    else:
        console.print("No added/changed files found; no processing run created.", markup=False)
    console.print("Product path: mindforge watch add <file-or-folder>", markup=False)
    console.print("Background processing status: mindforge runs list", markup=False)


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
        from mindforge_web.services.processing_run_service import latest_run_for_source

        latest_run = latest_run_for_source(
            cfg,
            source_ref=source.id,
            source_path=str(source.path),
        )
        run_status = latest_run.status if latest_run is not None else "-"
        run_id = latest_run.run_id if latest_run is not None else "-"
        run_message = latest_run.message if latest_run is not None else "-"
        kind = "default" if source.is_default else "user-added"
        console.print(
            f"- {source.id} · {source.path_type} · {kind} · status={source.status} · "
            f"path={source.path} · last_seen={source.last_seen_at or '-'} · "
            f"last_processed={source.last_processed_at or '-'} · "
            f"frequency={source.frequency} · last_scan={source.last_scan_at or '-'} · "
            f"next_scan={source.next_scan_at or '-'} · "
            f"processing_status={run_status} · run_id={run_id} · "
            f"diff={source.diff_counts or {}} · "
            f"strategy_id={source.strategy_id or '-'} · fingerprint={source.fingerprint or '-'}",
            markup=False,
            soft_wrap=True,
        )
        if latest_run is not None:
            console.print(f"  processing_message={run_message}", markup=False, soft_wrap=True)


def _set_status(ref: str, config: Path, status: str) -> None:
    cfg = load_cfg(config, read_env=False)
    render_active_vault_resolution_notice(cfg)
    updated = set_watch_status(cfg.vault.root, registry_path_for_vault(cfg.vault.root), ref, status)  # type: ignore[arg-type]
    if updated is None:
        console.print(f"watch source not found: {ref}", markup=False)
        raise typer.Exit(code=2)
    console.print(f"watch {status}: {updated.id} {updated.path}", markup=False, soft_wrap=True)
    console.print("source and cards were not deleted.", markup=False)


def _print_registered_source(*, action: str, target: Path) -> None:
    console.print(f"[bold]Source {action}[/bold]")
    console.print(f"target: {target}", markup=False, soft_wrap=True)


def _print_background_run_hint(run_id: str, *, reused_existing: bool = False) -> None:
    """CLI watch 主路径的异步 processing 提示。

    中文学习型说明：用户主路径只承诺 source 已登记、processing run 已创建；
    draft 是否生成由后台 run 决定。没有模型 key 也应表现为 run failed /
    needs_model_setup，而不是 watch add 命令同步失败。
    """

    if reused_existing:
        console.print("Background processing is already active.", markup=False)
    else:
        console.print("Background processing started.", markup=False)
    console.print(f"run_id: {run_id}", markup=False)
    console.print("You can continue using MindForge.", markup=False)
    console.print(f"Check progress: mindforge runs show {run_id}", markup=False)
    console.print("Or: mindforge watch status", markup=False)
    console.print("Drafts appear in: mindforge approve list after processing succeeds.", markup=False)
    console.print(
        "If model setup is incomplete, this run will fail with next actions; retry after setup is fixed.",
        markup=False,
        soft_wrap=True,
    )


__all__ = ["watch_app"]
