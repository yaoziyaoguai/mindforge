import { apiGet, apiPatch } from "./client";
import type { CardBodyUpdateResponse, KnowledgeCommunitiesResponse, LibraryCardDetailResponse, LibraryCardsResponse, ProvenanceTrailResponse, WorkflowSummaryResponse } from "./types";

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

export function getProvenanceTrail(ref: string) {
  return apiGet<ProvenanceTrailResponse>(`/api/library/trail?ref=${encodeURIComponent(ref)}`);
}

export function getKnowledgeCommunities() {
  return apiGet<KnowledgeCommunitiesResponse>("/api/knowledge/communities");
}
