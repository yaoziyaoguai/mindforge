/** Topic API client — v0.5 runtime Topic View.
 *
 * Consumes GET /api/topics and GET /api/topics/{name}.
 * No LLM synthesis, no rebuild — pure runtime view over human_approved cards.
 */

import { apiGet } from "./client";

export interface TopicCardView {
  id: string | null;
  title: string | null;
  knowledge_type: string;
  relations: { type: string; target_id: string }[];
  tags: string[];
  summary: string;
  human_note: string | null;
  approval_state: string;
  value_score: number | null;
  source_title: string | null;
  source_type: string | null;
  track: string | null;
  created_at: string | null;
  approved_at: string | null;
}

export interface TopicViewResponse {
  topic: string;
  total_approved_cards: number;
  type_counts: Record<string, number>;
  cards: TopicCardView[];
}

export interface TopicListResponse {
  topics: string[];
}

export function listTopics(): Promise<TopicListResponse> {
  return apiGet<TopicListResponse>("/api/topics");
}

export function getTopic(topicName: string): Promise<TopicViewResponse> {
  return apiGet<TopicViewResponse>(
    `/api/topics/${encodeURIComponent(topicName)}`,
  );
}
