"""Web ProcessingRun 持久化与后台执行边界。

中文学习型说明：ProcessingRun 是 Web 交互层的异步任务记录，不替代
``RunLogger``。RunLogger 记录 pipeline 内部事件；ProcessingRun 记录用户
点击 Process now 后能看到的任务状态、摘要、跳过原因和错误。这里不存 raw
source、不存 prompt、不存 API key，只保存用户可见的安全元数据。
"""

from __future__ import annotations

import json
import os
import secrets
import tempfile
import threading
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from mindforge.cards import iter_cards
from mindforge.config import MindForgeConfig
from mindforge.ingestion_service import IngestionSummary, WatchScanSummary

from mindforge_web.schemas import NextAction, ProcessingRunResponse


RunStatus = Literal["queued", "running", "succeeded", "skipped", "failed", "partial_failed"]
ACTIVE_RUN_STATUSES = {"queued", "running"}
ABANDONED_RUN_AFTER = timedelta(minutes=30)
HEARTBEAT_INTERVAL_SECONDS = 5.0


@dataclass
class ProcessingRunRecord:
    run_id: str
    source_ref: str
    source_path: str | None
    mode: str
    status: RunStatus
    started_at: str
    last_heartbeat_at: str | None = None
    finished_at: str | None = None
    current_step: str = "queued"
    summary: dict[str, int] = field(default_factory=lambda: {
        "discovered": 0,
        "processed": 0,
        "drafts": 0,
        "skipped": 0,
        "errors": 0,
    })
    draft_ids: list[str] = field(default_factory=list)
    message: str = "Processing started in the background. You can keep using MindForge."
    skip_reasons: list[str] = field(default_factory=list)
    error_type: str | None = None
    error_message: str | None = None


def start_processing_run(
    cfg: MindForgeConfig,
    *,
    source_ref: str,
    source_path: str | None,
    mode: str,
    work: Callable[[], IngestionSummary | WatchScanSummary],
) -> ProcessingRunRecord:
    """创建 run 文件并启动后台线程。

    中文学习型说明：HTTP 请求只做到“登记任务并返回 run_id”。LLM pipeline
    在 daemon thread 中继续执行，完成后把最后状态写回本地 JSON。第一版不做
    Redis/Celery/数据库，也不保证服务重启后恢复 queued/running，只保证已完成
    或失败的 summary 可在刷新后读取。
    """

    existing = latest_run_for_source(cfg, source_ref=source_ref, source_path=source_path)
    if existing is not None and existing.status in ACTIVE_RUN_STATUSES:
        # 中文学习型说明：当前实现是 request-spawn，不是 queue。同一 source 已有
        # active run 时复用原 run_id，避免重复点击生成多个并发 pipeline，造成 draft
        # attribution 和 Sources 状态互相覆盖。
        existing.message = (
            "Processing is already running in the background. You can keep using MindForge. "
            "Sources will show the final status, and Review will show any generated drafts."
        )
        _save_record(cfg, existing)
        return existing

    record = ProcessingRunRecord(
        run_id=_new_run_id(),
        source_ref=source_ref,
        source_path=source_path,
        mode=mode,
        status="queued",
        started_at=_now(),
        last_heartbeat_at=_now(),
        summary=_empty_summary(),
        message=started_response_message(),
    )
    _save_record(cfg, record)
    thread = threading.Thread(
        target=_run_worker,
        args=(cfg, record.run_id, work),
        name=f"mindforge-processing-{record.run_id}",
        daemon=True,
    )
    thread.start()
    return record


def get_processing_run(cfg: MindForgeConfig, run_id: str) -> ProcessingRunRecord | None:
    path = _run_path(cfg, run_id)
    if not path.exists():
        return None
    return _normalize_abandoned_run(cfg, _load_record(path))


def latest_run_for_source(
    cfg: MindForgeConfig,
    *,
    source_ref: str,
    source_path: str | None,
) -> ProcessingRunRecord | None:
    runs = [
        record
        for record in list_processing_runs(cfg)
        if record.source_ref == source_ref or (source_path is not None and record.source_path == source_path)
    ]
    if not runs:
        return None
    return max(runs, key=lambda item: item.started_at)


def list_processing_runs(cfg: MindForgeConfig) -> list[ProcessingRunRecord]:
    root = _runs_dir(cfg)
    if not root.is_dir():
        return []
    records: list[ProcessingRunRecord] = []
    for path in root.glob("*.json"):
        try:
            records.append(_normalize_abandoned_run(cfg, _load_record(path)))
        except Exception:
            continue
    return sorted(records, key=lambda item: item.started_at, reverse=True)


