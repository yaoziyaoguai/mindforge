import { apiDelete, apiGet, apiPatch, apiPost } from "./client";
import type {
  IngestionActionResponse,
  PathActionResponse,
  SourcesResponse,
  UnavailableResponse,
  WatchSourcesResponse,
} from "./types";

export function getSources() {
  return apiGet<SourcesResponse>("/api/sources");
}

export function getWatchedSources() {
  return apiGet<WatchSourcesResponse>("/api/sources/watch");
}

export function addWatchedSource(path: string, frequency = "manual", recursive = true, processNow = true) {
  return apiPost<IngestionActionResponse>("/api/sources/watch", { path, frequency, recursive, process_now: processNow });
}

export function deleteWatchedSource(ref: string) {
  return apiDelete<IngestionActionResponse>(`/api/sources/watch/${encodeURIComponent(ref)}`);
}

export function updateWatchedSourceFrequency(ref: string, frequency: string) {
  return apiPatch<IngestionActionResponse>(`/api/sources/watch/${encodeURIComponent(ref)}/frequency`, { frequency });
}

export function importSource(path: string) {
  return apiPost<IngestionActionResponse>("/api/sources/import", { path });
}

export function scanWatchedSources(ref?: string, allSources = false) {
  const params = new URLSearchParams();
  if (ref) params.set("ref", ref);
  if (allSources) params.set("all_sources", "true");
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return apiPost<IngestionActionResponse>(`/api/sources/watch/scan${suffix}`, {});
}

export function importLocalUnavailable() {
  return apiPost<UnavailableResponse>("/api/sources/import-local");
}

export function copySourcePath(path: string) {
  return apiPost<PathActionResponse>("/api/sources/path-actions/copy", { path });
}

export function revealSourcePath(path: string) {
  return apiPost<PathActionResponse>("/api/sources/path-actions/reveal", { path });
}
