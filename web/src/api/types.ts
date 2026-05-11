export type StatusLevel = "ok" | "info" | "warn" | "error";

export interface NextAction {
  label: string;
  description: string;
  command?: string | null;
  href?: string | null;
}

export interface StatusItem {
  key: string;
  label: string;
  status: StatusLevel;
  value: string;
  detail?: string | null;
  next_action?: NextAction | null;
}

export interface EnvKeyStatus {
  name: string;
  configured: boolean;
  sources: string[];
}

export interface ProviderStatus {
  active_profile: string;
  opt_in_state: string;
  can_run_real_smoke: boolean;
  aliases: Array<{
    alias: string;
    type: string;
    in_active_profile: boolean;
    api_key_env?: string | null;
    api_key_present: boolean;
    base_url_env_present: boolean;
  }>;
  blockers: string[];
}

export interface SafetySummary {
  local_only: boolean;
  host: string;
  vault_path: string;
  vault_status: StatusLevel;
  provider_state: string;
  env_status: StatusLevel;
  write_mode: "read_only" | "explicit_approval_required";
  pending_drafts_count: number;
  warnings: string[];
}

export interface VaultStatus {
  path: string;
  exists: boolean;
  inbox_exists: boolean;
  cards_exists: boolean;
  projects_exists: boolean;
  approved_card_count: number;
  draft_card_count: number;
  scan_error_count: number;
  is_real_environment: boolean;
}

export interface RecallStatus {
  index_path: string;
  index_exists: boolean;
  approved_card_count: number;
  available: boolean;
  next_action?: NextAction | null;
}

export interface HomeStatusResponse {
  safety: SafetySummary;
  workspace: {
    config_path: string;
    state_path: string;
    state_exists: boolean;
    state_item_count: number;
    source_counts: Record<string, number>;
    status_counts: Record<string, number>;
  };
  vault: VaultStatus;
  provider: ProviderStatus;
  env_keys: EnvKeyStatus[];
  recall: RecallStatus;
  cards_by_status: Record<string, number>;
  next_actions: NextAction[];
}

export interface ConfigStatusResponse {
  safety: SafetySummary;
  config_path: string;
  configured_keys: EnvKeyStatus[];
  missing_keys: EnvKeyStatus[];
  provider: ProviderStatus;
  cubox: StatusItem;
  vault: VaultStatus;
  checklist: StatusItem[];
  next_actions: NextAction[];
}

export interface EditableProviderConfig {
  name: string;
  type: string;
  default_base_url?: string | null;
  default_model?: string | null;
  api_key_env?: string | null;
  api_key_status: "present" | "missing" | "hidden";
  api_key_env_configured: boolean;
  api_key_secret_present: boolean;
  api_key_masked_value?: string | null;
  api_key_status_label: string;
  base_url_env?: string | null;
  base_url_env_present: boolean;
  base_url_env_status: "present" | "missing" | "not_configured";
  effective_base_url?: string | null;
  base_url_source: "env" | "config_default" | "missing";
  model_env?: string | null;
  model_env_present: boolean;
  model_env_status: "present" | "missing" | "not_configured";
  effective_model?: string | null;
  model_source: "env" | "config_default" | "missing";
}

export interface EditableModelConfig {
  model_id: string;
  type: string;
  base_url?: string | null;
  model?: string | null;
  api_key_env?: string | null;
  api_key_optional: boolean;
  api_key_status: "present" | "missing" | "hidden";
  api_key_env_configured: boolean;
  api_key_secret_present: boolean;
  api_key_masked_value?: string | null;
  api_key_status_label: string;
  api_key_source: "local_secret" | "env" | "missing" | "demo";
  is_demo_model: boolean;
  base_url_env?: string | null;
  model_env?: string | null;
  effective_base_url?: string | null;
  base_url_source: "env" | "config_default" | "missing";
  effective_model?: string | null;
  model_source: "env" | "config_default" | "missing";
}

export interface ResolvedWorkflowModelConfig {
  workflow_step: string;
  model_id: string;
  type: string;
  base_url?: string | null;
  model?: string | null;
}

export interface ProcessingWorkflowStep {
  id: string;
  label: string;
  purpose: string;
  model_id: string;
  prompt_id: string;
  prompt_version: string;
  prompt_description: string;
  can_view_prompt: boolean;
}

export interface ProcessingWorkflowConfig {
  active_strategy_id: string;
  active_strategy_label: string;
  active_strategy_description: string;
  active_strategy_status: string;
  available_strategies: { id: string; label: string; version: string; status: string; description: string }[];
  workflow_steps: ProcessingWorkflowStep[];
}

export interface EditableWikiConfig {
  mode: string;
  model?: string | null;
  auto_rebuild_on_approve: boolean;
}

