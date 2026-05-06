import { useEffect, useMemo, useState } from "react";
import { Check, Edit3, Save, X } from "lucide-react";
import type { CardBodyUpdateResponse, DraftDetailResponse, LibraryCardDetailResponse, LibraryCardResponse } from "../api/types";
import { truncateMiddle } from "../lib/utils";

type Detail = DraftDetailResponse | LibraryCardDetailResponse;

interface Props {
  detail: Detail;
  mode: "draft" | "library";
  onSave: (body: string) => Promise<CardBodyUpdateResponse>;
  onSaved?: () => void;
}

export function CardWorkspace({ detail, mode, onSave, onSaved }: Props) {
  const card = "draft" in detail ? detail.draft : detail.card;
  const body = detail.body ?? "";
  const sections = useMemo(() => parseSections(body), [body]);
  const [editing, setEditing] = useState(false);
  const [draftBody, setDraftBody] = useState(body);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setDraftBody(body);
    setEditing(false);
    setMessage(null);
    setError(null);
  }, [body, card.rel_path]);

  async function save() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await onSave(draftBody);
      setMessage(result.index_updated ? `${result.message} Recall index refreshed.` : result.message);
      setEditing(false);
      onSaved?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="rounded-md border border-line bg-panel">
      <header className="border-b border-line p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-sm text-muted">{card.rel_path}</div>
            <h2 className="mt-1 text-2xl font-semibold text-ink">{card.title ?? "Untitled card"}</h2>
            <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted">
              <span className={card.status === "human_approved" ? "text-safe" : "text-warn"}>{card.status}</span>
              {card.track ? <span>track:{card.track}</span> : null}
              {card.strategy_label ? <span>{card.strategy_label}</span> : null}
              {sourceLabel(card) ? <span>source:{sourceLabel(card)}</span> : null}
            </div>
          </div>
          <button
            className="inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-sm font-medium text-ink"
            onClick={() => setEditing(true)}
            type="button"
          >
            <Edit3 className="h-4 w-4" /> Edit
          </button>
        </div>
        {mode === "draft" ? (
          <p className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-warn">
            This is an AI draft. It requires explicit approval before becoming human_approved knowledge.
          </p>
        ) : null}
        {card.strategy_note ? <p className="mt-3 text-sm text-muted">{card.strategy_note}</p> : null}
      </header>

      <section className="p-5">
        <h3 className="text-lg font-semibold text-ink">Knowledge Card Content</h3>
        {editing ? (
          <div className="mt-4 space-y-3">
            <textarea
              className="min-h-[420px] w-full rounded-md border border-line bg-white p-3 font-mono text-sm leading-6 text-ink"
              onChange={(event) => setDraftBody(event.target.value)}
              value={draftBody}
            />
            <div className="flex flex-wrap gap-2">
              <button className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={busy} onClick={save} type="button">
                <Save className="h-4 w-4" /> Save
              </button>
              <button className="inline-flex items-center gap-2 rounded-md border border-line px-4 py-2 text-sm font-medium text-ink disabled:opacity-50" disabled={busy} onClick={() => { setDraftBody(body); setEditing(false); }} type="button">
                <X className="h-4 w-4" /> Cancel
              </button>
            </div>
            {message ? <p className="text-sm text-safe">{message}</p> : null}
            {error ? <p className="text-sm text-danger">{error}</p> : null}
          </div>
        ) : (
          <CardSections body={body} sections={sections} />
        )}
      </section>

      <details className="border-t border-line p-5">
        <summary className="cursor-pointer text-sm font-semibold text-ink">Provenance / Debug</summary>
        <dl className="mt-4 grid gap-3 text-sm md:grid-cols-2">
          <Meta label="Extraction Strategy" value={card.strategy_label ?? card.strategy_id} />
          <Meta label="strategy_id" value={card.strategy_id} />
          <Meta label="canonical strategy" value={card.strategy_canonical_id} />
          <Meta label="strategy_version" value={card.strategy_version} />
          <Meta label="schema_version" value={card.schema_version} />
          <Meta label="source_id" value={card.source_id} />
          <Meta label="source_title" value={card.source_title} />
          <Meta label="source_path" value={card.source_path} />
          <Meta label="source_content_hash" value={card.source_content_hash} />
          <Meta label="source_archive_path" value={card.source_archive_path} />
          <Meta label="profile/provider" value={card.profile ?? card.provider} />
          <Meta label="run_id" value={card.run_id} />
          <Meta label="prompt_versions" value={Object.entries(card.prompt_versions ?? {}).map(([stage, version]) => `${stage}@${version}`).join(", ")} />
          <Meta label="stage_models" value={JSON.stringify(card.stage_models ?? {})} />
        </dl>
      </details>
    </article>
  );
}

function CardSections({ body, sections }: { body: string; sections: Array<{ title: string; content: string }> }) {
  if (!body.trim()) return <p className="mt-4 text-sm text-muted">No card body.</p>;
  if (!sections.length) {
    return <pre className="mt-4 whitespace-pre-wrap rounded-md bg-stone-50 p-4 text-sm leading-7 text-ink">{body}</pre>;
  }
  return (
    <div className="mt-4 space-y-4">
      {sections.map((section) => (
        <section key={section.title} className="rounded-md border border-line bg-white p-4">
          <h4 className="font-semibold text-ink">{section.title}</h4>
          <div className="mt-2 whitespace-pre-wrap text-sm leading-7 text-ink">{section.content || "-"}</div>
        </section>
      ))}
    </div>
  );
}

function parseSections(body: string): Array<{ title: string; content: string }> {
  const lines = body.split(/\r?\n/);
  const sections: Array<{ title: string; content: string[] }> = [];
  for (const line of lines) {
    const match = /^##\s+(.+?)\s*$/.exec(line);
    if (match) {
      sections.push({ title: match[1], content: [] });
      continue;
    }
    if (sections.length) sections[sections.length - 1].content.push(line);
  }
  return sections.map((section) => ({ title: section.title, content: section.content.join("\n").trim() }));
}

function Meta({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <dt className="text-xs uppercase text-muted">{label}</dt>
      <dd className="mt-1 break-words text-ink">{value ? truncateMiddle(value, 120) : "-"}</dd>
    </div>
  );
}

function sourceLabel(card: Pick<LibraryCardResponse, "source_title" | "source_path">) {
  return card.source_title ?? card.source_path ?? null;
}
