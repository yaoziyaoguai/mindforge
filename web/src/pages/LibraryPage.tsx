import type { LibraryCardsResponse } from "../api/types";
import { StatusCard } from "../components/StatusCard";

export function LibraryPage({ data }: { data: LibraryCardsResponse }) {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">Knowledge Library</h1>
        <p className="mt-1 text-sm text-muted">Metadata-only card inventory with source provenance.</p>
      </header>
      <div className="grid gap-4 md:grid-cols-4">
        <StatusCard label="Total cards" value={data.stats.total_cards} status={data.stats.total_cards > 0 ? "ok" : "info"} detail={data.stats.cards_dir} />
        <StatusCard label="AI drafts" value={data.stats.by_status.ai_draft ?? 0} status={(data.stats.by_status.ai_draft ?? 0) > 0 ? "warn" : "ok"} detail="Not formal knowledge" />
        <StatusCard label="Approved" value={data.stats.by_status.human_approved ?? 0} status={(data.stats.by_status.human_approved ?? 0) > 0 ? "ok" : "info"} detail="Available to recall" />
        <StatusCard label="Index" value={data.stats.index_exists ? "present" : "missing"} status={data.stats.index_exists ? "ok" : "warn"} detail={data.stats.next_action} />
      </div>
      <div className="overflow-hidden rounded-md border border-line bg-panel">
        <table className="w-full text-left text-sm">
          <thead className="bg-stone-100 text-muted">
            <tr>
              <th className="px-4 py-3 font-medium">Card</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Source</th>
              <th className="px-4 py-3 font-medium">Provider</th>
              <th className="px-4 py-3 font-medium">Path</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {data.cards.map((card) => (
              <tr key={card.rel_path}>
                <td className="px-4 py-3">
                  <div className="font-medium text-ink">{card.title ?? "Untitled"}</div>
                  <div className="text-xs text-muted">{card.track ?? "unrouted"}</div>
                  <div className="text-xs text-muted">strategy:{card.strategy_label ?? card.strategy_id ?? "-"}</div>
                  {card.strategy_note ? <div className="text-xs text-muted">{card.strategy_note}</div> : null}
                </td>
                <td className="px-4 py-3">
                  <div>{card.status}</div>
                  <div className="text-xs text-muted">{card.status_explanation}</div>
                </td>
                <td className="px-4 py-3">
                  <div>{card.source_type ?? "-"}</div>
                  <div className="text-xs text-muted">id:{card.source_id ?? "-"}</div>
                  <div className="text-xs text-muted">hash:{card.source_content_hash ?? "-"}</div>
                  <div className="text-xs text-muted">{card.source_missing ? "source missing" : (card.source_archive_path ?? card.source_path ?? "-")}</div>
                </td>
                <td className="px-4 py-3">
                  <div>{card.profile ?? card.provider ?? "-"}</div>
                  <div className="text-xs text-muted">run:{card.run_id ?? "-"}</div>
                  {card.fake_provider_note ? <div className="text-xs text-muted">{card.fake_provider_note}</div> : null}
                </td>
                <td className="px-4 py-3 text-muted">{card.rel_path}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
