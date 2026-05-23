import { useRef, useState } from "react";
import { addWatchedSource } from "../api/sources";
import { useLocale } from "../lib/i18n";
import type { TFunc } from "../lib/i18n";

export function SourceAddPanel({ onRefresh, hasModels }: { onRefresh?: () => Promise<void> | void; hasModels?: boolean }) {
  const [path, setPath] = useState("");
  const [frequency, setFrequency] = useState("manual");
  const [result, setResult] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const { t } = useLocale();

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
    setResult(processNow ? t("source_add.starting_background") : t("source_add.adding"));
    try {
      const response = await addWatchedSource(path.trim(), frequency, true, processNow);
      setResult(formatRunSummary(response.message, response.counts, response.run_id));
      await onRefresh?.();
    } catch (error) {
      setResult(error instanceof Error ? error.message : t("source_add.request_failed"));
    } finally {
      setBusy(false);
    }
  }

  const freqOptions = getFrequencyOptions(t);

  return (
    <section className="rounded-md border border-line p-4">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-ink">{t("source_add.title")}</h2>
        <p className="mt-1 text-sm text-muted">{t("source_add.desc")}</p>
        <p className="mt-1 text-sm text-muted">{t("source_add.manual_desc")}</p>
        {!hasModels ? (
          <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            {t("source_add.no_model_warning")}{" "}<a href="/setup" className="underline">{t("source_add.add_model_link")}</a>。
          </p>
        ) : null}
      </div>
      <div className="space-y-3">
        <div className="flex gap-2">
          <label className="flex-1 space-y-1 text-sm">
            <span className="font-medium text-ink">{t("source_add.path_input")}</span>
            <input
              className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm"
              onChange={(event) => setPath(event.target.value)}
              placeholder="/path/to/file-or-folder"
              value={path}
            />
          </label>
          <div className="flex gap-1 self-end">
            <input ref={fileInputRef} className="hidden" type="file" onChange={handleFileSelect} />
            <button className="rounded-md border border-line px-3 py-2 text-xs font-medium text-ink hover:bg-stone-100" onClick={() => fileInputRef.current?.click()} type="button" title={t("source_add.pick_file_tooltip")}>
              {t("source_add.pick_file")}
            </button>
            <input ref={folderInputRef} className="hidden" type="file" {...{ webkitdirectory: "" } as any} onChange={handleFileSelect} />
            <button className="rounded-md border border-line px-3 py-2 text-xs font-medium text-ink hover:bg-stone-100" onClick={() => folderInputRef.current?.click()} type="button" title={t("source_add.pick_folder_tooltip")}>
              {t("source_add.pick_folder")}
            </button>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm">
            <span className="font-medium text-ink">{t("source_add.frequency")}</span>
            <select className="rounded-md border border-line bg-white px-3 py-2 text-sm" value={frequency} onChange={(event) => setFrequency(event.target.value)}>
              {freqOptions.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
          </label>
          <button className="rounded-md border border-line px-4 py-2 text-sm font-medium text-ink disabled:opacity-50" disabled={busy || !path.trim()} onClick={() => addSource(false)} type="button">
            {busy ? t("source_add.adding") : t("source_add.add_source")}
          </button>
          <button className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50" disabled={busy || !path.trim() || !hasModels} onClick={() => addSource(true)} type="button" title={!hasModels ? t("source_add.configure_model_first") : undefined}>
            {busy ? t("source_add.adding") : t("source_add.add_and_process")}
          </button>
        </div>
      </div>
      {!path.trim() ? (
        <p className="mt-2 text-xs text-muted">{t("source_add.path_hint")}</p>
      ) : null}
      {result ? <p className="mt-3 text-sm text-primary">{result}</p> : null}
      <button className="mt-3 text-sm text-primary" onClick={() => { window.location.hash = "#/sources"; }} type="button">
        {t("source_add.view_in_sources")}
      </button>
    </section>
  );
}

/** 返回本地化的监测频率选项列表。value 保持为 API 所需的 machine-readable string，
 *  label 根据当前 locale 展示本地化文案。 */
export function getFrequencyOptions(t: TFunc) {
  return [
    { value: "manual", label: t("source_add.freq_manual") },
    { value: "hourly", label: t("source_add.freq_hourly") },
    { value: "daily", label: t("source_add.freq_daily") },
    { value: "weekly", label: t("source_add.freq_weekly") },
    { value: "every 1h", label: t("source_add.freq_every_1h") },
    { value: "every 6h", label: t("source_add.freq_every_6h") },
    { value: "every 12h", label: t("source_add.freq_every_12h") },
    { value: "every 24h", label: t("source_add.freq_every_24h") },
  ];
}

function formatRunSummary(message: string, counts: Record<string, number>, runId?: string | null) {
  if (message.toLowerCase().includes("background")) {
    return `${message}${runId ? ` Run: ${runId}` : ""}${counts.seen ? `; queued files=${counts.seen}` : ""}`;
  }
  const filesScanned = counts.scanned ?? counts.seen ?? counts.processed ?? 0;
  const skipped = counts.skipped ?? 0;
  const draftsCreated = counts.processed ?? 0;
  const errors = counts.failed ?? 0;
  return `${message}; completed; files scanned=${filesScanned}, skipped=${skipped}, drafts created=${draftsCreated}, errors=${errors}`;
}
