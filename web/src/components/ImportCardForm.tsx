import { useState, useMemo } from "react";
import { FilePlus, Files, X } from "lucide-react";
import { importCard } from "../api/library";
import { useLocale } from "../lib/i18n";
import type { ImportCardResponse } from "../api/types";

interface ImportCardFormProps {
  onImported: () => void;
}

/** 从 body 文本中检测 --- 分隔的多篇文档。 */
function detectDocuments(body: string): { title: string; content: string }[] {
  // 仅当有多于 1 个 --- 分段且 next block 非空时认为多篇
  const blocks = body.split(/\n---\n/).filter(b => b.trim().length > 0);
  if (blocks.length <= 1) return [];

  return blocks.map((block) => {
    // 提取 YAML frontmatter 中的 title
    let title = "";
    let content = block;
    if (block.startsWith("---")) {
      const parts = block.split("---", 2);
      if (parts.length >= 2) {
        const fmLines = parts[1].trim().split("\n");
        for (const line of fmLines) {
          if (line.startsWith("title:") || line.startsWith("title :")) {
            title = line.split(":", 1)[1].trim().replace(/^["']|["']$/g, "");
            break;
          }
        }
        content = parts.slice(2).join("---").trim() || block;
      }
    }
    // Fallback: 取第一个 # heading
    if (!title) {
      for (const line of content.split("\n")) {
        if (line.trim().startsWith("# ") && !line.trim().startsWith("## ")) {
          title = line.trim().slice(2).trim();
          break;
        }
      }
    }
    return { title, content };
  });
}

export function ImportCardForm({ onImported }: ImportCardFormProps) {
  const { t } = useLocale();
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [sourceName, setSourceName] = useState("");
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<ImportCardResponse[] | null>(null);

  // v2.4 U3: 检测多篇文档
  const documents = useMemo(() => detectDocuments(body), [body]);
  const isMultiDocument = documents.length > 1;

  async function handleSubmit() {
    if (!title.trim() || !body.trim()) return;
    setImporting(true);
    setError(null);
    setResults(null);
    try {
      const result = await importCard(title, body, sourceName || undefined);
      setResults([result]);
      setTitle("");
      setBody("");
      setSourceName("");
      onImported();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setImporting(false);
    }
  }

  async function handleBatchSubmit() {
    if (documents.length === 0) return;
    setImporting(true);
    setError(null);
    setResults(null);
    try {
      const resp = await fetch("/api/knowledge/import/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          items: documents.map((d) => ({ title: d.title || "Untitled", body: d.content })),
          source_name: sourceName || "",
        }),
      });
      if (!resp.ok) throw new Error("Batch import failed");
      const data = await resp.json();
      setResults(data.results || []);
      setTitle("");
      setBody("");
      setSourceName("");
      if (data.created_count > 0) onImported();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Batch import failed");
    } finally {
      setImporting(false);
    }
  }

  if (!showForm) {
    return (
      <button
        type="button"
        className="inline-flex items-center gap-1.5 rounded-md border border-line bg-white px-3 py-1.5 text-sm text-muted hover:text-ink"
        onClick={() => setShowForm(true)}
      >
        <FilePlus className="h-4 w-4" />
        {t("library.import_btn")}
      </button>
    );
  }

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50/30 p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-ink">{t("library.import_title")}</h3>
          <p className="mt-1 text-xs text-muted">{t("library.import_desc")}</p>
          {isMultiDocument && (
            <p className="mt-1 text-xs text-primary">
              {t("library.import_batch_detected").replace("{count}", String(documents.length))}
            </p>
          )}
        </div>
        <button
          type="button"
          className="text-muted hover:text-ink"
          onClick={() => {
            setShowForm(false);
            setError(null);
            setResults(null);
          }}
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-3 space-y-3">
        <div>
          <label className="block text-xs font-medium text-ink mb-1">
            {isMultiDocument ? t("library.import_batch_title_label") : t("library.import_title_label")}
          </label>
          <input
            type="text"
            className="w-full rounded-md border border-line bg-white px-3 py-1.5 text-sm text-ink placeholder:text-muted/60 focus:border-primary focus:outline-none"
            placeholder={isMultiDocument ? t("library.import_batch_title_placeholder") : t("library.import_title_placeholder")}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-ink mb-1">{t("library.import_body_label")}</label>
          <textarea
            className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm text-ink placeholder:text-muted/60 focus:border-primary focus:outline-none"
            rows={10}
            placeholder={isMultiDocument ? t("library.import_batch_body_placeholder") : t("library.import_body_placeholder")}
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-ink mb-1">{t("library.import_source_label")}</label>
          <input
            type="text"
            className="w-full rounded-md border border-line bg-white px-3 py-1.5 text-sm text-ink placeholder:text-muted/60 focus:border-primary focus:outline-none"
            placeholder={t("library.import_source_placeholder")}
            value={sourceName}
            onChange={(e) => setSourceName(e.target.value)}
          />
        </div>
      </div>

      {/* Multi-document preview */}
      {isMultiDocument && (
        <div className="mt-3 rounded border border-amber-200 bg-amber-50/50 p-3">
          <p className="text-xs font-medium text-amber-800 mb-2">
            {t("library.import_batch_preview_label").replace("{count}", String(documents.length))}
          </p>
          <div className="max-h-40 overflow-y-auto space-y-1">
            {documents.map((doc, i) => (
              <div key={i} className="text-xs text-amber-700 flex items-start gap-2">
                <span className="text-amber-400 font-mono">{i + 1}.</span>
                <span className="truncate">{doc.title || "(no title)"}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {error ? <p className="mt-2 text-xs text-red-600">{error}</p> : null}

      {/* Import results manifest — v2.4 U3 */}
      {results && results.length > 0 && (
        <div className="mt-3 rounded border border-emerald-200 bg-emerald-50/50 p-3">
          <p className="text-xs font-medium text-emerald-800 mb-1">
            {results.length === 1 ? t("library.import_success") + results[0].rel_path : t("library.import_batch_result").replace("{count}", String(results.length))}
          </p>
          {results.length > 1 && (
            <div className="max-h-32 overflow-y-auto space-y-0.5">
              {results.map((r) => (
                <div key={r.id} className="text-xs text-emerald-700 truncate">{r.title}</div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="mt-3 flex items-center gap-2">
        <button
          type="button"
          className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          disabled={importing || (!title.trim() && !isMultiDocument) || !body.trim()}
          onClick={isMultiDocument || !title.trim() ? handleBatchSubmit : handleSubmit}
        >
          {isMultiDocument ? <Files className="h-4 w-4" /> : <FilePlus className="h-4 w-4" />}
          {importing ? "..." : isMultiDocument ? t("library.import_batch_submit") : t("library.import_submit")}
        </button>
        <button
          type="button"
          className="inline-flex items-center gap-1.5 rounded-md border border-line px-3 py-2 text-sm font-medium text-ink hover:bg-muted/10"
          onClick={() => {
            setShowForm(false);
            setError(null);
            setResults(null);
          }}
          disabled={importing}
        >
          <X className="h-4 w-4" /> {t("card.cancel")}
        </button>
      </div>
    </div>
  );
}
