import { useState } from "react";
import { approveDraft, rejectDraft } from "../api/approval";
import type { ApprovalResponse, DraftDetailResponse, UnavailableResponse } from "../api/types";

export function ApprovalPanel({ detail, onApproved }: { detail: DraftDetailResponse; onApproved: () => void }) {
  const [reviewed, setReviewed] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const id = detail.draft.id ?? detail.draft.rel_path;

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
      <h2 className="text-lg font-semibold text-ink">Approval</h2>
      <p className="mt-2 text-sm text-muted">
        Approve promotes this draft from ai_draft to human_approved. It enters local recall and project context.
      </p>
      <label className="mt-4 flex items-start gap-2 text-sm text-ink">
        <input checked={reviewed} onChange={(event) => setReviewed(event.target.checked)} type="checkbox" />
        I reviewed the source context and draft content.
      </label>
      {!confirming ? (
        <button
          className="mt-4 w-full rounded-md bg-danger px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-stone-300"
          disabled={!reviewed || busy}
          onClick={() => setConfirming(true)}
          type="button"
        >
          Approve...
        </button>
      ) : (
        <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3">
          <p className="text-sm text-danger">Second confirmation required. This writes human_approved.</p>
          <button
            className="mt-3 w-full rounded-md bg-danger px-4 py-2 text-sm font-semibold text-white"
            disabled={busy}
            onClick={approve}
            type="button"
          >
            Confirm approve
          </button>
          <button
            className="mt-2 w-full rounded-md border border-line bg-panel px-4 py-2 text-sm"
            onClick={() => setConfirming(false)}
            type="button"
          >
            Cancel
          </button>
        </div>
      )}
      <button
        className="mt-3 w-full rounded-md border border-line px-4 py-2 text-sm text-muted hover:text-ink"
        disabled={busy}
        onClick={reject}
        type="button"
      >
        Reject
      </button>
      {message ? <p className="mt-4 text-sm text-muted">{message}</p> : null}
    </aside>
  );
}
