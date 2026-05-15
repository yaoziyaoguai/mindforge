/**
 * Wiki empty state component.
 *
 * Shown when:
 * - No approved cards exist
 * - Wiki has not been built yet
 * - Model setup is not ready
 *
 * SDD_WIKI_PRESENTATION_V2 §9.2.
 */

import { FileQuestion } from "lucide-react";

interface WikiEmptyStateProps {
  noApprovedCards: boolean;
  modelReady: boolean;
}

export function WikiEmptyState({ noApprovedCards, modelReady }: WikiEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-md border border-line bg-panel p-12 text-center">
      <FileQuestion size={48} className="mb-4 text-muted" />
      {noApprovedCards ? (
        <>
          <h2 className="mb-2 text-lg font-semibold text-ink">No approved cards</h2>
          <p className="max-w-md text-sm text-muted">
            Wiki is generated from approved knowledge cards. Process sources to
            create drafts, then approve them to include in the Wiki.
          </p>
        </>
      ) : !modelReady ? (
        <>
          <h2 className="mb-2 text-lg font-semibold text-ink">Model setup required</h2>
          <p className="max-w-md text-sm text-muted">
            LLM synthesis requires model setup. Complete model configuration in
            Setup before rebuilding the Wiki.
          </p>
        </>
      ) : (
        <>
          <h2 className="mb-2 text-lg font-semibold text-ink">Wiki not built yet</h2>
          <p className="max-w-md text-sm text-muted">
            Click Rebuild Wiki to generate a structured synthesis from approved
            knowledge cards.
          </p>
        </>
      )}
    </div>
  );
}