def processing_run_response(record: ProcessingRunRecord) -> ProcessingRunResponse:
    return ProcessingRunResponse(
        run_id=record.run_id,
        source_ref=record.source_ref,
        source_path=record.source_path,
        mode=record.mode,
        status=record.status,
        started_at=record.started_at,
        last_heartbeat_at=record.last_heartbeat_at,
        finished_at=record.finished_at,
        current_step=record.current_step,
        summary=dict(record.summary),
        draft_ids=list(record.draft_ids),
        message=record.message,
        skip_reasons=list(record.skip_reasons),
        error_type=record.error_type,
        error_message=record.error_message,
        next_actions=next_actions_for_record(record),
    )


def next_actions_for_record(record: ProcessingRunRecord) -> list[NextAction]:
    if record.status in {"queued", "running"}:
        return [
            NextAction(
                label="View source status",
                description="Processing is running in the background.",
                href="/sources",
            )
        ]
    if record.summary.get("drafts", 0) > 0:
        return [
            NextAction(
                label="Go to Review",
                description="Review generated AI drafts before approving.",
                href="/drafts",
            ),
            NextAction(
                label="View source status",
                description="See the processing summary for this source.",
                href="/sources",
            ),
        ]
    if record.status in {"failed", "partial_failed"}:
        return [
            NextAction(
                label="View error",
                description="Open Sources to inspect the latest processing error.",
                href="/sources",
            ),
            NextAction(
                label="Retry processing",
                description="Try Process now again after fixing the issue.",
                href="/sources",
            ),
        ]
    return [
        NextAction(
            label="View source status",
            description="No draft was generated; Sources shows the reason.",
            href="/sources",
        )
    ]


def started_response_message() -> str:
    # 中文学习型说明：启动响应不能暗示已经生成 draft；它只说明后台任务已登记，
    # 用户可以继续操作，最终结果以 run status / Sources summary 为准。
    return (
        "Processing started in the background. You can keep using MindForge. "
        "Sources will show the final status, and Review will show any generated drafts."
    )


def _run_worker(
    cfg: MindForgeConfig,
    run_id: str,
    work: Callable[[], IngestionSummary | WatchScanSummary],
) -> None:
    record = get_processing_run(cfg, run_id)
    if record is None:
        return
    if record.status not in ACTIVE_RUN_STATUSES:
        return
    record.status = "running"
    record.current_step = "processing source"
    record.last_heartbeat_at = _now()
    _save_record(cfg, record)

    before_draft_ids = _draft_ids(cfg)
    stop_heartbeat = threading.Event()
    heartbeat_thread = threading.Thread(
        target=_heartbeat_loop,
        args=(cfg, run_id, stop_heartbeat),
        name=f"mindforge-processing-heartbeat-{run_id}",
        daemon=True,
    )
    heartbeat_thread.start()
    try:
        _heartbeat(cfg, run_id)
        summary = work()
        _heartbeat(cfg, run_id)
        after_draft_ids = _draft_ids(cfg)
        draft_ids = sorted(after_draft_ids - before_draft_ids)
        _apply_summary(record, summary, draft_ids=draft_ids)
    except Exception as exc:
        record.status = "failed"
        record.current_step = "failed"
        record.finished_at = _now()
        record.summary = {**_empty_summary(), "errors": 1}
        record.error_type = type(exc).__name__
        record.error_message = _safe_error_message(str(exc))
        record.message = f"Processing failed. Reason: {record.error_message}"
    finally:
        stop_heartbeat.set()
    _save_final_record_if_active(cfg, record)


def _apply_summary(
    record: ProcessingRunRecord,
    summary: IngestionSummary | WatchScanSummary,
    *,
    draft_ids: list[str],
) -> None:
    counts = dict(getattr(summary, "counts", {}) or {})
    discovered = int(counts.get("seen") or getattr(summary, "scanned", 0) or 0)
    drafts = int(counts.get("processed", 0))
    skipped = int(counts.get("skipped", 0))
    errors = int(counts.get("failed", 0))
    skip_reasons = _skip_reasons(summary)
    error_messages = [
        _safe_error_message(str(item))
        for item in (getattr(summary, "errors", ()) or ())
        if str(item).strip()
    ]
    provider_failure = getattr(summary, "provider_failure", None)
    record.finished_at = _now()
    record.current_step = "completed"
    record.summary = {
        "discovered": discovered,
        "processed": drafts,
        "drafts": drafts,
        "skipped": skipped,
        "errors": errors,
    }
    record.draft_ids = draft_ids
    record.skip_reasons = skip_reasons
    if provider_failure is not None and errors:
        record.error_type = "ProviderError"
        record.error_message = _safe_error_message(provider_failure.message)
    elif error_messages and errors:
        record.error_type = "ProcessingError"
        record.error_message = error_messages[0]

    if errors and (drafts or skipped):
        record.status = "partial_failed"
    elif errors:
        record.status = "failed"
    elif drafts:
        record.status = "succeeded"
    elif skipped or discovered == 0:
        record.status = "skipped"
    else:
        record.status = "succeeded"
    record.message = _message_for_summary(record)


