/** Wiki view model types — mirrors Python WikiPageViewModel JSON. */

export interface WikiReferenceView {
  card_id: string;
  card_title: string;
  source_title: string | null;
  source_type: string | null;
  source_path: string | null;
  track: string | null;
  tags: string[];
  value_score: number | null;
  approved_at: string | null;
  card_rel_path: string;
}

export interface WikiSectionView {
  id: string;
  title: string;
  body: string; // canonical Markdown text
  level: number;
  card_refs: WikiReferenceView[];
  anchor: string;
}

export interface WikiQuestionView {
  question: string;
}

export interface WikiQualityCoverage {
  used: number;
  unused: number;
  total: number;
  rate: number;
}

export interface WikiQualityUnusedCard {
  id: string;
  title: string;
  reason: string;
}

export interface WikiQualityFaithfulness {
  average: number;
  by_section: Record<string, number>;
}

export interface WikiQualityResponse {
  exists: boolean;
  coverage?: WikiQualityCoverage;
  unused_cards?: WikiQualityUnusedCard[];
  used_cards?: string[];
  faithfulness?: WikiQualityFaithfulness;
  faithfulness_issues?: string[];
  stale_sections?: string[];
  knowledge_gaps?: string[];
  conflicting_claims?: { card_a: string; card_b: string; topic: string }[];
  section_count?: number;
  error?: string;
}

export interface WikiPageViewModel {
  title: string;
  mode: string;
  model_id: string | null;
  last_rebuilt_at: string | null;
  overview: string; // canonical Markdown text
  sections: WikiSectionView[];
  additional_cards: WikiReferenceView[];
  open_questions: WikiQuestionView[];
  included_card_count: number;
  additional_card_count: number;
  warnings: string[];
}

/** v0.4 U1: Wiki Related Sections */
export interface WikiRelatedSection {
  title: string;
  overlap: number;
  shared_cards: number;
}

export interface WikiRelatedSectionsResponse {
  exists: boolean;
  sections: Record<string, WikiRelatedSection[]>;
}