export interface SetupEditableConfigResponse {
  config_path: string;
  normalized_on_save: boolean;
  vault: {
    root: string;
    exists: boolean;
    inbox_exists: boolean;
    cards_exists: boolean;
    projects_exists: boolean;
  };
  wiki?: EditableWikiConfig | null;
  llm: {
    active_provider: string;
    available_providers: string[];
    providers: Record<string, EditableProviderConfig>;
    readiness: ProviderStatus;
    configured_model_ids: string[];
    configured_models: Record<string, EditableModelConfig>;
    default_model?: string | null;
    routing: Record<string, string>;
    routing_is_explicit: boolean;
    resolved_per_step_models: Record<string, ResolvedWorkflowModelConfig>;
    processing_workflow?: ProcessingWorkflowConfig | null;
    legacy_config_detected: boolean;
    validation_errors: string[];
    warnings: string[];
  };
  cubox: {
    export_path?: string | null;
    import_path?: string | null;
    token_status: "present" | "missing" | "hidden";
  };
  watch_summary: StatusItem;
}

export interface SetupConfigPatch {
  vault_root?: string | null;
  create_vault?: boolean;
  active_provider?: string | null;
  providers?: Record<string, {
    default_base_url?: string | null;
    default_model?: string | null;
    api_key_env?: string | null;
    base_url_env?: string | null;
    model_env?: string | null;
  }>;
  default_model?: string | null;
  models?: Record<string, {
    type?: string | null;
    base_url?: string | null;
    model?: string | null;
    api_key_env?: string | null;
    api_key_optional?: boolean | null;
    base_url_env?: string | null;
    model_env?: string | null;
    api_key?: string | null;
    api_key_action?: "keep" | "clear" | "update" | null;
  }>;
  routing?: Record<string, string>;
  wiki_mode?: string | null;
  wiki_model?: string | null;
  wiki_auto_rebuild_on_approve?: boolean | null;
  cubox_export_path?: string | null;
  cubox_import_path?: string | null;
}

export interface SetupValidationResponse {
  ok: boolean;
  errors: string[];
  warnings: string[];
}

export interface SetupConfigUpdateResponse {
  ok: boolean;
  message: string;
  status: ConfigStatusResponse;
  editable: SetupEditableConfigResponse;
}

export interface SourceStatus {
  source_type: string;
  adapter: string;
  inbox_subdir: string;
  file_glob: string;
  enabled: boolean;
  path: string;
  exists: boolean;
  file_count: number;
  error_count: number;
  processed_count: number;
  pending_files: string[];
  processed_files: string[];
  display_status: string;
  generated_knowledge_status: string;
  generated_card_count: number;
  generated_card_paths: string[];
  next_action?: NextAction | null;
}

export interface ProcessingRunResponse {
  run_id: string;
  source_ref: string;
  source_path?: string | null;
  mode: string;
  status: "queued" | "running" | "succeeded" | "skipped" | "failed" | "partial_failed";
  started_at: string;
  finished_at?: string | null;
  current_step: string;
  summary: Record<string, number>;
  draft_ids: string[];
  message: string;
  skip_reasons: string[];
  error_type?: string | null;
  error_message?: string | null;
  next_actions: NextAction[];
}

export interface WatchedSourceResponse {
  id: string;
  path: string;
  path_type: "file" | "folder";
  is_default: boolean;
  kind: "default" | "user-added";
  status: string;
  added_at: string;
  last_seen_at?: string | null;
  last_processed_at?: string | null;
  last_scan_at?: string | null;
  next_scan_at?: string | null;
  frequency: string;
  due_status: "Due" | "Not due" | "Manual";
  fingerprint?: string | null;
  can_delete: boolean;
  error?: string | null;
  recursive: boolean;
  supported_file_count: number;
  processed_count: number;
  skipped_count: number;
  failed_count: number;
  skipped_reason_summary: Record<string, number>;
  diff_counts: Record<string, number>;
  generated_knowledge_status: string;
  generated_card_count: number;
  generated_card_paths: string[];
  status_label: string;
  active_run_id?: string | null;
  last_run_id?: string | null;
  last_run_started_at?: string | null;
  last_run_finished_at?: string | null;
  processing_status?: ProcessingRunResponse["status"] | null;
  last_run_summary?: Record<string, number> | null;
  last_message?: string | null;
  last_error?: string | null;
  generated_draft_count: number;
}

export interface WatchSourcesResponse {
  vault_root: string;
  registry_path: string;
  watched_sources: WatchedSourceResponse[];
  next_actions: NextAction[];
}

export interface IngestionActionResponse {
  ok: boolean;
  mode: string;
  target: string;
  counts: Record<string, number>;
  message: string;
  added_to_registry: boolean;
  registry_path?: string | null;
  watch_id?: string | null;
  source_deleted: boolean;
  cards_deleted: boolean;
  next_actions: NextAction[];
  run_id?: string | null;
  processing_status?: ProcessingRunResponse["status"] | null;
  skip_reasons: string[];
  error_message?: string | null;
}

export interface SourcesResponse {
  sources: SourceStatus[];
  bucket_counts: Record<string, Record<string, number>>;
  watched_sources: WatchedSourceResponse[];
  available_imports: StatusItem[];
  ingestion: {
    primary_entry: string;
    safety_note: string;
    advanced_note: string;
  };
  next_actions: NextAction[];
}

