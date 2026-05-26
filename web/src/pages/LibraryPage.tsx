import { useEffect, useMemo, useState } from "react";
import { Download, SlidersHorizontal, X } from "lucide-react";
import { getLibraryCardDetail, saveLibraryCardBody } from "../api/library";
import { moveLibraryCardToTrash } from "../api/trash";
import type { LibraryCardDetailResponse, LibraryCardsResponse } from "../api/types";
import { CardWorkspace } from "../components/CardWorkspace";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { GraphExplorer } from "../components/GraphExplorer";
import { HealthStatusBar } from "../components/HealthStatusBar";
import { ImportCardForm } from "../components/ImportCardForm";
import { FolderImportForm } from "../components/FolderImportForm";
import { KnowledgeCommunityPanel } from "../components/KnowledgeCommunityPanel";
import { StatusCard } from "../components/StatusCard";
import { friendlyStatus, friendlyTrack } from "../lib/utils";
import { useLocale } from "../lib/i18n";

const sourceTypeAccent: Record<string, string> = {
  plain_markdown: "border-t-slate-400",
  txt: "border-t-gray-400",
  html: "border-t-orange-400",
  pdf: "border-t-red-400",
  docx: "border-t-blue-400",
  cubox_markdown: "border-t-purple-400",
};

const sourceTypeLabels: Record<string, string> = {
  plain_markdown: "Markdown",
  txt: "Text",
  html: "HTML",
  pdf: "PDF",
  docx: "Word",
  cubox_markdown: "Cubox",
};

function formatDate(dateStr: string | null | undefined, locale: string): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr.slice(0, 10);
  return d.toLocaleDateString(locale === "zh" ? "zh-CN" : "en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function sourceTypeBadge(sourceType: string | null | undefined): string {
  if (!sourceType) return "";
  return sourceTypeLabels[sourceType] ?? sourceType;
}

