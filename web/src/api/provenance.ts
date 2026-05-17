/** M4 Source Location API client — SDD §8 */

import { apiGet } from "./client";

export interface SourceLocationResponse {
  source_type: string;
  heading_path: string[] | null;
  line_start: number | null;
  line_end: number | null;
  page_number: number | null;
  paragraph_start: number | null;
  paragraph_end: number | null;
  css_selector: string | null;
  display: string;
}

export function fetchCardLocation(
  cardId: string,
): Promise<SourceLocationResponse> {
  return apiGet<SourceLocationResponse>(
    `/api/provenance/cards/${encodeURIComponent(cardId)}/location`,
  );
}
