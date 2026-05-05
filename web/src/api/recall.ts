import { apiGet } from "./client";
import type { RecallResponse } from "./types";

export function recall(q: string) {
  return apiGet<RecallResponse>(`/api/recall?q=${encodeURIComponent(q)}`);
}
