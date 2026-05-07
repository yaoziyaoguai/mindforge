import { useState } from "react";
import { addWatchedSource } from "../api/sources";

export function SourceAddPanel({ onRefresh }: { onRefresh?: () => Promise<void> | void }) {
  const [path, setPath] = useState("");
  const [frequency, setFrequency] = useState("manual");
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

  return (
    <section className="rounded-md border border-line p-4">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-ink">Add a file or folder</h2>
        <p className="mt-1 text-sm text-muted">
          MindForge automatically detects whether the path is a file or folder. Folders are scanned recursively. Frequency applies only to the top-level source you add.
        </p>
        <p className="mt-1 text-sm text-muted">
          Manual means no automatic scanning. Automation only creates draft knowledge cards. Approved knowledge requires explicit approval.
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
      {result ? <p className="mt-3 text-sm text-primary">{result}</p> : null}
      <button className="mt-3 text-sm text-primary" onClick={() => { window.location.hash = "#/sources"; }} type="button">
        View in Sources
      </button>
    </section>
  );
}

export const frequencyOptions = [
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
  return `${message}; completed; files scanned=${filesScanned}, skipped=${skipped}, drafts created=${draftsCreated}, errors=${errors}`;
}
