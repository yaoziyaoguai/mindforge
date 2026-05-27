"""Web ProcessingRun 响应层 — thin re-export shim。

中文学习型说明：ProcessingRun 的持久化、查询和 worker 逻辑已迁移到
``mindforge.processing.run_store``（core 层）。此模块仅保留依赖 web schema
的响应构造函数，其余全部从 core 层 re-export。Web routers 可以继续从这里
import 而不需要改 import 路径。
"""

from __future__ import annotations

from pathlib import Path

from mindforge.processing.run_store import (  # noqa: F401 — re-export for backward compat
    ACTIVE_RUN_STATUSES,
    ABANDONED_RUN_AFTER,
    HEARTBEAT_INTERVAL_SECONDS,
    ProcessingRunRecord,
    RunStatus,
    _apply_summary,
    _draft_ids,
    _empty_summary,
    _failed_current_step,
    _first_skip_reason,
    _heartbeat,
    _heartbeat_loop,
    _load_record,
    _looks_like_secret,
    _message_for_summary,
    _new_run_id,
    _normalize_abandoned_run,
    _now,
    _parse_datetime,
    _run_worker,
    _running_message,
    _runs_dir,
    _run_path,
    _safe_error_message,
    _save_final_record_if_active,
    _save_record,
    _skip_reasons,
    get_processing_run,
    latest_run_for_source,
    list_processing_runs,
    start_processing_run,
    start_sync_processing_run,
    started_response_message,
)

from mindforge_web.schemas import NextAction, ProcessingRunResponse


# ── Web-specific response constructors（依赖 mindforge_web.schemas）─────

def processing_run_response(
    record: ProcessingRunRecord,
    *,
    path_action_service: object | None = None,
) -> ProcessingRunResponse:
    """把内部 run record 转成 Web-safe public response。

    中文学习型说明：ProcessingRunRecord 是本地持久化状态，source_path/source_ref
    可包含 import 时的 absolute path；ProcessingRunResponse 是浏览器可见契约，
    必须先构造 source_path_view，再决定 raw source_path/source_ref 是否可见。
    """

    message = record.message
    if record.status in ACTIVE_RUN_STATUSES and record.current_step:
        message = _running_message(record)
    source_path_view = None
    source_path = record.source_path
    if path_action_service is not None:
        source_path_view = path_action_service.build_source_path_view(record.source_path)
        source_path = path_action_service.safe_source_path(record.source_path, source_path_view)
    return ProcessingRunResponse(
        run_id=record.run_id,
        source_ref=_safe_public_source_ref(
            record.source_ref,
            raw_source_path=record.source_path,
            source_path_view=source_path_view,
            raw_source_visible=source_path is not None,
        ),
        source_path=source_path,
        source_path_view=source_path_view,
        mode=record.mode,
        status=record.status,
        started_at=record.started_at,
        last_heartbeat_at=record.last_heartbeat_at,
        finished_at=record.finished_at,
        current_step=record.current_step,
        summary=dict(record.summary),
        draft_ids=list(record.draft_ids),
        message=message,
        skip_reasons=list(record.skip_reasons),
        error_type=record.error_type,
        error_message=record.error_message,
        next_actions=next_actions_for_record(record),
    )


def _safe_public_source_ref(
    source_ref: str,
    *,
    raw_source_path: str | None,
    source_path_view: object | None,
    raw_source_visible: bool,
) -> str:
    """Redact source_ref 中嵌入的 raw path。

    中文学习型说明：import run 的内部 source_ref 形如 ``import:/absolute/path``，
    用于 active-run dedup；这个内部 key 不等于用户可见标识。若 path view 不允许
    展示 full path，就只保留安全 display_path，避免 source_ref 绕过
    source_path redaction。
    """

    if raw_source_visible or not raw_source_path:
        return source_ref
    display = getattr(source_path_view, "display_path", None) or Path(raw_source_path).name or "source"
    if raw_source_path in source_ref:
        return source_ref.replace(raw_source_path, display)
    if source_ref.startswith("import:"):
        return f"import:{display}"
    return source_ref


def next_actions_for_record(record: ProcessingRunRecord) -> list[NextAction]:
    if record.status in {"queued", "running"}:
        return [
            NextAction(
                label="View source status",
                description="Processing is running in the background.",
                href="/sources",
                action_key="processing.view_run_status",
                description_key="processing.view_run_status.desc",
            )
        ]
    if record.summary.get("drafts", 0) > 0:
        return [
            NextAction(
                label="Go to Review",
                description="Review generated AI drafts before approving.",
                href="/drafts",
                action_key="processing.review_drafts",
                description_key="processing.review_drafts.desc",
            ),
            NextAction(
                label="View source status",
                description="See the processing summary for this source.",
                href="/sources",
                action_key="processing.view_source_status",
                description_key="processing.view_source_status.desc",
            ),
        ]
    if record.status in {"failed", "partial_failed"}:
        return [
            NextAction(
                label="View error",
                description="Open Sources to inspect the latest processing error.",
                href="/sources",
                action_key="processing.view_error",
                description_key="processing.view_error.desc",
            ),
            NextAction(
                label="Retry processing",
                description="Try Process now again after fixing the issue.",
                href="/sources",
                action_key="processing.retry_processing",
                description_key="processing.retry_processing.desc",
            ),
        ]
    return [
        NextAction(
            label="View source status",
            description="No draft was generated; Sources shows the reason.",
            href="/sources",
            action_key="processing.view_sources",
            description_key="processing.view_sources.desc",
        )
    ]
