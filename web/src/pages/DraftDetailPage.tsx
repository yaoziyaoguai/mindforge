import type { DraftDetailResponse } from "../api/types";
import { ApprovalPanel } from "../components/ApprovalPanel";
import { DraftViewer } from "../components/DraftViewer";

export function DraftDetailPage({ detail, onApproved }: { detail: DraftDetailResponse; onApproved: () => void }) {
  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_300px]">
      <DraftViewer detail={detail} />
      <ApprovalPanel detail={detail} onApproved={onApproved} />
    </div>
  );
}
