import { apiGet } from "./client";
import type { DraftDetailResponse, DraftsResponse } from "./types";

export function getDrafts() {
  return apiGet<DraftsResponse>("/api/drafts");
}

export function getDraftDetail(id: string) {
  return apiGet<DraftDetailResponse>(`/api/drafts/${encodeURIComponent(id)}`);
}
