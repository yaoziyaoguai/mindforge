/**
 * Wiki Reference Panel component.
 *
 * Lists card references with provenance metadata. Visible by default —
 * provenance is a first-class feature, not debug info.
 *
 * SDD_WIKI_WEB_PRESENTATION_ADDENDUM §7.
 */

import { WikiReferenceCard } from "./WikiReferenceCard";
import type { WikiReferenceView } from "../../api/wiki";

interface WikiReferencePanelProps {
  refs: WikiReferenceView[];
  title?: string;
}

export function WikiReferencePanel({ refs, title }: WikiReferencePanelProps) {
  if (refs.length === 0) return null;

  return (
    <div className="mt-4">
      <h3 className="mb-2 text-sm font-semibold text-muted">
        {title ?? "References"} ({refs.length})
      </h3>
      <ul className="space-y-2">
        {refs.map((ref) => (
          <WikiReferenceCard key={ref.card_id} ref={ref} />
        ))}
      </ul>
    </div>
  );
}
