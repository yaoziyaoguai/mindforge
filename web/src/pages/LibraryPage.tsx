import { useEffect, useState } from "react";
import { getLibraryCardDetail, saveLibraryCardBody } from "../api/library";
import { moveLibraryCardToTrash } from "../api/trash";
import type { LibraryCardDetailResponse, LibraryCardsResponse } from "../api/types";
import { CardWorkspace } from "../components/CardWorkspace";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { StatusCard } from "../components/StatusCard";
import { friendlyStatus } from "../lib/utils";
import { useLocale } from "../lib/i18n";

export function LibraryPage({ data, onRefresh }: { data: LibraryCardsResponse; onRefresh?: () => void }) {
  const initialRef = new URLSearchParams(window.location.search).get("card") ?? data.cards[0]?.id ?? data.cards[0]?.rel_path;
  const [selected, setSelected] = useState<string | undefined>(initialRef ?? undefined);
  const [detail, setDetail] = useState<LibraryCardDetailResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { locale, t } = useLocale();

  useEffect(() => {
    if (!selected) return;
    setError(null);
    getLibraryCardDetail(selected)
      .then(setDetail)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Card failed to load"));
  }, [selected]);

  async function refreshSelected() {
    if (!selected) return;
    setDetail(await getLibraryCardDetail(selected));
  }

  async function handleMoveToTrash() {
    if (!selected) return;
    try {
      const result = await moveLibraryCardToTrash(selected);
      setMessage(result.message);
      setDetail(null);
      setSelected(undefined);
      onRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Move to trash failed");
    }
  }

  if (data.cards.length === 0) {
    return (
      <div className="space-y-6">
        <header>
          <h1 className="text-2xl font-semibold text-ink">{t("library.title")}</h1>
          <p className="mt-1 text-sm text-muted">{t("library.subtitle")}</p>
        </header>
        <EmptyState
          title={t("library.empty_title")}
          action={{
            label: t("library.empty_label"),
            description: t("library.empty_desc"),
            href: "/drafts",
          }}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">{t("library.title")}</h1>
        <p className="mt-1 text-sm text-muted">{t("library.subtitle")}</p>
      </header>
      <div className="grid gap-4 md:grid-cols-4">
        <StatusCard label={t("library.stats_approved")} value={data.stats.by_status.human_approved ?? 0} status={(data.stats.by_status.human_approved ?? 0) > 0 ? "ok" : "info"} detail={t("library.stats_approved_detail")} locale={locale} />
        <StatusCard label={t("library.stats_drafts")} value={data.stats.by_status.ai_draft ?? 0} status={(data.stats.by_status.ai_draft ?? 0) > 0 ? "warn" : "ok"} detail={t("library.stats_drafts_detail")} locale={locale} />
        <StatusCard label={t("library.stats_index")} value={data.stats.index_exists ? t("library.stats_index_ready") : t("library.stats_index_rebuild")} status={data.stats.index_exists ? "ok" : "warn"} detail={data.stats.next_action} locale={locale} />
        <StatusCard label={t("library.stats_total")} value={data.stats.total_cards} status={data.stats.total_cards > 0 ? "ok" : "info"} detail={t("library.stats_total_detail")} locale={locale} />
      </div>
      <div className="grid gap-5 lg:grid-cols-[340px_1fr]">
        <div className="space-y-2">
          {data.cards.map((card) => {
            const ref = card.id ?? card.rel_path;
            return (
              <button
                className={`w-full rounded-md border p-4 text-left transition ${selected === ref ? "border-primary bg-blue-50" : "border-line bg-panel hover:border-primary"}`}
                key={card.rel_path}
                onClick={() => setSelected(ref)}
                type="button"
              >
                <div className="flex items-center justify-between gap-3">
                  <h3 className="font-medium text-ink">{card.title ?? card.rel_path}</h3>
                  <span className={card.status === "human_approved" ? "text-xs text-safe" : "text-xs text-warn"}>{friendlyStatus(card.status, locale)}</span>
                </div>
                <p className="mt-1 text-sm text-muted">{card.source_title ?? card.source_path_view?.display_path ?? "No source title"}</p>
                <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted">
                  {card.track ? <span>track:{card.track}</span> : null}
                  {card.strategy_label ? <span>{card.strategy_label}</span> : null}
                  {card.updated_at ? <span>updated:{card.updated_at.slice(0, 10)}</span> : null}
                </div>
              </button>
            );
          })}
        </div>
        <div>
          {error ? <ErrorState message={error} /> : null}
          {!error && detail ? (
            <CardWorkspace
              detail={detail}
              mode="library"
              onSave={(body) => saveLibraryCardBody(selected ?? detail.card.id ?? detail.card.rel_path, body)}
              onSaved={refreshSelected}
              onMoveToTrash={handleMoveToTrash}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}
