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

export function DraftsPage({ data, onRefresh, providerState }: { data: DraftsResponse; onRefresh: () => void; providerState?: string }) {
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
        <p>
          {t("drafts.subtitle")}
          {/* provider 模式提示 — AI 草稿可能是 fake 输出 */}
          {providerState !== "ready" && (
            <span className="ml-2" style={{ color: "var(--mf-text-tertiary)", fontSize: "var(--mf-text-caption)" }}>
              · {t("drafts.demo_mode_hint")}
            </span>
          )}
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[280px_1fr_260px]">
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
          ) : (
            <div className="flex items-center justify-center h-64 text-sm" style={{ color: "var(--mf-text-tertiary)" }}>
              {t("drafts.empty_title")}
            </div>
          )}
        </div>
        {detail ? <ApprovalPanel detail={detail} onApproved={onRefresh} /> : null}
      </div>

      {message && (
        <p className="text-sm" style={{ color: "var(--mf-text-secondary)" }}>{message}</p>
      )}
    </div>
  );
}
