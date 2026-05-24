import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import type { DraftSummary } from "../api/types";
import { getDraftDetail } from "../api/drafts";
import { cardStatusBadgeClass, friendlyStatus, statusIcon } from "../lib/utils";
import { useLocale } from "../lib/i18n";

export function DraftList({
  drafts,
  selected,
  onSelect,
}: {
  drafts: DraftSummary[];
  selected?: string;
  onSelect: (id: string) => void;
}) {
  const { locale, t } = useLocale();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [previewBody, setPreviewBody] = useState<string | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  async function togglePreview(draftId: string) {
    if (expandedId === draftId) {
      setExpandedId(null);
      setPreviewBody(null);
      return;
    }
    setExpandedId(draftId);
    setPreviewBody(null);
    setLoadingPreview(true);
    try {
      const detail = await getDraftDetail(draftId);
      setPreviewBody(detail.body ?? "");
    } catch {
      setPreviewBody(null);
    } finally {
      setLoadingPreview(false);
    }
  }

  return (
    <div className="space-y-2">
      {drafts.map((draft) => {
        const id = draft.id ?? draft.rel_path;
        const isExpanded = expandedId === id;
        const Icon = statusIcon(draft.status === "human_approved" ? "ok" : "warn");

        return (
          <div
            key={draft.rel_path}
            className={`rounded-md border transition ${
              selected === id ? "border-primary bg-blue-50" : "border-line bg-panel"
            }`}
          >
            <button
              className="w-full p-4 text-left"
              onClick={() => onSelect(id)}
              type="button"
            >
              <div className="flex items-center justify-between gap-3">
                <h3 className="font-medium text-ink">{draft.title ?? draft.rel_path}</h3>
                <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium ${cardStatusBadgeClass(draft.status)}`}>
                  {Icon ? <Icon className="h-3 w-3" aria-hidden="true" /> : null}
                  {friendlyStatus(draft.status, locale)}
                </span>
              </div>
              <p className="mt-1 text-sm text-muted">{draft.source_title ?? draft.source_type ?? ""}</p>
              <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted">
                <span>
                  {t("draftlist.value_score")}:{" "}
                  {draft.value_score != null ? draft.value_score : "-"}
                </span>
                {draft.strategy_label ? <span>{draft.strategy_label}</span> : null}
                {draft.strategy_note ? <span>{draft.strategy_note}</span> : null}
                {draft.source_title || draft.source_path_view?.display_path ? <span>source:{draft.source_title ?? draft.source_path_view?.display_path}</span> : null}
                {draft.track ? <span>track:{draft.track}</span> : null}
                {draft.projects.map((project) => (
                  <span key={project}>project:{project}</span>
                ))}
              </div>
            </button>

            {/* Expand preview toggle */}
            <div className="border-t border-line px-4 py-2">
              <button
                type="button"
                className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                onClick={(e) => {
                  e.stopPropagation();
                  togglePreview(id);
                }}
              >
                {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                {isExpanded ? t("drafts.preview_collapse") : t("drafts.preview_expand")}
              </button>

              {isExpanded ? (
                <div className="mt-2 overflow-hidden transition-all">
                  {loadingPreview ? (
                    <p className="py-2 text-xs text-muted">Loading...</p>
                  ) : previewBody ? (
                    <div className="space-y-2">
                      <p className="rounded bg-stone-50 p-3 text-xs leading-relaxed text-ink whitespace-pre-wrap">
                        {previewBody.slice(0, 300)}{previewBody.length > 300 ? "..." : ""}
                      </p>
                      <div className="flex flex-wrap gap-2 text-xs text-muted">
                        <span>{t("draftlist.value_score")}: {draft.value_score != null ? draft.value_score : "-"}</span>
                        {draft.tags.length > 0 ? (
                          <span>tags: {draft.tags.join(", ")}</span>
                        ) : null}
                      </div>
                    </div>
                  ) : (
                    <p className="py-2 text-xs text-muted">Preview unavailable</p>
                  )}
                </div>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );
}
