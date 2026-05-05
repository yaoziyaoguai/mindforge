"""M5.7 — 本地使用 telemetry（**严格白名单 + 永不上传**）。

设计契约（详见 docs/SECURITY.md 的 local telemetry 边界）：

1. **本地 only**：写到 ``<state.workdir>/telemetry.jsonl``（默认
   ``.mindforge/telemetry.jsonl``），与 ``runs/`` 平级但分文件。
   .gitignore 默认覆盖 ``.mindforge/`` 整目录，避免误提交。
2. **永不上传**：本模块没有任何 HTTP 客户端、没有 sink，**只**写本地
   jsonl。``local_only`` 配置项目前固定为 True，未来若引入远程上传，
   必须先扩展协议、加 opt-in 开关、加额外测试。
3. **元数据 only**：字段白名单（见 ``ALLOWED_FIELDS``）只允许：
   命令名、是否成功、耗时、计数、错误码、版本号、时间戳。
   **绝不**记录 raw_text / source body / card body / prompt /
   completion / api_key / Authorization / .env / 全绝对私有路径
   （``error_code`` 是 ``ValueError`` 这类异常类名，不是异常文本）。
4. **disabled 时零开销**：``record_event`` 在 ``enabled=False`` 时直接
   返回，不打开文件、不写盘。
5. **失败安全**：写盘失败（磁盘满 / 权限）静默吞掉，不影响业务命令。

Telemetry 的目的不是 dashboard，不是运营分析，而是回答用户自己的问题：
"我到底用了哪些命令、哪些命令耗时长、哪些命令出错频繁"。
"""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from . import __version__ as _MINDFORGE_VERSION

# ---------------------------------------------------------------------------
# 字段白名单 — 任何未列出的字段都会被丢弃（不抛异常，避免业务命令崩溃）
# ---------------------------------------------------------------------------
ALLOWED_FIELDS: frozenset[str] = frozenset(
    {
        "event_name",
        "command",
        "success",
        "duration_ms",
        "result_count",
        "project_count",
        "card_count",
        "error_code",
        "timestamp",
        "mindforge_version",
    }
)


@dataclass(frozen=True)
class TelemetryConfig:
    """telemetry 子配置。``enabled=False`` 时整个模块静默。"""

    enabled: bool = True
    local_only: bool = True


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------


def telemetry_path(workdir: Path) -> Path:
    """``<state.workdir>/telemetry.jsonl``。"""
    return workdir / "telemetry.jsonl"


def record_event(
    workdir: Path,
    cfg: TelemetryConfig,
    *,
    event_name: str,
    command: str,
    success: bool,
    duration_ms: int | None = None,
    result_count: int | None = None,
    project_count: int | None = None,
    card_count: int | None = None,
    error_code: str | None = None,
) -> None:
    """追加一条 telemetry 记录。

    禁止把任何文本内容（card body / prompt / etc）传进来；本函数显式
    用关键字参数，每个字段都在白名单。``error_code`` 是异常类名（如
    ``"ValueError"``），**不是**异常文本。
    """
    if not cfg.enabled:
        return

    record: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "mindforge_version": _MINDFORGE_VERSION,
        "event_name": event_name,
        "command": command,
        "success": bool(success),
    }
    if duration_ms is not None:
        record["duration_ms"] = int(duration_ms)
    if result_count is not None:
        record["result_count"] = int(result_count)
    if project_count is not None:
        record["project_count"] = int(project_count)
    if card_count is not None:
        record["card_count"] = int(card_count)
    if error_code is not None:
        # 防御：error_code 必须是简短标识符（异常类名），剪裁到 80 字符
        record["error_code"] = str(error_code)[:80]

    # 二次过滤：白名单外的字段一律剔除（防御未来误传）
    record = {k: v for k, v in record.items() if k in ALLOWED_FIELDS}

    try:
        workdir.mkdir(parents=True, exist_ok=True)
        with telemetry_path(workdir).open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        # 写盘失败永远不影响业务命令
        return


