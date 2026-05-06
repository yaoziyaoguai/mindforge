import { apiGet, apiPatch } from "./client";
import type { CardBodyUpdateResponse, LibraryCardDetailResponse, LibraryCardsResponse, WorkflowSummaryResponse } from "./types";

export function getWorkflowSummary() {
  return apiGet<WorkflowSummaryResponse>("/api/workflow/summary");
}

export function getLibraryCards() {
  return apiGet<LibraryCardsResponse>("/api/library/cards");
}

export function getLibraryCardDetail(ref: string) {
  return apiGet<LibraryCardDetailResponse>(`/api/library/card?ref=${encodeURIComponent(ref)}`);
}

export function saveLibraryCardBody(ref: string, body: string) {
  return apiPatch<CardBodyUpdateResponse>(`/api/library/card?ref=${encodeURIComponent(ref)}`, { body });
}
