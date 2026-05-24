/**
 * v2.4 U1: 文件夹批量导入 Markdown 组件。
 *
 * 中文学习型说明：扫描指定文件夹中的 .md 文件，dry-run 预览后批量创建 ai_draft 卡片。
 * 不调用 LLM / provider / external service。
 */

import { useState } from "react";
import { FilePlus, FolderOpen, Loader2, Check, AlertTriangle, X, FileText, Search } from "lucide-react";
import { previewFolderImport, importFromFolder } from "../api/library";
import type { FolderImportPreviewFile, FolderImportResultItem } from "../api/types";
import { useLocale } from "../lib/i18n";

interface FolderImportFormProps {
  onImported: () => void;
}

type Step = "input" | "preview" | "result";

export function FolderImportForm({ onImported }: FolderImportFormProps) {
  const { t } = useLocale();
  const [showForm, setShowForm] = useState(false);
  const [step, setStep] = useState<Step>("input");
  const [folderPath, setFolderPath] = useState("");
  const [scanning, setScanning] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);
  const [previewFiles, setPreviewFiles] = useState<FolderImportPreviewFile[]>([]);
  const [folderWarning, setFolderWarning] = useState<string | null>(null);
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set());
  const [importing, setImporting] = useState(false);
  const [results, setResults] = useState<FolderImportResultItem[]>([]);
  const [resultCounts, setResultCounts] = useState({ created: 0, skipped: 0, failed: 0 });

  async function handleScan() {
    if (!folderPath.trim()) return;
    setScanning(true);
    setScanError(null);
    try {
      const resp = await previewFolderImport(folderPath.trim());
      setPreviewFiles(resp.files);
      setFolderWarning(resp.folder_warning);
      // 默认全选所有可导入文件
      const importable = new Set<number>();
      for (const f of resp.files) {
        if (!f.error) importable.add(f.index);
      }
      setSelectedIndices(importable);
      setStep("preview");
    } catch (err) {
      setScanError(err instanceof Error ? err.message : t("library.folder_import_error_read"));
    } finally {
      setScanning(false);
    }
  }

  async function handleImport() {
    if (selectedIndices.size === 0) return;
    setImporting(true);
    try {
      const resp = await importFromFolder(folderPath.trim(), Array.from(selectedIndices).sort((a, b) => a - b));
      setResults(resp.results);
      setResultCounts({ created: resp.created_count, skipped: resp.skipped_count, failed: resp.failed_count });
      setStep("result");
      if (resp.created_count > 0) onImported();
    } catch (err) {
      setScanError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setImporting(false);
    }
  }

  function handleReset() {
    setShowForm(false);
    setStep("input");
    setFolderPath("");
    setPreviewFiles([]);
    setFolderWarning(null);
    setSelectedIndices(new Set());
    setResults([]);
    setScanError(null);
  }

  function toggleSelect(index: number) {
    const next = new Set(selectedIndices);
    if (next.has(index)) next.delete(index);
    else next.add(index);
    setSelectedIndices(next);
  }

  function toggleSelectAll() {
    if (selectedIndices.size === previewFiles.filter(f => !f.error).length) {
      setSelectedIndices(new Set());
    } else {
      setSelectedIndices(new Set(previewFiles.filter(f => !f.error).map(f => f.index)));
    }
  }

  const importableCount = previewFiles.filter(f => !f.error).length;

  if (!showForm) {
    return (
      <button
        type="button"
        className="inline-flex items-center gap-1.5 rounded-md border border-line bg-white px-3 py-1.5 text-sm text-muted hover:text-ink"
        onClick={() => setShowForm(true)}
      >
        <FolderOpen className="h-4 w-4" />
        {t("library.folder_import_btn")}
      </button>
    );
  }

  return (
    <div className="rounded-lg border border-emerald-200 bg-emerald-50/30 p-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-ink">{t("library.folder_import_title")}</h3>
          <p className="mt-1 text-xs text-muted">{t("library.folder_import_desc")}</p>
        </div>
        <button type="button" className="text-muted hover:text-ink" onClick={handleReset}>
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Step: Input */}
      {step === "input" && (
        <div className="mt-4 space-y-3">
          <div>
            <label className="block text-xs font-medium text-ink mb-1">
              {t("library.folder_import_path_label")}
            </label>
            <input
              type="text"
              className="w-full rounded-md border border-line bg-white px-3 py-1.5 text-sm text-ink placeholder:text-muted/60 focus:border-primary focus:outline-none"
              placeholder={t("library.folder_import_path_placeholder")}
              value={folderPath}
              onChange={(e) => setFolderPath(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleScan()}
            />
          </div>
          {scanError && (
            <div className="rounded bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
              {scanError}
            </div>
          )}
          <button
            type="button"
            className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-1.5 text-sm text-white hover:bg-primary/90 disabled:opacity-50"
            onClick={handleScan}
            disabled={!folderPath.trim() || scanning}
          >
            {scanning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            {scanning ? t("library.folder_import_scanning") : t("library.folder_import_scan")}
          </button>
        </div>
      )}

      {/* Step: Preview */}
      {step === "preview" && (
        <div className="mt-4 space-y-3">
          {folderWarning && (
            <div className="rounded bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-700 flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
              {folderWarning}
            </div>
          )}
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted">
              {t("library.folder_import_preview_count").replace("{total}", String(previewFiles.length)).replace("{importable}", String(importableCount))}
            </span>
            <button type="button" className="text-xs text-primary hover:underline" onClick={toggleSelectAll}>
              {selectedIndices.size === importableCount
                ? t("library.folder_import_deselect_all")
                : t("library.folder_import_select_all")}
            </button>
          </div>
          <div className="max-h-64 overflow-y-auto rounded-md border border-line bg-white divide-y divide-line/50">
            {previewFiles.map((file) => {
              const hasError = file.error !== null;
              const isSelected = selectedIndices.has(file.index);
              return (
                <label
                  key={file.index}
                  className={`flex items-start gap-3 px-3 py-2.5 cursor-pointer hover:bg-slate-50 ${hasError ? "opacity-50" : ""}`}
                >
                  <input
                    type="checkbox"
                    className="mt-0.5 rounded border-line"
                    checked={isSelected}
                    disabled={hasError}
                    onChange={() => toggleSelect(file.index)}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <FileText className="h-3.5 w-3.5 text-muted flex-shrink-0" />
                      <span className="text-sm font-medium text-ink truncate">{file.title}</span>
                      {isSelected && <Check className="h-3.5 w-3.5 text-primary flex-shrink-0" />}
                    </div>
                    <div className="mt-0.5 flex items-center gap-2 text-xs text-muted">
                      <span>{file.filename}</span>
                      <span>{Math.round(file.size_bytes / 1024)} KB</span>
                    </div>
                    {file.body_preview && (
                      <p className="mt-1 text-xs text-muted/70 line-clamp-1">{file.body_preview}</p>
                    )}
                    {file.warnings.map((w, i) => (
                      <div key={i} className="mt-1 flex items-center gap-1 text-xs text-amber-600">
                        <AlertTriangle className="h-3 w-3" />{w}
                      </div>
                    ))}
                    {/* v2.4 U2: 去重警告 */}
                    {file.potential_duplicates.length > 0 && (
                      <div className="mt-1 rounded bg-amber-50 border border-amber-100 px-2 py-1 text-xs">
                        <div className="text-amber-700 font-medium mb-0.5">{t("library.import_dedup_warning")}</div>
                        {file.potential_duplicates.slice(0, 3).map((dup) => (
                          <div key={dup.card_id} className="text-amber-600 truncate">
                            {dup.match_type === "exact_hash"
                              ? t("library.import_dedup_exact")
                              : t("library.import_dedup_fuzzy").replace("{sim}", String(Math.round(dup.similarity * 100)))
                            }
                            {dup.title}
                          </div>
                        ))}
                        {file.potential_duplicates.length > 3 && (
                          <div className="text-amber-500">... 还有 {file.potential_duplicates.length - 3} 个相似卡片</div>
                        )}
                      </div>
                    )}
                    {file.error && (
                      <div className="mt-1 text-xs text-red-500">{file.error}</div>
                    )}
                  </div>
                </label>
              );
            })}
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-1.5 text-sm text-white hover:bg-primary/90 disabled:opacity-50"
              onClick={handleImport}
              disabled={selectedIndices.size === 0 || importing}
            >
              {importing ? <Loader2 className="h-4 w-4 animate-spin" /> : <FilePlus className="h-4 w-4" />}
              {importing ? t("library.folder_import_importing") : t("library.folder_import_confirm").replace("{count}", String(selectedIndices.size))}
            </button>
            <button
              type="button"
              className="text-xs text-muted hover:text-ink"
              onClick={() => { setStep("input"); setScanError(null); }}
            >
              Back
            </button>
          </div>
        </div>
      )}

      {/* Step: Result */}
      {step === "result" && (
        <div className="mt-4 space-y-3">
          <div className="rounded bg-emerald-50 border border-emerald-200 px-3 py-2 text-sm text-emerald-800">
            {t("library.folder_import_result_summary")
              .replace("{created}", String(resultCounts.created))
              .replace("{skipped}", String(resultCounts.skipped))
              .replace("{failed}", String(resultCounts.failed))}
          </div>
          <div className="max-h-64 overflow-y-auto rounded-md border border-line bg-white divide-y divide-line/50">
            {results.map((r) => (
              <div key={r.index} className="flex items-center gap-2 px-3 py-2">
                {r.status === "created" && <Check className="h-4 w-4 text-emerald-500 flex-shrink-0" />}
                {r.status === "skipped" && <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0" />}
                {r.status === "failed" && <X className="h-4 w-4 text-red-500 flex-shrink-0" />}
                <span className="flex-1 text-sm text-ink truncate">{r.filename}</span>
                <span className={`text-xs ${
                  r.status === "created" ? "text-emerald-600" :
                  r.status === "skipped" ? "text-amber-600" : "text-red-600"
                }`}>
                  {r.status === "created" ? t("library.folder_import_result_created") :
                   r.status === "skipped" ? t("library.folder_import_result_skipped") :
                   t("library.folder_import_result_failed")}
                </span>
                {r.error && <span className="text-xs text-red-500">{r.error}</span>}
              </div>
            ))}
          </div>
          <button
            type="button"
            className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-1.5 text-sm text-white hover:bg-primary/90"
            onClick={handleReset}
          >
            Done
          </button>
        </div>
      )}
    </div>
  );
}
