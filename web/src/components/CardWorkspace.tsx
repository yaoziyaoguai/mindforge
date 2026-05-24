import { useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronUp, Clipboard, Edit3, File, FileCode, FileEdit, FileText, FileType, FolderOpen, Save, Trash2, X } from "lucide-react";
import { revealSourceByRef } from "../api/sources";
import { getProvenanceTrail } from "../api/library";
import { ApprovalTimeline } from "./ApprovalTimeline";
import { GraphNavigationPanel } from "./GraphNavigationPanel";
import { LocalGraphPreview } from "./LocalGraphPreview";
import { ProvenanceTrail } from "./ProvenanceTrail";
import { QualityPanel } from "./quality/QualityPanel";
import { SourceLocationBadge } from "./provenance/SourceLocationBadge";
import type { CardBodyUpdateResponse, DraftDetailResponse, LibraryCardDetailResponse, LibraryCardResponse, ProvenanceTrailResponse } from "../api/types";
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
  onSelectCard?: (ref: string) => void;
}

const sourceTypeIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  plain_markdown: FileText,
  txt: FileText,
  html: FileCode,
  pdf: FileType,
  docx: FileEdit,
};

export function CardWorkspace({ detail, mode, onSave, onSaved, onMoveToTrash, onSelectCard }: Props) {
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
  const [summaryOpen, setSummaryOpen] = useState(true);
  const [trail, setTrail] = useState<ProvenanceTrailResponse | null>(null);
  const { locale, t } = useLocale();

  useEffect(() => {
    const ref = card.id ?? card.rel_path;
    if (!ref || mode !== "library") return;
    getProvenanceTrail(ref).then((t) => setTrail(t)).catch(() => setTrail(null));
  }, [card.id, card.rel_path, mode]);

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
              {"quality_score" in card && card.quality_score != null ? (
                <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium ${
                  card.quality_level === "high" ? "bg-green-50 text-green-700" :
                  card.quality_level === "medium" ? "bg-amber-50 text-amber-700" :
                  "bg-red-50 text-red-700"
                }`} title={`${t("card.quality_score")}: ${card.quality_score}`}>
                  {qualityLevelLabel(card.quality_level ?? "", t)} {card.quality_score}
                </span>
              ) : null}
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

      {mode === "library" ? (
        <SummaryPanel
          body={body}
          card={card}
          open={summaryOpen}
          onToggle={() => setSummaryOpen((v) => !v)}
          t={t}
          locale={locale}
        />
      ) : null}

      {/* v1.4 W1: Relationship Map as primary navigation — elevated from bottom section */}
      {mode === "library" && (card.id || card.rel_path) ? (
        <div className="px-5 pt-5">
          <GraphNavigationPanel
            cardRef={card.id ?? card.rel_path ?? ""}
            onSelectCard={onSelectCard}
          />
        </div>
      ) : null}

      <QualityPanel cardId={card.id ?? ""} />

      {mode === "library" && trail ? (
        <ProvenanceTrail trail={trail} onSelectCard={onSelectCard} />
      ) : null}

      {mode === "library" && "local_graph" in detail ? (
        <LocalGraphPreview graph={detail.local_graph} relatedCards={detail.related_cards ?? []} onSelectCard={onSelectCard} />
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
        <ApprovalTimeline
          created_at={"created_at" in card ? (card as LibraryCardResponse).created_at : null}
          approved_at={"approved_at" in card ? (card as LibraryCardResponse).approved_at : null}
          updated_at={"updated_at" in card ? (card as LibraryCardResponse).updated_at : null}
        />
        <dl className="mt-4 grid gap-3 text-sm md:grid-cols-2">
          <Meta label={t("card.source")} value={card.source_title ?? pathView?.display_path ?? t("card.source_unavailable")} />
          <Meta label={t("card.file_location")} value={pathView?.display_path ?? t("card.source_unavailable")} />
          <SourceLocationBadge cardId={card.id ?? ""} hasSource={!!card.source_path} />
          <Meta label={t("card.archived_source")} value={card.source_archive_path ? truncateMiddle(card.source_archive_path, 80) : null} />
          <Meta label={t("card.extraction_method")} value={card.strategy_label ?? card.strategy_id} />
        </dl>
      </section>

      {mode === "library" && "related_cards" in detail ? (
        <RelatedCardsPanel
          relatedCards={detail.related_cards}
          onSelectCard={onSelectCard}
          t={t}
        />
      ) : null}

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

function qualityLevelLabel(level: string, t: (key: string) => string): string {
  if (level === "high") return t("card.quality_high");
  if (level === "medium") return t("card.quality_medium");
  if (level === "low") return t("card.quality_low");
  return level;
}

function sourceTypeIcon(st: string | null | undefined): React.ComponentType<{ className?: string }> {
  if (!st) return File;
  return sourceTypeIcons[st] ?? File;
}

function extractHeadings(body: string): Array<{ level: number; text: string }> {
  const re = /^(#{2,3})\s+(.+?)\s*$/gm;
  const result: Array<{ level: number; text: string }> = [];
  let match;
  while ((match = re.exec(body)) !== null) {
    result.push({ level: match[1].length, text: match[2] });
  }
  return result;
}

function stripMarkdown(text: string): string {
  return text
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/\*{1,2}([^*]+)\*{1,2}/g, "$1")
    .replace(/_{1,2}([^_]+)_{1,2}/g, "$1")
    .replace(/`{1,3}[^`]*`{1,3}/g, "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/[>*\-+]/g, "")
    .replace(/\n+/g, " ")
    .trim();
}

function SummaryPanel({ body, card, open, onToggle, t, locale }: {
  body: string;
  card: Pick<LibraryCardResponse, "track" | "strategy_label">;
  open: boolean;
  onToggle: () => void;
  t: (key: string) => string;
  locale: string;
}) {
  const headings = extractHeadings(body);

  return (
    <div className="border-b border-line p-5">
      <button
        type="button"
        className="flex w-full items-center justify-between text-sm font-semibold text-ink"
        onClick={onToggle}
      >
        <span>{t("library.summary_title")}</span>
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {open ? (
        <div className="mt-3 space-y-2">
          {headings.length > 0 ? (
            <ul className="space-y-1 text-sm text-muted">
              {headings.map((h, i) => (
                <li key={i} className={h.level === 3 ? "ml-4" : ""}>
                  {h.text}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted">{stripMarkdown(body).slice(0, 150)}{body.length > 150 ? "..." : ""}</p>
          )}
          <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted">
            {card.track ? <span className="rounded bg-muted/20 px-1.5 py-0.5">track: {card.track}</span> : null}
            {card.strategy_label ? <span className="rounded bg-muted/20 px-1.5 py-0.5">{card.strategy_label}</span> : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}

/** Reason code → i18n key mapping for group headers. */
const REASON_GROUP_KEYS: Record<string, string> = {
  same_source: "library.related_group_same_source",
  same_tag: "library.related_group_same_tag",
  same_wiki_section: "library.related_group_same_wiki_section",
  same_review_batch: "library.related_group_same_review_batch",
  source_location_neighbor: "library.related_group_source_location_neighbor",
};

function RelatedCardsPanel({ relatedCards, onSelectCard, t }: {
  relatedCards: Array<{ card: LibraryCardResponse; reasons: Array<{ reason: string; label: string; detail: string; strength: number }> }>;
  onSelectCard?: (ref: string) => void;
  t: (key: string) => string;
}) {
  if (relatedCards.length === 0) {
    return (
      <section className="border-t border-line p-5">
        <h3 className="text-sm font-semibold text-ink">{t("library.related_cards")}</h3>
        <p className="mt-3 text-sm text-muted leading-relaxed">{t("library.related_empty_guide")}</p>
      </section>
    );
  }

  // Group related cards by each reason. A card with multiple reasons appears in multiple groups.
  const groups: Record<string, Array<{ card: LibraryCardResponse; ref: string; reasons: Array<{ reason: string; label: string; detail: string }> }>> = {};
  for (const rc of relatedCards) {
    const ref = rc.card.id ?? rc.card.rel_path;
    for (const r of rc.reasons) {
      (groups[r.reason] ??= []).push({ card: rc.card, ref, reasons: rc.reasons });
    }
  }

  // Sort groups by reason strength (roughly: same_source > same_wiki_section > same_tag > source_location_neighbor > same_review_batch)
  const sortOrder = ["same_source", "same_wiki_section", "same_tag", "source_location_neighbor", "same_review_batch"];
  const sortedReasons = Object.keys(groups).sort((a, b) => sortOrder.indexOf(a) - sortOrder.indexOf(b));

  return (
    <section className="border-t border-line p-5">
      <h3 className="text-sm font-semibold text-ink">{t("library.related_cards")}</h3>
      <div className="mt-3 space-y-4">
        {sortedReasons.map((reason) => {
          const cards = groups[reason];
          const reasonLabel = cards[0]?.reasons.find(r => r.reason === reason)?.label;
          const groupLabel = t(REASON_GROUP_KEYS[reason] ?? reason) || reasonLabel || reason;
          return (
            <div key={reason}>
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
                {groupLabel} · {cards.length}
              </h4>
              <div className="flex gap-3 overflow-x-auto pb-1">
                {cards.map((rc) => {
                  const Icon = sourceTypeIcon(rc.card.source_type);
                  return (
                    <button
                      key={`${reason}-${rc.ref}`}
                      type="button"
                      className="flex-shrink-0 w-48 rounded-md border border-line bg-white p-3 text-left hover:border-primary transition"
                      onClick={() => onSelectCard?.(rc.ref)}
                    >
                      <h4 className="text-sm font-medium text-ink line-clamp-2">{rc.card.title ?? rc.card.rel_path}</h4>
                      <div className="mt-1.5 flex items-center gap-1.5 text-[10px] text-muted">
                        <Icon className="h-3 w-3" />
                        <span className="uppercase">{sourceTypeBadge(rc.card) ?? rc.card.source_type}</span>
                        {"quality_level" in rc.card && rc.card.quality_level ? (
                          <span className={`ml-auto h-1.5 w-1.5 rounded-full ${
                            rc.card.quality_level === "high" ? "bg-safe" :
                            rc.card.quality_level === "medium" ? "bg-amber-500" :
                            "bg-red-500"
                          }`} title={`${rc.card.quality_level} (${(rc.card as LibraryCardResponse & { quality_score?: number }).quality_score})`} />
                        ) : (
                          <span className={`ml-auto h-1.5 w-1.5 rounded-full ${rc.card.status === "human_approved" ? "bg-safe" : "bg-warn"}`} />
                        )}
                      </div>
                      {rc.reasons.length > 0 && (
                        <p className="mt-1.5 text-[10px] text-muted leading-relaxed">
                          {rc.reasons.map((r) => r.label).join(" · ")}
                        </p>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
