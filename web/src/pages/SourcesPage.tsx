import type { SourcesResponse, WatchedSourceResponse } from "../api/types";
import { deleteWatchedSource, scanWatchedSources, updateWatchedSourceFrequency } from "../api/sources";
import { SourceAddPanel, getFrequencyOptions } from "../components/SourceAddPanel";
import { BoundaryBadge } from "../components/BoundaryBadge";
import { useLocale } from "../lib/i18n";
import { sourceDueStatusLabel, sourceRunStatusLabel, sourceStatusLabel } from "../lib/utils";
import { useState } from "react";
import { ArrowDown, FolderOpen, Terminal, Clipboard, Globe, Rss, FileText, Package, ExternalLink, Play, Clock, BarChart3, Plus } from "lucide-react";

/**
 * SourcesPage - 知识来源管理 / Import Center
 *
 * 中文学习型说明：
 * 此页面承载 Source Ingestion (资料摄入) 的逻辑。
 * 1. 明确 Source Adapter 角色：它是"只读"资料源。
 * 2. 强化"导入不等于确认"边界：导入后资料仅进入 ai_draft，需手动审批。
 * 3. 区分 Source (资料) 与 Provider (加工能力)。
 * 4. 参考图风格：clean import center，source adapter cards 展示。
 * 5. 未实现的 adapter (Cubox/WebClipper/RSS) 不伪造为可用，展示为空/coming soon。
 */

/** Source Adapter 定义 — 保护 Source ≠ Provider 的产品边界 */
interface SourceAdapter {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
  collectionInfo?: string;
  status: "implemented" | "coming_soon";
  /** 如果已实现，对应后端的 adapter name */
  adapterName?: string;
}

const sourceAdapters: SourceAdapter[] = [
  {
    id: "local_files",
    label: "Local Files",
    icon: FolderOpen,
    description: "Monitor local files and folders for knowledge ingestion.",
    status: "implemented",
    adapterName: "plain_markdown",
  },
  {
    id: "cubox",
    label: "Cubox",
    icon: Globe,
    description: "Import saved articles from Cubox collections.",
    status: "coming_soon",
  },
  {
    id: "web_clipper",
    label: "Web Clipper",
    icon: Clipboard,
    description: "Clip articles from the web into your knowledge base.",
    status: "coming_soon",
  },
  {
    id: "rss_feed",
    label: "RSS Feed",
    icon: Rss,
    description: "Follow RSS feeds and auto-generate knowledge drafts.",
    status: "coming_soon",
  },
];

