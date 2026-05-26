import { useEffect, useState } from "react";
import { getDraftDetail, saveDraftBody } from "../api/drafts";
import { moveDraftToTrash } from "../api/trash";
import type { DraftDetailResponse, DraftsResponse } from "../api/types";
import { ApprovalPanel } from "../components/ApprovalPanel";
import { CardWorkspace } from "../components/CardWorkspace";
import { DraftList } from "../components/DraftList";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { useLocale } from "../lib/i18n";

export function DraftsPage({ data, onRefresh }: { data: DraftsResponse; onRefresh: () => void }) {
  const [selected, setSelected] = useState<string | undefined>(data.drafts[0]?.id ?? data.drafts[0]?.rel_path);
  const [detail, setDetail] = useState<DraftDetailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const { locale, t } = useLocale();

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
        title={t("drafts.empty_title")}
        action={data.empty_state ?? {
          label: t("drafts.empty_label"),
          description: t("drafts.empty_desc"),
          href: "/sources",
        }}
        locale={locale}
      />
    );
  }

  return (
    <div className="space-y-6">
      <header className="page-header">
        <h1>{t("drafts.title")}</h1>
        <p>{t("drafts.subtitle")}</p>
      </header>

      {/* v4.4 A2: Why Review Matters — calm callout per Variant A */}
      <div
        className="rounded-md border p-3 text-xs leading-relaxed"
        style={{
          borderColor: "var(--mf-border)",
          background: "var(--mf-surface-alt)",
          color: "var(--mf-text-secondary)",
        }}
      >
        {t("drafts.why_review")}
      </div>

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