def _message_for_summary(record: ProcessingRunRecord) -> str:
    drafts = record.summary.get("drafts", 0)
    skipped = record.summary.get("skipped", 0)
    errors = record.summary.get("errors", 0)
    discovered = record.summary.get("discovered", 0)
    reason = record.error_message or _first_skip_reason(record.skip_reasons)
    if errors:
        suffix = f" Reason: {reason}" if reason else ""
        return f"Processing failed for {errors} item(s).{suffix}"
    if drafts:
        return f"Generated {drafts} AI draft{'s' if drafts != 1 else ''}."
    if skipped:
        suffix = f" Reason: {reason}" if reason else ""
        return f"Evaluated source, but no draft was generated.{suffix}"
    if discovered == 0:
        return "No supported source files found."
    return "Processing completed."


def _skip_reasons(summary: IngestionSummary | WatchScanSummary) -> list[str]:
    reasons: list[str] = []
    for item in getattr(summary, "skipped", ()) or ():
        reason = getattr(item, "reason", None)
        if reason:
            reasons.append(str(reason))
    return reasons


def _first_skip_reason(reasons: list[str]) -> str | None:
    if not reasons:
        return None
    return reasons[0]


def _draft_ids(cfg: MindForgeConfig) -> set[str]:
    ids: set[str] = set()
    for card in iter_cards(cfg.vault.root, cfg.vault.cards_dir).cards:
        if card.status == "ai_draft":
            ids.add(card.id or card.rel_path)
    return ids


def _empty_summary() -> dict[str, int]:
    return {"discovered": 0, "processed": 0, "drafts": 0, "skipped": 0, "errors": 0}


def _runs_dir(cfg: MindForgeConfig) -> Path:
    return cfg.state.workdir / "processing_runs"


def _run_path(cfg: MindForgeConfig, run_id: str) -> Path:
    return _runs_dir(cfg) / f"{run_id}.json"


def _save_record(cfg: MindForgeConfig, record: ProcessingRunRecord) -> None:
    root = _runs_dir(cfg)
    root.mkdir(parents=True, exist_ok=True)
    payload = asdict(record)
    fd, tmp_path = tempfile.mkstemp(prefix=".processing-run.", suffix=".tmp", dir=str(root))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(tmp_path, _run_path(cfg, record.run_id))
    except Exception:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise


def _load_record(path: Path) -> ProcessingRunRecord:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return ProcessingRunRecord(
        run_id=str(raw["run_id"]),
        source_ref=str(raw["source_ref"]),
        source_path=raw.get("source_path"),
        mode=str(raw.get("mode") or "watch_scan"),
        status=raw.get("status", "failed"),
        started_at=str(raw.get("started_at") or ""),
        finished_at=raw.get("finished_at"),
        current_step=str(raw.get("current_step") or ""),
        summary={str(k): int(v) for k, v in (raw.get("summary") or {}).items()},
        draft_ids=[str(item) for item in (raw.get("draft_ids") or [])],
        message=str(raw.get("message") or ""),
        skip_reasons=[str(item) for item in (raw.get("skip_reasons") or [])],
        error_type=raw.get("error_type"),
        error_message=raw.get("error_message"),
        last_heartbeat_at=raw.get("last_heartbeat_at"),
    )


