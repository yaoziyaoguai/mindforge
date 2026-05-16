/**
 * Wiki Reading Pane component.
 *
 * Main reading area: overview, sections, open questions, additional cards.
 * Does not handle fetching, state management, or TOC.
 *
 * SDD_WIKI_WEB_PRESENTATION_ADDENDUM §5.1, §6, §12.
 */

import { renderMarkdown } from "../../lib/wiki-renderer";
import { WikiSection } from "./WikiSection";
import { WikiReferencePanel } from "./WikiReferencePanel";
import type { WikiPageViewModel } from "../../api/wiki";

interface WikiReadingPaneProps {
  page: WikiPageViewModel;
}

export function WikiReadingPane({ page }: WikiReadingPaneProps) {
  return (
    <div className="min-w-0 flex-1 space-y-10">
      {/* Overview */}
      {page.overview && (
        <section>
          <div
            className="prose prose-sm max-w-[720px] text-ink leading-relaxed"
            dangerouslySetInnerHTML={{
              __html: renderMarkdown(page.overview),
            }}
          />
        </section>
      )}

      {/* Sections */}
      {page.sections.map((sec) => (
        <WikiSection key={sec.id} section={sec} />
      ))}

      {/* Open questions */}
      {page.open_questions.length > 0 && (
        <section className="max-w-[720px]">
          <h2 className="mb-3 text-lg font-semibold text-ink">
            Open Questions
          </h2>
          <ul className="list-disc space-y-1 pl-5 text-sm text-ink leading-relaxed">
            {page.open_questions.map((q, i) => (
              <li key={i}>{q.question}</li>
            ))}
          </ul>
        </section>
      )}

      {/* Additional cards (uncited approved cards) */}
      {page.additional_cards.length > 0 && (
        <div className="max-w-[720px]">
          <WikiReferencePanel
            refs={page.additional_cards}
            title="Additional knowledge cards"
          />
        </div>
      )}

      {/* Warnings */}
      {page.warnings.length > 0 && (
        <div className="max-w-[720px] rounded-md border border-warn/30 bg-warn/5 p-3">
          <p className="text-sm font-medium text-warn">Warnings</p>
          <ul className="mt-1 list-disc pl-5 text-xs text-muted">
            {page.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
