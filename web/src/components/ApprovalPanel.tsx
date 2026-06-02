import { useState } from "react";
import { approveDraft, rejectDraft } from "../api/approval";
import type { ApprovalResponse, DraftDetailResponse, UnavailableResponse } from "../api/types";
import { useLocale } from "../lib/i18n";

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "-";
  try {
    const d = new Date(iso);
    return d.toLocaleString();
  } catch {
    return iso;
  }
}

export function ApprovalPanel({ detail, onApproved }: { detail: DraftDetailResponse; onApproved: () => void }) {
  const [reviewed, setReviewed] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const { t } = useLocale();
  const id = detail.draft.id ?? detail.draft.rel_path;
  const isApproved = detail.draft.status === "human_approved";

  async function approve() {
    setBusy(true);
    setMessage(null);
    try {
      const response: ApprovalResponse = await approveDraft(id, { confirm: true, reviewed_source: reviewed });
      setMessage(
        response.index_updated
          ? `${response.message} Recall index updated.`
          : response.message
      );
      if (response.ok) onApproved();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Approve failed");
    } finally {
      setBusy(false);
    }
  }

  async function reject() {
    setBusy(true);
    setMessage(null);
    try {
      const response: UnavailableResponse = await rejectDraft(id, {});
      setMessage(response.reason);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Reject failed");
    } finally {
      setBusy(false);
    }
  }

  const accent = "var(--mf-accent)";
  const surface = "var(--mf-surface)";
  const border = "var(--mf-border)";

  return (
    <aside
      className="rounded-lg border p-5"
      style={{ background: surface, borderColor: border, borderRadius: "var(--mf-radius-lg)" }}
    >
      <h2
        className="font-medium"
        style={{ fontFamily: "var(--mf-font-serif)", fontSize: "var(--mf-text-h3)", color: "var(--mf-text-primary)" }}
      >
        {t("approval.title")}
      </h2>
      <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--mf-text-secondary)" }}>
        {t("approval.description")}
      </p>

      <div className="mt-4 rounded-md px-3 py-2.5" style={{ background: "var(--mf-surface-alt)" }}>
        <span className="text-xs" style={{ color: "var(--mf-text-tertiary)" }}>{t("approval.value_score")}</span>
        <div className="text-lg font-medium" style={{ color: "var(--mf-text-primary)" }}>
          {detail.draft.value_score != null ? detail.draft.value_score : "-"}
        </div>
      </div>

      <div className="mt-4 border-t pt-4" style={{ borderColor: border }}>
        <h3 className="text-xs font-medium" style={{ color: "var(--mf-text-tertiary)" }}>
          {t("approval.status_timeline")}
        </h3>
        <div className="mt-2 space-y-1.5 text-sm">
          <div className="flex justify-between">
            <span style={{ color: "var(--mf-text-secondary)" }}>{t("approval.status_created")}</span>
            <span style={{ color: "var(--mf-text-primary)" }}>{formatDate(detail.draft.created_at)}</span>
          </div>
          <div className="flex justify-between items-center">
            <span style={{ color: "var(--mf-text-secondary)" }}>{t("approval.status_current")}</span>
            <span
              className="inline-block rounded-full px-2 py-0.5 text-xs font-medium"
              style={{
                background: isApproved ? "rgba(45,125,95,0.12)" : "rgba(184,134,11,0.12)",
                color: isApproved ? "var(--mf-approved)" : "var(--mf-draft)",
              }}
            >
              {isApproved ? t("approval.status_human_approved") : t("approval.status_ai_draft")}
            </span>
          </div>
          {isApproved && detail.draft.approved_at && (
            <div className="flex justify-between">
              <span style={{ color: "var(--mf-text-secondary)" }}>{t("approval.status_approved_at")}</span>
              <span style={{ color: "var(--mf-text-primary)" }}>{formatDate(detail.draft.approved_at)}</span>
            </div>
          )}
        </div>
      </div>

      {!isApproved && (
        <div className="mt-5 border-t pt-5" style={{ borderColor: border }}>
          <label className="flex items-start gap-2.5 text-sm cursor-pointer" style={{ color: "var(--mf-text-primary)" }}>
            <input
              checked={reviewed}
              onChange={(event) => setReviewed(event.target.checked)}
              type="checkbox"
              className="mt-0.5 h-4 w-4 rounded"
              style={{ accentColor: accent }}
            />
            <span className="leading-relaxed">{t("approval.reviewed_checkbox")}</span>
          </label>

          {!confirming ? (
            <button
              className="mt-4 w-full rounded-lg px-4 py-2.5 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:opacity-40"
              style={{ background: accent }}
              disabled={!reviewed || busy}
              onClick={() => setConfirming(true)}
              type="button"
            >
              {t("approval.confirm_button")}
            </button>
          ) : (
            <div
              className="mt-4 rounded-lg p-4"
              style={{ border: `1px solid ${accent}33`, background: `${accent}0D` }}
            >
              <p className="text-sm font-medium" style={{ color: accent }}>
                {t("approval.confirm_title")}
              </p>
              <button
                className="mt-3 w-full rounded-lg px-4 py-2.5 text-sm font-medium text-white transition-colors hover:opacity-90"
                style={{ background: accent }}
                disabled={busy}
                onClick={approve}
                type="button"
              >
                {t("approval.confirm_final")}
              </button>
              <button
                className="mt-2 w-full rounded-lg border px-4 py-2.5 text-sm transition-colors hover:bg-stone-50"
                style={{ borderColor: border, color: "var(--mf-text-secondary)" }}
                onClick={() => setConfirming(false)}
                type="button"
              >
                {t("approval.cancel")}
              </button>
            </div>
          )}

          <button
            className="mt-3 w-full rounded-lg border px-4 py-2.5 text-sm transition-colors hover:opacity-80"
            style={{
              borderColor: "var(--mf-error)",
              color: "var(--mf-error)",
              background: "rgba(192,64,64,0.04)",
            }}
            disabled={busy}
            onClick={reject}
            type="button"
          >
            {t("approval.reject")}
          </button>
        </div>
      )}

      {message && (
        <p className="mt-4 text-sm" style={{ color: "var(--mf-text-secondary)" }}>{message}</p>
      )}
    </aside>
  );
}
