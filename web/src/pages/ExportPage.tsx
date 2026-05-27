import { useCallback, useEffect, useMemo, useState } from "react";
import { Download, Eye, FileText, Package } from "lucide-react";
import { getLibraryCards } from "../api/library";
import type { LibraryCardResponse, LibraryCardsResponse } from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { useLocale } from "../lib/i18n";
import { cx } from "../lib/utils";

type ExportFormat = "markdown" | "zip";

export function ExportPage() {
  const { locale, t } = useLocale();
  const [data, setData] = useState<LibraryCardsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scope, setScope] = useState<"all" | "tag" | "track">("all");
  const [selectedTag, setSelectedTag] = useState<string>("");
  const [selectedTrack, setSelectedTrack] = useState<string>("");
  const [format, setFormat] = useState<ExportFormat>("markdown");
  const [exporting, setExporting] = useState(false);
  const [previewText, setPreviewText] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    getLibraryCards()
      .then(setData)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : t("export.error_load")),
      );
  }, []);

  const approvedCards: LibraryCardResponse[] = useMemo(
    () => (data?.cards ?? []).filter((c) => c.status === "human_approved"),
    [data],
  );

  const allTags: string[] = useMemo(
    () => {
      const tagSet = new Set<string>();
      // tags come from API as string but the type might not include it
      for (const c of approvedCards) {
        // LibraryCardResponse doesn't have a 'tags' field directly visible,
        // but the API returns it. Cast through unknown.
        const raw = c as unknown as Record<string, unknown>;
        if (Array.isArray(raw.tags)) {
          for (const t of raw.tags as string[]) tagSet.add(t);
        }
      }
      return [...tagSet].sort();
    },
    [approvedCards],
  );

  const allTracks: string[] = useMemo(
    () => [...new Set(approvedCards.map((c) => c.track).filter(Boolean))].sort() as string[],
    [approvedCards],
  );

  const filteredCards = useMemo(() => {
    if (scope === "tag" && selectedTag) {
      return approvedCards.filter((c) => {
        const raw = c as unknown as Record<string, unknown>;
        return Array.isArray(raw.tags) && (raw.tags as string[]).includes(selectedTag);
      });
    }
    if (scope === "track" && selectedTrack) {
      return approvedCards.filter((c) => c.track === selectedTrack);
    }
    return approvedCards;
  }, [approvedCards, scope, selectedTag, selectedTrack]);

  const cardRefs: string[] = useMemo(
    () => filteredCards.map((c) => c.id ?? c.rel_path).filter(Boolean),
    [filteredCards],
  );

  const estimatedSize = useMemo(() => {
    const avgBytesPerCard = 2000;
    return cardRefs.length * avgBytesPerCard;
  }, [cardRefs.length]);

  function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  const doPreview = useCallback(async () => {
    if (cardRefs.length === 0) return;
    setError(null);
    try {
      const resp = await fetch("/api/knowledge/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ card_ids: cardRefs, format: "markdown" }),
      });
      if (!resp.ok) throw new Error(t("export.error_export"));
      const result = await resp.json();
      setPreviewText(typeof result.markdown === "string" ? result.markdown : JSON.stringify(result, null, 2));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("export.error_export"));
    }
  }, [cardRefs]);

  const doDownload = useCallback(async () => {
    if (cardRefs.length === 0) return;
    setExporting(true);
    setError(null);
    setSuccessMsg(null);
    try {
      if (format === "zip") {
        const resp = await fetch("/api/knowledge/export/download", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ card_ids: cardRefs, format: "zip" }),
        });
        if (!resp.ok) throw new Error(t("export.error_export"));
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
          body: JSON.stringify({ card_ids: cardRefs, format: "markdown" }),
        });
        if (!resp.ok) throw new Error(t("export.error_export"));
        const result = await resp.json();
        const content = typeof result.markdown === "string" ? result.markdown : "";
        const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `mindforge-export-${new Date().toISOString().slice(0, 10)}.md`;
        a.click();
        URL.revokeObjectURL(url);
      }
      setSuccessMsg(t("export.download_success"));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("export.error_export"));
    } finally {
      setExporting(false);
    }
  }, [cardRefs, format]);

  if (error && !data) {
    return (
      <div className="space-y-6">
        <header className="page-header">
          <h1>{t("export.title")}</h1>
          <p>{t("export.subtitle")}</p>
        </header>
        <div className="rounded-lg border border-[var(--mf-warn)]/30 bg-[var(--mf-warn)]/5 p-4 text-sm text-[var(--mf-warn)]">
          {error}
        </div>
      </div>
    );
  }

  if (data && approvedCards.length === 0) {
    return (
      <div className="space-y-6">
        <header className="page-header">
          <h1>{t("export.title")}</h1>
          <p>{t("export.subtitle")}</p>
        </header>
        <EmptyState
          title={t("export.preview_empty")}
          action={{
            label: "前往审阅草稿",
            description: "导入来源、审阅 AI 生成的草稿并确认知识卡片后即可导出。",
            href: "/drafts",
          }}
          locale={locale}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="page-header">
        <h1>{t("export.title")}</h1>
        <p>{t("export.subtitle")}</p>
      </header>

      {/* Scope Selection */}
      <section className="rounded-lg border border-line bg-white/60 p-5">
        <h2 className="mb-3 text-sm font-semibold text-ink">{t("export.scope_label")}</h2>
        <div className="mb-4 flex flex-wrap gap-2">
          {(["all", "tag", "track"] as const).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setScope(s)}
              className={cx(
                "rounded-md px-3 py-1.5 text-sm transition-colors",
                scope === s
                  ? "bg-[var(--mf-accent)] text-white"
                  : "bg-muted/30 text-muted hover:bg-muted/50 hover:text-ink",
              )}
            >
              {s === "all" && t("export.scope_all_approved")}
              {s === "tag" && t("export.scope_by_tag")}
              {s === "track" && t("export.scope_by_track")}
            </button>
          ))}
        </div>

        {scope === "tag" && (
          <select
            value={selectedTag}
            onChange={(e) => setSelectedTag(e.target.value)}
            className="rounded-md border border-line bg-white px-3 py-1.5 text-sm text-ink"
          >
            <option value="">-- {t("export.scope_by_tag")} --</option>
            {allTags.map((tag) => (
              <option key={tag} value={tag}>{tag}</option>
            ))}
          </select>
        )}

        {scope === "track" && (
          <select
            value={selectedTrack}
            onChange={(e) => setSelectedTrack(e.target.value)}
            className="rounded-md border border-line bg-white px-3 py-1.5 text-sm text-ink"
          >
            <option value="">-- {t("export.scope_by_track")} --</option>
            {allTracks.map((track) => (
              <option key={track} value={track}>{track}</option>
            ))}
          </select>
        )}
      </section>

      {/* Format Selection */}
      <section className="rounded-lg border border-line bg-white/60 p-5">
        <h2 className="mb-3 text-sm font-semibold text-ink">{t("export.format_label")}</h2>
        <div className="flex flex-wrap gap-3">
          {([
            ["markdown", t("export.format_markdown"), t("export.format_markdown_desc"), FileText],
            ["zip", t("export.format_zip"), t("export.format_zip_desc"), Package],
          ] as const).map(([key, label, desc, Icon]) => (
            <button
              key={key}
              type="button"
              onClick={() => setFormat(key)}
              className={cx(
                "flex items-start gap-3 rounded-lg border p-4 text-left transition-colors",
                format === key
                  ? "border-[var(--mf-accent)] bg-[var(--mf-accent)]/5"
                  : "border-line hover:border-[var(--mf-accent)]/40",
              )}
            >
              <Icon className="mt-0.5 h-5 w-5 shrink-0 text-muted" aria-hidden="true" />
              <div>
                <div className="text-sm font-medium text-ink">{label}</div>
                <div className="text-xs text-muted">{desc}</div>
              </div>
            </button>
          ))}
        </div>
      </section>

      {/* Preview */}
      <section className="rounded-lg border border-line bg-white/60 p-5">
        <h2 className="mb-3 text-sm font-semibold text-ink">{t("export.preview_title")}</h2>
        <p className="mb-3 text-sm text-muted">
          {t("export.preview_count").replace("{count}", String(cardRefs.length))}
          {" · "}
          {t("export.estimated_size")}: {formatSize(estimatedSize)}
        </p>

        {cardRefs.length > 0 && (
          <details className="mb-4">
            <summary className="cursor-pointer text-sm text-muted hover:text-ink">
              {t("export.card_list_title")} ({cardRefs.length})
            </summary>
            <ul className="mt-2 max-h-48 space-y-1 overflow-y-auto rounded border border-line bg-muted/20 p-3 text-sm">
              {filteredCards.map((c) => (
                <li key={c.id ?? c.rel_path} className="text-ink">
                  {c.title ?? c.rel_path}
                </li>
              ))}
            </ul>
          </details>
        )}

        {cardRefs.length === 0 && (
          <p className="text-sm text-muted">{t("export.no_selection")}</p>
        )}
      </section>

      {/* Safety Notice */}
      <div className="rounded-lg border border-[var(--mf-info)]/30 bg-[var(--mf-info)]/5 p-4 text-sm text-ink">
        <span className="font-medium">安全说明：</span>
        {t("export.safety_notice")}
      </div>

      {/* Actions */}
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          disabled={cardRefs.length === 0 || exporting}
          onClick={doPreview}
          className="inline-flex items-center gap-2 rounded-md border border-[var(--mf-accent)] px-4 py-2 text-sm font-medium text-[var(--mf-accent)] transition-colors hover:bg-[var(--mf-accent)]/8 disabled:opacity-40"
        >
          <Eye className="h-4 w-4" aria-hidden="true" />
          {t("export.preview_btn")}
        </button>
        <button
          type="button"
          disabled={cardRefs.length === 0 || exporting}
          onClick={doDownload}
          className="inline-flex items-center gap-2 rounded-md bg-[var(--mf-accent)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--mf-accent)]/90 disabled:opacity-40"
        >
          <Download className="h-4 w-4" aria-hidden="true" />
          {exporting ? "..." : t("export.download_btn")}
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-[var(--mf-warn)]/30 bg-[var(--mf-warn)]/5 p-3 text-sm text-[var(--mf-warn)]">
          {error}
        </div>
      )}

      {successMsg && (
        <div className="rounded-lg border border-green-300 bg-green-50 p-3 text-sm text-green-700">
          {successMsg}
        </div>
      )}

      {/* Preview Modal */}
      {previewText !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setPreviewText(null)}>
          <div
            className="mx-4 max-h-[80vh] w-full max-w-3xl overflow-y-auto rounded-lg bg-white p-6 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-ink">{t("export.preview_modal_title")}</h2>
              <button
                type="button"
                onClick={() => setPreviewText(null)}
                className="rounded-md px-2 py-1 text-sm text-muted hover:text-ink"
              >
                {t("export.preview_close")}
              </button>
            </div>
            <pre className="whitespace-pre-wrap rounded border border-line bg-muted/20 p-4 text-sm text-ink font-mono">
              {previewText.slice(0, 10000)}
              {previewText.length > 10000 && "\n\n... (内容过长，已截断)"}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
