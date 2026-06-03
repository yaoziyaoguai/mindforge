/**
 * LibraryPage — 知识库 / Knowledge Base
 *
 * 中文学习型说明：
 * 此页面仅展示 human_approved 知识，不混入 ai_draft。
 * 参考图 image5 风格：table 列表 + 右侧详情面板，filter tabs。
 * Graph Explorer 和 Community Panel 是 lab/internal 功能，
 * 不在主路径上展示，避免让用户误以为图谱/社区是核心产品能力。
 * 保护产品边界：Library = 已确认知识，不是草稿暂存区。
 */

import { useEffect, useMemo, useState } from "react";
import { Download, Pencil, Search, SlidersHorizontal, Star, X } from "lucide-react";
import { getLibraryCardDetail, saveLibraryCardBody } from "../api/library";
import { moveLibraryCardToTrash } from "../api/trash";
import type { LibraryCardDetailResponse, LibraryCardsResponse } from "../api/types";
import { BulkActions } from "../components/BulkActions";
import { CardWorkspace } from "../components/CardWorkspace";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { ImportCardForm } from "../components/ImportCardForm";
import { FolderImportForm } from "../components/FolderImportForm";
import { ViewSwitcher } from "../components/ViewSwitcher";
import type { SavedViewResponse } from "../api/types";
import { friendlyStatus, friendlyTrack } from "../lib/utils";
import { useLocale } from "../lib/i18n";

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

/** Filter tab 类型 — 保护 Library 只表达 human_approved 知识 */
type FilterTab = "all" | "by_source" | "by_track" | "favorites" | "recent";

const filterTabs: { key: FilterTab; label: string; disabled?: boolean }[] = [
  { key: "all", label: "library.filter_all_knowledge" },
  { key: "by_source", label: "library.filter_by_source" },
  { key: "by_track", label: "library.filter_by_track" },
  { key: "favorites", label: "library.filter_favorites", disabled: true },
  { key: "recent", label: "library.filter_recent", disabled: true },
];

