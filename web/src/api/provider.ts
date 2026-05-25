import type { ProviderReadinessResponse } from "./types";

export async function getProviderReadiness(): Promise<ProviderReadinessResponse> {
  const resp = await fetch("/api/provider/readiness");
  if (!resp.ok) throw new Error("Failed to load provider readiness");
  return resp.json();
}
