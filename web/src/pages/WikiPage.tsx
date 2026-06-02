/**
 * WikiPage — 知识 Wiki 综合文档
 *
 * 中文学习型说明：
 * 参考图 image8 风格：filter tabs + page list + "What can you do?" section。
 * Favorites / Recent / Recently Updated 目前没有后端支持，标记为 disabled。
 * Wiki 是从 human_approved 知识卡片自动生成的综合文档，
 * 不依赖 RAG、向量数据库或图谱推理。
 * 保护产品边界：Wiki = 派生视图，不是原始知识源。
 */

import { useEffect, useState, useCallback, useMemo } from "react";
import { BookOpen, FileText, Search, Star, X } from "lucide-react";
import { useLocale } from "../lib/i18n";
import type { WikiPageViewModel, WikiQualityResponse, WikiRelatedSectionsResponse } from "../api/wiki";

/** Filter tab 类型 — Wiki 页面浏览 */
type WikiFilterTab = "all" | "favorites" | "recent" | "recently_updated";

const filterTabs: { key: WikiFilterTab; label: string; disabled?: boolean }[] = [
  { key: "all", label: "wiki.tab_all_pages" },
  { key: "favorites", label: "wiki.tab_favorites", disabled: true },
  { key: "recent", label: "wiki.tab_recent", disabled: true },
  { key: "recently_updated", label: "wiki.tab_recently_updated", disabled: true },
];

interface WikiStatus {
  wiki_path: string;
  exists: boolean;
  last_rebuilt_at: string | null;
  approved_card_count: number;
  wiki_card_count: number;
  is_stale: boolean;
  new_approved_count: number;
  model_ready: boolean;
  model_ready_label: string;
}

interface WikiRebuildResult {
  ok: boolean;
  mode?: string;
  wiki_path?: string;
  included_cards?: number;
  section_count?: number;
  additional_cards?: number;
  model_id?: string;
  warnings?: string[];
  last_rebuilt_at?: string;
  error?: string;
}

