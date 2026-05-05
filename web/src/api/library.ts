import { apiGet } from "./client";
import type { LibraryCardsResponse, WorkflowSummaryResponse } from "./types";

export function getWorkflowSummary() {
  return apiGet<WorkflowSummaryResponse>("/api/workflow/summary");
}

export function getLibraryCards() {
  return apiGet<LibraryCardsResponse>("/api/library/cards");
}