export interface LibraryCardResponse {
  id?: string | null;
  title?: string | null;
  status: string;
  status_explanation: string;
  track?: string | null;
  source_id?: string | null;
  source_type?: string | null;
  adapter_name?: string | null;
  source_title?: string | null;
  source_path?: string | null;
  source_content_hash?: string | null;
  source_archive_path?: string | null;
  source_missing: boolean;
  profile?: string | null;
  provider?: string | null;
  strategy_id?: string | null;
  strategy_label?: string | null;
  strategy_note?: string | null;
  strategy_canonical_id?: string | null;
  strategy_version?: string | null;
  schema_version?: string | null;
  prompt_version?: string | null;
  prompt_versions: Record<string, string>;
  stage_models: Record<string, unknown>;
  run_id?: string | null;
  created_at?: string | null;
  approved_at?: string | null;
  updated_at?: string | null;
  rel_path: string;
  fake_provider_note?: string | null;
}

export interface LibraryStatsResponse {
  vault_root: string;
  cards_dir: string;
  total_cards: number;
  by_status: Record<string, number>;
  by_track: Record<string, number>;
  by_provider: Record<string, number>;
  recent_count: number;
  index_path: string;
  index_exists: boolean;
  next_action: string;
}

export interface LibraryCardsResponse {
  stats: LibraryStatsResponse;
  cards: LibraryCardResponse[];
}

export interface LibraryCardDetailResponse {
  card: LibraryCardResponse;
  body?: string | null;
}

export interface CardBodyUpdateResponse {
  ok: boolean;
  status: string;
  message: string;
  card_path: string;
  rel_path?: string | null;
  index_updated: boolean;
  index_path?: string | null;
  index_error?: string | null;
}

export interface WorkflowSummaryResponse {
  vault_root: string;
  cards_dir: string;
  inbox_pending_count: number;
  processed_source_count: number;
  ai_draft_count: number;
  human_approved_count: number;
  index: RecallStatus;
  provider: ProviderStatus;
  source_bucket_counts: Record<string, Record<string, number>>;
  next_actions: NextAction[];
}

export interface DraftSummary {
  id?: string | null;
  title?: string | null;
  path: string;
  rel_path: string;
  status: string;
  track?: string | null;
  projects: string[];
  tags: string[];
  source_type?: string | null;
  source_id?: string | null;
  source_title?: string | null;
  source_path?: string | null;
  source_archive_path?: string | null;
  source_content_hash?: string | null;
  value_score?: number | null;
  profile?: string | null;
  provider?: string | null;
  strategy_id?: string | null;
  strategy_label?: string | null;
  strategy_note?: string | null;
  strategy_canonical_id?: string | null;
  strategy_version?: string | null;
  schema_version?: string | null;
  prompt_version?: string | null;
  prompt_versions: Record<string, string>;
  stage_models: Record<string, unknown>;
  run_id?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface DraftsResponse {
  drafts: DraftSummary[];
  scan_errors: StatusItem[];
  empty_state?: NextAction | null;
}

export interface DraftDetailResponse {
  draft: DraftSummary;
  frontmatter: Record<string, unknown>;
  body: string;
  source_context: Record<string, unknown>;
  approval_required: boolean;
}

export interface ApprovalResponse {
  ok: boolean;
  status: string;
  message: string;
  card_path?: string | null;
  previous_status?: string | null;
  new_status?: string | null;
  idempotent: boolean;
  index_updated: boolean;
  index_path?: string | null;
  index_error?: string | null;
}

export interface UnavailableResponse {
  available: false;
  reason: string;
  next_action: NextAction;
}

export interface PathActionResponse {
  ok: boolean;
  action: "copy" | "reveal";
  path: string;
  path_type: "file" | "folder";
  message: string;
  command: string[];
}

export interface RecallResponse {
  query: string;
  hits: Array<{
    score: number;
    title?: string | null;
    card_ref?: string | null;
    detail_href?: string | null;
    rel_path: string;
    status: string;
    track?: string | null;
    projects: string[];
    tags: string[];
    source_type?: string | null;
    why_this_matched: string;
  }>;
  index: RecallStatus;
  warnings: string[];
  empty_state?: NextAction | null;
}

export interface TrashCardResponse {
  trash_rel_path: string;
  title: string;
  previous_status: string;
  original_path: string;
  trashed_at: string;
  track?: string | null;
  tags: string[];
  source_title?: string | null;
}

export interface TrashListResponse {
  trashed_cards: TrashCardResponse[];
  trash_dir: string;
}

export interface TrashDetailResponse {
  card: TrashCardResponse;
  frontmatter: Record<string, unknown>;
  body?: string | null;
}

export interface TrashActionResponse {
  ok: boolean;
  action: string;
  message: string;
  card_id?: string | null;
  previous_status?: string | null;
  restored_path?: string | null;
  conflict_resolved: boolean;
}