/** 格式化相对时间 */
function formatRelative(dateStr: string | null | undefined, locale: string): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr.slice(0, 10);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 60) return locale === "zh" ? `${diffMin} 分钟前` : `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return locale === "zh" ? `${diffHr} 小时前` : `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay < 7) return locale === "zh" ? `${diffDay} 天前` : `${diffDay}d ago`;
  return d.toLocaleDateString(locale === "zh" ? "zh-CN" : "en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function WikiPage() {
  const [status, setStatus] = useState<WikiStatus | null>(null);
  const [page, setPage] = useState<WikiPageViewModel | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [readerMode, setReaderMode] = useState(false);
  const [quality, setQuality] = useState<WikiQualityResponse | null>(null);
  const [relatedSections, setRelatedSections] = useState<WikiRelatedSectionsResponse | null>(null);
  const [activeTab, setActiveTab] = useState<WikiFilterTab>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const { locale, t } = useLocale();

  const load = useCallback(async () => {
    setError(null);
    try {
      const [s, p, q, rs] = await Promise.all([
        fetch("/api/wiki/status").then((r) => r.json()),
        fetch("/api/wiki/page").then((r) => r.json()),
        fetch("/api/wiki/quality").then((r) => r.json()),
        fetch("/api/wiki/related-sections").then((r) => r.json()),
      ]);
      setStatus(s as WikiStatus);
      if ((p as Record<string, unknown>).exists === false) {
        setPage(null);
      } else {
        setPage(p as WikiPageViewModel);
      }
      setQuality(q as WikiQualityResponse);
      setRelatedSections(rs as WikiRelatedSectionsResponse);
    } catch {
      setError(t("wiki.load_failed"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  async function rebuild(mode: string) {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const resp = await fetch("/api/wiki/rebuild", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });
      const data: WikiRebuildResult = await resp.json();
      if (data.ok) {
        setMessage(
          t("wiki.rebuild_result")
            .replace("{mode}", data.mode ?? "?")
            .replace("{cards}", String(data.included_cards ?? 0))
            .replace("{sections}", String(data.section_count ?? 0))
            .replace("{model}", data.model_id ?? "-"),
        );
        if (data.warnings?.length) {
          setMessage(
            (prev) =>
              (prev ?? "") + " — " + t("wiki.warnings") + ": " + data.warnings!.join("; "),
          );
        }
        if (data.last_rebuilt_at) {
          setStatus((prev) =>
            prev
              ? {
                  ...prev,
                  last_rebuilt_at: data.last_rebuilt_at ?? null,
                  wiki_card_count:
                    data.included_cards ?? prev.wiki_card_count,
                }
              : prev,
          );
        }
      } else {
        setError(t("wiki.rebuild_server_error").replace("{error}", data.error ?? "unknown error"));
      }
      await load();
    } catch {
      setError(t("wiki.rebuild_failed"));
    } finally {
      setBusy(false);
    }
  }

  // -- 过滤后的 sections 列表 -----------------------------------------------

  const filteredSections = useMemo(() => {
    if (!page) return [];
    let sections = page.sections;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      sections = sections.filter(
        (s) =>
          (s.title ?? "").toLowerCase().includes(q) ||
          (s.body ?? "").toLowerCase().includes(q),
      );
    }
    // Favorites / Recent / Recently Updated 没有后端支持，fallback 到 all
    return sections;
  }, [page, searchQuery, activeTab]);

  // -- loading state -------------------------------------------------------

  if (loading) {
    return (
      <div className="space-y-6">
        <WikiLoadingHeader />
        <div className="flex items-center justify-center py-16 text-sm text-muted">
          {locale === "zh" ? "正在加载 Wiki..." : "Loading Wiki..."}
        </div>
      </div>
    );
  }

  // -- error state after initial load --------------------------------------

  if (error && !page) {
    return (
      <div className="space-y-6">
        <WikiLoadingHeader />
        <div className="rounded-lg border border-[var(--mf-warn)]/30 bg-[var(--mf-warn)]/5 p-6 text-center">
          <p className="text-sm text-[var(--mf-warn)]">{error}</p>
          <button
            type="button"
            onClick={() => load()}
            className="mt-3 text-sm font-medium text-[var(--mf-accent)] hover:underline"
          >
            {t("wiki.retry")}
          </button>
        </div>
      </div>
    );
  }

  // -- busy / rebuild in progress ------------------------------------------

  if (busy) {
    return (
      <div className="space-y-6">
        <WikiLoadingHeader />
        <div className="flex items-center justify-center py-16 text-sm text-muted">
          {locale === "zh" ? "正在构建 Wiki..." : "Building Wiki..."}
        </div>
      </div>
    );
  }

  // -- empty state (no wiki / no approved cards) ---------------------------

  const noApprovedCards = status != null && status.approved_card_count === 0;
  const wikiNotBuilt = status != null && !status.exists && !noApprovedCards;

  if (!page && (noApprovedCards || wikiNotBuilt || !status?.model_ready)) {
    const modelReady = status?.model_ready ?? false;
    return (
      <div className="space-y-6">
        <WikiLoadingHeader
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
        />

        {/* Boundary callout */}
        <section className="rounded-md border border-stone-200/70 bg-stone-50/50 px-4 py-3">
          <p className="text-xs text-muted leading-relaxed">
            {t("wiki.boundary_callout")}
          </p>
        </section>

        {/* Empty state */}
        <div className="rounded-lg border border-line bg-white/60 p-8 text-center">
          {noApprovedCards ? (
            <>
              <h3 className="mb-2 text-base font-semibold text-ink">{t("wiki.empty_no_approved")}</h3>
              <p className="mb-4 text-sm text-muted">{t("wiki.empty_no_approved_desc")}</p>
              <a
                href="/sources"
                className="inline-flex items-center gap-2 rounded-md bg-[var(--mf-accent)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--mf-accent)]/90"
              >
                {t("home.add_sources")}
              </a>
            </>
          ) : !modelReady ? (
            <>
              <h3 className="mb-2 text-base font-semibold text-ink">{t("wiki.empty_model_required")}</h3>
              <p className="text-sm text-muted">{t("wiki.empty_model_required_desc")}</p>
            </>
          ) : (
            <>
              <h3 className="mb-2 text-base font-semibold text-ink">{t("wiki.empty_not_built")}</h3>
              <p className="mb-4 text-sm text-muted">{t("wiki.empty_not_built_desc")}</p>
              <button
                type="button"
                onClick={() => rebuild("llm")}
                className="inline-flex items-center gap-2 rounded-md bg-[var(--mf-accent)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--mf-accent)]/90"
              >
                {t("wiki.generate")}
              </button>
            </>
          )}
        </div>

        {/* What can you do? */}
        <section className="rounded-lg border border-line bg-white/60 p-5">
          <h3 className="mb-3 text-sm font-semibold text-ink">{t("wiki.what_can_you_do")}</h3>
          <ul className="space-y-2 text-sm text-muted">
            <li className="flex items-start gap-2">
              <BookOpen className="mt-0.5 h-4 w-4 shrink-0 text-[var(--mf-accent)]" />
              {t("wiki.what_can_you_do_1")}
            </li>
            <li className="flex items-start gap-2">
              <Search className="mt-0.5 h-4 w-4 shrink-0 text-[var(--mf-accent)]" />
              {t("wiki.what_can_you_do_2")}
            </li>
            <li className="flex items-start gap-2">
              <FileText className="mt-0.5 h-4 w-4 shrink-0 text-[var(--mf-accent)]" />
              {t("wiki.what_can_you_do_3")}
            </li>
            <li className="flex items-start gap-2">
              <Star className="mt-0.5 h-4 w-4 shrink-0 text-[var(--mf-accent)]" />
              {t("wiki.what_can_you_do_4")}
            </li>
          </ul>
        </section>

        {/* Fallback rebuild */}
        <details className="rounded-lg border border-line bg-white/60 p-5">
          <summary className="cursor-pointer text-sm font-medium text-muted hover:text-ink">
            {t("wiki.troubleshooting")}
          </summary>
          <div className="mt-3 space-y-3">
            <p className="text-sm text-muted">{t("wiki.troubleshooting_desc")}</p>
            <button
              type="button"
              onClick={() => rebuild("deterministic")}
              className="rounded-md border border-line px-3 py-1.5 text-sm text-muted hover:text-ink hover:border-[var(--mf-accent)]/40"
            >
              {t("wiki.safe_fallback_rebuild")}
            </button>
          </div>
        </details>
      </div>
    );
  }

  // -- ready state: structured wiki with sections --------------------------

  return (
    <div className="space-y-6">
      {/* Header with filter tabs + search */}
      <WikiLoadingHeader
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
      />

      {message ? <p className="text-sm text-primary">{message}</p> : null}
      {error ? <p className="text-sm text-[var(--mf-warn)]">{error}</p> : null}

      {/* Boundary callout */}
      <section className="rounded-md border border-stone-200/70 bg-stone-50/50 px-4 py-3">
        <p className="text-xs text-muted leading-relaxed">
          {t("wiki.boundary_callout")}
        </p>
      </section>

      {/* Status bar */}
      {status && (
        <div className="rounded-lg border border-line bg-white/60 px-4 py-3 flex flex-wrap items-center gap-4 text-sm">
          <span className="text-muted">{t("wiki.status_label")}:</span>
          <span
            className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium"
            style={{
              background: status.exists ? "rgba(45,125,95,0.08)" : "rgba(204,122,0,0.08)",
              color: status.exists ? "var(--mf-approved)" : "var(--mf-warning)",
            }}
          >
            {status.exists ? t("wiki.status_ready") : t("wiki.status_not_built")}
          </span>
          {status.last_rebuilt_at && (
            <span className="text-muted">
              {t("wiki.last_rebuilt")}: {formatRelative(status.last_rebuilt_at, locale)}
            </span>
          )}
          <span className="text-muted">
            {t("wiki.cards_in_wiki")}: {status.wiki_card_count}
          </span>
          {status.new_approved_count > 0 && (
            <span className="text-[var(--mf-accent)] text-xs">
              {t("wiki.new_approved_hint").replace("{count}", String(status.new_approved_count))}
            </span>
          )}
          <div className="ml-auto flex gap-2">
            <button
              type="button"
              onClick={() => rebuild("llm")}
              disabled={busy}
              className="rounded-md bg-[var(--mf-accent)] px-3 py-1 text-xs font-medium text-white transition-colors hover:bg-[var(--mf-accent)]/90 disabled:opacity-40"
              title={t("wiki.rebuild_tooltip")}
            >
              {busy ? (locale === "zh" ? "构建中..." : "Building...") : t("wiki.refresh")}
            </button>
            <button
              type="button"
              onClick={() => setReaderMode((prev) => !prev)}
              className={cx(
                "rounded-md border px-3 py-1 text-xs font-medium transition-colors",
                readerMode
                  ? "border-[var(--mf-accent)] text-[var(--mf-accent)] bg-[var(--mf-accent)]/5"
                  : "border-line text-muted hover:text-ink",
              )}
            >
              {readerMode ? t("wiki.reader_mode_off") : t("wiki.reader_mode_on")}
            </button>
          </div>
        </div>
      )}

      {/* Page list / sections */}
      {page && filteredSections.length > 0 && (
        <div className="rounded-lg border border-line bg-white/60 divide-y">
          {filteredSections.map((section, i) => (
            <details key={i} className="group">
              <summary className="flex cursor-pointer items-center gap-3 px-5 py-3 text-sm hover:bg-muted/20">
                <FileText className="h-4 w-4 shrink-0 text-muted" />
                <span className="font-medium text-ink">{section.title || t("wiki.untitled_section")}</span>
                <span className="ml-auto text-xs text-muted">
                  {(section.card_refs?.length ?? 0)} {t("wiki.knowledge_cards")}
                </span>
              </summary>
              <div className="px-5 pb-4 pl-12 text-sm text-muted leading-relaxed whitespace-pre-wrap">
                {section.body?.slice(0, 500) ?? ""}
                {(section.body?.length ?? 0) > 500 && (
                  <span className="text-[var(--mf-accent)]"> ...</span>
                )}
              </div>
            </details>
          ))}
        </div>
      )}

      {page && filteredSections.length === 0 && searchQuery && (
        <div className="rounded-lg border border-line bg-white/60 p-8 text-center text-sm text-muted">
          {locale === "zh" ? "未找到匹配的 Wiki 章节" : "No matching Wiki sections found"}
        </div>
      )}

      {page && filteredSections.length === 0 && !searchQuery && status && (
        <div className="rounded-lg border border-line bg-white/60 p-8 text-center">
          <h3 className="mb-2 text-base font-semibold text-ink">
            {locale === "zh" ? "Wiki 暂无内容" : "Wiki is empty"}
          </h3>
          <p className="mb-1 text-sm text-muted">
            {status.approved_card_count > 0
              ? (locale === "zh"
                  ? `已有 ${status.approved_card_count} 条已确认知识，可以重新生成 Wiki`
                  : `${status.approved_card_count} approved cards available — regenerate Wiki to include them`)
              : (locale === "zh" ? "没有已确认知识，无法生成 Wiki" : "No approved knowledge to generate Wiki from")}
          </p>
          {status.approved_card_count > 0 && (
            <button
              type="button"
              onClick={() => rebuild("llm")}
              disabled={busy}
              className="mt-3 inline-flex items-center gap-2 rounded-md bg-[var(--mf-accent)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--mf-accent)]/90 disabled:opacity-40"
            >
              {t("wiki.generate")}
            </button>
          )}
        </div>
      )}

      {/* Quality metrics — 简化显示 */}
      {quality?.exists && quality.coverage && (
        <details className="rounded-lg border border-line bg-white/60 p-5">
          <summary className="cursor-pointer text-sm font-medium text-muted hover:text-ink">
            {t("wiki.quality_title")}
          </summary>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs" style={{ background: "rgba(45,125,95,0.08)", color: "var(--mf-approved)" }}>
              {t("wiki.quality_coverage")}: {quality.coverage.used}/{quality.coverage.total} ({Math.round(quality.coverage.rate * 100)}%)
            </span>
            {quality.faithfulness && (
              <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs" style={{
                background: quality.faithfulness.average >= 0.7 ? "rgba(45,125,95,0.08)" :
                  quality.faithfulness.average >= 0.4 ? "rgba(204,122,0,0.08)" :
                  "rgba(192,64,64,0.08)",
                color: quality.faithfulness.average >= 0.7 ? "var(--mf-approved)" :
                  quality.faithfulness.average >= 0.4 ? "var(--mf-warning)" :
                  "var(--mf-error)",
              }}>
                {t("wiki.quality_faithfulness")}: {Math.round(quality.faithfulness.average * 100)}%
              </span>
            )}
            {quality.unused_cards && quality.unused_cards.length > 0 && (
              <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs" style={{ background: "rgba(204,122,0,0.08)", color: "var(--mf-warning)" }}>
                {t("wiki.quality_unused")}: {quality.unused_cards.length}
              </span>
            )}
            {quality.stale_sections && quality.stale_sections.length > 0 && (
              <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs" style={{ background: "rgba(204,122,0,0.08)", color: "var(--mf-warning)" }}>
                {t("wiki.quality_stale")}: {quality.stale_sections.length}
              </span>
            )}
            {quality.knowledge_gaps && quality.knowledge_gaps.length > 0 && (
              <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs" style={{ background: "rgba(192,64,64,0.08)", color: "var(--mf-error)" }}>
                {t("wiki.quality_gaps")}: {quality.knowledge_gaps.length}
              </span>
            )}
          </div>
        </details>
      )}

      {/* What can you do? */}
      <section className="rounded-lg border border-line bg-white/60 p-5">
        <h3 className="mb-3 text-sm font-semibold text-ink">{t("wiki.what_can_you_do")}</h3>
        <ul className="space-y-2 text-sm text-muted">
          <li className="flex items-start gap-2">
            <BookOpen className="mt-0.5 h-4 w-4 shrink-0 text-[var(--mf-accent)]" />
            {t("wiki.what_can_you_do_1")}
          </li>
          <li className="flex items-start gap-2">
            <Search className="mt-0.5 h-4 w-4 shrink-0 text-[var(--mf-accent)]" />
            {t("wiki.what_can_you_do_2")}
          </li>
          <li className="flex items-start gap-2">
            <FileText className="mt-0.5 h-4 w-4 shrink-0 text-[var(--mf-accent)]" />
            {t("wiki.what_can_you_do_3")}
          </li>
          <li className="flex items-start gap-2">
            <Star className="mt-0.5 h-4 w-4 shrink-0 text-[var(--mf-accent)]" />
            {t("wiki.what_can_you_do_4")}
          </li>
        </ul>
      </section>

      {/* Fallback rebuild */}
      <details className="rounded-lg border border-line bg-white/60 p-5">
        <summary className="cursor-pointer text-sm font-medium text-muted hover:text-ink">
          {t("wiki.troubleshooting")}
        </summary>
        <div className="mt-3 space-y-3">
          <p className="text-sm text-muted">{t("wiki.troubleshooting_desc")}</p>
          <button
            type="button"
            onClick={() => rebuild("deterministic")}
            className="rounded-md border border-line px-3 py-1.5 text-sm text-muted hover:text-ink hover:border-[var(--mf-accent)]/40"
          >
            {t("wiki.safe_fallback_rebuild")}
          </button>
        </div>
      </details>
    </div>
  );
}

