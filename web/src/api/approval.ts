import { apiPost } from "./client";
import type { ApprovalResponse, UnavailableResponse } from "./types";

export function approveDraft(id: string, payload: { confirm: boolean; reviewed_source: boolean; reason?: string }) {
  return apiPost<ApprovalResponse>(`/api/drafts/${encodeURIComponent(id)}/approve`, payload);
}

export function rejectDraft(id: string, payload: { reason?: string }) {
  return apiPost<UnavailableResponse>(`/api/drafts/${encodeURIComponent(id)}/reject`, payload);
}
