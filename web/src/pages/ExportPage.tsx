import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Download,
  Eye,
  FileText,
  Package,
  ShieldCheck,
  FileJson,
  FileType,
  FileCode,
  Lock,
} from "lucide-react";
import { getLibraryCards } from "../api/library";
import type { LibraryCardResponse, LibraryCardsResponse } from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { BoundaryBadge } from "../components/BoundaryBadge";
import { useLocale } from "../lib/i18n";
import { cx } from "../lib/utils";

/**
 * ExportPage — 知识导出
 *
 * 中文学习型说明：
 * 此页面承载知识"流出"系统的逻辑。
 * 1. 明确 Staging 角色：导出仅为生成副本，不操作用户生产环境。
 * 2. 强化"只导出已审批"约束：不消费 ai_draft。
 * 3. 保护主工作区安全：明确不直接写入真实 Obsidian 库。
 *
 * 参考图 image6 风格：format cards grid + Coming Soon 标记。
 * 只有 Markdown 和 ZIP 是已实现的后端能力。
 * PDF / HTML / Word / JSON 标记为 Coming Soon，不可点击，不伪造能力。
 */

type ExportFormat = "markdown" | "zip";

interface FormatCard {
  key: string;
  label: string;
  desc: string;
  icon: typeof FileText;
  enabled: boolean;
  comingSoon?: boolean;
}

const formatCards: FormatCard[] = [
  {
    key: "markdown",
    label: "export.format_markdown",
    desc: "export.format_markdown_desc",
    icon: FileText,
    enabled: true,
  },
  {
    key: "zip",
    label: "export.format_zip",
    desc: "export.format_zip_desc",
    icon: Package,
    enabled: true,
  },
  {
    key: "pdf",
    label: "export.format_pdf",
    desc: "export.format_pdf_desc",
    icon: FileType,
    enabled: false,
    comingSoon: true,
  },
  {
    key: "html",
    label: "export.format_html",
    desc: "export.format_html_desc",
    icon: FileCode,
    enabled: false,
    comingSoon: true,
  },
  {
    key: "word",
    label: "export.format_word",
    desc: "export.format_word_desc",
    icon: FileText,
    enabled: false,
    comingSoon: true,
  },
  {
    key: "json",
    label: "export.format_json",
    desc: "export.format_json_desc",
    icon: FileJson,
    enabled: false,
    comingSoon: true,
  },
];

