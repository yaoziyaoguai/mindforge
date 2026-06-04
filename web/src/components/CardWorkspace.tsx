import { useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronUp, Clipboard, Edit3, File, FileCode, FileEdit, FileText, FileType, FolderOpen, Link, Save, Trash2, X } from "lucide-react";
import { revealSourceByRef } from "../api/sources";
import { getProvenanceTrail, linkCards } from "../api/library";
import { ApprovalTimeline } from "./ApprovalTimeline";
import { GraphNavigationPanel } from "./GraphNavigationPanel";
import { ProvenanceTrail } from "./ProvenanceTrail";
import { SourceLocationBadge } from "./provenance/SourceLocationBadge";
import type { CardBodyUpdateResponse, DraftDetailResponse, LibraryCardDetailResponse, LibraryCardResponse, ProvenanceTrailResponse } from "../api/types";
import { friendlyStatus, friendlyTrack, statusIcon, truncateMiddle } from "../lib/utils";
import { useLocale, type Locale } from "../lib/i18n";

const sourceTypeLabels: Record<string, string> = {
  plain_markdown: "Markdown",
  txt: "Text",
  html: "HTML",
  pdf: "PDF",
  docx: "Word",
  cubox_markdown: "Cubox",
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
  cubox_markdown: FileText,
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
                <span
                  className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium"
                  style={{
                    background: card.quality_level === "high" ? "rgba(45,125,95,0.1)" :
                      card.quality_level === "medium" ? "rgba(204,122,0,0.1)" :
                      "rgba(192,64,64,0.1)",
                    color: card.quality_level === "high" ? "var(--mf-approved)" :
                      card.quality_level === "medium" ? "var(--mf-warning)" :
                      "var(--mf-error)",
                  }}
                  title={`${t("card.quality_score")}: ${card.quality_score}`}
                >
                  {qualityLevelLabel(card.quality_level ?? "", t)} {card.quality_score}
                </span>
              ) : null}
              {card.track ? <span className="rounded bg-muted/20 px-1 py-0.5 text-[11px]">{friendlyTrack(card.track, locale)}</span> : null}
              {card.strategy_label ? <span>{card.strategy_label}</span> : null}
              {mode === "library" && "approved_at" in card && card.approved_at ? <span>{card.approved_at.slice(0, 10)}</span> : null}
              {sourceLabel(card) ? <span>{sourceLabel(card)}</span> : null}
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
                className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium transition-colors hover:opacity-80"
                style={{ borderColor: "var(--mf-error)", color: "var(--mf-error)" }}
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
          <p
            className="mt-4 rounded-md border px-3 py-2 text-sm"
            style={{
              borderColor: "rgba(204,122,0,0.2)",
              background: "rgba(204,122,0,0.06)",
              color: "var(--mf-warning)",
            }}
          >
            {t("card.draft_warning")}
          </p>
        ) : null}
        {card.strategy_note ? <p className="mt-3 text-sm text-muted">{card.strategy_note}</p> : null}
      </header>

      {/* Layer 1: KnowledgeHero — what this knowledge is */}
      {mode === "library" ? (
        <KnowledgeHero
          body={body}
          sections={sections}
          card={card}
          t={t}
          locale={locale}
        />
      ) : null}

      {/* Layer 2: KnowledgeSections — structured content, grouped & collapsible */}
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
          <KnowledgeSections body={body} sections={sections} t={t} />
        )}
      </section>

      {/* Layer 3: Related Knowledge — merged graph + related cards */}
      {mode === "library" && (card.id || card.rel_path) ? (
        <section className="border-t border-line p-5">
          <div className="flex items-center gap-2.5 mb-4">
            <span className="flex items-center justify-center w-8 h-8 rounded-md bg-primary/10 text-primary">
              <Link className="h-4 w-4" />
            </span>
            <div>
              <h3 className="text-sm font-semibold text-ink">{t("card.related_knowledge")}</h3>
              <p className="text-xs text-muted mt-0.5">{t("card.related_knowledge_desc")}</p>
            </div>
          </div>
          <GraphNavigationPanel
            cardRef={card.id ?? card.rel_path ?? ""}
            onSelectCard={onSelectCard}
          />
          {"related_cards" in detail ? (
            <div className="mt-4">
              <RelatedCardsPanel
                relatedCards={detail.related_cards}
                onSelectCard={onSelectCard}
                t={t}
                currentCardRef={card.id ?? card.rel_path ?? ""}
              />
            </div>
          ) : null}
        </section>
      ) : null}

      {mode === "library" && trail ? (
        <ProvenanceTrail trail={trail} onSelectCard={onSelectCard} />
      ) : null}

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

