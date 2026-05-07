import { apiGet, apiPatch } from "./client";
import type { CardBodyUpdateResponse, DraftDetailResponse, DraftsResponse } from "./types";

export function getDrafts() {
  return apiGet<DraftsResponse>("/api/drafts");
}

export function getDraftDetail(id: string) {
  return apiGet<DraftDetailResponse>(`/api/drafts/${encodeURIComponent(id)}`);
}

export function saveDraftBody(id: string, body: string) {
  return apiPatch<CardBodyUpdateResponse>(`/api/drafts/${encodeURIComponent(id)}`, { body });
}
