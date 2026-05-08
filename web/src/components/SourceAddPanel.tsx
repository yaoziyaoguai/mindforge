import { useRef, useState } from "react";
import { addWatchedSource } from "../api/sources";

export function SourceAddPanel({ onRefresh, hasModels }: { onRefresh?: () => Promise<void> | void; hasModels?: boolean }) {
  const [path, setPath] = useState("");
  const [frequency, setFrequency] = useState("manual");
  const [result, setResult] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  /** 从文件/文件夹选择器获取最佳可用路径，填入文本输入框。

  浏览器限制：不返回绝对路径。webkitRelativePath 提供文件夹内的相对路径；
  单文件选择仅返回文件名。选择后请手动补全或粘贴目录前缀。*/
  function handleFileSelect(event: React.ChangeEvent<HTMLInputElement>) {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    const first = files[0];
    // webkitRelativePath (文件夹内相对路径) > name (单文件名)
    const selected = (first as any).webkitRelativePath || first.name;
    setPath(selected);
    event.target.value = "";
  }

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
        {!hasModels ? (
          <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            No model configured. You can register a source now, but AI draft generation requires a configured model. <a href="/setup" className="underline">Add a model in Setup</a> before processing sources.
          </p>
        ) : null}
      </div>
      <div className="space-y-3">
        <div className="flex gap-2">
          <label className="flex-1 space-y-1 text-sm">
            <span className="font-medium text-ink">Path input</span>
            <input
              className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm"
              onChange={(event) => setPath(event.target.value)}
              placeholder="/path/to/file-or-folder"
              value={path}
            />
          </label>
          <div className="flex gap-1 self-end">
            <input ref={fileInputRef} className="hidden" type="file" onChange={handleFileSelect} />
            <button className="rounded-md border border-line px-3 py-2 text-xs font-medium text-ink hover:bg-stone-100" onClick={() => fileInputRef.current?.click()} type="button" title="Choose a file">
              Choose File
            </button>
            <input ref={folderInputRef} className="hidden" type="file" {...{ webkitdirectory: "" } as any} onChange={handleFileSelect} />
            <button className="rounded-md border border-line px-3 py-2 text-xs font-medium text-ink hover:bg-stone-100" onClick={() => folderInputRef.current?.click()} type="button" title="Choose a folder">
              Choose Folder
            </button>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm">
            <span className="font-medium text-ink">Frequency</span>
            <select className="rounded-md border border-line bg-white px-3 py-2 text-sm" value={frequency} onChange={(event) => setFrequency(event.target.value)}>
              {frequencyOptions.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
          </label>
          <button className="rounded-md border border-line px-4 py-2 text-sm font-medium text-ink disabled:opacity-50" disabled={busy || !path.trim()} onClick={() => addSource(false)} type="button">
            {busy ? "Processing..." : "Add source"}
          </button>
          <button className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50" disabled={busy || !path.trim() || !hasModels} onClick={() => addSource(true)} type="button" title={!hasModels ? "Configure a model before processing" : undefined}>
            {busy ? "Processing..." : "Add and process now"}
          </button>
        </div>
      </div>
      {!path.trim() ? (
        <p className="mt-2 text-xs text-muted">Type or paste the full path. Choose File / Choose Folder can fill in the name, but you still need to type or paste the directory portion.</p>
      ) : null}
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
