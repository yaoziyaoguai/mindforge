import { useState } from "react";
import { FilePlus, X } from "lucide-react";
import { importCard } from "../api/library";
import { useLocale } from "../lib/i18n";

interface ImportCardFormProps {
  onImported: () => void;
}

export function ImportCardForm({ onImported }: ImportCardFormProps) {
  const { t } = useLocale();
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [sourceName, setSourceName] = useState("");
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successRef, setSuccessRef] = useState<string | null>(null);

  async function handleSubmit() {
    if (!title.trim() || !body.trim()) return;
    setImporting(true);
    setError(null);
    setSuccessRef(null);
    try {
      const result = await importCard(title, body, sourceName || undefined);
      setSuccessRef(result.rel_path);
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
        </div>
        <button
          type="button"
          className="text-muted hover:text-ink"
          onClick={() => {
            setShowForm(false);
            setError(null);
            setSuccessRef(null);
          }}
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-3 space-y-3">
        <div>
          <label className="block text-xs font-medium text-ink mb-1">{t("library.import_title_label")}</label>
          <input
            type="text"
            className="w-full rounded-md border border-line bg-white px-3 py-1.5 text-sm text-ink placeholder:text-muted/60 focus:border-primary focus:outline-none"
            placeholder={t("library.import_title_placeholder")}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-ink mb-1">{t("library.import_body_label")}</label>
          <textarea
            className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm text-ink placeholder:text-muted/60 focus:border-primary focus:outline-none"
            rows={10}
            placeholder={t("library.import_body_placeholder")}
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

      {error ? <p className="mt-2 text-xs text-red-600">{error}</p> : null}
      {successRef ? <p className="mt-2 text-xs text-safe">{t("library.import_success")}{successRef}</p> : null}

      <div className="mt-3 flex items-center gap-2">
        <button
          type="button"
          className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          disabled={!title.trim() || !body.trim() || importing}
          onClick={handleSubmit}
        >
          <FilePlus className="h-4 w-4" />
          {importing ? "..." : t("library.import_submit")}
        </button>
        <button
          type="button"
          className="inline-flex items-center gap-1.5 rounded-md border border-line px-3 py-2 text-sm font-medium text-ink hover:bg-muted/10"
          onClick={() => {
            setShowForm(false);
            setError(null);
          }}
          disabled={importing}
        >
          <X className="h-4 w-4" /> {t("card.cancel")}
        </button>
      </div>
    </div>
  );
}
