import type { SourcesResponse } from "../api/types";
import { copySourcePath, deleteWatchedSource, revealSourcePath, scanWatchedSources, updateWatchedSourceFrequency } from "../api/sources";
import { frequencyOptions } from "../components/SourceAddPanel";
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

  async function removeWatch(ref: string) {
    setBusy(true);
    setResult(null);
    try {
      const response = await deleteWatchedSource(ref);
      setResult(response.message);
      await onRefresh?.();
    } catch (error) {
      setResult(error instanceof Error ? error.message : "Request failed");
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
      setResult(error instanceof Error ? error.message : "Edit frequency failed");
    } finally {
      setBusy(false);
    }
  }

  async function scanWatch(ref?: string, allSources = false) {
    setBusy(true);
    setResult("Processing...");
    try {
      const response = await scanWatchedSources(ref, allSources);
      setResult(formatRunSummary(response.message, response.counts));
      await onRefresh?.();
    } catch (error) {
      setResult(error instanceof Error ? error.message : "Process failed");
    } finally {
      setBusy(false);
    }
  }

  async function copyPath(targetPath: string) {
    setResult(null);
    try {
      const response = await copySourcePath(targetPath);
      await navigator.clipboard?.writeText(response.path);
      setResult("Copied");
    } catch (error) {
      setResult(error instanceof Error ? error.message : "Copy path failed");
    }
  }

  async function revealPath(targetPath: string) {
    setResult(null);
    try {
      const response = await revealSourcePath(targetPath);
      setResult(response.ok ? "Opened" : response.message);
    } catch (error) {
      setResult(error instanceof Error ? error.message : "Reveal in Finder failed");
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">Sources</h1>
        <p className="mt-1 text-sm text-muted">MindForge monitors local files and folders. New or changed supported files create draft knowledge cards; approval is always explicit.</p>
        <button className="mt-3 rounded-md border border-line px-3 py-2 text-sm font-medium text-ink" onClick={() => onNavigate("/setup")} type="button">
          Add source in Setup
        </button>
      </header>
      <section className="rounded-md border border-line bg-panel p-4 shadow-subtle">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-ink">Watched sources</h2>
            <p className="mt-1 text-sm text-muted">Manage existing watched files and folders. Adding a new source starts in Setup.</p>
          </div>
          <button className="rounded-md border border-line px-3 py-2 text-sm font-medium text-ink" onClick={() => onNavigate("/setup")} type="button">
            Add source in Setup
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
                      <span className="rounded-md bg-stone-100 px-2 py-1 text-xs text-muted">{source.is_default ? "Built-in inbox" : "User-added source"}</span>
                    </div>
                    <p className="mt-1 text-xs text-muted">Source details: {source.path_type}{source.path_type === "folder" ? ` · ${source.recursive ? "Recursive: yes" : "Recursive: no"}` : ""}</p>
                  </div>
                  <div>
                    <div className="text-xs font-medium uppercase text-muted">Path</div>
                    <div className="mt-1 break-all text-sm text-ink">{source.path}</div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <button className="rounded-md border border-line px-2 py-1 text-xs text-ink" onClick={() => copyPath(source.path)} type="button">
                        Copy path
                      </button>
                      <button className="rounded-md border border-line px-2 py-1 text-xs text-ink" onClick={() => revealPath(source.path)} type="button">
                        Reveal in Finder
                      </button>
                    </div>
                  </div>
                  <div className="grid gap-3 md:grid-cols-3">
                    <SummaryItem label="Status" value={source.status_label || (source.status === "active" ? "Watching" : source.status)} />
                    <SummaryItem label="Last scan" value={source.last_scan_at ?? source.last_processed_at ?? source.last_seen_at ?? "-"} />
                    <SummaryItem label="Next scan / Due" value={`${source.next_scan_at ?? "-"} · ${source.due_status}`} />
                  </div>
                  <div>
                    <div className="text-xs font-medium uppercase text-muted">Frequency</div>
                    <div className="mt-1 text-sm text-ink">{source.frequency}</div>
                    <select
                      className="mt-2 w-full max-w-[220px] rounded-md border border-line bg-white px-2 py-1 text-xs disabled:bg-stone-100"
                      disabled={busy || !source.can_delete}
                      onChange={(event) => setRowFrequencies({ ...rowFrequencies, [source.id]: event.target.value })}
                      title={source.can_delete ? "Edit frequency" : "Built-in inbox frequency is fixed."}
                      value={rowFrequencies[source.id] ?? source.frequency}
                    >
                      {frequencyOptions.map((item) => (
                        <option key={item.value} value={item.value}>{item.label}</option>
                      ))}
                    </select>
                    {!source.can_delete ? <p className="mt-1 text-xs text-muted">Built-in inbox frequency is fixed.</p> : null}
                  </div>
                  <details className="rounded-md border border-line p-3">
                    <summary className="cursor-pointer text-sm font-medium text-ink">Diagnostics</summary>
                    <p className="mt-2 text-xs text-muted">
                      Skipped reasons: {Object.keys(source.skipped_reason_summary).length ? Object.entries(source.skipped_reason_summary).map(([reason, count]) => `${reason} ${count}`).join(", ") : "none"}
                    </p>
                  </details>
                </div>
                <div className="space-y-4">
                  <div>
                    <div className="text-xs font-medium uppercase text-muted">Last run summary</div>
                    <div className="mt-2 grid grid-cols-2 gap-2">
                      <SummaryMetric label="New" value={source.diff_counts.added ?? 0} />
                      <SummaryMetric label="Changed" value={source.diff_counts.changed ?? 0} />
                      <SummaryMetric label="Missing" value={source.diff_counts.deleted ?? 0} />
                      <SummaryMetric label="Skipped" value={source.skipped_count} />
                      <SummaryMetric label="Drafts created" value={source.generated_card_count} />
                      <SummaryMetric label="Errors" value={source.failed_count} />
                    </div>
                  </div>
                  <div>
                    <div className="text-xs font-medium uppercase text-muted">Actions</div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <button className="rounded-md bg-primary px-3 py-1 text-xs font-medium text-white disabled:opacity-50" disabled={busy} onClick={() => scanWatch(source.id)} type="button">
                        {busy ? "Processing..." : "Process now"}
                      </button>
                      <button className="rounded-md border border-line px-3 py-1 text-xs text-primary" onClick={() => onNavigate("/library")} type="button">
                        Open related knowledge
                      </button>
                      <button className="rounded-md border border-line px-3 py-1 text-xs text-ink disabled:opacity-50" disabled={busy || !source.can_delete} onClick={() => editFrequency(source.id, source.frequency)} title={source.can_delete ? "Edit frequency" : "Built-in inbox frequency is fixed."} type="button">
                        Edit frequency
                      </button>
                      <button className="rounded-md border border-line px-3 py-1 text-xs text-ink" onClick={() => copyPath(source.path)} type="button">
                        Copy path
                      </button>
                      <button className="rounded-md border border-line px-3 py-1 text-xs text-ink" onClick={() => revealPath(source.path)} type="button">
                        Reveal in Finder
                      </button>
                      <button className="rounded-md border border-line px-3 py-1 text-xs text-ink disabled:opacity-50" disabled={busy || !source.can_delete} onClick={() => removeWatch(source.id)} title={source.can_delete ? "Remove" : "Built-in inbox cannot be removed."} type="button">
                        Remove
                      </button>
                    </div>
                    {!source.can_delete ? <p className="mt-2 text-xs text-muted">Built-in inbox cannot be removed.</p> : null}
                  </div>
                </div>
              </div>
            </article>
          ))}
        </div>
        <p className="mt-3 text-sm text-muted">Removing a watched source only stops future intake. It does not delete original files or knowledge cards.</p>
      </section>
      <section className="rounded-md border border-line bg-panel p-4 shadow-subtle">
        <h2 className="text-lg font-semibold text-ink">Advanced / Technical details</h2>
        <p className="mt-2 text-sm text-muted">{data.ingestion.advanced_note}</p>
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

function formatRunSummary(message: string, counts: Record<string, number>) {
  const filesScanned = counts.scanned ?? counts.seen ?? counts.processed ?? 0;
  const skipped = counts.skipped ?? 0;
  const draftsCreated = counts.processed ?? 0;
  const errors = counts.failed ?? 0;
  return `${message}; files scanned=${filesScanned}, skipped=${skipped}, drafts created=${draftsCreated}, errors=${errors}`;
}

function sourceLabel(source: SourcesResponse["watched_sources"][number]) {
  if (source.is_default) return "Built-in inbox";
  const cleanPath = source.path.replace(/\/$/, "");
  return cleanPath.split("/").pop() || source.path;
}
