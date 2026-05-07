import { useEffect, useState } from "react";
import { getTrashCards, getTrashDetail, restoreTrashCard } from "../api/trash";
import type { TrashCardResponse, TrashDetailResponse } from "../api/types";

export function TrashPage({ onRefresh }: { onRefresh?: () => void }) {
  const [cards, setCards] = useState<TrashCardResponse[]>([]);
  const [detail, setDetail] = useState<TrashDetailResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { void load(); }, []);

  async function load() {
    try {
      const response = await getTrashCards();
      setCards(response.trashed_cards);
    } catch {
      setCards([]);
    }
  }

  async function openDetail(trashRelPath: string) {
    setBusy(true);
    try {
      setDetail(await getTrashDetail(trashRelPath));
    } catch {
      setMessage("Failed to load card detail");
    } finally {
      setBusy(false);
    }
  }

  async function restore(trashRelPath: string) {
    setBusy(true);
    try {
      const response = await restoreTrashCard(trashRelPath);
      setMessage(response.message);
      setDetail(null);
      await load();
      onRefresh?.();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Restore failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">Trash</h1>
        <p className="mt-1 text-sm text-muted">Trash contains knowledge cards you moved out of Review or Library. Source files are not deleted.</p>
      </header>

      {message ? <p className="text-sm text-primary">{message}</p> : null}

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Card list */}
        <div className="space-y-2 lg:col-span-1">
          {cards.length === 0 ? (
            <div className="rounded-md border border-line p-4 text-sm text-muted">Trash is empty.</div>
          ) : (
            cards.map((card) => (
              <button
                key={card.trash_rel_path}
                className="w-full rounded-md border border-line bg-panel p-3 text-left hover:bg-stone-50"
                onClick={() => openDetail(card.trash_rel_path)}
                type="button"
              >
                <div className="text-sm font-medium text-ink truncate">{card.title}</div>
                <div className="mt-1 text-xs text-muted">{card.previous_status === "human_approved" ? "Approved" : "Draft"} · trashed {card.trashed_at?.slice(0, 10)}</div>
                {card.track ? <div className="text-xs text-muted">{card.track}</div> : null}
              </button>
            ))
          )}
        </div>

        {/* Card detail */}
        <div className="lg:col-span-2">
          {detail ? (
            <div className="rounded-md border border-line bg-panel p-4">
              <h2 className="text-lg font-semibold text-ink">{detail.card.title}</h2>
              <dl className="mt-3 grid gap-2 text-sm md:grid-cols-2">
                <div><dt className="text-xs text-muted">Previous status</dt><dd className="text-ink">{detail.card.previous_status}</dd></div>
                <div><dt className="text-xs text-muted">Trashed at</dt><dd className="text-ink">{detail.card.trashed_at}</dd></div>
                <div><dt className="text-xs text-muted">Original path</dt><dd className="text-ink truncate">{detail.card.original_path}</dd></div>
                <div><dt className="text-xs text-muted">Source title</dt><dd className="text-ink">{detail.card.source_title || "—"}</dd></div>
                {detail.card.track ? <div><dt className="text-xs text-muted">Track</dt><dd className="text-ink">{detail.card.track}</dd></div> : null}
              </dl>
              {detail.body ? (
                <div className="mt-4 max-h-96 overflow-y-auto rounded-md border border-line bg-white p-3">
                  <pre className="whitespace-pre-wrap text-sm text-ink">{detail.body}</pre>
                </div>
              ) : null}
              <div className="mt-4 flex gap-2">
                <button className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50" disabled={busy} onClick={() => restore(detail.card.trash_rel_path)} type="button">
                  Restore
                </button>
                <button className="rounded-md border border-line px-3 py-2 text-sm text-ink" onClick={() => setDetail(null)} type="button">Close</button>
              </div>
            </div>
          ) : (
            <div className="rounded-md border border-line p-4 text-sm text-muted">Select a trashed card to preview.</div>
          )}
        </div>
      </div>
    </div>
  );
}
