/**
 * WikiPage — Knowledge Topic Browser (v0.5).
 *
 * Replaces the deprecated LLM Wiki synthesis UI with a runtime Topic View
 * driven by GET /api/topics and GET /api/topics/{topic_name}.
 *
 * This page is a thin adapter that composes TopicBrowser.
 * No /api/wiki/rebuild calls. No LLM synthesis. No Generate Wiki button.
 * Only human_approved cards are shown — the approval boundary is enforced
 * by the backend TopicPresenter.
 */

import { TopicBrowser } from "../components/wiki/TopicBrowser";

export function WikiPage() {
  return <TopicBrowser />;
}