def _normalize_abandoned_run(
    cfg: MindForgeConfig,
    record: ProcessingRunRecord,
) -> ProcessingRunRecord:
    """把服务重启后不可恢复的 active run 收敛成用户可见失败。

    中文学习型说明：第一阶段后台执行只靠当前进程的 daemon thread。进程重启后
    queued/running JSON 不会自动恢复执行；继续展示 running 会误导用户。这里
    不引入队列，只把超过阈值的 active run 标记为 abandoned failed，并保留
    retry/reprocess 的可行动入口。
    """

    if record.status not in ACTIVE_RUN_STATUSES:
        return record
    heartbeat_at = _parse_datetime(record.last_heartbeat_at or record.started_at)
    if heartbeat_at is None:
        return record
    now = datetime.now(timezone.utc).astimezone()
    if now - heartbeat_at <= ABANDONED_RUN_AFTER:
        return record

    record.status = "failed"
    record.current_step = "abandoned"
    record.finished_at = _now()
    record.summary = {**_empty_summary(), **dict(record.summary)}
    record.summary["errors"] = max(int(record.summary.get("errors", 0)), 1)
    record.error_type = "AbandonedProcessingRun"
    record.error_message = (
        "Processing did not finish after MindForge was closed or restarted. "
        "Run Process now again to retry."
    )
    record.message = f"Processing did not finish. Reason: {record.error_message}"
    _save_record(cfg, record)
    return record


def _heartbeat(cfg: MindForgeConfig, run_id: str) -> None:
    """轻量刷新 active run 的 heartbeat，不创建 scheduler 或 queue。

    中文学习型说明：heartbeat 只说明当前进程里的 worker 仍在推进该 run。
    它不是分布式 lease，也不恢复已中断任务；normalizer 只用它避免长耗时
    pipeline 被 started_at 固定阈值误判 abandoned。
    """

    latest = get_processing_run(cfg, run_id)
    if latest is None or latest.status not in ACTIVE_RUN_STATUSES:
        return
    latest.last_heartbeat_at = _now()
    _save_record(cfg, latest)


def _heartbeat_loop(
    cfg: MindForgeConfig,
    run_id: str,
    stop_event: threading.Event,
) -> None:
    """worker 运行期间定期刷新 heartbeat，避免长 pipeline 被误判 abandoned。"""

    while not stop_event.wait(HEARTBEAT_INTERVAL_SECONDS):
        _heartbeat(cfg, run_id)


def _save_final_record_if_active(cfg: MindForgeConfig, candidate: ProcessingRunRecord) -> None:
    """最终状态写盘前重新读取最新 record，保证 lifecycle 单调。

    中文学习型说明：normalizer 可能在 worker 长时间运行时先把 run 标记为
    abandoned failed。worker 完成后若直接保存旧内存对象，就会产生
    running -> failed -> succeeded 的状态回退。这里用 final reload guard 做
    最小 coordination：只有最新 record 仍是 queued/running，worker 才能写最终
    succeeded/failed/partial_failed。
    """

    latest = get_processing_run(cfg, candidate.run_id)
    if latest is None:
        return
    if latest.status not in ACTIVE_RUN_STATUSES:
        return
    candidate.last_heartbeat_at = _now()
    _save_record(cfg, candidate)


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc).astimezone()
    return parsed.astimezone()


def _new_run_id() -> str:
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H-%M-%S")
    return f"pr_{stamp}_{secrets.token_hex(3)}"


def _now() -> str:
    # 中文学习型说明：Sources 以 started_at 判断同一 source 的最新 run。
    # Process Now 可能被快速重复点击，秒级时间戳会让并发 run 的排序变得不稳定。
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="microseconds")


def _safe_error_message(message: str) -> str:
    # 中文学习型说明：用户主路径只需要可行动的 provider 错误。代理或网关常返回
    # HTML 错误页，直接塞进 run record 会让 Sources 变成不可读的内部噪音。
    lowered = message.lower()
    if "<!doctype html" in lowered or "<html" in lowered:
        status_hint = ""
        for code in ("400", "401", "403", "404", "408", "429", "500", "502", "503", "504"):
            if f"HTTP {code}" in message or f"HTTP {code}:" in message:
                status_hint = f" (HTTP {code})"
                break
        return (
            f"Provider returned an HTML error page{status_hint}. "
            "Check the model base URL, proxy, or provider availability."
        )
    # 保留 env var name / provider type 等诊断信息，但避免异常里夹带 token 形态值。
    redacted_words = []
    for word in message.split():
        if _looks_like_secret(word):
            redacted_words.append("[redacted]")
        else:
            redacted_words.append(word)
    return " ".join(redacted_words)


def _looks_like_secret(value: str) -> bool:
    lowered = value.lower()
    return (
        len(value) >= 20
        and (
            lowered.startswith(("sk-", "sk_", "api-", "token"))
            or "secret" in lowered
            or "apikey" in lowered
        )
    )
