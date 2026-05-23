/**
 * Wiki Advanced Actions component.
 *
 * Collapsible troubleshooting area. Only the safe fallback rebuild lives here —
 * never the primary user path.
 *
 * SDD_WIKI_WEB_PRESENTATION_ADDENDUM §8.3, §12.
 */

import { Wrench } from "lucide-react";
import { useLocale } from "../../lib/i18n";

interface WikiAdvancedActionsProps {
  busy: boolean;
  onFallbackRebuild: () => void;
}

export function WikiAdvancedActions({
  busy,
  onFallbackRebuild,
}: WikiAdvancedActionsProps) {
  const { t } = useLocale();

  return (
    <details className="rounded-md border border-line p-3">
      <summary className="flex cursor-pointer items-center gap-1.5 text-sm font-medium text-muted">
        <Wrench size={14} />
        {t("wiki.troubleshooting")}
      </summary>
      <div className="mt-3 space-y-3">
        <p className="text-xs text-muted leading-relaxed">
          {t("wiki.troubleshooting_desc")}
        </p>
        <button
          className="rounded-md border border-line px-3 py-2 text-sm font-medium text-ink disabled:opacity-50 hover:bg-hover transition-colors"
          disabled={busy}
          onClick={onFallbackRebuild}
          type="button"
        >
          {t("wiki.safe_fallback_rebuild")}
        </button>
      </div>
    </details>
  );
}
