/**
 * Wiki Reference Card component.
 *
 * Single approved knowledge card reference with provenance metadata.
 * Visible by default — provenance is a first-class feature, not debug info.
 *
 * SDD_WIKI_WEB_PRESENTATION_ADDENDUM §7.
 */

import { FileText, Tag, Star, CheckCircle } from "lucide-react";
import type { WikiReferenceView } from "../../api/wiki";

interface WikiReferenceCardProps {
  ref: WikiReferenceView;
}

const sourceTypeLabels: Record<string, string> = {
  plain_markdown: "Markdown",
  txt: "Text",
  html: "HTML",
  pdf: "PDF",
  docx: "Word",
};

export function WikiReferenceCard({ ref }: WikiReferenceCardProps) {
  const sourceLabel =
    (ref.source_type ? sourceTypeLabels[ref.source_type] : null) ??
    ref.source_type ??
    null;

  return (
    <li className="rounded-md border border-line bg-panel p-3 text-sm transition-colors hover:border-muted">
      <div className="flex items-start gap-2.5">
        <FileText size={15} className="mt-0.5 shrink-0 text-muted" />
        <div className="min-w-0 flex-1">
          {/* Card title + approved indicator */}
          <div className="flex items-center gap-2">
            <span className="font-medium text-ink truncate">
              {ref.card_title}
            </span>
            <span
              className="inline-flex shrink-0 items-center gap-1 rounded bg-safe/10 px-1.5 py-0.5 text-[10px] font-medium text-safe"
              title="Human-approved knowledge card"
            >
              <CheckCircle size={10} />
              Approved
            </span>
          </div>

          {/* Provenance metadata */}
          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
            {sourceLabel && (
              <span className="inline-flex items-center rounded bg-muted/20 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide">
                {sourceLabel}
              </span>
            )}
            {ref.source_title && (
              <span className="truncate max-w-[200px]">
                {ref.source_title}
              </span>
            )}
            {ref.track && (
              <span className="inline-flex items-center gap-1">
                <Tag size={10} />
                {ref.track}
              </span>
            )}
            {ref.value_score != null && (
              <span className="inline-flex items-center gap-1">
                <Star size={10} className="text-amber-500" />
                {ref.value_score}
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
        </div>
      </div>
    </li>
  );
}
