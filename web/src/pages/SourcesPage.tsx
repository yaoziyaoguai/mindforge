import type { SourcesResponse } from "../api/types";
import { deleteWatchedSource, scanWatchedSources, updateWatchedSourceFrequency } from "../api/sources";
import { getFrequencyOptions } from "../components/SourceAddPanel";
import { useLocale } from "../lib/i18n";
import { sourceDueStatusLabel, sourceRunStatusLabel, sourceStatusLabel } from "../lib/utils";
import { useState } from "react";

export function SourcesPage({
  data,
  onNavigate,
  onRefresh,
}: {
  data: SourcesResponse;
  onNavigate: (href: string) => void;
  onRefresh?: () => Promise<void>;
}) {
  const [rowFrequencies, setRowFrequencies] = useState<Record<string, string>>({});
  const [result, setResult] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
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

  /* 中文学习型说明：client-side clipboard copy —— raw path endpoint 已禁用。
   * SourcesPage 只信任 source_path_view；没有 view 时 fail-closed。 */
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
  /* 中文学习型说明：raw path reveal 已禁用。SourcesPage 的 reveal 功能待
   * source-ref based endpoint 实现后恢复。 */

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">{t("sources.title")}</h1>
        <p className="mt-1 text-sm text-muted">{t("sources.subtitle")}</p>
        <button className="mt-3 rounded-md border border-line px-3 py-2 text-sm font-medium text-ink" onClick={() => onNavigate("/setup")} type="button">
          {t("sources.add_source_in_setup")}
        </button>
      </header>
      <section className="rounded-md border border-line bg-panel p-4 shadow-subtle">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-ink">{t("sources.watched_sources")}</h2>
            <p className="mt-1 text-sm text-muted">{t("sources.watched_sources_desc")}</p>
          </div>
          <button className="rounded-md border border-line px-3 py-2 text-sm font-medium text-ink" onClick={() => onNavigate("/setup")} type="button">
            {t("sources.add_source_in_setup")}
          </button>
        </div>
        {result ? <p className="mt-3 text-sm text-primary">{result}</p> : null}
        <div className="mt-4 space-y-4">
          {data.watched_sources.map((source) => (
            <article key={source.id} className="rounded-md border border-line p-4">
              <div className="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(260px,0.8fr)]">
                <div className="space-y-4">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-base font-semibold text-ink">{sourceLabel(source)}</h3>
                      <span className="rounded-md bg-stone-100 px-2 py-1 text-xs text-muted">{source.is_default ? t("sources.builtin_inbox") : t("sources.user_added_source")}</span>
                    </div>
                    <p className="mt-1 text-xs text-muted">{t("sources.source_details")}: {source.path_type}{source.path_type === "folder" ? ` · ${source.recursive ? t("sources.recursive_yes") : t("sources.recursive_no")}` : ""}</p>
                  </div>
                  <div>
                    <div className="text-xs font-medium uppercase text-muted">{t("sources.path")}</div>
                    <div className="mt-1 break-all text-sm text-ink">{sourceDisplayPath(source)}</div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <button className="rounded-md border border-line px-2 py-1 text-xs text-ink disabled:opacity-50" disabled={!source.source_path_view?.can_copy_display_path} onClick={() => copySourcePath(source)} type="button">
                        {source.source_path_view?.can_copy_full_path ? t("sources.copy_path") : t("sources.copy_display_path")}
                      </button>
                      {/* 中文学习型说明：raw path reveal 已禁用；source-ref reveal 待实现 */}
                    </div>
                  </div>
                  <div className="grid gap-3 md:grid-cols-3">
                    <SummaryItem label={t("sources.status")} value={source.status_label || sourceStatusLabel(source.status, locale)} />
                    <SummaryItem label={t("sources.run_status")} value={sourceRunStatusLabel(source.processing_status, locale)} />
                    <SummaryItem label={t("sources.last_scan")} value={source.last_scan_at ?? source.last_processed_at ?? source.last_seen_at ?? "-"} />
                    <SummaryItem label={t("sources.last_updated")} value={source.last_run_finished_at ?? source.last_run_started_at ?? "-"} />
                    <SummaryItem label={t("sources.next_scan_due")} value={`${source.next_scan_at ?? "-"} · ${sourceDueStatusLabel(source.due_status, locale)}`} />
                  </div>
                  {source.processing_status === "queued" || source.processing_status === "running" ? (
                    <div className="rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-primary">
                      {t("sources.processing_background")}
                    </div>
                  ) : null}
                  {source.last_message ? (
                    <div className={source.processing_status === "failed" || source.processing_status === "partial_failed" ? "rounded-md border border-red-200 bg-red-50 p-3 text-sm text-danger" : "rounded-md border border-line bg-stone-50 p-3 text-sm text-ink"}>
                      {source.last_message}
                      {source.last_error ? <div className="mt-1 text-xs text-danger">{source.last_error}</div> : null}
                      {source.processing_status === "failed" || source.processing_status === "partial_failed" ? <div className="mt-1 text-xs text-danger">{t("sources.try_process_again")}</div> : null}
                      {source.processing_status === "skipped" && (source.last_run_summary?.drafts ?? 0) === 0 ? <div className="mt-1 text-xs text-muted">{t("sources.no_draft_generated")}</div> : null}
                    </div>
                  ) : null}
                  <div>
                    <div className="text-xs font-medium uppercase text-muted">{t("sources.frequency")}</div>
                    <div className="mt-1 text-sm text-ink">{source.frequency}</div>
                    <select
                      id={`frequency-${source.id}`}
                      className="mt-2 w-full max-w-[220px] rounded-md border border-line bg-white px-2 py-1 text-xs disabled:bg-stone-100"
                      disabled={busy}
                      onChange={(event) => setRowFrequencies({ ...rowFrequencies, [source.id]: event.target.value })}
                      aria-label={t("sources.edit_frequency")}
                      title={t("sources.edit_frequency")}
                      value={rowFrequencies[source.id] ?? source.frequency}
                    >
                      {getFrequencyOptions(t).map((item) => (
                        <option key={item.value} value={item.value}>{item.label}</option>
                      ))}
                    </select>
                  </div>
                  <details className="rounded-md border border-line p-3">
                    <summary className="cursor-pointer text-sm font-medium text-ink">{t("sources.diagnostics")}</summary>
                    <p className="mt-2 text-xs text-muted">
                      {t("sources.skipped_reasons")}: {Object.keys(source.skipped_reason_summary).length ? Object.entries(source.skipped_reason_summary).map(([reason, count]) => `${reason} ${count}`).join(", ") : "none"}
                    </p>
                  </details>
                </div>
                <div className="space-y-4">
                  <div>
                    <div className="text-xs font-medium uppercase text-muted">{t("sources.last_run_summary")}</div>
                    <div className="mt-2 grid grid-cols-2 gap-2">
                      <SummaryMetric label={t("sources.metric_new")} value={source.diff_counts.added ?? 0} />
                      <SummaryMetric label={t("sources.metric_changed")} value={source.diff_counts.changed ?? 0} />
                      <SummaryMetric label={t("sources.metric_missing")} value={source.diff_counts.deleted ?? 0} />
                      {/* 中文学习型说明：用户看到的是最近一次 processing run 的结果，
                      因此 skipped/errors 优先使用 last_run_summary；source-level
                      discovery counts 只作为没有 run record 时的 fallback。 */}
                      <SummaryMetric label={t("sources.metric_skipped")} value={source.last_run_summary?.skipped ?? source.skipped_count} />
                      <SummaryMetric label={t("sources.metric_drafts")} value={source.last_run_summary?.drafts ?? source.generated_draft_count ?? source.generated_card_count} />
                      <SummaryMetric label={t("sources.metric_errors")} value={source.last_run_summary?.errors ?? source.failed_count} />
                    </div>
                  </div>
                  <div>
                    <div className="text-xs font-medium uppercase text-muted">{t("sources.actions")}</div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <button className="rounded-md bg-primary px-3 py-1 text-xs font-medium text-white disabled:opacity-50" disabled={busy} onClick={() => scanWatch(source.id)} type="button">
                        {busy ? t("sources.processing") : t("sources.process_now")}
                      </button>
                      <button className="rounded-md border border-line px-3 py-1 text-xs text-primary" onClick={() => onNavigate("/library")} type="button">
                        {t("sources.open_related_knowledge")}
                      </button>
                      <button className="rounded-md border border-line px-3 py-1 text-xs text-ink disabled:opacity-50" disabled={busy} onClick={() => editFrequency(source.id, source.frequency)} title={t("sources.edit_frequency")} type="button">
                        {t("sources.edit_frequency")}
                      </button>
                      <button className="rounded-md border border-line px-3 py-1 text-xs text-ink disabled:opacity-50" disabled={!source.source_path_view?.can_copy_display_path} onClick={() => copySourcePath(source)} type="button">
                        {source.source_path_view?.can_copy_full_path ? t("sources.copy_path") : t("sources.copy_display_path")}
                      </button>
                      {/* 中文学习型说明：raw path reveal 已禁用 */}
                      <button className="rounded-md border border-line px-3 py-1 text-xs text-ink disabled:opacity-50" disabled={busy} onClick={() => removeWatch(source)} title={t("sources.stop_watching")} type="button">
                        {t("sources.stop_watching")}
                      </button>
                    </div>
                    {source.is_default ? <p className="mt-2 text-xs text-muted">{t("sources.stop_watching_warning")}</p> : null}
                  </div>
                </div>
              </div>
            </article>
          ))}
        </div>
        <p className="mt-3 text-sm text-muted">{t("sources.remove_warning")}</p>
      </section>
      <section className="rounded-md border border-line bg-panel p-4 shadow-subtle">
        <h2 className="text-lg font-semibold text-ink">{t("sources.advanced_tech_details")}</h2>
        <p className="mt-2 text-sm text-muted">{t("sources.advanced_note_default")}</p>
        <code className="mt-3 block text-xs text-ink">mindforge import /path/to/source</code>
      </section>
    </div>
  );
}

function SummaryItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md border border-line px-3 py-2">
      <div className="text-xs text-muted">{label}</div>
      <div className="mt-1 break-words text-sm font-medium text-ink">{value}</div>
    </div>
  );
}

function SummaryMetric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md border border-line bg-stone-50 px-3 py-2">
      <div className="text-xs text-muted">{label}</div>
      <div className="mt-1 text-lg font-semibold leading-none text-ink">{value}</div>
    </div>
  );
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

function sourceLabel(source: SourcesResponse["watched_sources"][number]) {
  if (source.is_default) return source.source_path_view?.display_source_name ?? source.source_path_view?.display_path ?? source.id;
  return source.source_path_view?.display_source_name ?? source.source_path_view?.display_path ?? source.id;
}

function sourceDisplayPath(source: SourcesResponse["watched_sources"][number]) {
  return source.source_path_view?.display_path ?? source.path ?? "-";
}
