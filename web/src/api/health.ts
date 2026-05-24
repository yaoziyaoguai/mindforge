import { apiGet } from "./client";
import type { HealthReportResponse } from "./types";

export function getKnowledgeHealth() {
  return apiGet<HealthReportResponse>("/api/knowledge/health");
}
