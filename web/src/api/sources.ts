import { apiDelete, apiGet, apiPost } from "./client";
import type {
  IngestionActionResponse,
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

export function addWatchedSource(path: string) {
  return apiPost<IngestionActionResponse>("/api/sources/watch", { path });
}

export function deleteWatchedSource(ref: string) {
  return apiDelete<IngestionActionResponse>(`/api/sources/watch/${encodeURIComponent(ref)}`);
}

export function importSource(path: string) {
  return apiPost<IngestionActionResponse>("/api/sources/import", { path });
}

export function importLocalUnavailable() {
  return apiPost<UnavailableResponse>("/api/sources/import-local");
}