export function LibraryPage({ data, onRefresh }: { data: LibraryCardsResponse; onRefresh?: () => void }) {
  const searchParams = new URLSearchParams(window.location.search);
  const initialRef = searchParams.get("card") ?? data.cards[0]?.id ?? data.cards[0]?.rel_path;
  const filterCardsParam = searchParams.get("cards");
  const [selected, setSelected] = useState<string | undefined>(initialRef ?? undefined);
  const [detail, setDetail] = useState<LibraryCardDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exportSelection, setExportSelection] = useState<Set<string>>(new Set());
  const [exporting, setExporting] = useState(false);
  const [showExportPreview, setShowExportPreview] = useState(false);
  const [exportFormat, setExportFormat] = useState<"markdown" | "json" | "opml" | "zip">("markdown");
  const [bulkMode, setBulkMode] = useState(false);
  const [bulkSelectedRefs, setBulkSelectedRefs] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState("");
  const [fullView, setFullView] = useState(false);
  const { locale, t } = useLocale();

  // Support ?cards=id1,id2 filtering (from Health Page exploration links)
  const filterIds = filterCardsParam ? filterCardsParam.split(",").map((s) => s.trim()).filter(Boolean) : null;
  const cardsFromUrl = filterIds
    ? data.cards.filter((card) => {
        const ref = card.id ?? card.rel_path;
        return filterIds.includes(ref);
      })
    : data.cards;

  // Only show human_approved cards — protect the "Library = approved" boundary
  const approvedCards = useMemo(
    () => cardsFromUrl.filter((c) => c.status === "human_approved"),
    [cardsFromUrl],
  );

  // Filter tabs
  const [activeTab, setActiveTab] = useState<FilterTab>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [trackFilter, setTrackFilter] = useState<string>("all");
  const [sourceTypeFilter, setSourceTypeFilter] = useState<string>("all");
  const [qualityFilter, setQualityFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<string>("newest");

  const uniqueTracks = useMemo(() => [...new Set(approvedCards.map((c) => c.track).filter(Boolean))].sort(), [approvedCards]);
  const uniqueSourceTypes = useMemo(() => [...new Set(approvedCards.map((c) => c.source_type).filter(Boolean))].sort(), [approvedCards]);
  const uniqueQualities = useMemo(() => [...new Set(approvedCards.map((c) => c.quality_level).filter(Boolean))].sort(), [approvedCards]);

  const displayedCards = useMemo(() => {
    let filtered = approvedCards;
    if (activeTab === "favorites" || activeTab === "recent") {
      // No backend support — fallback to all
      return approvedCards;
    }
    if (statusFilter !== "all") filtered = filtered.filter((c) => c.status === statusFilter);
    if (trackFilter !== "all") filtered = filtered.filter((c) => c.track === trackFilter);
    if (sourceTypeFilter !== "all") filtered = filtered.filter((c) => c.source_type === sourceTypeFilter);
    if (qualityFilter !== "all") filtered = filtered.filter((c) => c.quality_level === qualityFilter);
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter((c) =>
        (c.title ?? "").toLowerCase().includes(q) ||
        (c.source_title ?? "").toLowerCase().includes(q) ||
        (c.track ?? "").toLowerCase().includes(q),
      );
    }

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
  }, [approvedCards, activeTab, statusFilter, trackFilter, sourceTypeFilter, qualityFilter, searchQuery, sortBy]);

  const activeFilterCount = [statusFilter, trackFilter, sourceTypeFilter, qualityFilter].filter((v) => v !== "all").length;

  function clearAllFilters() {
    setStatusFilter("all");
    setTrackFilter("all");
    setSourceTypeFilter("all");
    setQualityFilter("all");
    setSearchQuery("");
  }

  function applyView(view: SavedViewResponse) {
    setStatusFilter(view.status_filter);
    setTrackFilter(view.track_filter);
    setSourceTypeFilter(view.source_type_filter);
    setQualityFilter(view.quality_filter);
    setSortBy(view.sort_by);
  }

  useEffect(() => {
    if (!selected) return;
    setError(null);
    setDetailLoading(true);
    getLibraryCardDetail(selected)
      .then((d) => {
        setDetail(d);
        setDetailLoading(false);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Card failed to load");
        setDetailLoading(false);
      });
  }, [selected]);

  function selectCard(ref: string) {
    setSelected(ref);
    setDetailLoading(true);
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

  function enterBulkMode() {
    setBulkMode(true);
    setBulkSelectedRefs(new Set());
    setExportSelection(new Set());
  }

  function exitBulkMode() {
    setBulkMode(false);
    setBulkSelectedRefs(new Set());
  }

  function toggleBulkSelect(cardRef: string) {
    setBulkSelectedRefs((prev) => {
      const next = new Set(prev);
      if (next.has(cardRef)) next.delete(cardRef);
      else next.add(cardRef);
      return next;
    });
  }

  function selectAllForBulk() {
    setBulkSelectedRefs(new Set(displayedCards.map((c) => c.id ?? c.rel_path)));
  }

  function deselectAllForBulk() {
    setBulkSelectedRefs(new Set());
  }

  function handleBulkApplied() {
    setBulkSelectedRefs(new Set());
    onRefresh?.();
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
        const result = await resp.json();
        const content = fmt === "json" ? (result as Record<string, unknown>).json : fmt === "opml" ? (result as Record<string, unknown>).opml : (result as Record<string, unknown>).markdown;
        const mimeType = fmt === "json" ? "application/json" : fmt === "opml" ? "text/xml" : "text/markdown";
        const ext = fmt === "json" ? ".json" : fmt === "opml" ? ".opml" : ".md";
        const blob = new Blob([String(content ?? "")], { type: `${mimeType};charset=utf-8` });
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
            href: "/review",
          }}
          locale={locale}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="page-header flex flex-wrap items-start justify-between gap-3">
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
          {bulkMode ? (
            <>
              <button
                type="button"
                className="inline-flex items-center gap-1 rounded-md border border-line px-2 py-1 text-xs text-muted hover:text-ink"
                onClick={bulkSelectedRefs.size === displayedCards.length ? deselectAllForBulk : selectAllForBulk}
              >
                {bulkSelectedRefs.size === displayedCards.length ? t("bulk.deselect_all") : t("bulk.select_all")}
              </button>
              <button
                type="button"
                className="inline-flex items-center gap-1.5 rounded-md border border-line bg-white px-3 py-1.5 text-sm text-ink hover:bg-muted/10"
                onClick={exitBulkMode}
              >
                <X className="h-4 w-4" /> {t("bulk.exit")}
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                className="inline-flex items-center gap-1 rounded-md border border-line px-2 py-1 text-xs text-muted hover:text-ink"
                onClick={exportSelection.size === displayedCards.length ? deselectAllForExport : selectAllForExport}
              >
                {exportSelection.size === displayedCards.length ? t("library.deselect_all") : t("library.select_all")}
              </button>
              <button
                type="button"
                className="inline-flex items-center gap-1.5 rounded-md border border-line bg-white px-3 py-1.5 text-sm text-ink hover:bg-muted/10"
                onClick={enterBulkMode}
              >
                <Pencil className="h-4 w-4" /> {t("bulk.select_mode")}
              </button>
            </>
          )}
          <ImportCardForm onImported={onRefresh ? () => onRefresh() : () => {}} />
          <FolderImportForm onImported={onRefresh ? () => onRefresh() : () => {}} />
          <button
            type="button"
            className="inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            style={{ background: "linear-gradient(135deg, var(--mf-accent), #6f5cff)", boxShadow: "0 6px 16px rgba(91, 70, 246, 0.2)" }}
            disabled={exportSelection.size === 0 || exporting}
            onClick={startExport}
          >
            <Download className="h-4 w-4" />
            {exporting ? "..." : t("library.export_selected")}{exportSelection.size > 0 ? ` (${exportSelection.size})` : ""}
          </button>
        </div>
      </header>

      {/* Export Preview */}
      {showExportPreview ? (
        <div className="rounded-xl border border-line bg-panel p-5 shadow-subtle">
          <h3 className="text-sm font-semibold text-ink">{t("library.export_preview_title")}</h3>
          <p className="mt-1 text-xs text-muted">
            {t("library.export_preview_desc").replace("{count}", String(exportSelection.size)).replace("{format}", exportFormat === "zip" ? "ZIP" : exportFormat === "json" ? "JSON" : exportFormat === "opml" ? "OPML" : "Markdown")}
          </p>
          <div className="mt-2 flex items-center gap-1.5 flex-wrap">
            <span className="text-[11px] text-muted">{t("library.export_format")}:</span>
            {(["markdown", "json", "opml", "zip"] as const).map((f) => (
              <button
                key={f}
                type="button"
                className={`rounded-lg px-3 py-1 text-[11px] font-medium transition ${
                  exportFormat === f
                    ? "bg-[var(--mf-accent)] text-white"
                    : "border border-line text-muted hover:text-ink"
                }`}
                onClick={() => setExportFormat(f)}
              >
                {f === "markdown" ? "Markdown" : f === "zip" ? "ZIP" : f.toUpperCase()}
              </button>
            ))}
          </div>
          <p className="mt-2 text-[11px] text-muted italic border-t border-line/50 pt-2">
            {t("library.export_safety_note")}
          </p>
          <div className="mt-3 max-h-48 overflow-y-auto">
            <div className="grid gap-1 sm:grid-cols-2">
              {Array.from(exportSelection).map((ref) => {
                const card = displayedCards.find((c) => (c.id ?? c.rel_path) === ref);
                return (
                  <span key={ref} className="text-xs text-ink/80 px-2 py-1 rounded bg-muted/10 border border-line/50 truncate" title={card?.title ?? ref}>
                    {card?.title ?? ref}
                  </span>
                );
              })}
            </div>
          </div>
          <div className="mt-4 flex items-center gap-2">
            <button
              type="button"
              className="inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              style={{ background: "var(--mf-accent)" }}
              disabled={exporting}
              onClick={confirmExport}
            >
              <Download className="h-4 w-4" />
              {exporting ? "..." : t("library.export_confirm")}
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-1.5 rounded-lg border border-line px-3 py-2 text-sm font-medium text-ink hover:bg-muted/10"
              onClick={cancelExport}
              disabled={exporting}
            >
              <X className="h-4 w-4" /> {t("card.cancel")}
            </button>
          </div>
        </div>
      ) : null}

      {/* Boundary callout — 中文学习型说明：明确 Library 只包含已确认知识，不混入草稿 */}
      <section className="rounded-lg border border-stone-200/70 bg-stone-50/50 px-4 py-3">
        <p className="text-xs text-muted leading-relaxed">{t("library.boundary_callout")}</p>
      </section>

      {/* Bulk Actions */}
      <BulkActions
        selectedRefs={Array.from(bulkSelectedRefs)}
        onClearSelection={deselectAllForBulk}
        onApplied={handleBulkApplied}
      />

      {/* Stats row */}
      <div className="flex flex-wrap items-center gap-6 text-sm">
        <span className="flex items-center gap-1.5">
          <span className="rounded-full px-2 py-0.5 text-xs font-bold" style={{ background: "rgba(20,150,107,0.12)", color: "var(--mf-approved)" }}>
            {data.stats.by_status.human_approved ?? 0}
          </span>
          <span style={{ color: "var(--mf-text-secondary)" }}>{t("library.stats_approved")}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="rounded-full px-2 py-0.5 text-xs font-bold" style={{ background: "rgba(216,135,34,0.12)", color: "var(--mf-draft)" }}>
            {data.stats.by_status.ai_draft ?? 0}
          </span>
          <span style={{ color: "var(--mf-text-secondary)" }}>{t("library.stats_drafts")}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-bold" style={{ color: "var(--mf-accent)" }}>
            {data.stats.total_cards}
          </span>
          <span style={{ color: "var(--mf-text-secondary)" }}>{t("library.stats_total")}</span>
        </span>
      </div>

      {/* Filter tabs + search bar */}
      <div className="rounded-xl border border-line bg-panel p-4 shadow-subtle">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-1">
            {filterTabs.map((tab) => {
              const isActive = activeTab === tab.key && !tab.disabled;
              return (
                <button
                  key={tab.key}
                  type="button"
                  disabled={tab.disabled}
                  className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                    isActive
                      ? "bg-[var(--mf-accent)] text-white"
                      : tab.disabled
                        ? "opacity-40 cursor-not-allowed text-muted"
                        : "text-muted hover:bg-muted/10 hover:text-ink"
                  }`}
                  onClick={() => { if (!tab.disabled) setActiveTab(tab.key); }}
                >
                  {t(tab.label)}
                </button>
              );
            })}
          </div>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted" />
              <input
                type="text"
                placeholder={t("library.search_placeholder")}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="rounded-lg border border-line bg-white pl-8 pr-3 py-1.5 text-xs text-ink placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-[var(--mf-accent)]/30"
              />
            </div>
          </div>
        </div>

        {/* Advanced filter dropdowns (shown below tabs) */}
        <div className="mt-3 flex flex-wrap items-center gap-2 pt-3 border-t border-line/50">
          <SlidersHorizontal className="h-4 w-4 text-muted shrink-0" />
          <ViewSwitcher
            statusFilter={statusFilter}
            trackFilter={trackFilter}
            sourceTypeFilter={sourceTypeFilter}
            qualityFilter={qualityFilter}
            sortBy={sortBy}
            onApplyView={applyView}
          />
          <select className="rounded-md border border-line bg-white px-2 py-1 text-xs text-ink" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} aria-label={t("library.filter_status")}>
            <option value="all">{t("library.filter_status")}: {t("library.filter_all")}</option>
            <option value="human_approved">{t("approval.status_human_approved")}</option>
          </select>
          {uniqueTracks.length > 0 ? (
            <select className="rounded-md border border-line bg-white px-2 py-1 text-xs text-ink" value={trackFilter} onChange={(e) => setTrackFilter(e.target.value)} aria-label={t("library.filter_track")}>
              <option value="all">{t("library.filter_track")}: {t("library.filter_all")}</option>
              {uniqueTracks.map((tr) => (
                <option key={tr} value={tr ?? ""}>{friendlyTrack(tr, locale)}</option>
              ))}
            </select>
          ) : null}
          {uniqueSourceTypes.length > 0 ? (
            <select className="rounded-md border border-line bg-white px-2 py-1 text-xs text-ink" value={sourceTypeFilter} onChange={(e) => setSourceTypeFilter(e.target.value)} aria-label={t("library.filter_source_type")}>
              <option value="all">{t("library.filter_source_type")}: {t("library.filter_all")}</option>
              {uniqueSourceTypes.map((st) => (
                <option key={st} value={st ?? ""}>{sourceTypeLabels[st ?? ""] ?? st}</option>
              ))}
            </select>
          ) : null}
          {uniqueQualities.length > 0 ? (
            <select className="rounded-md border border-line bg-white px-2 py-1 text-xs text-ink" value={qualityFilter} onChange={(e) => setQualityFilter(e.target.value)} aria-label={t("library.filter_quality")}>
              <option value="all">{t("library.filter_quality")}: {t("library.filter_all")}</option>
              {uniqueQualities.map((q) => (
                <option key={q} value={q ?? ""}>{q}</option>
              ))}
            </select>
          ) : null}
          <select className="rounded-md border border-line bg-white px-2 py-1 text-xs text-ink" value={sortBy} onChange={(e) => setSortBy(e.target.value)} aria-label={t("library.sort_label")}>
            <option value="newest">{t("library.sort_newest")}</option>
            <option value="oldest">{t("library.sort_oldest")}</option>
            <option value="title">{t("library.sort_title")}</option>
            <option value="score">{t("library.sort_score")}</option>
          </select>
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
      </div>

      {/* Content: table + detail panel */}
      <div className="grid gap-4" style={{ gridTemplateColumns: fullView ? "1fr" : selected ? "2fr 3fr" : "1fr" }}>
        {/* Table list */}
        {!fullView && (
        <div className="rounded-xl border border-line bg-panel shadow-subtle overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line text-xs font-medium" style={{ color: "var(--mf-text-tertiary)" }}>
                <th className="px-4 py-3 text-left w-8">
                  <input
                    type="checkbox"
                    className="h-3.5 w-3.5 rounded"
                    style={{ accentColor: "var(--mf-accent)" }}
                    checked={bulkMode ? bulkSelectedRefs.size === displayedCards.length && displayedCards.length > 0 : exportSelection.size === displayedCards.length && displayedCards.length > 0}
                    onChange={(e) => {
                      if (bulkMode) {
                        e.target.checked ? selectAllForBulk() : deselectAllForBulk();
                      } else {
                        e.target.checked ? selectAllForExport() : deselectAllForExport();
                      }
                    }}
                  />
                </th>
                <th className="px-4 py-3 text-left">{t("library.col_title") ?? "Title"}</th>
                <th className="px-4 py-3 text-left">{t("library.col_source")}</th>
                <th className="px-4 py-3 text-left">{t("library.col_date")}</th>
                <th className="px-4 py-3 text-left">{t("library.col_status")}</th>
                <th className="px-4 py-3 text-left">{t("library.col_tags")}</th>
              </tr>
            </thead>
            <tbody>
              {displayedCards.map((card) => {
                const ref = card.id ?? card.rel_path;
                const isSelected = selected === ref;
                // tags come from API — cast through unknown
                const raw = card as unknown as Record<string, unknown>;
                const tags: string[] = Array.isArray(raw.tags) ? (raw.tags as string[]) : [];
                return (
                  <tr
                    key={ref}
                    className={`border-b border-line/50 cursor-pointer transition-colors ${
                      isSelected ? "bg-[var(--mf-accent)]/5" : "hover:bg-muted/5"
                    }`}
                    onClick={() => selectCard(ref)}
                  >
                    <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        className="h-3.5 w-3.5 rounded"
                        style={{ accentColor: "var(--mf-accent)" }}
                        checked={bulkMode ? bulkSelectedRefs.has(ref) : exportSelection.has(ref)}
                        onChange={(e) => {
                          if (bulkMode) toggleBulkSelect(ref);
                          else toggleExportSelect(ref);
                        }}
                      />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Star className="h-3.5 w-3.5 shrink-0" style={{ color: "var(--mf-accent)" }} />
                        <span className="font-medium text-ink truncate" style={{ fontFamily: "var(--mf-font-serif)" }}>
                          {card.title ?? t("card.untitled")}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs" style={{ color: "var(--mf-text-tertiary)" }}>
                      {card.source_type ? (sourceTypeLabels[card.source_type] ?? card.source_type) : "-"}
                    </td>
                    <td className="px-4 py-3 text-xs" style={{ color: "var(--mf-text-tertiary)" }}>
                      {formatDate(card.updated_at ?? card.created_at, locale)}
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium" style={{ background: "rgba(20,150,107,0.12)", color: "var(--mf-approved)" }}>
                        {friendlyStatus(card.status, locale)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {tags.slice(0, 2).map((tag) => (
                          <span key={tag} className="rounded-full px-2 py-0.5 text-[10px] font-medium" style={{ background: "var(--mf-accent-soft)", color: "var(--mf-accent)" }}>
                            {tag}
                          </span>
                        ))}
                        {tags.length > 2 && (
                          <span className="text-[10px]" style={{ color: "var(--mf-text-tertiary)" }}>+{tags.length - 2}</span>
                        )}
                        {tags.length === 0 && (
                          <span className="text-[10px]" style={{ color: "var(--mf-text-tertiary)" }}>{t("library.no_tags")}</span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {displayedCards.length === 0 && (
            <div className="py-12 text-center text-sm text-muted">
              {searchQuery ? t("review.no_results") : t("library.select_to_view")}
            </div>
          )}
          {displayedCards.length > 0 && (
            <div className="px-4 py-2 border-t border-line/50 text-xs" style={{ color: "var(--mf-text-tertiary)" }}>
              {displayedCards.length} / {approvedCards.length} {t("library.card_count").replace("{count}", String(approvedCards.length))}
            </div>
          )}
        </div>
        )}

        {/* Detail panel */}
        {selected && (
          <div className="rounded-xl border border-line bg-panel shadow-subtle overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-line">
              <span className="text-sm font-medium text-ink">{detail?.card.title ?? (detailLoading ? (locale === "zh" ? "加载中..." : "Loading...") : t("library.select_to_view"))}</span>
              <button
                className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted hover:text-ink"
                onClick={deselectCard}
                type="button"
              >
                <X className="h-3.5 w-3.5" /> {t("shared.close")}
              </button>
            </div>
            <div className="p-4 overflow-y-auto max-h-[85vh]">
              {error ? <ErrorState message={error} /> : null}
              {detailLoading && !detail && !error ? (
                <div className="flex items-center justify-center py-16 text-sm text-muted">
                  {locale === "zh" ? "正在加载知识卡详情..." : "Loading card details..."}
                </div>
              ) : null}
              {!error && !detailLoading && detail ? (
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
            </div>
            )}
            </div>
            </div>
            );
            }
