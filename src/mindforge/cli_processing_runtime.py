"""CLI background processing runtime.

中文学习型说明：CLI 主路径和 Web 一样使用 ProcessingRun 作为用户可见
lifecycle，但 CLI 进程会在命令返回后退出，不能依赖 daemon thread。这里
只启动一次性 Python 子进程执行既有 ingestion service，不引入 queue /
scheduler，也不改变 pipeline 架构。
"""

from __future__ import annotations

import os
import secrets
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from mindforge.config import MindForgeConfig
from mindforge.processing.run_store import (
    ACTIVE_RUN_STATUSES,
    ProcessingRunRecord,
    _save_record as _save_processing_run_record,
    latest_run_for_source,
    started_response_message,
)


@dataclass(frozen=True)
class CliProcessingRunStart:
    record: ProcessingRunRecord
    reused_existing: bool = False


def start_cli_processing_run(
    cfg: MindForgeConfig,
    *,
    config_path: Path,
    source_ref: str,
    source_path: Path,
    mode: str,
    worker_args: list[str],
) -> CliProcessingRunStart:
    """创建 durable run 并启动一次性后台 worker 子进程。

    中文学习型说明：这里是 command path，允许写 run record；相对地，
    ``status`` / ``watch status`` / ``runs show`` 只能读取这些 record，
    不能为了展示而创建新的 processing run。
    """

    existing = latest_run_for_source(
        cfg,
        source_ref=source_ref,
        source_path=str(source_path.resolve()),
    )
    if existing is not None and existing.status in ACTIVE_RUN_STATUSES:
        return CliProcessingRunStart(record=existing, reused_existing=True)

    record = ProcessingRunRecord(
        run_id=_new_run_id(),
        source_ref=source_ref,
        source_path=str(source_path.resolve()),
        mode=mode,
        status="queued",
        started_at=_now(),
        last_heartbeat_at=_now(),
        message=started_response_message(),
    )
    _save_processing_run_record(cfg, record)
    _spawn_worker(config_path=config_path, run_id=record.run_id, worker_args=worker_args)
    return CliProcessingRunStart(record=record)


def config_path_from_cfg(cfg: MindForgeConfig, fallback: Path) -> Path:
    raw = cfg.raw if isinstance(cfg.raw, dict) else {}
    meta = raw.get("_mindforge_config")
    if isinstance(meta, dict) and meta.get("path"):
        return Path(str(meta["path"]))
    return fallback.expanduser().resolve()


def _spawn_worker(*, config_path: Path, run_id: str, worker_args: list[str]) -> None:
    cmd = [
        sys.executable,
        "-m",
        "mindforge.processing_worker",
        "--config",
        str(config_path.expanduser().resolve()),
        "--run-id",
        run_id,
        *worker_args,
    ]
    env = os.environ.copy()
    subprocess.Popen(  # noqa: S603 - argv is constructed internally, no shell.
        cmd,
        cwd=str(Path.cwd()),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="microseconds")


def _new_run_id() -> str:
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H-%M-%S")
    return f"pr_{stamp}_{secrets.token_hex(3)}"


__all__ = ["CliProcessingRunStart", "config_path_from_cfg", "start_cli_processing_run"]
