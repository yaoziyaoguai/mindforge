import { useEffect, useState } from "react";
import { getDraftDetail } from "../api/drafts";
import type { DraftDetailResponse, DraftsResponse } from "../api/types";
import { ApprovalPanel } from "../components/ApprovalPanel";
import { DraftList } from "../components/DraftList";
import { DraftViewer } from "../components/DraftViewer";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";

export function DraftsPage({ data, onRefresh }: { data: DraftsResponse; onRefresh: () => void }) {
  const [selected, setSelected] = useState<string | undefined>(data.drafts[0]?.id ?? data.drafts[0]?.rel_path);
  const [detail, setDetail] = useState<DraftDetailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selected) return;
    setError(null);
    getDraftDetail(selected)
      .then(setDetail)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Draft failed to load"));
  }, [selected]);

  if (data.drafts.length === 0) {
    return <EmptyState title="No drafts waiting for review" action={data.empty_state} />;
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">Drafts / Review</h1>
        <p className="mt-1 text-sm text-muted">Approve requires source review and second confirmation.</p>
      </header>
      <div className="grid gap-5 lg:grid-cols-[340px_1fr_280px]">
        <DraftList drafts={data.drafts} selected={selected} onSelect={setSelected} />
        <div>{error ? <ErrorState message={error} /> : detail ? <DraftViewer detail={detail} /> : null}</div>
        {detail ? <ApprovalPanel detail={detail} onApproved={onRefresh} /> : null}
      </div>
    </div>
  );
}
