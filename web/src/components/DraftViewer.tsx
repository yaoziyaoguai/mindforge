import { CardWorkspace } from "./CardWorkspace";
import type { CardBodyUpdateResponse, DraftDetailResponse } from "../api/types";

export function DraftViewer({ detail }: { detail: DraftDetailResponse }) {
  const readOnlySave = async (): Promise<CardBodyUpdateResponse> => ({
    ok: false,
    status: detail.draft.status,
    message: "Open this draft from the Drafts workspace to edit it.",
    card_path: detail.draft.path,
    rel_path: detail.draft.rel_path,
    index_updated: false,
  });
  return <CardWorkspace detail={detail} mode="draft" onSave={readOnlySave} />;
}
