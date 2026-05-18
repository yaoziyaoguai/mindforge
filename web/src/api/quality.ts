/** M1 Card Quality API client — SDD §4.1 */

import { apiGet } from "./client";

export interface QualityRubricScore {
  dimension: string;
  score: number;
  max_score: number;
  notes: string;
}

export interface QualityWarning {
  code: string;
  severity: "info" | "warn" | "critical";
  message: string;
  suggestion: string;
}

export interface CardQuality {
  card_id: string;
  overall_level: "high" | "medium" | "low";
  overall_level_label: string;
  overall_score: number;
  rubric_scores: QualityRubricScore[];
  warnings: QualityWarning[];
  card_type: string | null;
  regenerate_suggestion: string | null;
  split_candidate: boolean;
  merge_candidate: boolean;
}

export function fetchCardQuality(cardId: string): Promise<CardQuality> {
  return apiGet<CardQuality>(`/api/quality/cards/${encodeURIComponent(cardId)}`);
}
