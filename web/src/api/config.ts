import { apiGet, apiPost } from "./client";
import type { ConfigStatusResponse } from "./types";

export function getConfigStatus() {
  return apiGet<ConfigStatusResponse>("/api/config/status");
}

export function checkConfigStatus() {
  return apiPost<ConfigStatusResponse>("/api/config/check");
}