/** Wiki Header — 带 filter tabs + search */
function WikiLoadingHeader({
  activeTab,
  setActiveTab,
  searchQuery,
  setSearchQuery,
}: {
  activeTab?: WikiFilterTab;
  setActiveTab?: (t: WikiFilterTab) => void;
  searchQuery?: string;
  setSearchQuery?: (q: string) => void;
}) {
  const { t } = useLocale();

  return (
    <div>
      <header className="page-header">
        <h1>{t("wiki.title")}</h1>
        <p>{t("wiki.subtitle")}</p>
      </header>

      {/* Filter tabs */}
      <div className="mb-4 flex flex-wrap items-center gap-1">
        {filterTabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            disabled={tab.disabled}
            onClick={() => setActiveTab?.(tab.key)}
            className={cx(
              "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
              tab.disabled
                ? "cursor-not-allowed text-muted/40"
                : activeTab === tab.key
                  ? "bg-[var(--mf-accent)] text-white"
                  : "text-muted hover:bg-muted/30 hover:text-ink",
              activeTab === tab.key && !tab.disabled && "bg-[var(--mf-accent)] text-white",
            )}
          >
            {t(tab.label)}
            {tab.disabled && (
              <span className="ml-1 text-[10px] opacity-60">
                {t("export.format_coming_soon")}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Search + actions row */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            type="text"
            value={searchQuery ?? ""}
            onChange={(e) => setSearchQuery?.(e.target.value)}
            placeholder={t("wiki.search_placeholder")}
            className="w-full rounded-md border border-line bg-white/80 py-2 pl-9 pr-8 text-sm text-ink placeholder:text-muted focus:border-[var(--mf-accent)] focus:outline-none"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery?.("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-muted hover:text-ink"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function cx(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(" ");
}
