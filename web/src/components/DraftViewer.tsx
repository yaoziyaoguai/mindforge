import type { DraftDetailResponse } from "../api/types";

export function DraftViewer({ detail }: { detail: DraftDetailResponse }) {
  return (
    <article className="rounded-md border border-line bg-panel">
      <header className="border-b border-line p-5">
        <div className="text-sm text-muted">{detail.draft.rel_path}</div>
        <h2 className="mt-1 text-2xl font-semibold text-ink">{detail.draft.title ?? "Untitled draft"}</h2>
      </header>
      <section className="prose prose-stone max-w-none whitespace-pre-wrap p-5 text-sm leading-7 text-ink">
        {detail.body || "No draft body."}
      </section>
    </article>
  );
}
