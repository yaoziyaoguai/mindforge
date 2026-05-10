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
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from mindforge.cards import iter_cards
from mindforge.config import MindForgeConfig
from mindforge.ingestion_service import IngestionSummary, WatchScanSummary

from mindforge_web.schemas import NextAction, ProcessingRunResponse


RunStatus = Literal["queued", "running", "succeeded", "skipped", "failed", "partial_failed"]


@dataclass
class ProcessingRunRecord:
    run_id: str
    source_ref: str
    source_path: str | None
    mode: str
    status: RunStatus
    started_at: str
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

    record = ProcessingRunRecord(
        run_id=_new_run_id(),
        source_ref=source_ref,
        source_path=source_path,
        mode=mode,
        status="queued",
        started_at=_now(),
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
    return _load_record(path)


def latest_run_for_source(
    cfg: MindForgeConfig,
    *,
    source_ref: str,
    source_path: str,
) -> ProcessingRunRecord | None:
    runs = [
        record
        for record in list_processing_runs(cfg)
        if record.source_ref == source_ref or record.source_path == source_path
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
            records.append(_load_record(path))
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
                description="Run Process now again after fixing the error.",
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
    record.status = "running"
    record.current_step = "processing source"
    _save_record(cfg, record)

    before_draft_ids = _draft_ids(cfg)
    try:
        summary = work()
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
    _save_record(cfg, record)


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
    )


def _new_run_id() -> str:
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H-%M-%S")
    return f"pr_{stamp}_{secrets.token_hex(3)}"


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


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
