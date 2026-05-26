"""Source, Watch, and Ingestion schemas.

中文学习型说明：这些 schema 涵盖源文件管理、监控注册、导入/处理
运行状态等 Web adapter 层的核心契约。所有路径以安全视图暴露，
通过 SourcePathViewModel 控制可显示/可复制/可 Finder 揭示的范围。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from mindforge_web.schemas.common import NextAction, SourcePathViewModel, StatusItem


class SourceStatus(BaseModel):
    source_type: str
    adapter: str
    inbox_subdir: str
    file_glob: str
    enabled: bool
    path: str
    source_path_view: SourcePathViewModel | None = None
    exists: bool
    file_count: int
    error_count: int = 0
    processed_count: int = 0
    pending_files: list[str] = Field(default_factory=list)
    processed_files: list[str] = Field(default_factory=list)
    display_status: str
    generated_knowledge_status: str
    generated_card_count: int = 0
    generated_card_paths: list[str] = Field(default_factory=list)
    next_action: NextAction | None = None


class WatchedSourceResponse(BaseModel):
    id: str
    path: str
    source_path_view: SourcePathViewModel | None = None
    path_type: Literal["file", "folder"]
    is_default: bool
    kind: Literal["default", "user-added"]
    status: str
    added_at: str
    last_seen_at: str | None = None
    last_processed_at: str | None = None
    last_scan_at: str | None = None
    next_scan_at: str | None = None
    frequency: str = "manual"
    due_status: Literal["Due", "Not due", "Manual"] = "Manual"
    fingerprint: str | None = None
    can_delete: bool
    error: str | None = None
    recursive: bool = False
    supported_file_count: int = 0
    processed_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    skipped_reason_summary: dict[str, int] = Field(default_factory=dict)
    diff_counts: dict[str, int] = Field(default_factory=dict)
    generated_knowledge_status: str = "No generated knowledge"
    generated_card_count: int = 0
    generated_card_paths: list[str] = Field(default_factory=list)
    status_label: str = "Watching"
    active_run_id: str | None = None
    last_run_id: str | None = None
    last_run_started_at: str | None = None
    last_run_finished_at: str | None = None
    processing_status: str | None = None
    last_run_summary: dict[str, int] | None = None
    last_message: str | None = None
    last_error: str | None = None
    generated_draft_count: int = 0


class WatchSourcesResponse(BaseModel):
    vault_root: str
    registry_path: str
    watched_sources: list[WatchedSourceResponse]
    next_actions: list[NextAction]


class IngestionRequest(BaseModel):
    path: str
    frequency: str | None = None
    recursive: bool | None = None
    process_now: bool = True


class FrequencyUpdateRequest(BaseModel):
    frequency: str


class IngestionActionResponse(BaseModel):
    ok: bool
    mode: str
    target: str
    counts: dict[str, int]
    message: str
    added_to_registry: bool
    registry_path: str | None = None
    watch_id: str | None = None
    source_deleted: bool = False
    cards_deleted: bool = False
    next_actions: list[NextAction] = Field(default_factory=list)
    run_id: str | None = None
    processing_status: str | None = None
    skip_reasons: list[str] = Field(default_factory=list)
    error_message: str | None = None


class ProcessingRunResponse(BaseModel):
    run_id: str
    source_ref: str
    source_path: str | None = None
    source_path_view: SourcePathViewModel | None = None
    mode: str
    status: Literal["queued", "running", "succeeded", "skipped", "failed", "partial_failed"]
    started_at: str
    last_heartbeat_at: str | None = None
    finished_at: str | None = None
    current_step: str
    summary: dict[str, int] = Field(default_factory=dict)
    draft_ids: list[str] = Field(default_factory=list)
    message: str
    skip_reasons: list[str] = Field(default_factory=list)
    error_type: str | None = None
    error_message: str | None = None
    next_actions: list[NextAction] = Field(default_factory=list)


class IngestionSummaryStatus(BaseModel):
    primary_entry: str
    safety_note: str
    advanced_note: str


class SourcesResponse(BaseModel):
    sources: list[SourceStatus]
    bucket_counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    watched_sources: list[WatchedSourceResponse] = Field(default_factory=list)
    available_imports: list[StatusItem]
    ingestion: IngestionSummaryStatus
    next_actions: list[NextAction]
