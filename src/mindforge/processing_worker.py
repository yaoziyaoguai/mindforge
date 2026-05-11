"""One-shot CLI processing worker.

中文学习型说明：这是 CLI async path 的子进程入口。它只执行已经登记好的
ProcessingRun，不提供长期 daemon、不扫描队列、不调度其它任务。用户命令
返回 run_id 后，最终状态由这个 worker 写回本地 run JSON。
"""

from __future__ import annotations

from pathlib import Path

import typer

from .app_context import load_app_config
from .cli_runtime import apply_provider_selection
from .ingestion_service import import_sources, watch_scan_sources
from .strategy_selection import resolve_strategy_selection
from mindforge_web.services.processing_run_service import _run_worker

app = typer.Typer(add_completion=False)


@app.callback(invoke_without_command=True)
def run(
    config: Path = typer.Option(..., "--config"),
    run_id: str = typer.Option(..., "--run-id"),
    mode: str = typer.Option(..., "--mode"),
    ref: str | None = typer.Option(None, "--ref"),
    target: Path | None = typer.Option(None, "--target"),
    force: bool = typer.Option(False, "--force"),
    strategy: str | None = typer.Option(None, "--strategy"),
    provider: str | None = typer.Option(None, "--provider", hidden=True),
    profile: str | None = typer.Option(None, "--profile", hidden=True),
) -> None:
    """执行单个 run；所有异常交给 ProcessingRun worker 收敛成 failed。"""

    cfg = load_app_config(config, cwd=Path.cwd())
    cfg = apply_provider_selection(cfg, provider=provider, legacy_profile=profile)

    def work():
        selected_strategy = resolve_strategy_selection(cfg, explicit_strategy=strategy)
        if mode == "watch_scan":
            if not ref:
                raise ValueError("watch processing requires --ref")
            return watch_scan_sources(cfg, ref=ref, all_sources=True, strategy=selected_strategy)
        if mode == "import":
            if target is None:
                raise ValueError("import processing requires --target")
            return import_sources(
                cfg,
                target.expanduser().resolve(),
                bypass_triage_gate=force,
                strategy=selected_strategy,
            )
        raise ValueError(f"unknown processing mode: {mode}")

    _run_worker(cfg, run_id, work)


if __name__ == "__main__":  # pragma: no cover
    app()
