import { useEffect, useMemo, useState } from "react";
import { Clipboard, Edit3, FolderOpen, Save, Trash2, X } from "lucide-react";
import { revealSourceByRef } from "../api/sources";
import { LocalGraphPreview } from "./LocalGraphPreview";
import { QualityPanel } from "./quality/QualityPanel";
import { SourceLocationBadge } from "./provenance/SourceLocationBadge";
import type { CardBodyUpdateResponse, DraftDetailResponse, LibraryCardDetailResponse, LibraryCardResponse } from "../api/types";
import { friendlyStatus, statusIcon, truncateMiddle } from "../lib/utils";
import { useLocale } from "../lib/i18n";

const sourceTypeLabels: Record<string, string> = {
  plain_markdown: "Markdown",
  txt: "Text",
  html: "HTML",
  pdf: "PDF",
  docx: "Word",
};

type Detail = DraftDetailResponse | LibraryCardDetailResponse;

interface Props {
  detail: Detail;
  mode: "draft" | "library";
  onSave: (body: string) => Promise<CardBodyUpdateResponse>;
  onSaved?: () => void;
  onMoveToTrash?: () => void;
}

export function CardWorkspace({ detail, mode, onSave, onSaved, onMoveToTrash }: Props) {
  const card = "draft" in detail ? detail.draft : detail.card;
  const body = detail.body ?? "";
  const sections = useMemo(() => parseSections(body), [body]);
  const [editing, setEditing] = useState(false);
  const [draftBody, setDraftBody] = useState(body);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pathActionMsg, setPathActionMsg] = useState<string | null>(null);
  const [pathActionErr, setPathActionErr] = useState<string | null>(null);
  const { locale, t } = useLocale();

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

  const pathView = "source_path_view" in card ? card.source_path_view : null;

  async function copyPath() {
    setPathActionMsg(null);
    setPathActionErr(null);
    if (!navigator.clipboard?.writeText) {
      setPathActionErr(t("card.clipboard_unavailable"));
      return;
    }
    const text = pathView?.display_path ?? null;
    if (!text) {
      setPathActionErr(t("card.no_path_to_copy"));
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      setPathActionMsg(pathView?.can_copy_full_path ? t("card.copied_source_path") : t("card.copied_display_path"));
    } catch (err) {
      setPathActionErr(err instanceof Error ? err.message : "Copy failed");
    }
  }

  async function openInFinder() {
    setPathActionMsg(null);
    setPathActionErr(null);
    const cid = "id" in card ? (card.id ?? null) : null;
    try {
      const result = await revealSourceByRef(cid, null);
      setPathActionMsg(result.message);
    } catch (err) {
      setPathActionErr(err instanceof Error ? err.message : "Reveal failed");
    }
  }

  return (
    <article className="rounded-md border border-line bg-panel">
      <header className="border-b border-line p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-sm text-muted">{mode === "draft" ? t("card.draft_label") : t("card.library_label")}</div>
            <h2 className="mt-1 text-2xl font-semibold text-ink">{card.title ?? t("card.untitled")}</h2>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted">
              <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium ${card.status === "human_approved" ? "bg-safe/10 text-safe" : "bg-warn/10 text-warn"}`}>
                {(() => { const Icon = statusIcon(card.status === "human_approved" ? "ok" : "warn"); return Icon ? <Icon className="h-3 w-3" aria-hidden="true" /> : null; })()}
                {friendlyStatus(card.status, locale)}
              </span>
              {sourceTypeBadge(card) && (
                <span className="inline-flex items-center rounded bg-muted/20 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide">{sourceTypeBadge(card)}</span>
              )}
              {card.track ? <span>track:{card.track}</span> : null}
              {card.strategy_label ? <span>{card.strategy_label}</span> : null}
              {mode === "library" && "approved_at" in card && card.approved_at ? <span>approved:{card.approved_at.slice(0, 10)}</span> : null}
              {sourceLabel(card) ? <span>source:{sourceLabel(card)}</span> : null}
            </div>
          </div>
          <div className="flex gap-2">
            <button
              className="inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-sm font-medium text-ink"
              onClick={() => setEditing(true)}
              type="button"
            >
              <Edit3 className="h-4 w-4" /> {t("card.edit")}
            </button>
            {onMoveToTrash ? (
              <button
                className="inline-flex items-center gap-2 rounded-md border border-danger px-3 py-2 text-sm font-medium text-danger hover:bg-red-50"
                onClick={() => {
                  if (window.confirm(mode === "draft" ? t("card.confirm_trash_draft") : t("card.confirm_trash_library"))) {
                    onMoveToTrash();
                  }
                }}
                type="button"
              >
                <Trash2 className="h-4 w-4" /> {t("card.move_to_trash")}
              </button>
            ) : null}
          </div>
        </div>
        {mode === "draft" ? (
          <p className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-warn">
            {t("card.draft_warning")}
          </p>
        ) : null}
        {card.strategy_note ? <p className="mt-3 text-sm text-muted">{card.strategy_note}</p> : null}
      </header>

      <QualityPanel cardId={card.id ?? ""} />

      {mode === "library" && "local_graph" in detail ? (
        <LocalGraphPreview graph={detail.local_graph} relatedCards={detail.related_cards ?? []} />
      ) : null}

      <section className="p-5">
        <h3 className="text-lg font-semibold text-ink">{t("card.knowledge_content")}</h3>
        {editing ? (
          <div className="mt-4 space-y-3">
            <textarea
              className="min-h-[420px] w-full rounded-md border border-line bg-white p-3 font-mono text-sm leading-6 text-ink"
              onChange={(event) => setDraftBody(event.target.value)}
              value={draftBody}
            />
            <div className="flex flex-wrap gap-2">
              <button className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={busy} onClick={save} type="button">
                <Save className="h-4 w-4" /> {t("card.save")}
              </button>
              <button className="inline-flex items-center gap-2 rounded-md border border-line px-4 py-2 text-sm font-medium text-ink disabled:opacity-50" disabled={busy} onClick={() => { setDraftBody(body); setEditing(false); }} type="button">
                <X className="h-4 w-4" /> {t("card.cancel")}
              </button>
            </div>
            {message ? <p className="text-sm text-safe">{message}</p> : null}
            {error ? <p className="text-sm text-danger">{error}</p> : null}
          </div>
        ) : (
          <CardSections body={body} sections={sections} />
        )}
      </section>

      <section className="border-t border-line p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-sm font-semibold text-ink">{t("card.source_history")}</h3>
          {pathView ? (
            <div className="flex gap-2">
              {pathView.can_copy_display_path ? (
                <button
                  type="button"
                  className="inline-flex items-center gap-1.5 rounded-md border border-line px-2.5 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-muted/10"
                  onClick={copyPath}
                  title={pathView.can_copy_full_path ? "Copy source absolute path to clipboard" : "Copy source path basename to clipboard"}
                >
                  <Clipboard size={12} /> {pathView.can_copy_full_path ? t("card.copy_path") : t("card.copy_display_path")}
                </button>
              ) : null}
              {pathView.can_reveal_in_finder ? (
                <button
                  type="button"
                  className="inline-flex items-center gap-1.5 rounded-md border border-line px-2.5 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-muted/10"
                  onClick={openInFinder}
                  title="Reveal source file in Finder"
                >
                  <FolderOpen size={12} /> Reveal in Finder
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
        {pathActionMsg ? <p className="mt-2 text-xs text-safe">{pathActionMsg}</p> : null}
        {pathActionErr ? <p className="mt-2 text-xs text-danger">{pathActionErr}</p> : null}
        {pathView?.warning ? <p className="mt-2 text-xs text-warn">{pathView.warning}</p> : null}
        <dl className="mt-4 grid gap-3 text-sm md:grid-cols-2">
          <Meta label={t("card.source")} value={card.source_title ?? pathView?.display_path ?? t("card.source_unavailable")} />
          <Meta label={t("card.file_location")} value={pathView?.display_path ?? t("card.source_unavailable")} />
          <SourceLocationBadge cardId={card.id ?? ""} hasSource={!!card.source_path} />
          <Meta label={t("card.archived_source")} value={card.source_archive_path ? truncateMiddle(card.source_archive_path, 80) : null} />
          <Meta label={t("card.extraction_method")} value={card.strategy_label ?? card.strategy_id} />
        </dl>
      </section>

      <details className="border-t border-line p-5">
        <summary className="cursor-pointer text-sm font-semibold text-ink">{t("card.tech_details")}</summary>
        <dl className="mt-4 grid gap-3 text-sm md:grid-cols-2">
          <Meta label={t("card.internal_status")} value={card.status} />
          <Meta label={t("card.strategy_id")} value={card.strategy_id} />
          <Meta label={t("card.strategy_canonical")} value={card.strategy_canonical_id} />
          <Meta label={t("card.strategy_version")} value={card.strategy_version} />
          <Meta label={t("card.schema_version")} value={card.schema_version} />
          <Meta label={t("card.source_id")} value={card.source_id} />
          <Meta label={t("card.source_hash")} value={card.source_content_hash} />
          <Meta label={t("card.model_run")} value={card.provider} />
          <Meta label={t("card.run_id")} value={card.run_id} />
          <Meta label={t("card.prompt_versions")} value={Object.entries(card.prompt_versions ?? {}).map(([stage, version]) => `${stage}@${version}`).join(", ")} />
          <Meta label={t("card.model_routing")} value={JSON.stringify(card.stage_models ?? {})} />
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

function sourceLabel(card: Pick<LibraryCardResponse, "source_title" | "source_path_view">) {
  return card.source_title ?? card.source_path_view?.display_path ?? null;
}

function sourceTypeBadge(card: Pick<LibraryCardResponse, "source_type">) {
  if (!card.source_type) return null;
  return sourceTypeLabels[card.source_type] ?? card.source_type;
}
