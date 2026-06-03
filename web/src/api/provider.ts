import type { ProviderReadinessResponse } from "./types";

export async function getProviderReadiness(): Promise<ProviderReadinessResponse> {
  const resp = await fetch("/api/provider/readiness");
  if (!resp.ok) throw new Error("Failed to load provider readiness");
  return resp.json();
}

export interface ProviderStatusResponse {
  provider_type: string | null;
  model: string | null;
  configured: boolean;
  verified: boolean;
  verification_status: "not_verified" | "verified" | "failed";
  masked_key: string | null;
  base_url_host: string | null;
  base_url_path: string | null;
  last_checked_at: string | null;
  last_error: string | null;
  provider_mode: "fake" | "real";
  can_run_real_smoke: boolean;
}

export async function getProviderStatus(): Promise<ProviderStatusResponse> {
  const resp = await fetch("/api/provider/status");
  if (!resp.ok) throw new Error("Failed to load provider status");
  return resp.json();
}

export interface TestConnectionResponse {
  ok: boolean;
  message: string;
  verification_status: "not_verified" | "verified" | "failed";
  last_checked_at: string | null;
  last_error: string | null;
  latency_ms: number | null;
}

export async function testProviderConnection(modelId: string): Promise<TestConnectionResponse> {
  const resp = await fetch("/api/provider/test-connection", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model_id: modelId }),
  });
  if (!resp.ok) throw new Error("Test connection failed");
  return resp.json();
}

export interface UsageReportResponse {
  generated_at: string;
  total_cards: number;
  approved_count: number;
  draft_count: number;
  total_sources: number;
  wiki_sections: number;
  search_available: boolean;
  provider_configured: boolean;
  provider_verified: boolean;
  provider_verification_status: string;
  provider_mode: string;
  provider_status: ProviderStatusResponse;
  recent_runs: number;
  backend_gaps: string[];
}

export async function getUsageReport(): Promise<UsageReportResponse> {
  const resp = await fetch("/api/usage/report");
  if (!resp.ok) throw new Error("Failed to load usage report");
  return resp.json();
}
