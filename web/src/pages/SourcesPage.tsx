import type { SourcesResponse } from "../api/types";
import { addWatchedSource, copySourcePath, deleteWatchedSource, revealSourcePath, scanWatchedSources, updateWatchedSourceFrequency } from "../api/sources";
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
  const [path, setPath] = useState("");
  const [frequency, setFrequency] = useState("manual");
  const [rowFrequencies, setRowFrequencies] = useState<Record<string, string>>({});
  const [result, setResult] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function addSource(processNow: boolean) {
    if (!path.trim()) return;
    setBusy(true);
    setResult(processNow ? "Processing..." : "Adding source...");
    try {
      const response = await addWatchedSource(path.trim(), frequency, true, processNow);
      setResult(formatRunSummary(response.message, response.counts));
      await onRefresh?.();
    } catch (error) {
      setResult(error instanceof Error ? error.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

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
      </header>
      <section className="rounded-md border border-line bg-panel p-4 shadow-subtle">
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-ink">Add a file or folder</h2>
          <p className="mt-1 text-sm text-muted">
            MindForge automatically detects whether the path is a file or folder. Folders are scanned recursively. Frequency applies only to the top-level source you add, not to files inside the folder.
          </p>
          <p className="mt-1 text-sm text-muted">
            Manual means no automatic scanning. Use Process now when you want MindForge to check this source. Automation only creates draft knowledge cards. Approved knowledge requires explicit approval.
          </p>
        </div>
        <div className="grid gap-3 md:grid-cols-[1fr_180px_auto_auto]">
          <label className="space-y-1 text-sm">
            <span className="font-medium text-ink">Path input</span>
            <input
              className="min-w-0 rounded-md border border-line bg-white px-3 py-2 text-sm"
              onChange={(event) => setPath(event.target.value)}
              placeholder="/path/to/file-or-folder"
              value={path}
            />
          </label>
          <label className="space-y-1 text-sm">
            <span className="font-medium text-ink">Frequency</span>
            <select className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm" value={frequency} onChange={(event) => setFrequency(event.target.value)}>
              {frequencyOptions.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
          </label>
          <button className="self-end rounded-md border border-line px-4 py-2 text-sm font-medium text-ink disabled:opacity-50" disabled={busy || !path.trim()} onClick={() => addSource(false)} type="button">
            {busy ? "Processing..." : "Add source"}
          </button>
          <button className="self-end rounded-md bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50" disabled={busy || !path.trim()} onClick={() => addSource(true)} type="button">
            {busy ? "Processing..." : "Add and process now"}
          </button>
        </div>
        <p className="mt-3 text-sm text-muted">{data.ingestion.safety_note}</p>
        {result ? <p className="mt-3 text-sm text-primary">{result}</p> : null}
      </section>
      <section className="rounded-md border border-line bg-panel p-4 shadow-subtle">
        <h2 className="text-lg font-semibold text-ink">Watched sources</h2>
        <div className="mt-3 overflow-hidden rounded-md border border-line">
          <table className="w-full text-left text-sm">
            <thead className="bg-stone-100 text-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Source</th>
                <th className="px-4 py-3 font-medium">Path</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Frequency</th>
                <th className="px-4 py-3 font-medium">Last scan</th>
                <th className="px-4 py-3 font-medium">Next scan</th>
                <th className="px-4 py-3 font-medium">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {data.watched_sources.map((source) => (
                <tr key={source.id}>
                  <td className="px-4 py-3">
                    <div className="font-medium text-ink">{sourceLabel(source)}</div>
                    <div className="text-xs text-muted">{source.path_type}{source.is_default ? " · built-in inbox" : ""}</div>
                    {source.path_type === "folder" ? (
                      <div className="mt-1 text-xs text-muted">{source.recursive ? "Recursive: yes" : "Recursive: no"}</div>
                    ) : null}
                  </td>
                  <td className="max-w-[320px] px-4 py-3 text-muted">
                    <div className="truncate">{source.path}</div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <button className="rounded-md border border-line px-2 py-1 text-xs text-ink" onClick={() => copyPath(source.path)} type="button">
                        Copy path
                      </button>
                      <button className="rounded-md border border-line px-2 py-1 text-xs text-ink" onClick={() => revealPath(source.path)} type="button">
                        Reveal in Finder
                      </button>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div>{source.status_label || (source.status === "active" ? "Watching" : source.status)}</div>
                    <div className="mt-1 text-xs text-muted">
                      New={source.diff_counts.added ?? 0} Changed={source.diff_counts.changed ?? 0} Missing={source.diff_counts.deleted ?? 0}
                    </div>
                    <div className="mt-1 text-xs text-muted">
                      New since last scan={source.diff_counts.added ?? 0} Changed since last scan={source.diff_counts.changed ?? 0} Deleted since last scan={source.diff_counts.deleted ?? 0}
                    </div>
                    <div className="mt-1 text-xs text-muted">
                      Skipped={source.skipped_count} Drafts created={source.generated_card_count}
                    </div>
                    {Object.keys(source.skipped_reason_summary).length ? (
                      <div className="mt-1 text-xs text-muted">
                        Skipped reasons: {Object.entries(source.skipped_reason_summary).map(([reason, count]) => `${reason} ${count}`).join(", ")}
                      </div>
                    ) : null}
                  </td>
                  <td className="px-4 py-3 text-muted">
                    <div>{source.frequency}</div>
                    <div className="text-xs">{source.due_status === "Due" ? "Due" : source.due_status}</div>
                    {source.can_delete ? (
                      <select
                        className="mt-2 w-full rounded-md border border-line bg-white px-2 py-1 text-xs"
                        disabled={busy}
                        onChange={(event) => setRowFrequencies({ ...rowFrequencies, [source.id]: event.target.value })}
                        value={rowFrequencies[source.id] ?? source.frequency}
                      >
                        {frequencyOptions.map((item) => (
                          <option key={item.value} value={item.value}>{item.label}</option>
                        ))}
                      </select>
                    ) : null}
                  </td>
                  <td className="px-4 py-3 text-muted">{source.last_scan_at ?? source.last_processed_at ?? source.last_seen_at ?? "-"}</td>
                  <td className="px-4 py-3 text-muted">{source.next_scan_at ?? "-"}</td>
                  <td className="px-4 py-3">
                    <button className="mb-2 block rounded-md border border-line px-3 py-1 text-xs text-ink disabled:opacity-50" disabled={busy} onClick={() => scanWatch(source.id)} type="button">
                      {busy ? "Processing..." : "Process now"}
                    </button>
                    {source.can_delete ? (
                      <button className="mb-2 block rounded-md border border-line px-3 py-1 text-xs text-ink disabled:opacity-50" disabled={busy} onClick={() => editFrequency(source.id, source.frequency)} type="button">
                        Edit frequency
                      </button>
                    ) : null}
                    {source.can_delete ? (
                      <button className="rounded-md border border-line px-3 py-1 text-xs text-ink disabled:opacity-50" disabled={busy} onClick={() => removeWatch(source.id)} type="button">
                        Remove
                      </button>
                    ) : (
                      <span className="text-xs text-muted">built-in inbox</span>
                    )}
                    {source.generated_card_count ? (
                      <button className="mt-2 block rounded-md border border-line px-3 py-1 text-xs text-primary" onClick={() => onNavigate("/library")} type="button">
                        Open related knowledge
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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

const frequencyOptions = [
  { value: "manual", label: "Manual" },
  { value: "hourly", label: "Hourly" },
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "every 1h", label: "Every 1h" },
  { value: "every 6h", label: "Every 6h" },
  { value: "every 12h", label: "Every 12h" },
  { value: "every 24h", label: "Every 24h" },
];

function formatRunSummary(message: string, counts: Record<string, number>) {
  const filesScanned = counts.scanned ?? counts.seen ?? counts.processed ?? 0;
  const skipped = counts.skipped ?? 0;
  const draftsCreated = counts.processed ?? 0;
  const errors = counts.failed ?? 0;
  return `${message}; files scanned=${filesScanned}, skipped=${skipped}, drafts created=${draftsCreated}, errors=${errors}`;
}

function sourceLabel(source: SourcesResponse["watched_sources"][number]) {
  if (source.is_default) return "System inbox";
  const cleanPath = source.path.replace(/\/$/, "");
  return cleanPath.split("/").pop() || source.path;
}
