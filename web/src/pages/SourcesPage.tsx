import type { SourcesResponse } from "../api/types";
import { addWatchedSource, copySourcePath, deleteWatchedSource, importSource, revealSourcePath } from "../api/sources";
import { SourceList } from "../components/SourceList";
import { StatusCard } from "../components/StatusCard";
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
  const [result, setResult] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(action: "watch" | "import") {
    if (!path.trim()) return;
    setBusy(true);
    setResult(null);
    try {
      const response = action === "watch"
        ? await addWatchedSource(path.trim())
        : await importSource(path.trim());
      setResult(`${response.message}; processed=${response.counts.processed ?? 0}, skipped=${response.counts.skipped ?? 0}`);
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
        <p className="mt-1 text-sm text-muted">Add original material and review the knowledge generated from it.</p>
      </header>
      <section className="rounded-md border border-line bg-panel p-4 shadow-subtle">
        <div className="grid gap-3 md:grid-cols-[1fr_auto_auto]">
          <input
            className="min-w-0 rounded-md border border-line bg-white px-3 py-2 text-sm"
            onChange={(event) => setPath(event.target.value)}
            placeholder="/path/to/file-or-folder"
            value={path}
          />
          <button className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50" disabled={busy || !path.trim()} onClick={() => run("watch")} type="button">
            Watch add
          </button>
          <button className="rounded-md border border-line px-4 py-2 text-sm font-medium text-ink disabled:opacity-50" disabled={busy || !path.trim()} onClick={() => run("import")} type="button">
            Import once
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
                <th className="px-4 py-3 font-medium">Last processed</th>
                <th className="px-4 py-3 font-medium">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {data.watched_sources.map((source) => (
                <tr key={source.id}>
                  <td className="px-4 py-3">
                    <div className="font-medium text-ink">{source.id}</div>
                    <div className="text-xs text-muted">{source.path_type} · {source.kind}</div>
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
                    <div className="mt-1 text-xs text-muted">{source.generated_knowledge_status}</div>
                    <div className="mt-1 text-xs text-muted">
                      supported={source.supported_file_count} processed={source.processed_count} skipped={source.skipped_count} failed={source.failed_count}
                    </div>
                    {Object.keys(source.skipped_reason_summary).length ? (
                      <div className="mt-1 text-xs text-muted">
                        Skipped reasons: {Object.entries(source.skipped_reason_summary).map(([reason, count]) => `${reason} ${count}`).join(", ")}
                      </div>
                    ) : null}
                  </td>
                  <td className="px-4 py-3 text-muted">{source.last_processed_at ?? source.last_seen_at ?? "-"}</td>
                  <td className="px-4 py-3">
                    {source.can_delete ? (
                      <button className="rounded-md border border-line px-3 py-1 text-xs text-ink disabled:opacity-50" disabled={busy} onClick={() => removeWatch(source.id)} type="button">
                        Delete watch
                      </button>
                    ) : (
                      <span className="text-xs text-muted">default cannot be deleted</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-sm text-muted">Removing a watched source only stops future intake. It does not delete original files or knowledge cards.</p>
      </section>
      <SourceList sources={data.sources} onCopyPath={copyPath} onRevealPath={revealPath} onOpenCards={() => onNavigate("/library")} />
      <section className="grid gap-4 md:grid-cols-2">
        {data.available_imports.map((item) => (
          <StatusCard key={item.key} label={item.label} value={item.value} status={item.status} detail={item.detail} nextAction={item.next_action} />
        ))}
      </section>
      <section className="rounded-md border border-line bg-panel p-4 shadow-subtle">
        <h2 className="text-lg font-semibold text-ink">Advanced / Troubleshooting</h2>
        <p className="mt-2 text-sm text-muted">{data.ingestion.advanced_note}</p>
        <code className="mt-3 block text-xs text-ink">mindforge import /path/to/source</code>
      </section>
    </div>
  );
}
