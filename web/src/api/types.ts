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
  next_action?: NextAction | null;
}

export interface SourcesResponse {
  sources: SourceStatus[];
  available_imports: StatusItem[];
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
  source_title?: string | null;
  value_score?: number | null;
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
