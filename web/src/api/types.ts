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
  next_action?: NextAction | null;
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
  fingerprint?: string | null;
  can_delete: boolean;
  error?: string | null;
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
  source_content_hash?: string | null;
  value_score?: number | null;
  strategy_id?: string | null;
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

export interface RecallResponse {
  query: string;
  hits: Array<{
    score: number;
    title?: string | null;
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
