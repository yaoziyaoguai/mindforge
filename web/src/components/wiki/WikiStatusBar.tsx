/**
 * Wiki Status Bar component.
 *
 * Shows wiki metadata and Rebuild action. Does not render wiki content.
 *
 * SDD_WIKI_WEB_PRESENTATION_ADDENDUM §5.1, §12.
 */

import { RefreshCw } from "lucide-react";
import { useLocale } from "../../lib/i18n";

interface WikiStatusBarProps {
  exists: boolean;
  lastRebuiltAt: string | null;
  wikiCardCount: number;
  approvedCardCount: number;
  isStale: boolean;
  newApprovedCount: number;
  modelReady: boolean;
  modelReadyLabel: string;
  busy: boolean;
  onRebuild: () => void;
}

export function WikiStatusBar({
  exists,
  lastRebuiltAt,
  wikiCardCount,
  approvedCardCount,
  isStale,
  newApprovedCount,
  modelReady,
  modelReadyLabel,
  busy,
  onRebuild,
}: WikiStatusBarProps) {
  const { t } = useLocale();

  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      {/* Exists indicator */}
      <div className="inline-flex items-center gap-1.5 rounded-md border border-line bg-panel px-3 py-2">
        <span
          className={`inline-block h-2 w-2 rounded-full ${
            exists ? "bg-safe" : "bg-warn"
          }`}
        />
        <span className="text-muted">{t("wiki.status_label")}: </span>
        <span className={exists ? "text-safe font-medium" : "text-warn font-medium"}>
          {exists ? t("wiki.status_ready") : t("wiki.status_not_built")}
        </span>
      </div>

      {/* Metadata (only when exists) */}
      {exists && (
        <>
          <div className="rounded-md border border-line bg-panel px-3 py-2">
            <span className="text-muted">{t("wiki.last_rebuilt")}: </span>
            <span className="text-ink">
              {lastRebuiltAt?.slice(0, 19) ?? "—"}
            </span>
          </div>
          <div className="rounded-md border border-line bg-panel px-3 py-2">
            <span className="text-muted">{t("wiki.cards_in_wiki")}: </span>
            <span className="text-ink">{wikiCardCount}</span>
          </div>
        </>
      )}

      {/* Approved card count (always shown) */}
      <div className="rounded-md border border-line bg-panel px-3 py-2">
        <span className="text-muted">{t("wiki.knowledge_cards")}: </span>
        <span className="text-ink">{approvedCardCount}</span>
      </div>

      {/* Stale indicator */}
      {isStale && (
        <div className="rounded-md border border-warn/30 bg-warn/10 px-3 py-2 text-sm text-warn">
          {t("wiki.new_approved_hint").replace("{count}", String(newApprovedCount))}
        </div>
      )}

      {/* Rebuild action (primary, LLM-first) */}
      <button
        className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50 transition-opacity hover:opacity-90"
        disabled={busy || !modelReady}
        onClick={onRebuild}
        type="button"
        title={
          modelReady
            ? t("wiki.rebuild_tooltip")
            : modelReadyLabel
        }
      >
        <RefreshCw size={14} className={busy ? "animate-spin" : ""} />
        {exists ? t("wiki.refresh") : t("wiki.generate")}
      </button>
    </div>
  );
}
