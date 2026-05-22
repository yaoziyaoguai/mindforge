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

  {/* 中文学习型说明：approve 是"确认并保存为知识"，不是危险操作。
      按钮使用 bg-primary（正向操作色），不用 bg-danger（破坏性操作色）。
      两步确认机制完整保留，仅改变视觉语义和文案语气。
      API 调用、审批语义、human_approved 生成规则完全不变。 */}
  return (
    <aside className="rounded-md border border-line bg-panel p-5">
      <h2 className="text-lg font-semibold text-ink">确认知识卡片</h2>
      <p className="mt-2 text-sm text-muted">
        审查并编辑 AI 草稿后确认保存。确认后的知识卡片会出现在知识库和搜索结果中。此操作不会自动发生，需要你主动确认。
      </p>
      <p className="mt-2 text-sm">
        价值评分:{" "}
        <span className="font-semibold">
          {detail.draft.value_score != null ? detail.draft.value_score : "-"}
        </span>
      </p>
      <label className="mt-4 flex items-start gap-2 text-sm text-ink">
        <input checked={reviewed} onChange={(event) => setReviewed(event.target.checked)} type="checkbox" />
        我已审查来源内容和 AI 草稿
      </label>
      {!confirming ? (
        <button
          className="mt-4 w-full rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-stone-300"
          disabled={!reviewed || busy}
          onClick={() => setConfirming(true)}
          type="button"
        >
          确认并保存...
        </button>
      ) : (
        <div className="mt-4 rounded-md border border-primary/30 bg-blue-50 p-3">
          <p className="text-sm text-primary">二次确认：这将把 AI 草稿提升为人工确认知识，你可以随时取消。</p>
          <button
            className="mt-3 w-full rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white"
            disabled={busy}
            onClick={approve}
            type="button"
          >
            确认并保存此知识
          </button>
          <button
            className="mt-2 w-full rounded-md border border-line bg-panel px-4 py-2 text-sm"
            onClick={() => setConfirming(false)}
            type="button"
          >
            取消
          </button>
        </div>
      )}
      <button
        className="mt-3 w-full rounded-md border border-danger/30 px-4 py-2 text-sm text-danger hover:bg-red-50"
        disabled={busy}
        onClick={reject}
        type="button"
      >
        拒绝此草稿
      </button>
      {message ? <p className="mt-4 text-sm text-muted">{message}</p> : null}
    </aside>
  );
}