/** Layer 2: 结构化内容 — 分组折叠，分为"理解内容"和"处理过程" */
function KnowledgeSections({ body, sections, t }: {
  body: string;
  sections: Array<{ title: string; content: string }>;
  t: (key: string) => string;
}) {
  const [expandUnderstanding, setExpandUnderstanding] = useState(false);
  const [expandProcessing, setExpandProcessing] = useState(false);

  if (!body.trim()) return <p className="mt-4 text-sm text-muted">No card body.</p>;
  if (!sections.length) {
    return <pre className="mt-4 whitespace-pre-wrap rounded-md bg-stone-50 p-4 text-sm leading-7 text-ink">{body}</pre>;
  }

  // 分组规则：匹配 AI Summary / Human Note / Key Points 等归为"理解内容"
  const understandingPatterns = /^(AI\s*Summary|Human\s*Note|Key\s*Points|Summary|核心要点|人工备注|摘要|要点|关键点|笔记)\s*$/i;

  const understandingSections = sections.filter((s) => understandingPatterns.test(s.title));
  const processingSections = sections.filter((s) => !understandingPatterns.test(s.title));

  return (
    <div className="mt-4 space-y-4">
      {/* 理解内容组 */}
      {understandingSections.length > 0 ? (
        <div className="rounded-md border border-line bg-white overflow-hidden">
          <button
            type="button"
            className="flex w-full items-center justify-between px-4 py-3 text-sm font-semibold text-ink hover:bg-stone-50/50 transition"
            onClick={() => setExpandUnderstanding((v) => !v)}
          >
            <span className="flex items-center gap-2">
              {expandUnderstanding ? <ChevronUp className="h-4 w-4 text-muted" /> : <ChevronDown className="h-4 w-4 text-muted" />}
              {t("card.understanding_sections")}
              <span className="font-normal text-muted/60 text-xs">({understandingSections.length})</span>
            </span>
          </button>
          {expandUnderstanding ? (
            <div className="border-t border-line px-4 py-3 space-y-4">
              {understandingSections.map((section) => (
                <div key={section.title}>
                  <h4 className="text-sm font-semibold text-ink mb-1">{section.title}</h4>
                  <div className="whitespace-pre-wrap text-sm leading-7 text-ink">{section.content || "-"}</div>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      {/* 处理过程组 */}
      {processingSections.length > 0 ? (
        <div className="rounded-md border border-line bg-white overflow-hidden">
          <button
            type="button"
            className="flex w-full items-center justify-between px-4 py-3 text-sm font-semibold text-ink hover:bg-stone-50/50 transition"
            onClick={() => setExpandProcessing((v) => !v)}
          >
            <span className="flex items-center gap-2">
              {expandProcessing ? <ChevronUp className="h-4 w-4 text-muted" /> : <ChevronDown className="h-4 w-4 text-muted" />}
              {t("card.processing_sections")}
              <span className="font-normal text-muted/60 text-xs">({processingSections.length})</span>
            </span>
          </button>
          {expandProcessing ? (
            <div className="border-t border-line px-4 py-3 space-y-4">
              {processingSections.map((section) => (
                <div key={section.title}>
                  <h4 className="text-sm font-semibold text-ink mb-1">{section.title}</h4>
                  <div className="whitespace-pre-wrap text-sm leading-7 text-ink">{section.content || "-"}</div>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
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

/** Layer 1: 默认阅读层 — 用户第一眼看到的知识概览 */
function KnowledgeHero({ body, sections, card, t, locale }: {
  body: string;
  sections: Array<{ title: string; content: string }>;
  card: Pick<LibraryCardResponse, "track" | "strategy_label" | "source_title" | "source_type"> & { tags?: string[] };
  t: (key: string) => string;
  locale: Locale;
}) {
  // 一句话摘要：取 body 前 150 字符，stripped markdown
  const summary = useMemo(() => {
    const stripped = stripMarkdown(body);
    return stripped ? stripped.slice(0, 150) + (stripped.length > 150 ? "..." : "") : null;
  }, [body]);

  // 核心要点：从 ## Key Points / 核心要点 section 提取
  const keyPointsContent = useMemo(() => {
    const kpSection = sections.find((s) =>
      /^(Key Points|核心要点|要点|关键点)\s*$/i.test(s.title),
    );
    if (kpSection?.content) return kpSection.content;
    return null;
  }, [sections]);

  // 人工备注
  const humanNote = useMemo(() => {
    const hnSection = sections.find((s) =>
      /^(Human Note|人工备注|备注|笔记)\s*$/i.test(s.title),
    );
    if (hnSection?.content) return hnSection.content;
    return null;
  }, [sections]);

  const { tags } = card;

  return (
    <div className="border-b border-line p-5 space-y-4">
      {/* 一句话摘要 */}
      {summary ? (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted mb-1.5">{t("card.one_sentence_summary")}</h4>
          <p className="text-sm text-ink leading-relaxed">{summary}</p>
        </div>
      ) : (
        <p className="text-sm text-muted">{t("card.no_summary")}</p>
      )}

      {/* 核心要点 */}
      {keyPointsContent ? (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted mb-1.5">{t("card.key_points")}</h4>
          <div className="rounded-md bg-stone-50 border border-line p-3">
            <div className="text-sm text-ink leading-relaxed whitespace-pre-wrap">{keyPointsContent}</div>
          </div>
        </div>
      ) : null}

      {/* 标签 */}
      {tags && tags.length > 0 ? (
        <div className="flex flex-wrap items-center gap-1.5">
          {tags.map((tag) => (
            <span key={tag} className="inline-flex items-center rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">
              #{tag}
            </span>
          ))}
        </div>
      ) : null}

      {/* 元信息行 */}
      <div className="flex flex-wrap items-center gap-3 text-xs text-muted">
        {card.source_title ? (
          <span className="inline-flex items-center gap-1">
            <FolderOpen className="h-3 w-3" />
            {card.source_title}
          </span>
        ) : null}
        {card.track ? (
          <span className="rounded bg-muted/20 px-1.5 py-0.5">{friendlyTrack(card.track, locale)}</span>
        ) : null}
        {card.strategy_label ? (
          <span className="rounded bg-muted/20 px-1.5 py-0.5">{card.strategy_label}</span>
        ) : null}
        {card.source_type ? (
          <span className="inline-flex items-center rounded bg-muted/20 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide">
            {sourceTypeLabels[card.source_type] ?? card.source_type}
          </span>
        ) : null}
      </div>

      {/* 人工备注预览 */}
      {humanNote ? (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted mb-1.5">{t("card.human_note_preview")}</h4>
          <div className="rounded-md border border-amber-200 bg-amber-50/50 p-3">
            <div className="text-sm text-ink leading-relaxed whitespace-pre-wrap line-clamp-3">{humanNote}</div>
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

function RelatedCardsPanel({ relatedCards, onSelectCard, t, currentCardRef }: {
  relatedCards: Array<{ card: LibraryCardResponse; reasons: Array<{ reason: string; label: string; detail: string; strength: number }> }>;
  onSelectCard?: (ref: string) => void;
  t: (key: string) => string;
  currentCardRef?: string;
}) {
  const [showLinkForm, setShowLinkForm] = useState(false);
  const [linkTarget, setLinkTarget] = useState("");
  const [linkReason, setLinkReason] = useState("see_also");
  const [linking, setLinking] = useState(false);
  const [linkMsg, setLinkMsg] = useState("");

  async function handleLink() {
    if (!linkTarget.trim() || !currentCardRef) return;
    setLinking(true);
    setLinkMsg("");
    try {
      const r = await linkCards({ card1_ref: currentCardRef, card2_ref: linkTarget.trim(), reason: linkReason });
      setLinkMsg(r.ok ? t("card.link_success") : r.message);
      if (r.ok) {
        setLinkTarget("");
        setShowLinkForm(false);
      }
    } catch (e) {
      setLinkMsg(String(e));
    } finally {
      setLinking(false);
    }
  }

  if (relatedCards.length === 0 && !showLinkForm) {
    return (
      <section className="border-t border-line p-5">
        <h3 className="text-sm font-semibold text-ink">{t("library.related_cards")}</h3>
        <p className="mt-3 text-sm text-muted leading-relaxed">{t("library.related_empty_guide")}</p>
        <button
          type="button"
          className="mt-3 inline-flex items-center gap-1.5 rounded border border-line bg-white px-2 py-1 text-xs text-ink hover:bg-muted/10"
          onClick={() => setShowLinkForm(true)}
        >
          <Link className="h-3 w-3" /> {t("card.link_card")}
        </button>
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

      {/* Manual link button + form */}
      {!showLinkForm ? (
        <button
          type="button"
          className="mt-3 inline-flex items-center gap-1.5 rounded border border-line bg-white px-2 py-1 text-xs text-ink hover:bg-muted/10"
          onClick={() => setShowLinkForm(true)}
        >
          <Link className="h-3 w-3" /> {t("card.link_card")}
        </button>
      ) : (
        <div className="mt-3 space-y-2 rounded-md border border-dashed border-line p-3">
          <div className="flex items-center gap-2">
            <input
              type="text"
              className="flex-1 rounded border border-line px-2 py-1 text-xs text-ink placeholder:text-muted"
              placeholder={t("card.link_target_placeholder")}
              value={linkTarget}
              onChange={(e) => setLinkTarget(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleLink(); if (e.key === "Escape") setShowLinkForm(false); }}
              autoFocus
            />
            <select
              className="rounded border border-line bg-white px-2 py-1 text-xs text-ink"
              value={linkReason}
              onChange={(e) => setLinkReason(e.target.value)}
            >
              <option value="see_also">See Also</option>
              <option value="related">Related</option>
              <option value="cites">Cites</option>
              <option value="extends">Extends</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="rounded px-2 py-1 text-xs font-medium text-white disabled:opacity-50 inline-flex items-center gap-1"
              style={{ background: "var(--mf-accent)" }}
              disabled={!linkTarget.trim() || linking}
              onClick={handleLink}
            >
              <Link className="h-3 w-3" />
              {linking ? "..." : t("card.link_apply")}
            </button>
            <button
              type="button"
              className="rounded border border-line px-2 py-1 text-xs text-muted hover:text-ink"
              onClick={() => { setShowLinkForm(false); setLinkMsg(""); }}
            >
              <X className="h-3 w-3" />
            </button>
          </div>
          {linkMsg ? <p className={`text-[11px] ${linkMsg === t("card.link_success") ? "text-green-600" : "text-red-500"}`}>{linkMsg}</p> : null}
        </div>
      )}
    </section>
  );
}
