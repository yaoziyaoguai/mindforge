import { apiDelete, apiGet, apiPatch, apiPost } from "./client";
import type {
  IngestionActionResponse,
  PathActionResponse,
  ProcessingRunResponse,
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

export function getProcessingRun(runId: string) {
  return apiGet<ProcessingRunResponse>(`/api/processing/runs/${encodeURIComponent(runId)}`);
}

export function importLocalUnavailable() {
  return apiPost<UnavailableResponse>("/api/sources/import-local");
}

/* raw path endpoints 已禁用 —— 安全优先。
 * 中文学习型说明：旧 copySourcePath / revealSourcePath 接受 raw absolute path，
 * 构成 path probing oracle。前端改用 source_path_view + client-side clipboard
 * （copy）和 object-reference endpoint（reveal）。
 */

export function revealSourceByRef(cardId?: string | null, draftId?: string | null) {
  return apiPost<PathActionResponse>("/api/sources/reveal", { card_id: cardId, draft_id: draftId });
}
