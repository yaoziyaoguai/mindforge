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

function statusBadgeClass(status: string): string {
  if (status === "human_approved") return "bg-green-100 text-green-800";
  return "bg-amber-100 text-amber-800";
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

  return (
    <aside className="rounded-md border border-line bg-panel p-5">
      {/* 信息区：标题 → 状态说明 → 价值评分 */}
      <h2 className="text-lg font-semibold text-ink">{t("approval.title")}</h2>
      <p className="mt-2 text-sm text-muted">{t("approval.description")}</p>
      <div className="mt-3 rounded-md border border-line bg-stone-50 px-3 py-2">
        <span className="text-xs text-muted">{t("approval.value_score")}</span>
        <div className="text-lg font-semibold text-ink">
          {detail.draft.value_score != null ? detail.draft.value_score : "-"}
        </div>
      </div>

      {/* 状态时间线：ai_draft → human_approved 的完整审批路径 */}
      <div className="mt-3 border-t border-line pt-3">
        <h3 className="text-xs font-medium text-muted uppercase tracking-wide">{t("approval.status_timeline")}</h3>
        <div className="mt-2 space-y-1.5 text-sm">
          <div className="flex justify-between">
            <span className="text-muted">{t("approval.status_created")}</span>
            <span className="text-ink">{formatDate(detail.draft.created_at)}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-muted">{t("approval.status_current")}</span>
            <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${statusBadgeClass(detail.draft.status)}`}>
              {detail.draft.status === "human_approved" ? t("approval.status_human_approved") : t("approval.status_ai_draft")}
            </span>
          </div>
          {isApproved && detail.draft.approved_at ? (
            <div className="flex justify-between">
              <span className="text-muted">{t("approval.status_approved_at")}</span>
              <span className="text-ink">{formatDate(detail.draft.approved_at)}</span>
            </div>
          ) : null}
        </div>
      </div>

      {/* 操作区：审查确认 → 主操作（确认）→ 次操作（拒绝） */}
      {!isApproved ? (
      <div className="mt-5 border-t border-line pt-4">
        <label className="flex items-start gap-2 text-sm text-ink">
          <input checked={reviewed} onChange={(event) => setReviewed(event.target.checked)} type="checkbox" />
          {t("approval.reviewed_checkbox")}
        </label>
        {!confirming ? (
          <button
            className="mt-3 w-full rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-stone-300"
            disabled={!reviewed || busy}
            onClick={() => setConfirming(true)}
            type="button"
          >
            {t("approval.confirm_button")}
          </button>
        ) : (
          <div className="mt-3 rounded-md border border-primary/30 bg-blue-50 p-3">
            <p className="text-sm text-primary">{t("approval.confirm_title")}</p>
            <button
              className="mt-3 w-full rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white"
              disabled={busy}
              onClick={approve}
              type="button"
            >
              {t("approval.confirm_final")}
            </button>
            <button
              className="mt-2 w-full rounded-md border border-line bg-panel px-4 py-2 text-sm"
              onClick={() => setConfirming(false)}
              type="button"
            >
              {t("approval.cancel")}
            </button>
          </div>
        )}
        <button
          className="mt-2 w-full rounded-md border border-danger/30 px-4 py-2 text-sm text-danger hover:bg-red-50"
          disabled={busy}
          onClick={reject}
          type="button"
        >
          {t("approval.reject")}
        </button>
      </div>
      ) : null}
      {message ? <p className="mt-4 text-sm text-muted">{message}</p> : null}
    </aside>
  );
}