export function LibraryPage({ data, onRefresh }: { data: LibraryCardsResponse; onRefresh?: () => void }) {
  const searchParams = new URLSearchParams(window.location.search);
  const initialRef = searchParams.get("card") ?? data.cards[0]?.id ?? data.cards[0]?.rel_path;
  const filterCardsParam = searchParams.get("cards");
  const [selected, setSelected] = useState<string | undefined>(initialRef ?? undefined);
  const [detail, setDetail] = useState<LibraryCardDetailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exportSelection, setExportSelection] = useState<Set<string>>(new Set());
  const [exporting, setExporting] = useState(false);
  const [showExportPreview, setShowExportPreview] = useState(false);
  const [exportFormat, setExportFormat] = useState<"markdown" | "json" | "opml" | "zip">("markdown");
  const { locale, t } = useLocale();

  // Support ?cards=id1,id2 filtering (from Health Page exploration links)
  const filterIds = filterCardsParam ? filterCardsParam.split(",").map((s) => s.trim()).filter(Boolean) : null;
  const cardsFromUrl = filterIds
    ? data.cards.filter((card) => {
        const ref = card.id ?? card.rel_path;
        return filterIds.includes(ref);
      })
    : data.cards;

  // Filter state — client-side library organization
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [trackFilter, setTrackFilter] = useState<string>("all");
  const [sourceTypeFilter, setSourceTypeFilter] = useState<string>("all");
  const [qualityFilter, setQualityFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<string>("newest");

  const uniqueTracks = useMemo(() => [...new Set(cardsFromUrl.map((c) => c.track).filter(Boolean))].sort(), [cardsFromUrl]);
  const uniqueSourceTypes = useMemo(() => [...new Set(cardsFromUrl.map((c) => c.source_type).filter(Boolean))].sort(), [cardsFromUrl]);
  const uniqueQualities = useMemo(() => [...new Set(cardsFromUrl.map((c) => c.quality_level).filter(Boolean))].sort(), [cardsFromUrl]);

  const displayedCards = useMemo(() => {
    let filtered = cardsFromUrl;
    if (statusFilter !== "all") filtered = filtered.filter((c) => c.status === statusFilter);
    if (trackFilter !== "all") filtered = filtered.filter((c) => c.track === trackFilter);
    if (sourceTypeFilter !== "all") filtered = filtered.filter((c) => c.source_type === sourceTypeFilter);
    if (qualityFilter !== "all") filtered = filtered.filter((c) => c.quality_level === qualityFilter);

    const sorted = [...filtered];
    switch (sortBy) {
      case "oldest":
        sorted.sort((a, b) => (a.created_at ?? "").localeCompare(b.created_at ?? ""));
        break;
      case "title":
        sorted.sort((a, b) => (a.title ?? "").localeCompare(b.title ?? ""));
        break;
      case "score":
        sorted.sort((a, b) => (b.quality_score ?? 0) - (a.quality_score ?? 0));
        break;
      case "newest":
      default:
        sorted.sort((a, b) => (b.created_at ?? "").localeCompare(a.created_at ?? ""));
        break;
    }
    return sorted;
  }, [cardsFromUrl, statusFilter, trackFilter, sourceTypeFilter, qualityFilter, sortBy]);

  const activeFilterCount = [statusFilter, trackFilter, sourceTypeFilter, qualityFilter].filter((v) => v !== "all").length;

  function clearAllFilters() {
    setStatusFilter("all");
    setTrackFilter("all");
    setSourceTypeFilter("all");
    setQualityFilter("all");
  }

  useEffect(() => {
    if (!selected) return;
    setError(null);
    getLibraryCardDetail(selected)
      .then(setDetail)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Card failed to load"));
  }, [selected]);

  function selectCard(ref: string) {
    setSelected(ref);
    setDetail(null);
    const url = new URL(window.location.href);
    url.searchParams.set("card", ref);
    window.history.pushState({}, "", url.toString());
  }

  function deselectCard() {
    setSelected(undefined);
    setDetail(null);
    const url = new URL(window.location.href);
    url.searchParams.delete("card");
    window.history.pushState({}, "", url.toString());
  }

  async function refreshSelected() {
    if (!selected) return;
    setDetail(await getLibraryCardDetail(selected));
  }

  async function handleMoveToTrash() {
    if (!selected) return;
    try {
      await moveLibraryCardToTrash(selected);
      setDetail(null);
      setSelected(undefined);
      onRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Move to trash failed");
    }
  }

  function clearFilter() {
    const url = new URL(window.location.href);
    url.searchParams.delete("cards");
    window.history.pushState({}, "", url.toString());
    window.dispatchEvent(new PopStateEvent("popstate"));
  }

  function toggleExportSelect(cardRef: string) {
    setExportSelection((prev) => {
      const next = new Set(prev);
      if (next.has(cardRef)) next.delete(cardRef);
      else next.add(cardRef);
      return next;
    });
  }

  function selectAllForExport() {
    setExportSelection(new Set(displayedCards.map((c) => c.id ?? c.rel_path)));
  }

  function deselectAllForExport() {
    setExportSelection(new Set());
  }

  function startExport() {
    if (exportSelection.size === 0) return;
    setError(null);
    setShowExportPreview(true);
  }

  async function confirmExport() {
    setExporting(true);
    setShowExportPreview(false);
    const fmt = exportFormat;
    try {
      if (fmt === "zip") {
        // v2.4 U6: zip 格式使用 streaming download endpoint
        const resp = await fetch("/api/knowledge/export/download", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ card_ids: Array.from(exportSelection), format: "zip" }),
        });
        if (!resp.ok) throw new Error("Export failed");
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `mindforge-export-${new Date().toISOString().slice(0, 10)}.zip`;
        a.click();
        URL.revokeObjectURL(url);
      } else {
        const resp = await fetch("/api/knowledge/export", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ card_ids: Array.from(exportSelection), format: fmt }),
        });
        if (!resp.ok) throw new Error("Export failed");
        const data = await resp.json();
        const content = fmt === "json" ? data.json : fmt === "opml" ? data.opml : data.markdown;
        const mimeType = fmt === "json" ? "application/json" : fmt === "opml" ? "text/xml" : "text/markdown";
        const ext = fmt === "json" ? ".json" : fmt === "opml" ? ".opml" : ".md";
        const blob = new Blob([content], { type: `${mimeType};charset=utf-8` });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `mindforge-export-${new Date().toISOString().slice(0, 10)}${ext}`;
        a.click();
        URL.revokeObjectURL(url);
      }
      setExportSelection(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setExporting(false);
    }
  }

  function cancelExport() {
    setShowExportPreview(false);
  }

  if (data.cards.length === 0) {
    return (
      <div className="space-y-6">
        <header className="page-header">
          <h1>{t("library.title")}</h1>
          <p>{t("library.subtitle")}</p>
        </header>
        <EmptyState
          title={t("library.empty_title")}
          action={{
            label: t("library.empty_label"),
            description: t("library.empty_desc"),
            href: "/drafts",
          }}
          locale={locale}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="page-header flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1>{t("library.title")}</h1>
          <p>{t("library.subtitle")}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {filterIds ? (
            <button
              type="button"
              className="inline-flex items-center gap-1.5 rounded-md border border-line bg-white px-3 py-1.5 text-sm text-muted hover:text-ink"
              onClick={clearFilter}
            >
              <X className="h-4 w-4" /> Clear filter ({displayedCards.length}/{data.cards.length})
            </button>
          ) : null}
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-md border border-line px-2 py-1 text-xs text-muted hover:text-ink"
            onClick={exportSelection.size === displayedCards.length ? deselectAllForExport : selectAllForExport}
          >
            {exportSelection.size === displayedCards.length ? t("library.deselect_all") : t("library.select_all")}
          </button>
          <ImportCardForm onImported={onRefresh ? () => onRefresh() : () => {}} />
          <FolderImportForm onImported={onRefresh ? () => onRefresh() : () => {}} />
          <button
            type="button"
            className="inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
            style={{ background: "var(--mf-accent)" }}
            disabled={exportSelection.size === 0 || exporting}
            onClick={startExport}
          >
            <Download className="h-4 w-4" />
            {exporting ? "..." : t("library.export_selected")}{exportSelection.size > 0 ? ` (${exportSelection.size})` : ""}
          </button>
        </div>
      </header>

      {/* Export Preview (v1.4 W7: Safe Export Review) */}
      {showExportPreview ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50/30 p-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-ink">{t("library.export_preview_title")}</h3>
              <p className="mt-1 text-xs text-muted">
                {t("library.export_preview_desc").replace("{count}", String(exportSelection.size)).replace("{format}", exportFormat === "zip" ? "ZIP" : exportFormat === "json" ? "JSON" : exportFormat === "opml" ? "OPML" : "Markdown")}
              </p>
              {/* Format selector */}
              <div className="mt-2 flex items-center gap-1.5">
                <span className="text-[11px] text-muted">{t("library.export_format")}:</span>
                {(["markdown", "json", "opml", "zip"] as const).map((f) => (
                  <button
                    key={f}
                    type="button"
                    className={`rounded px-2 py-0.5 text-[11px] font-medium transition ${
                      exportFormat === f
                        ? "bg-primary text-white"
                        : "bg-white border border-line text-muted hover:text-ink"
                    }`}
                    onClick={() => setExportFormat(f)}
                    title={
                      f === "markdown" ? t("library.export_format_md_desc") :
                      f === "json" ? t("library.export_format_json_desc") :
                      f === "opml" ? t("library.export_format_opml_desc") :
                      t("library.export_format_zip_desc")
                    }
                  >
                    {f === "markdown" ? "Markdown" : f === "zip" ? "ZIP" : f.toUpperCase()}
                  </button>
                ))}
              </div>
              <p className="mt-1 text-[11px] text-muted">
                {exportFormat === "markdown" ? t("library.export_format_md_desc") :
                 exportFormat === "json" ? t("library.export_format_json_desc") :
                 exportFormat === "opml" ? t("library.export_format_opml_desc") :
                 t("library.export_format_zip_desc")}
              </p>
              {/* v4.4 A3: Export safety note */}
              <p className="mt-2 text-[11px] text-muted italic border-t border-line/50 pt-2">
                {t("library.export_safety_note")}
              </p>
              <div className="mt-3 max-h-48 overflow-y-auto">
                <div className="grid gap-1 sm:grid-cols-2">
                  {Array.from(exportSelection).map((ref) => {
                    const card = displayedCards.find((c) => (c.id ?? c.rel_path) === ref);
                    return (
                      <span key={ref} className="text-xs text-ink/80 px-2 py-1 rounded bg-white/50 border border-line/50 truncate" title={card?.title ?? ref}>
                        {card?.title ?? ref}
                      </span>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
          <div className="mt-4 flex items-center gap-2">
            <button
              type="button"
              className="inline-flex items-center gap-1.5 rounded-md px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              style={{ background: "var(--mf-accent)" }}
              disabled={exporting}
              onClick={confirmExport}
            >
              <Download className="h-4 w-4" />
              {exporting ? "..." : t("library.export_confirm")}
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-1.5 rounded-md border border-line px-3 py-2 text-sm font-medium text-ink hover:bg-muted/10"
              onClick={cancelExport}
              disabled={exporting}
            >
              <X className="h-4 w-4" /> {t("card.cancel")}
            </button>
          </div>
        </div>
      ) : null}

      {filterIds && displayedCards.length === 0 ? (
        <p className="py-6 text-center text-sm text-muted">None of the affected cards were found in this vault. They may have been deleted or are no longer approved.</p>
      ) : null}

      {/* Filter Bar — track / source_type / quality / status with sort */}
      <div className="flex flex-wrap items-center gap-2 rounded-md border border-line bg-panel p-3">
        <SlidersHorizontal className="h-4 w-4 text-muted shrink-0" />
        {/* Status filter */}
        <select className="rounded border border-line bg-white px-2 py-1 text-xs text-ink" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} aria-label={t("library.filter_status")}>
          <option value="all">{t("library.filter_status")}: {t("library.filter_all")}</option>
          <option value="ai_draft">{t("approval.status_ai_draft")}</option>
          <option value="human_approved">{t("approval.status_human_approved")}</option>
        </select>
        {/* Track filter — only shown when tracks exist */}
        {uniqueTracks.length > 0 ? (
          <select className="rounded border border-line bg-white px-2 py-1 text-xs text-ink" value={trackFilter} onChange={(e) => setTrackFilter(e.target.value)} aria-label={t("library.filter_track")}>
            <option value="all">{t("library.filter_track")}: {t("library.filter_all")}</option>
            {uniqueTracks.map((tr) => (
              <option key={tr} value={tr ?? ""}>{friendlyTrack(tr, locale)}</option>
            ))}
          </select>
        ) : null}
        {/* Source type filter — only shown when types exist */}
        {uniqueSourceTypes.length > 0 ? (
          <select className="rounded border border-line bg-white px-2 py-1 text-xs text-ink" value={sourceTypeFilter} onChange={(e) => setSourceTypeFilter(e.target.value)} aria-label={t("library.filter_source_type")}>
            <option value="all">{t("library.filter_source_type")}: {t("library.filter_all")}</option>
            {uniqueSourceTypes.map((st) => (
              <option key={st} value={st ?? ""}>{sourceTypeBadge(st)}</option>
            ))}
          </select>
        ) : null}
        {/* Quality filter — only shown when qualities exist */}
        {uniqueQualities.length > 0 ? (
          <select className="rounded border border-line bg-white px-2 py-1 text-xs text-ink" value={qualityFilter} onChange={(e) => setQualityFilter(e.target.value)} aria-label={t("library.filter_quality")}>
            <option value="all">{t("library.filter_quality")}: {t("library.filter_all")}</option>
            {uniqueQualities.map((q) => (
              <option key={q} value={q ?? ""}>{q}</option>
            ))}
          </select>
        ) : null}
        {/* Sort */}
        <select className="rounded border border-line bg-white px-2 py-1 text-xs text-ink" value={sortBy} onChange={(e) => setSortBy(e.target.value)} aria-label={t("library.sort_label")}>
          <option value="newest">{t("library.sort_newest")}</option>
          <option value="oldest">{t("library.sort_oldest")}</option>
          <option value="title">{t("library.sort_title")}</option>
          <option value="score">{t("library.sort_score")}</option>
        </select>
        {/* Active filter badge + clear */}
        {activeFilterCount > 0 ? (
          <>
            <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium text-[var(--mf-accent)]" style={{ background: "var(--mf-accent)15" }}>
              {t("library.filter_active").replace("{count}", String(activeFilterCount))}
            </span>
            <button type="button" className="text-xs text-muted hover:text-ink" onClick={clearAllFilters}>
              {t("library.filter_clear")}
            </button>
          </>
        ) : null}
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <StatusCard label={t("library.stats_approved")} value={data.stats.by_status.human_approved ?? 0} status={(data.stats.by_status.human_approved ?? 0) > 0 ? "ok" : "info"} detail={t("library.stats_approved_detail")} locale={locale} />
        <StatusCard label={t("library.stats_drafts")} value={data.stats.by_status.ai_draft ?? 0} status={(data.stats.by_status.ai_draft ?? 0) > 0 ? "warn" : "ok"} detail={t("library.stats_drafts_detail")} locale={locale} />
        <StatusCard label={t("library.stats_index")} value={data.stats.index_exists ? t("library.stats_index_ready") : t("library.stats_index_rebuild")} status={data.stats.index_exists ? "ok" : "warn"} detail={data.stats.next_action} locale={locale} />
        <StatusCard label={t("library.stats_total")} value={data.stats.total_cards} status={data.stats.total_cards > 0 ? "ok" : "info"} detail={t("library.stats_total_detail")} locale={locale} />
      </div>

      {/* Health Status Bar */}
      <HealthStatusBar />

      {/* Graph Explorer */}
      <GraphExplorer onSelectCard={selectCard} />

      {/* Knowledge Community Browser */}
      <details className="border border-line rounded-md bg-panel" open={false}>
        <summary className="px-5 py-3 cursor-pointer select-none text-sm font-medium text-ink hover:text-primary">
          {t("community.title")}
        </summary>
        <KnowledgeCommunityPanel />
      </details>

      {/* Card Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
        {displayedCards.map((card) => {
          const ref = card.id ?? card.rel_path;
          const isSelected = selected === ref;
          const accent = sourceTypeAccent[card.source_type ?? ""] ?? "border-t-neutral-300";
          return (
            <button
              className={`w-full p-5 text-left transition ${
                isSelected ? "ring-2" : ""
              }`}
              style={{
                background: "var(--mf-surface)",
                boxShadow: isSelected ? "var(--mf-shadow-card), 0 0 0 2px var(--mf-accent)" : "var(--mf-shadow-card)",
                borderRadius: "var(--mf-radius-lg)",
                border: "1px solid var(--mf-border)",
                borderTop: `4px solid ${card.source_type === "pdf" ? "var(--mf-error)" : card.source_type === "html" ? "var(--mf-warning)" : card.source_type === "docx" ? "#3b82f6" : "var(--mf-text-tertiary)"}`,
              }}
              key={card.rel_path}
              onClick={() => selectCard(ref)}
              type="button"
            >
              <div className="flex items-start justify-between gap-2">
                <h3
                  className="font-medium leading-snug line-clamp-2"
                  style={{
                    fontFamily: "var(--mf-font-serif)",
                    fontSize: "var(--mf-text-h2)",
                    lineHeight: 1.25,
                  }}
                >
                  {card.title ?? t("card.untitled")}
                </h3>
                <input
                  type="checkbox"
                  className="mt-0.5 h-4 w-4 rounded border-line accent-primary"
                  checked={exportSelection.has(ref)}
                  onChange={(e) => {
                    e.stopPropagation();
                    toggleExportSelect(ref);
                  }}
                  onClick={(e) => e.stopPropagation()}
                />
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium ${card.status === "human_approved" ? "bg-safe/10 text-safe" : "bg-warn/10 text-warn"}`}>
                  {friendlyStatus(card.status, locale)}
                </span>
                {card.source_type ? (
                  <span className="inline-flex items-center rounded bg-muted/20 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide">{sourceTypeBadge(card.source_type)}</span>
                ) : null}
                {card.track ? <span className="text-muted">{friendlyTrack(card.track, locale)}</span> : null}
              </div>
              <p className="mt-2 text-xs text-muted line-clamp-1">{card.source_title ?? card.source_path_view?.display_path}</p>
              {card.updated_at ? (
                <p className="mt-2 text-[11px] text-muted">{t("library.updated_at").replace("{date}", formatDate(card.updated_at, locale))}</p>
              ) : null}
            </button>
          );
        })}
      </div>

      {/* Selected Card Detail */}
      {selected ? (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <button
              className="inline-flex items-center gap-1.5 rounded-md border border-line px-3 py-1.5 text-sm font-medium text-ink hover:bg-muted/10"
              onClick={deselectCard}
              type="button"
            >
              <X className="h-4 w-4" /> {t("shared.close")}
            </button>
            <span className="text-sm text-muted">{detail?.card.title ?? ""}</span>
          </div>
          {error ? <ErrorState message={error} /> : null}
          {!error && detail ? (
            <CardWorkspace
              detail={detail}
              mode="library"
              onSave={(body) => saveLibraryCardBody(selected ?? detail.card.id ?? detail.card.rel_path, body)}
              onSaved={refreshSelected}
              onMoveToTrash={handleMoveToTrash}
              onSelectCard={selectCard}
            />
          ) : null}
        </div>
      ) : (
        <p className="py-8 text-center text-sm text-muted">{t("library.select_to_view")}</p>
      )}
    </div>
  );
}
