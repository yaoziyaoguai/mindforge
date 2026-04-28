"""run_logger — 运行事件日志（observer / event log）。

定位（与 state.json 的职责分离）：
- ``state.json`` 是 **checkpoint**：当前每条 source 的最新状态、content_hash、
  stage 路由记录（M2 起）。它是"现在的快照"。
- ``.mindforge/runs/<run_id>.jsonl`` 是 **observer / event log**：一次命令运行
  期间发生的所有事件（按时间顺序，append-only）。它是"过程的回放证据"。

约定（v0.1）：
- 每次 CLI 命令运行 = 一个 run = 一个 jsonl 文件 = 一个 ``run_id``。
- ``run_id`` 形如 ``2026-04-28T13-00-00_ab12cd``（ISO 时间 + 6 位随机 hex）。
- 事件文件按 append-only 写入，**不**回头改前面的行。
- **绝不**写入 raw_text / 文章正文 / 卡片正文，避免泄漏隐私和 token 浪费。
- 事件字段白名单：``source_id`` / ``source_type`` / ``adapter_name`` /
  ``content_hash`` / ``status`` / ``path`` / ``command`` / ``run_id`` / ``ts`` /
  ``error_message`` / ``counts`` / ``items_count``。
- M2 起每条 ``llm_call`` 事件还会追加：``stage`` / ``model_alias`` / ``provider``
  / ``actual_model`` / ``prompt_version`` / ``input_file_hash`` / ``tokens_in`` /
  ``tokens_out`` / ``latency_ms``。

使用方式：

    with RunLogger(runs_dir, command="scan") as logger:
        for result in scanner.iter_results():
            logger.emit("source_seen", source_type=..., path=..., ...)
        logger.emit("state_written", path=..., items_count=...)
        # 退出时自动 emit run_finished；异常时自动 emit run_failed 并保留异常
"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from typing import Any, TextIO

EVENT_RUN_STARTED = "run_started"
EVENT_RUN_FINISHED = "run_finished"
EVENT_RUN_FAILED = "run_failed"
EVENT_SOURCE_SEEN = "source_seen"
EVENT_SOURCE_SKIPPED_OR_UNCHANGED = "source_skipped_or_unchanged"
EVENT_SOURCE_ERROR = "source_error"
EVENT_STATE_WRITTEN = "state_written"
EVENT_STATUS_REPORTED = "status_reported"

# 字段白名单 — 任何 emit 调用传入的字段都必须在此（除 event/ts/run_id 内置外）。
# 用白名单显式抵御"顺手把 raw_text 塞进日志"的反模式。
_ALLOWED_FIELDS: frozenset[str] = frozenset(
    {
        "command",
        "config_path",
        "source_id",
        "source_type",
        "adapter_name",
        "source_path",
        "path",
        "content_hash",
        "status",
        "error_message",
        "counts",
        "items_count",
        "active_profile",
        # M2 起追加的 LLM 字段（提前白名单，避免 M2 改这里）
        "stage",
        "model_alias",
        "provider",
        "actual_model",
        "prompt_version",
        "input_file_hash",
        "tokens_in",
        "tokens_out",
        "latency_ms",
    }
)


def _generate_run_id(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc).astimezone()
    stamp = now.strftime("%Y-%m-%dT%H-%M-%S")
    suffix = secrets.token_hex(3)
    return f"{stamp}_{suffix}"


def _utc_iso(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc).astimezone()
    return now.isoformat(timespec="seconds")


@dataclass
class RunLogger:
    """一次 CLI 运行的事件日志（append-only jsonl）。

    线程模型：单线程使用，不做锁。M2 引入并发时再考虑。
    """

    runs_dir: Path
    command: str
    run_id: str = field(default_factory=_generate_run_id)
    _fp: TextIO | None = field(default=None, init=False, repr=False)
    _closed: bool = field(default=False, init=False, repr=False)

    @property
    def jsonl_path(self) -> Path:
        return self.runs_dir / f"{self.run_id}.jsonl"

    # ------------------------------------------------------------------ open
    def open(self) -> RunLogger:
        if self._fp is not None:
            return self
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self._fp = self.jsonl_path.open("a", encoding="utf-8")
        return self

    # ------------------------------------------------------------------ emit
    def emit(self, event: str, **fields: Any) -> None:
        if self._closed:
            raise RuntimeError("RunLogger 已关闭，不可再 emit")
        if self._fp is None:
            self.open()
        unknown = set(fields) - _ALLOWED_FIELDS
        if unknown:
            raise ValueError(
                f"RunLogger.emit: 字段 {sorted(unknown)} 不在白名单内。"
                "如确需新字段，请在 run_logger._ALLOWED_FIELDS 显式登记。"
            )
        record: dict[str, Any] = {
            "ts": _utc_iso(),
            "run_id": self.run_id,
            "event": event,
            **fields,
        }
        line = json.dumps(record, ensure_ascii=False, default=str)
        assert self._fp is not None
        self._fp.write(line + "\n")
        self._fp.flush()

    # ----------------------------------------------------------------- close
    def close(self) -> None:
        if self._fp is not None:
            self._fp.close()
            self._fp = None
        self._closed = True

    # --------------------------------------------------- context manager API
    def __enter__(self) -> RunLogger:
        self.open()
        self.emit(EVENT_RUN_STARTED, command=self.command)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            if exc_val is not None:
                # 不吞异常；只记录后让其继续传播
                try:
                    self.emit(
                        EVENT_RUN_FAILED,
                        error_message=f"{type(exc_val).__name__}: {exc_val}",
                    )
                except Exception:
                    pass
            else:
                self.emit(EVENT_RUN_FINISHED)
        finally:
            self.close()


__all__ = [
    "RunLogger",
    "EVENT_RUN_STARTED",
    "EVENT_RUN_FINISHED",
    "EVENT_RUN_FAILED",
    "EVENT_SOURCE_SEEN",
    "EVENT_SOURCE_SKIPPED_OR_UNCHANGED",
    "EVENT_SOURCE_ERROR",
    "EVENT_STATE_WRITTEN",
    "EVENT_STATUS_REPORTED",
]
