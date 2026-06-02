import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import type { DraftSummary } from "../api/types";
import { getDraftDetail } from "../api/drafts";
import { friendlyStatus, friendlyTrack, cardStatusBadgeClass, statusIcon } from "../lib/utils";
import { useLocale } from "../lib/i18n";

function statusBorderClass(status: string): string {
  if (status === "human_approved") return "border-l-[var(--mf-approved)]";
  return "border-l-[var(--mf-draft)]";
}

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
        const isApproved = draft.status === "human_approved";
        const isActive = selected === id;

        return (
          <div
            key={draft.rel_path}
            className={`rounded-lg border border-l-[3px] transition-colors ${
              isActive
                ? "border-[var(--mf-accent)]/30 bg-[var(--mf-accent)]/3"
                : "border-[var(--mf-border)] bg-[var(--mf-surface)] hover:border-[var(--mf-accent)]/20"
            } ${isApproved ? "opacity-50" : ""}`}
            style={{
              borderLeftColor: isActive ? undefined : draft.status === "human_approved" ? "var(--mf-approved)" : "var(--mf-draft)",
              borderRadius: "var(--mf-radius-md)",
            }}
          >
            <button
              className="w-full p-3.5 text-left"
              onClick={() => onSelect(id)}
              type="button"
            >
              <h3
                className="font-medium leading-snug text-[var(--mf-text-primary)]"
                style={{
                  fontFamily: "var(--mf-font-serif)",
                  fontSize: "var(--mf-text-body-l)",
                  lineHeight: 1.35,
                }}
              >
                {draft.title ?? draft.rel_path}
              </h3>
              <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
                <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium ${cardStatusBadgeClass(draft.status)}`}>
                  {(() => { const Icon = statusIcon(draft.status === "human_approved" ? "ok" : "warn"); return Icon ? <Icon className="h-3 w-3" /> : null; })()}
                  {friendlyStatus(draft.status, locale)}
                </span>
                {draft.source_title && <span style={{ color: "var(--mf-text-tertiary)" }}>{draft.source_title}</span>}
                {draft.track && <span style={{ color: "var(--mf-text-tertiary)" }}>{friendlyTrack(draft.track, locale)}</span>}
                {draft.value_score != null && (
                  <span style={{ color: "var(--mf-text-tertiary)" }}>{t("draftlist.value_score")}: {draft.value_score}</span>
                )}
              </div>
            </button>

            <div className="border-t border-[var(--mf-border)]/50 px-3.5 py-1.5">
              <button
                type="button"
                className="inline-flex items-center gap-1 text-[11px] text-[var(--mf-text-tertiary)] hover:text-[var(--mf-accent)]"
                onClick={(e) => {
                  e.stopPropagation();
                  togglePreview(id);
                }}
              >
                {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                {isExpanded ? t("drafts.preview_collapse") : t("drafts.preview_expand")}
              </button>

              {isExpanded && (
                <div className="mt-2 pb-2">
                  {loadingPreview ? (
                    <p className="py-2 text-xs text-[var(--mf-text-tertiary)]">Loading...</p>
                  ) : previewBody ? (
                    <p
                      className="rounded p-3 text-sm leading-relaxed text-[var(--mf-text-primary)] whitespace-pre-wrap"
                      style={{ background: "var(--mf-surface-alt)", lineHeight: 1.6 }}
                    >
                      {previewBody.slice(0, 300)}
                      {previewBody.length > 300 ? "..." : ""}
                    </p>
                  ) : (
                    <p className="py-2 text-xs text-[var(--mf-text-tertiary)]">Preview unavailable</p>
                  )}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