export function SourcesPage({
  data,
  onNavigate,
  onRefresh,
  providerState,
}: {
  data: SourcesResponse;
  onNavigate: (href: string) => void;
  onRefresh?: () => Promise<void>;
  providerState?: string;
}) {
  const [rowFrequencies, setRowFrequencies] = useState<Record<string, string>>({});
  const [result, setResult] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [expandedSourceId, setExpandedSourceId] = useState<string | null>(null);
  const [showAddPanel, setShowAddPanel] = useState(false);
  const { locale, t } = useLocale();

  async function removeWatch(source: SourcesResponse["watched_sources"][number]) {
    if (source.is_default && !window.confirm(t("sources.stop_watching_warning"))) return;
    setBusy(true);
    setResult(null);
    try {
      const response = await deleteWatchedSource(source.id);
      setResult(response.message);
      await onRefresh?.();
    } catch (error) {
      setResult(error instanceof Error ? error.message : t("source_add.request_failed"));
    } finally {
      setBusy(false);
    }
  }

  async function cleanupMissingSources() {
    const missingSources = data.watched_sources.filter((s) => s.status_label === "Missing" || s.status === "missing");
    if (missingSources.length === 0 || !window.confirm(t("sources.cleanup_missing_confirm").replace("{count}", String(missingSources.length)))) return;
    setBusy(true);
    setResult(null);
    let removed = 0;
    for (const source of missingSources) {
      try {
        await deleteWatchedSource(source.id);
        removed++;
      } catch {
        // continue with remaining
      }
    }
    setResult(t("sources.cleanup_missing_result").replace("{count}", String(removed)));
    await onRefresh?.();
    setBusy(false);
  }

  async function editFrequency(ref: string, currentFrequency: string) {
    setBusy(true);
    setResult(null);
    try {
      const response = await updateWatchedSourceFrequency(ref, rowFrequencies[ref] ?? currentFrequency);
      setResult(response.message);
      await onRefresh?.();
    } catch (error) {
      setResult(error instanceof Error ? error.message : t("source_add.request_failed"));
    } finally {
      setBusy(false);
    }
  }

  async function scanWatch(ref?: string, allSources = false) {
    setBusy(true);
    setResult(t("sources.starting_background"));
    try {
      const response = await scanWatchedSources(ref, allSources);
      setResult(formatRunSummary(response.message, response.counts, response.run_id));
      await onRefresh?.();
    } catch (error) {
      setResult(error instanceof Error ? error.message : t("source_add.request_failed"));
    } finally {
      setBusy(false);
    }
  }

  async function copySourcePath(source: SourcesResponse["watched_sources"][number]) {
    setResult(null);
    const view = source.source_path_view;
    if (!view?.can_copy_display_path) {
      setResult(t("sources.no_safe_path"));
      return;
    }
    const targetPath = view.can_copy_full_path ? source.path : view.display_path;
    if (!targetPath) {
      setResult(t("sources.no_safe_path"));
      return;
    }
    try {
      await navigator.clipboard?.writeText(targetPath);
      setResult(view.can_copy_full_path ? t("sources.copied_source_path") : t("sources.copied_safe_path"));
    } catch (error) {
      setResult(error instanceof Error ? error.message : t("sources.copy_path_failed"));
    }
  }

  const totalDrafts = data.watched_sources.reduce((sum, s) => sum + (s.generated_draft_count ?? 0), 0);

  return (
    <div className="space-y-8">
      <header className="page-header">
        <h1>{t("sources.title")}</h1>
        <p>{t("sources.import_center_subtitle")}</p>
      </header>

      {/* 产品边界提示：Source 不是 Provider */}
      <section className="mf-card-soft rounded-lg p-4">
        <p className="text-xs text-muted leading-relaxed">
          <BoundaryBadge type="source" />
          <span className="ml-1.5">{t("sources.boundary_desc")}</span>
          {providerState !== "ready" && (
            <span className="ml-2" style={{ color: "var(--mf-text-tertiary)" }}>
              · {t("sources.demo_mode_hint")}
            </span>
          )}
        </p>
      </section>

      {/* ── 统计摘要 ── */}
      <div className="flex flex-wrap items-center gap-6 text-sm">
        <span className="flex items-center gap-1.5">
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-bold" style={{ color: "var(--mf-accent)" }}>
            {data.watched_sources.length}
          </span>
          <span style={{ color: "var(--mf-text-secondary)" }}>{t("sources.stat_sources")}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="rounded-full px-2 py-0.5 text-xs font-bold" style={{ background: "rgba(216,135,34,0.12)", color: "var(--mf-draft)" }}>
            {totalDrafts}
          </span>
          <span style={{ color: "var(--mf-text-secondary)" }}>{t("sources.stat_drafts")}</span>
        </span>
      </div>

      {/* ── Source Adapter Catalog ── */}
      <section className="rounded-xl border border-line bg-panel p-5 shadow-subtle">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-ink">{t("sources.adapters_title")}</h2>
            <p className="mt-1 text-xs text-muted">{t("sources.adapters_desc")}</p>
          </div>
          <button
            className="mf-primary-button rounded-lg px-4 py-2 text-sm"
            onClick={() => setShowAddPanel(!showAddPanel)}
            type="button"
          >
            <Plus className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
            {t("sources.new_source_btn")}
          </button>
        </div>

        {/* Inline Source Add Panel */}
        {showAddPanel && (
          <div className="mt-4">
            <SourceAddPanel onRefresh={onRefresh} hasModels />
          </div>
        )}
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {sourceAdapters.map((adapter) => {
            const Icon = adapter.icon;
            const isActive = adapter.status === "implemented";
            const sourceCount = isActive ? data.watched_sources.length : 0;
            return (
              <div
                key={adapter.id}
                className={`rounded-xl border p-4 transition-colors ${
                  isActive
                    ? "border-line hover:border-[var(--mf-accent)]/20"
                    : "border-line/50 opacity-60"
                }`}
                style={{ borderRadius: "var(--mf-radius-lg)" }}
              >
                <div className="flex items-start gap-3">
                  <div
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
                    style={{
                      background: isActive ? "var(--mf-accent-soft)" : "var(--mf-surface-alt)",
                      color: isActive ? "var(--mf-accent)" : "var(--mf-text-tertiary)",
                    }}
                  >
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold text-ink">{adapter.label}</h3>
                    <p className="mt-0.5 text-[11px] leading-snug" style={{ color: "var(--mf-text-tertiary)" }}>
                      {adapter.description}
                    </p>
                    <div className="mt-2 flex items-center gap-1.5">
                      {isActive ? (
                        <>
                          <span className="text-[10px] font-medium" style={{ color: "var(--mf-text-secondary)" }}>
                            {sourceCount} source{sourceCount !== 1 ? "s" : ""}
                          </span>
                          <span className="rounded-full px-1.5 py-0.5 text-[10px] font-bold" style={{ background: "rgba(20,150,107,0.12)", color: "var(--mf-approved)" }}>
                            Active
                          </span>
                        </>
                      ) : (
                        <span className="rounded-full px-1.5 py-0.5 text-[10px] font-bold" style={{ background: "var(--mf-surface-alt)", color: "var(--mf-text-tertiary)" }}>
                          Coming Soon
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── Import Methods ── */}
      <section className="rounded-xl border border-line bg-panel p-5">
        <h2 className="text-sm font-semibold text-ink">{t("sources.import_paths_title")}</h2>
        <p className="mt-1 text-xs text-muted">{t("sources.import_paths_desc")}</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <ImportPathCard icon={FolderOpen} title={t("sources.import_path_watch_title")} desc={t("sources.import_path_watch_desc")} />
          <ImportPathCard icon={Terminal} title={t("sources.import_path_oneshot_title")} desc={t("sources.import_path_oneshot_desc")} />
          <ImportPathCard icon={Clipboard} title={t("sources.import_path_paste_title")} desc={t("sources.import_path_paste_desc")} />
        </div>
      </section>

      {/* ── Watched Sources ── */}
      <section className="rounded-xl border border-line bg-panel p-5 shadow-subtle">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-base font-semibold text-ink">{t("sources.watched_sources")}</h2>
            <p className="mt-1 text-sm text-muted">{t("sources.watched_sources_desc")}</p>
          </div>
          {data.watched_sources.some((s) => s.status_label === "Missing" || s.status === "missing") && (
            <button
              className="rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-40"
              style={{ borderColor: "var(--mf-error)", color: "var(--mf-error)", background: "rgba(208, 75, 75, 0.04)" }}
              disabled={busy}
              onClick={cleanupMissingSources}
              type="button"
            >
              {t("sources.cleanup_missing")}
            </button>
          )}
        </div>
        {result && <p className="mt-3 text-sm text-primary">{result}</p>}
        <div className="mt-4 space-y-3">
          {data.watched_sources.length === 0 ? (
            <div className="rounded-xl border border-dashed border-line p-8 text-center">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full" style={{ background: "var(--mf-accent-soft)" }}>
                <FolderOpen className="h-6 w-6" style={{ color: "var(--mf-accent)" }} />
              </div>
              <p className="font-medium text-ink" style={{ fontFamily: "var(--mf-font-serif)" }}>
                {t("sources.empty_watched_title")}
              </p>
              <p className="mt-1 text-sm" style={{ color: "var(--mf-text-tertiary)" }}>
                {t("sources.empty_watched_desc")}
              </p>
              <button
                className="mt-4 mf-primary-button rounded-lg px-4 py-2 text-sm"
                onClick={() => setShowAddPanel(true)}
                type="button"
              >
                {t("sources.add_source_in_setup")}
              </button>
            </div>
          ) : (
            data.watched_sources.map((source) => {
              const isMissingOrError = source.status_label === "Missing" || source.status === "missing" || source.status_label === "Error" || source.status === "error";
              return (
              <article
                key={source.id}
                className={`rounded-xl border transition-colors ${
                  isMissingOrError
                    ? "border-[var(--mf-error)]/20 bg-[var(--mf-error)]/3 opacity-75 hover:opacity-100 hover:border-[var(--mf-error)]/30"
                    : "border-line hover:border-[var(--mf-accent)]/15"
                }`}
                style={{ borderRadius: "var(--mf-radius-lg)" }}
              >
                {/* Source header row */}
                <div className="flex items-start justify-between gap-4 p-4">
                  <div className="flex items-start gap-3 min-w-0">
                    <div
                      className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
                      style={{ background: "var(--mf-accent-soft)", color: "var(--mf-accent)" }}
                    >
                      {getSourceIcon(source)}
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-sm font-semibold text-ink truncate">
                        {sourceLabel(source)}
                      </h3>
                      <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5">
                        <span className="rounded-full px-1.5 py-0.5 text-[10px] font-medium" style={{ background: source.is_default ? "var(--mf-surface-alt)" : "var(--mf-accent-faint)", color: source.is_default ? "var(--mf-text-tertiary)" : "var(--mf-accent)" }}>
                          {source.is_default ? t("sources.builtin_inbox") : t("sources.user_added_source")}
                        </span>
                        <span className="text-[11px]" style={{ color: "var(--mf-text-tertiary)" }}>
                          {source.path_type}
                          {source.path_type === "folder" ? (source.recursive ? " · recursive" : " · flat") : ""}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <button
                      className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:border-[var(--mf-accent)]/30 disabled:opacity-40"
                      disabled={busy}
                      onClick={() => scanWatch(source.id)}
                      type="button"
                    >
                      {busy ? t("sources.processing") : t("sources.process_now")}
                    </button>
                    <button
                      className="rounded-lg px-3 py-1.5 text-xs font-bold text-white transition-all"
                      style={{
                        background: "linear-gradient(135deg, var(--mf-accent), #6f5cff)",
                        boxShadow: "0 6px 16px rgba(91, 70, 246, 0.2)",
                      }}
                      onClick={() => onNavigate("/review")}
                      type="button"
                    >
                      {t("sources.browse_drafts")}
                    </button>
                  </div>
                </div>

                {/* Expandable details */}
                <button
                  type="button"
                  className="w-full border-t border-line px-4 py-2 text-left text-xs font-medium transition-colors hover:bg-stone-50"
                  style={{ color: "var(--mf-text-tertiary)" }}
                  onClick={() => setExpandedSourceId(expandedSourceId === source.id ? null : source.id)}
                >
                  {expandedSourceId === source.id ? t("sources.collapse_details") : t("sources.view_details")}
                </button>

                {expandedSourceId === source.id && (
                  <div className="border-t border-line px-4 pb-4 pt-3 space-y-4">
                    {/* Path info */}
                    <div>
                      <div className="text-[10px] font-semibold uppercase tracking-wide" style={{ color: "var(--mf-text-tertiary)" }}>
                        {t("sources.path")}
                      </div>
                      <div className="mt-1 break-all text-sm text-ink">
                        {sourceDisplayPath(source)}
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <button
                          className="rounded-md border border-line px-2 py-1 text-xs text-ink disabled:opacity-50"
                          disabled={!source.source_path_view?.can_copy_display_path}
                          onClick={() => copySourcePath(source)}
                          type="button"
                        >
                          {source.source_path_view?.can_copy_full_path ? t("sources.copy_path") : t("sources.copy_display_path")}
                        </button>
                      </div>
                    </div>

                    {/* Metrics grid */}
                    <div>
                      <div className="text-[10px] font-semibold uppercase tracking-wide" style={{ color: "var(--mf-text-tertiary)" }}>
                        {t("sources.last_run_summary")}
                      </div>
                      <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-6">
                        <MetricItem label={t("sources.status")} value={source.status_label || sourceStatusLabel(source.status, locale)} />
                      <MetricItem label={t("sources.run_status")} value={sourceRunStatusLabel(source.processing_status, locale)} />
                      <MetricItem label={t("sources.metric_new")} value={source.diff_counts.added ?? 0} />
                      <MetricItem label={t("sources.metric_changed")} value={source.diff_counts.changed ?? 0} />
                      <MetricItem label={t("sources.metric_drafts")} value={source.last_run_summary?.drafts ?? source.generated_draft_count ?? 0} />
                      <MetricItem label={t("sources.metric_errors")} value={source.last_run_summary?.errors ?? source.failed_count} />
                    </div>
                    </div>

                    {/* Status messages */}
                    {source.processing_status === "queued" || source.processing_status === "running" ? (
                      <div className="rounded-md border border-[var(--mf-accent)]/20 bg-[var(--mf-accent)]/5 p-3 text-sm" style={{ color: "var(--mf-accent)" }}>
                        {t("sources.processing_background")}
                      </div>
                    ) : null}
                    {source.last_message ? (
                      <div className={source.processing_status === "failed" || source.processing_status === "partial_failed"
                        ? "rounded-md border border-[var(--mf-error)]/20 bg-[var(--mf-error)]/5 p-3 text-sm"
                        : "rounded-md border border-line bg-stone-50 p-3 text-sm text-ink"}
                      >
                        {source.last_message}
                        {source.last_error && <div className="mt-1 text-xs" style={{ color: "var(--mf-error)" }}>{source.last_error}</div>}
                      </div>
                    ) : null}

                    {/* Frequency + Actions */}
                    <div className="flex flex-wrap items-center gap-3">
                      <div>
                        <div className="text-[10px] font-semibold uppercase tracking-wide" style={{ color: "var(--mf-text-tertiary)" }}>
                          {t("sources.frequency")}
                        </div>
                        <select
                          className="mt-1 rounded-md border border-line bg-white px-2 py-1 text-xs disabled:bg-stone-100"
                          disabled={busy}
                          onChange={(event) => setRowFrequencies({ ...rowFrequencies, [source.id]: event.target.value })}
                          value={rowFrequencies[source.id] ?? source.frequency}
                        >
                          {getFrequencyOptions(t).map((item) => (
                            <option key={item.value} value={item.value}>{item.label}</option>
                          ))}
                        </select>
                        <button
                          className="ml-2 rounded-md border border-line px-2 py-1 text-xs text-ink disabled:opacity-50"
                          disabled={busy}
                          onClick={() => editFrequency(source.id, source.frequency)}
                          type="button"
                        >
                          {t("sources.edit_frequency")}
                        </button>
                      </div>
                      <button
                        className="rounded-md border border-line px-2 py-1 text-xs text-ink disabled:opacity-50"
                        disabled={busy}
                        onClick={() => removeWatch(source)}
                        type="button"
                      >
                        {t("sources.stop_watching")}
                      </button>
                    </div>

                    {/* Diagnostics */}
                    <details className="rounded-md border border-line p-3">
                      <summary className="cursor-pointer text-xs font-medium text-ink">{t("sources.diagnostics")}</summary>
                      <p className="mt-2 text-[11px] text-muted">
                        {t("sources.skipped_reasons")}: {Object.keys(source.skipped_reason_summary).length
                          ? Object.entries(source.skipped_reason_summary).map(([reason, count]) => `${reason} ×${count}`).join(", ")
                          : "none"}
                      </p>
                    </details>
                  </div>
                )}
              </article>
              );
            })
          )}
        </div>
        {data.watched_sources.length > 0 && (
          <p className="mt-3 text-xs" style={{ color: "var(--mf-text-tertiary)" }}>{t("sources.remove_warning")}</p>
        )}
      </section>

      {/* ── Adapter Request ── */}
      <section className="mf-card-soft rounded-lg p-4 flex items-center justify-between flex-wrap gap-3">
        <div>
          <p className="text-sm font-medium text-ink">{t("sources.adapter_request_title")}</p>
          <p className="text-xs" style={{ color: "var(--mf-text-tertiary)" }}>{t("sources.adapter_request_desc")}</p>
        </div>
        <a
          href="https://github.com/yaoziyaoguai/mindforge/issues"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 rounded-lg border border-line px-3 py-2 text-xs font-medium text-ink transition-colors hover:border-[var(--mf-accent)]/30"
        >
          {t("sources.request_adapter_btn")}
          <ExternalLink className="h-3 w-3" />
        </a>
      </section>
    </div>
  );
}

function MetricItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md border border-line bg-stone-50 px-2.5 py-2">
      <div className="text-[10px] text-muted">{label}</div>
      <div className="mt-0.5 text-base font-semibold leading-none text-ink">{value}</div>
    </div>
  );
}

function getSourceIcon(source: SourcesResponse["watched_sources"][number]) {
  if (source.path_type === "folder") return <FolderOpen className="h-5 w-5" />;
  return <FileText className="h-5 w-5" />;
}

function sourceLabel(source: SourcesResponse["watched_sources"][number]) {
  if (source.is_default) return source.source_path_view?.display_source_name ?? source.source_path_view?.display_path ?? source.id;
  return source.source_path_view?.display_source_name ?? source.source_path_view?.display_path ?? source.id;
}

function sourceDisplayPath(source: SourcesResponse["watched_sources"][number]) {
  return source.source_path_view?.display_path ?? source.path ?? "-";
}

function formatRunSummary(message: string, counts: Record<string, number>, runId?: string | null) {
  if (message.toLowerCase().includes("background")) {
    return `${message}${runId ? ` Run: ${runId}` : ""}`;
  }
  const filesScanned = counts.scanned ?? counts.seen ?? counts.processed ?? 0;
  const skipped = counts.skipped ?? 0;
  const draftsCreated = counts.processed ?? 0;
  const errors = counts.failed ?? 0;
  return `${message}; files scanned=${filesScanned}, skipped=${skipped}, drafts created=${draftsCreated}, errors=${errors}`;
}

function ImportPathCard({ icon: Icon, title, desc }: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  desc: string;
}) {
  return (
    <div className="flex gap-3 rounded-lg border border-line bg-white p-3">
      <Icon className="h-5 w-5 shrink-0 text-muted mt-0.5" aria-hidden="true" />
      <div>
        <h3 className="text-sm font-medium text-ink">{title}</h3>
        <p className="mt-1 text-xs text-muted leading-relaxed">{desc}</p>
      </div>
    </div>
  );
}
