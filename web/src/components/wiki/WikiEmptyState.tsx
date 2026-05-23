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
import { useLocale } from "../../lib/i18n";

interface WikiEmptyStateProps {
  noApprovedCards: boolean;
  modelReady: boolean;
}

export function WikiEmptyState({ noApprovedCards, modelReady }: WikiEmptyStateProps) {
  const { t } = useLocale();

  return (
    <div className="flex flex-col items-center justify-center rounded-md border border-line bg-panel p-12 text-center">
      <FileQuestion size={48} className="mb-4 text-muted" />
      {noApprovedCards ? (
        <>
          <h2 className="mb-2 text-lg font-semibold text-ink">{t("wiki.empty_no_approved")}</h2>
          <p className="max-w-md text-sm text-muted">{t("wiki.empty_no_approved_desc")}</p>
        </>
      ) : !modelReady ? (
        <>
          <h2 className="mb-2 text-lg font-semibold text-ink">{t("wiki.empty_model_required")}</h2>
          <p className="max-w-md text-sm text-muted">{t("wiki.empty_model_required_desc")}</p>
        </>
      ) : (
        <>
          <h2 className="mb-2 text-lg font-semibold text-ink">{t("wiki.empty_not_built")}</h2>
          <p className="max-w-md text-sm text-muted">{t("wiki.empty_not_built_desc")}</p>
        </>
      )}
    </div>
  );
}
