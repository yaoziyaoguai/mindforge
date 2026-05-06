import { useEffect, useState } from "react";
import { getLibraryCardDetail, saveLibraryCardBody } from "../api/library";
import type { LibraryCardDetailResponse, LibraryCardsResponse } from "../api/types";
import { CardWorkspace } from "../components/CardWorkspace";
import { ErrorState } from "../components/ErrorState";
import { StatusCard } from "../components/StatusCard";

export function LibraryPage({ data }: { data: LibraryCardsResponse }) {
  const initialRef = new URLSearchParams(window.location.search).get("card") ?? data.cards[0]?.id ?? data.cards[0]?.rel_path;
  const [selected, setSelected] = useState<string | undefined>(initialRef ?? undefined);
  const [detail, setDetail] = useState<LibraryCardDetailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">Knowledge Library</h1>
        <p className="mt-1 text-sm text-muted">Readable and editable human_approved knowledge cards.</p>
      </header>
      <div className="grid gap-4 md:grid-cols-4">
        <StatusCard label="Total cards" value={data.stats.total_cards} status={data.stats.total_cards > 0 ? "ok" : "info"} detail={data.stats.cards_dir} />
        <StatusCard label="AI drafts" value={data.stats.by_status.ai_draft ?? 0} status={(data.stats.by_status.ai_draft ?? 0) > 0 ? "warn" : "ok"} detail="Not formal knowledge" />
        <StatusCard label="Approved" value={data.stats.by_status.human_approved ?? 0} status={(data.stats.by_status.human_approved ?? 0) > 0 ? "ok" : "info"} detail="Available to recall" />
        <StatusCard label="Index" value={data.stats.index_exists ? "present" : "missing"} status={data.stats.index_exists ? "ok" : "warn"} detail={data.stats.next_action} />
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
                  <span className={card.status === "human_approved" ? "text-xs text-safe" : "text-xs text-warn"}>{card.status}</span>
                </div>
                <p className="mt-1 text-sm text-muted">{card.source_title ?? card.source_path ?? "No source title"}</p>
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
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}