@contextmanager
def measure(
    workdir: Path,
    cfg: TelemetryConfig,
    command: str,
    *,
    project_count: int | None = None,
) -> Iterator["TelemetryHandle"]:
    """计时上下文：进入时记 start，退出时写一条 telemetry。

    使用：

        with measure(workdir, tcfg, "project-context", project_count=2) as h:
            ...
            h.set_counts(card_count=5, result_count=5)
    """
    handle = TelemetryHandle(project_count=project_count)
    t0 = time.monotonic()
    try:
        yield handle
        success = True
        error_code: str | None = None
    except BaseException as exc:  # noqa: BLE001 — 我们要立即记一条再继续抛
        success = False
        error_code = type(exc).__name__
        raise
    finally:
        duration_ms = int((time.monotonic() - t0) * 1000)
        record_event(
            workdir,
            cfg,
            event_name="command_completed",
            command=command,
            success=success,
            duration_ms=duration_ms,
            result_count=handle.result_count,
            project_count=handle.project_count,
            card_count=handle.card_count,
            error_code=error_code,
        )


@dataclass
class TelemetryHandle:
    """``measure`` 上下文返回的句柄；用 setter 写入计数字段。"""

    project_count: int | None = None
    card_count: int | None = None
    result_count: int | None = None

    def set_counts(
        self,
        *,
        card_count: int | None = None,
        result_count: int | None = None,
        project_count: int | None = None,
    ) -> None:
        if card_count is not None:
            self.card_count = card_count
        if result_count is not None:
            self.result_count = result_count
        if project_count is not None:
            self.project_count = project_count


# ---------------------------------------------------------------------------
# 读取与汇总（mindforge telemetry status / summary 的核心）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TelemetrySummary:
    total: int
    success: int
    failure: int
    by_command: dict[str, int]
    avg_duration_ms_by_command: dict[str, int]
    recent_errors: list[dict[str, Any]]  # 最近 N 条失败事件（仅元数据）


def read_events(workdir: Path) -> list[dict[str, Any]]:
    """读取 telemetry.jsonl 全量；缺文件返回空列表，不抛。"""
    p = telemetry_path(workdir)
    if not p.exists() or not p.is_file():
        return []
    out: list[dict[str, Any]] = []
    try:
        for line in p.read_text("utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict):
                out.append(rec)
    except OSError:
        return []
    return out


def summarize(events: list[dict[str, Any]], *, recent_errors: int = 5) -> TelemetrySummary:
    """聚合统计；只看白名单字段。"""
    total = len(events)
    success = sum(1 for e in events if e.get("success") is True)
    failure = total - success

    by_command: dict[str, int] = {}
    durations: dict[str, list[int]] = {}
    for e in events:
        cmd = str(e.get("command") or "(unknown)")
        by_command[cmd] = by_command.get(cmd, 0) + 1
        d = e.get("duration_ms")
        if isinstance(d, int):
            durations.setdefault(cmd, []).append(d)

    avg_duration: dict[str, int] = {
        cmd: int(sum(ds) / len(ds)) for cmd, ds in durations.items() if ds
    }

    errors_only = [
        {
            "timestamp": e.get("timestamp"),
            "command": e.get("command"),
            "error_code": e.get("error_code"),
            "duration_ms": e.get("duration_ms"),
        }
        for e in events
        if e.get("success") is False
    ]
    errors_only = errors_only[-recent_errors:]

    return TelemetrySummary(
        total=total,
        success=success,
        failure=failure,
        by_command=by_command,
        avg_duration_ms_by_command=avg_duration,
        recent_errors=errors_only,
    )


__all__ = [
    "ALLOWED_FIELDS",
    "TelemetryConfig",
    "TelemetryHandle",
    "TelemetrySummary",
    "measure",
    "read_events",
    "record_event",
    "summarize",
    "telemetry_path",
]
