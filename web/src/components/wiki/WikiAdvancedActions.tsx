/**
 * Wiki Advanced Actions component.
 *
 * Collapsible troubleshooting area. Only the safe fallback rebuild lives here —
 * never the primary user path.
 *
 * SDD_WIKI_WEB_PRESENTATION_ADDENDUM §8.3, §12.
 */

import { Wrench } from "lucide-react";

interface WikiAdvancedActionsProps {
  busy: boolean;
  onFallbackRebuild: () => void;
}

export function WikiAdvancedActions({
  busy,
  onFallbackRebuild,
}: WikiAdvancedActionsProps) {
  return (
    <details className="rounded-md border border-line p-3">
      <summary className="flex cursor-pointer items-center gap-1.5 text-sm font-medium text-muted">
        <Wrench size={14} />
        Troubleshooting
      </summary>
      <div className="mt-3 space-y-3">
        <p className="text-xs text-muted leading-relaxed">
          Safe fallback uses template-based synthesis that does not require a
          model. Use this only when LLM synthesis is unavailable or
          troubleshooting wiki generation issues.
        </p>
        <button
          className="rounded-md border border-line px-3 py-2 text-sm font-medium text-ink disabled:opacity-50 hover:bg-hover transition-colors"
          disabled={busy}
          onClick={onFallbackRebuild}
          type="button"
        >
          Safe fallback rebuild
        </button>
      </div>
    </details>
  );
}
