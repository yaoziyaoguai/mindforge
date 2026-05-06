import { useState } from "react";
import { recall } from "../api/recall";
import type { RecallResponse } from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";

export function RecallPage({ onNavigate }: { onNavigate: (href: string) => void }) {
  const [query, setQuery] = useState("");
  const [data, setData] = useState<RecallResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      setData(await recall(query));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Recall failed");
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">Recall / Knowledge</h1>
        <p className="mt-1 text-sm text-muted">Local lexical recall over human_approved cards. No RAG or embeddings.</p>
      </header>
      <form className="flex gap-2" onSubmit={submit}>
        <input
          className="min-w-0 flex-1 rounded-md border border-line bg-panel px-3 py-2"
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search approved knowledge"
          value={query}
        />
        <button className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white" type="submit">
          Search
        </button>
      </form>
      {error ? <ErrorState message={error} /> : null}
      {!data ? <EmptyState title="Start with a keyword" action={{ label: "Search", description: "输入关键词后查询本地 approved cards。" }} /> : null}
      {data?.empty_state && data.hits.length === 0 ? <EmptyState title="No recall hits" action={data.empty_state} /> : null}
      {data?.hits.length ? (
        <div className="space-y-3">
          {data.hits.map((hit) => (
            <article key={hit.rel_path} className="rounded-md border border-line bg-panel p-4">
              <div className="flex items-center justify-between gap-3">
                <h2 className="font-semibold text-ink">{hit.title ?? hit.rel_path}</h2>
                <span className="text-sm text-muted">{hit.score.toFixed(2)}</span>
              </div>
              <p className="mt-2 text-sm text-muted">{hit.why_this_matched}</p>
              <button
                className="mt-3 rounded-md border border-line px-3 py-1.5 text-sm font-medium text-primary"
                onClick={() => onNavigate(hit.detail_href ?? `/library?card=${encodeURIComponent(hit.card_ref ?? hit.rel_path)}`)}
                type="button"
              >
                Open Knowledge Card
              </button>
            </article>
          ))}
        </div>
      ) : null}
    </div>
  );
}
