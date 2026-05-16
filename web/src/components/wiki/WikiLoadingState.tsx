/**
 * Wiki loading state component.
 *
 * Shown while rebuilding Wiki or fetching Wiki content.
 *
 * SDD_WIKI_PRESENTATION_V2 §9.
 */

import { Loader2 } from "lucide-react";

export function WikiLoadingState() {
  return (
    <div className="flex flex-col items-center justify-center rounded-md border border-line bg-panel p-12 text-center">
      <Loader2 size={48} className="mb-4 animate-spin text-muted" />
      <h2 className="mb-2 text-lg font-semibold text-ink">Building Wiki</h2>
      <p className="max-w-md text-sm text-muted">
        Synthesizing knowledge cards with LLM. This may take a moment.
      </p>
    </div>
  );
}
