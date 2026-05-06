import type { DraftDetailResponse } from "../api/types";

export function DraftViewer({ detail }: { detail: DraftDetailResponse }) {
  const promptVersions = Object.entries(detail.draft.prompt_versions ?? {});
  return (
    <article className="rounded-md border border-line bg-panel">
      <header className="border-b border-line p-5">
        <div className="text-sm text-muted">{detail.draft.rel_path}</div>
        <h2 className="mt-1 text-2xl font-semibold text-ink">{detail.draft.title ?? "Untitled draft"}</h2>
        <div className="mt-4 grid gap-2 text-xs text-muted md:grid-cols-2">
          <div>status: {detail.draft.status}</div>
          <div>
            Extraction Strategy: {detail.draft.strategy_label ?? detail.draft.strategy_id ?? "-"}
            {detail.draft.strategy_version ? `@${detail.draft.strategy_version}` : ""}
          </div>
          {detail.draft.strategy_note ? <div>{detail.draft.strategy_note}</div> : null}
          <div>source: {detail.draft.source_id ?? "-"}</div>
          <div>source hash: {detail.draft.source_content_hash ?? "-"}</div>
          <div>schema: {detail.draft.schema_version ?? "-"}</div>
          <div>run: {detail.draft.run_id ?? "-"}</div>
          <div className="md:col-span-2">
            prompts: {promptVersions.length ? promptVersions.map(([stage, version]) => `${stage}@${version}`).join(", ") : "-"}
          </div>
        </div>
      </header>
      <section className="prose prose-stone max-w-none whitespace-pre-wrap p-5 text-sm leading-7 text-ink">
        {detail.body || "No draft body."}
      </section>
    </article>
  );
}
