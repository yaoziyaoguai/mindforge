import { apiGet, apiPatch, apiPost } from "./client";
import type { CardBodyUpdateResponse, FolderImportPreviewResponse, FolderImportResponse, ImportCardResponse, KnowledgeCommunitiesResponse, KnowledgeTopicsResponse, LibraryCardDetailResponse, LibraryCardsResponse, ProvenanceTrailResponse, WorkflowSummaryResponse } from "./types";

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

export function getKnowledgeTopics() {
  return apiGet<KnowledgeTopicsResponse>("/api/knowledge/topics");
}

export function importCard(title: string, body: string, sourceName?: string) {
  return apiPost<ImportCardResponse>("/api/knowledge/import", { title, body, source_name: sourceName || "" });
}

// ── v2.4 U1 Folder Import ──────────────────────

export function previewFolderImport(folderPath: string) {
  return apiPost<FolderImportPreviewResponse>("/api/knowledge/import/folder-preview", { folder_path: folderPath });
}

export function importFromFolder(folderPath: string, indices: number[]) {
  return apiPost<FolderImportResponse>("/api/knowledge/import/folder", { folder_path: folderPath, indices });
}
