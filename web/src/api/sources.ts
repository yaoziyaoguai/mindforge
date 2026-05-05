import { apiGet, apiPost } from "./client";
import type { SourcesResponse, UnavailableResponse } from "./types";

export function getSources() {
  return apiGet<SourcesResponse>("/api/sources");
}

export function importLocalUnavailable() {
  return apiPost<UnavailableResponse>("/api/sources/import-local");
}