/** Staging boundary callout — 保护导出安全边界 */
function StagingBoundaryCallout() {
  const { t } = useLocale();
  return (
    <section className="rounded-md border border-stone-200/70 bg-stone-50/50 px-4 py-3">
      <p className="text-xs text-muted leading-relaxed">
        <BoundaryBadge type="staging" />
        <span className="ml-1.5">{t("export.staging_desc")}</span>
      </p>
    </section>
  );
}

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
      for (const c of approvedCards) {
        const raw = c as unknown as Record<string, unknown>;
        if (Array.isArray(raw.tags)) {
          for (const tag of raw.tags as string[]) tagSet.add(tag);
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

  // -- error: can't load cards ---------------------------------------------

  if (error && !data) {
    return (
      <div className="space-y-6">
        <header className="page-header">
          <h1>{t("export.title")}</h1>
          <p>{t("export.subtitle")}</p>
        </header>
        <StagingBoundaryCallout />
        <div className="rounded-lg border border-[var(--mf-warn)]/30 bg-[var(--mf-warn)]/5 p-4 text-sm text-[var(--mf-warn)]">
          {error}
        </div>
      </div>
    );
  }

  // -- no approved cards to export -----------------------------------------

  if (data && approvedCards.length === 0) {
    return (
      <div className="space-y-6">
        <header className="page-header">
          <h1>{t("export.title")}</h1>
          <p>{t("export.subtitle")}</p>
        </header>
        <StagingBoundaryCallout />
        <EmptyState
          title={t("export.preview_empty")}
          action={{
            label: "前往审阅草稿",
            description: "导入来源、审阅 AI 生成的草稿并确认知识卡片后即可导出。",
            href: "/drafts",
          }}
          locale={locale}
        />

        {/* Format cards grid — 展示所有格式，未实现的 disabled */}
        <FormatCardsGrid
          selectedFormat={format}
          onSelectFormat={() => {}}
          disabled
        />
      </div>
    );
  }

  // -- main export page ----------------------------------------------------

  return (
    <div className="space-y-6">
      <header className="page-header">
        <h1>{t("export.title")}</h1>
        <p>{t("export.subtitle")}</p>
      </header>

      <StagingBoundaryCallout />

      {/* Format Cards Grid */}
      <FormatCardsGrid
        selectedFormat={format}
        onSelectFormat={(key) => {
          if (key === "markdown" || key === "zip") {
            setFormat(key as ExportFormat);
          }
        }}
        disabled={false}
      />

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

      {/* Export Options — 后端暂不支持，标记 Coming Soon */}
      <details className="rounded-lg border border-line bg-white/60 p-5">
        <summary className="cursor-pointer text-sm font-medium text-muted hover:text-ink">
          {t("export.options_label")}
          <span className="ml-2 inline-flex items-center rounded-full bg-muted/30 px-2 py-0.5 text-[10px] font-medium text-muted">
            {t("export.format_coming_soon")}
          </span>
        </summary>
        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4 opacity-50">
          {([
            ["export.opt_include_metadata", "export.opt_include_metadata_desc"],
            ["export.opt_include_toc", "export.opt_include_toc_desc"],
            ["export.opt_include_tags", "export.opt_include_tags_desc"],
            ["export.opt_include_frontmatter", "export.opt_include_frontmatter_desc"],
          ] as const).map(([label, desc]) => (
            <div key={label} className="flex flex-col gap-0.5 rounded-md border border-line/50 bg-muted/10 p-3">
              <div className="text-xs font-medium text-muted">{t(label)}</div>
              <div className="text-[11px] text-muted/60">{t(desc)}</div>
            </div>
          ))}
        </div>
      </details>

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
              {filteredCards.slice(0, 20).map((c) => (
                <li key={c.id ?? c.rel_path} className="text-ink">
                  {c.title ?? c.rel_path}
                </li>
              ))}
              {filteredCards.length > 20 && (
                <li className="text-muted text-xs">
                  ... +{filteredCards.length - 20} {locale === "zh" ? "更多" : "more"}
                </li>
              )}
            </ul>
          </details>
        )}

        {cardRefs.length === 0 && (
          <p className="text-sm text-muted">{t("export.no_selection")}</p>
        )}
      </section>

      {/* Safety Notice */}
      <div className="rounded-lg border border-green-300 bg-green-50 p-4 text-sm text-ink shadow-sm flex items-start gap-3">
        <ShieldCheck className="h-5 w-5 text-green-700 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold text-green-800 flex items-center gap-2 mb-1">
            {t("shared.safety_notice") || "安全说明"}
            <BoundaryBadge type="staging" />
          </span>
          {t("export.safety_notice")}
        </div>
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

/** Format Cards Grid — 展示导出格式，已实现的可用，未实现的 Coming Soon */
function FormatCardsGrid({
  selectedFormat,
  onSelectFormat,
  disabled,
}: {
  selectedFormat: string;
  onSelectFormat: (key: string) => void;
  disabled: boolean;
}) {
  const { t } = useLocale();

  return (
    <section className="rounded-lg border border-line bg-white/60 p-5">
      <h2 className="mb-1 text-sm font-semibold text-ink">{t("export.format_label")}</h2>
      <p className="mb-4 text-xs text-muted">
        {disabled
          ? ""
          : t("export.format_coming_soon") + " " + (t("export.format_json") || "") + " ..."}
      </p>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {formatCards.map((card) => {
          const isSelected = selectedFormat === card.key;
          const Icon = card.icon;

          if (!card.enabled) {
            // Coming Soon — disabled card
            return (
              <div
                key={card.key}
                className="flex flex-col items-start gap-2 rounded-lg border border-line/50 bg-muted/10 p-4 opacity-60 cursor-not-allowed"
              >
                <div className="flex items-center gap-2">
                  <Icon className="h-5 w-5 text-muted" aria-hidden="true" />
                  <span className="text-sm font-medium text-muted">{t(card.label)}</span>
                </div>
                <span className="inline-flex items-center rounded-full bg-muted/30 px-2 py-0.5 text-[10px] font-medium text-muted">
                  {t("export.format_coming_soon")}
                </span>
                <Lock className="h-3 w-3 text-muted/40" />
              </div>
            );
          }

          return (
            <button
              key={card.key}
              type="button"
              onClick={() => onSelectFormat(card.key)}
              className={cx(
                "flex flex-col items-start gap-2 rounded-lg border p-4 text-left transition-colors",
                isSelected && !disabled
                  ? "border-[var(--mf-accent)] bg-[var(--mf-accent)]/5"
                  : "border-line hover:border-[var(--mf-accent)]/40",
              )}
            >
              <div className="flex items-center gap-2">
                <Icon className="h-5 w-5 shrink-0 text-muted" aria-hidden="true" />
                <span className="text-sm font-medium text-ink">{t(card.label)}</span>
              </div>
              <span className="text-xs text-muted">{t(card.desc)}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
