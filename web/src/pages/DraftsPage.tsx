import { useEffect, useState } from "react";
import { getDraftDetail, saveDraftBody } from "../api/drafts";
import { moveDraftToTrash } from "../api/trash";
import type { DraftDetailResponse, DraftsResponse } from "../api/types";
import { ApprovalPanel } from "../components/ApprovalPanel";
import { CardWorkspace } from "../components/CardWorkspace";
import { DraftList } from "../components/DraftList";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";

export function DraftsPage({ data, onRefresh }: { data: DraftsResponse; onRefresh: () => void }) {
  const [selected, setSelected] = useState<string | undefined>(data.drafts[0]?.id ?? data.drafts[0]?.rel_path);
  const [detail, setDetail] = useState<DraftDetailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!selected) return;
    setError(null);
    getDraftDetail(selected)
      .then(setDetail)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Draft failed to load"));
  }, [selected]);

  async function refreshSelected() {
    if (!selected) return;
    const next = await getDraftDetail(selected);
    setDetail(next);
    onRefresh();
  }

  async function handleMoveToTrash() {
    if (!selected) return;
    try {
      const result = await moveDraftToTrash(selected);
      setMessage(result.message);
      setDetail(null);
      setSelected(undefined);
      onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Move to trash failed");
    }
  }

  if (data.drafts.length === 0) {
    return (
      <EmptyState
        title="没有待确认的 AI 草稿"
        action={data.empty_state ?? {
          label: "添加资料",
          description: "添加知识源并运行处理流程后，AI 生成的草稿会出现在这里等待你审阅确认。你也可以直接查看已确认的知识库。",
          href: "/sources",
        }}
      />
    );
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">审阅 AI 草稿</h1>
        <p className="mt-1 text-sm text-muted">检查 AI 生成的知识草稿，确认内容准确后保存为知识卡片。</p>
      </header>
      <div className="grid gap-5 lg:grid-cols-[320px_1fr_280px]">
        <DraftList drafts={data.drafts} selected={selected} onSelect={setSelected} />
        <div>
          {error ? <ErrorState message={error} /> : detail ? (
            <CardWorkspace
              detail={detail}
              mode="draft"
              onSave={(body) => saveDraftBody(selected ?? detail.draft.id ?? detail.draft.rel_path, body)}
              onSaved={refreshSelected}
              onMoveToTrash={handleMoveToTrash}
            />
          ) : null}
        </div>
        {detail ? <ApprovalPanel detail={detail} onApproved={onRefresh} /> : null}
      </div>
    </div>
  );
}
