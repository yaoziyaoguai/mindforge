/**
 * Wiki Reference Panel component.
 *
 * Lists card references with provenance metadata (source, track, tags, value).
 *
 * SDD_WIKI_PRESENTATION_V2 §5.1.
 */

import { FileText, Tag, Star } from "lucide-react";
import type { WikiReferenceView } from "../../api/wiki";

interface WikiReferencePanelProps {
  refs: WikiReferenceView[];
  title?: string;
}

export function WikiReferencePanel({ refs, title }: WikiReferencePanelProps) {
  if (refs.length === 0) return null;

  return (
    <details className="mt-4 rounded-md border border-line bg-panel/50 p-3">
      <summary className="cursor-pointer text-sm font-medium text-muted">
        {title ?? "References"} ({refs.length})
      </summary>
      <ul className="mt-2 space-y-2">
        {refs.map((ref) => (
          <li
            key={ref.card_id}
            className="rounded border border-line bg-panel p-2 text-sm"
          >
            <div className="flex items-center gap-2">
              <FileText size={14} className="shrink-0 text-muted" />
              <span className="font-medium text-ink">{ref.card_title}</span>
              {ref.value_score != null && (
                <span className="inline-flex items-center gap-1 rounded bg-safe/10 px-1.5 py-0.5 text-xs text-safe">
                  <Star size={10} />
                  {ref.value_score}
                </span>
              )}
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
              {ref.source_title && (
                <span>Source: {ref.source_title}</span>
              )}
              {ref.source_type && (
                <span className="rounded bg-muted/20 px-1 py-0.5 font-mono text-[10px] uppercase">
                  {ref.source_type}
                </span>
              )}
              {ref.track && (
                <span className="flex items-center gap-1">
                  <Tag size={10} />
                  {ref.track}
                </span>
              )}
              {ref.tags.length > 0 && (
                <span className="flex items-center gap-1">
                  {ref.tags.slice(0, 3).map((t) => (
                    <span
                      key={t}
                      className="rounded bg-muted/20 px-1 py-0.5 text-[10px]"
                    >
                      {t}
                    </span>
                  ))}
                </span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </details>
  );
}
