import { useState } from "react";
import { Check, Tags, X } from "lucide-react";
import { bulkUpdateCards } from "../api/library";
import { useLocale } from "../lib/i18n";

interface BulkActionsProps {
  selectedRefs: string[];
  onClearSelection: () => void;
  onApplied: () => void;
}

export function BulkActions({ selectedRefs, onClearSelection, onApplied }: BulkActionsProps) {
  const { t } = useLocale();
  const [showTagsInput, setShowTagsInput] = useState(false);
  const [showTrackInput, setShowTrackInput] = useState(false);
  const [tagsValue, setTagsValue] = useState("");
  const [trackValue, setTrackValue] = useState("");
  const [applying, setApplying] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  if (selectedRefs.length === 0) return null;

  async function handleApplyTags() {
    if (!tagsValue.trim()) return;
    setApplying(true);
    setError("");
    const tags = tagsValue.split(",").map((s) => s.trim()).filter(Boolean);
    try {
      const r = await bulkUpdateCards({ card_refs: selectedRefs, set_tags: tags });
      setMessage(t("bulk.applied").replace("{count}", String(r.updated_count)));
      if (r.errors.length > 0) setError(r.errors.join("; "));
      setTagsValue("");
      setShowTagsInput(false);
      onApplied();
    } catch (e) {
      setError(String(e));
    } finally {
      setApplying(false);
    }
  }

  async function handleApplyTrack() {
    if (!trackValue.trim()) return;
    setApplying(true);
    setError("");
    try {
      const r = await bulkUpdateCards({ card_refs: selectedRefs, set_track: trackValue.trim() });
      setMessage(t("bulk.applied").replace("{count}", String(r.updated_count)));
      if (r.errors.length > 0) setError(r.errors.join("; "));
      setTrackValue("");
      setShowTrackInput(false);
      onApplied();
    } catch (e) {
      setError(String(e));
    } finally {
      setApplying(false);
    }
  }

  return (
    <div className="rounded-md border border-[var(--mf-accent)] bg-[var(--mf-accent)]/5 p-3 space-y-2">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs font-medium text-ink">
          {t("bulk.select_count").replace("{count}", String(selectedRefs.length))}
        </span>

        <button
          type="button"
          className="rounded border border-line bg-white px-2 py-1 text-[11px] text-ink hover:bg-muted/10 inline-flex items-center gap-1"
          onClick={() => { setShowTagsInput(!showTagsInput); setShowTrackInput(false); }}
        >
          <Tags className="h-3 w-3" />
          {t("bulk.set_tags")}
        </button>

        <button
          type="button"
          className="rounded border border-line bg-white px-2 py-1 text-[11px] text-ink hover:bg-muted/10"
          onClick={() => { setShowTrackInput(!showTrackInput); setShowTagsInput(false); }}
        >
          {t("bulk.set_track")}
        </button>

        <button
          type="button"
          className="rounded px-2 py-1 text-[11px] text-muted hover:text-ink inline-flex items-center gap-1"
          onClick={onClearSelection}
        >
          <X className="h-3 w-3" />
          {t("bulk.exit")}
        </button>
      </div>

      {showTagsInput && (
        <div className="flex items-center gap-2">
          <input
            type="text"
            className="flex-1 rounded border border-line px-2 py-1 text-xs text-ink placeholder:text-muted"
            placeholder={t("bulk.tags_placeholder")}
            value={tagsValue}
            onChange={(e) => setTagsValue(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleApplyTags(); if (e.key === "Escape") setShowTagsInput(false); }}
            autoFocus
          />
          <button
            type="button"
            className="rounded px-2 py-1 text-xs font-medium text-white disabled:opacity-50 inline-flex items-center gap-1"
            style={{ background: "var(--mf-accent)" }}
            disabled={!tagsValue.trim() || applying}
            onClick={handleApplyTags}
          >
            <Check className="h-3 w-3" />
            {applying ? "..." : t("bulk.apply")}
          </button>
        </div>
      )}

      {showTrackInput && (
        <div className="flex items-center gap-2">
          <input
            type="text"
            className="flex-1 rounded border border-line px-2 py-1 text-xs text-ink placeholder:text-muted"
            placeholder={t("bulk.track_placeholder")}
            value={trackValue}
            onChange={(e) => setTrackValue(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleApplyTrack(); if (e.key === "Escape") setShowTrackInput(false); }}
            autoFocus
          />
          <button
            type="button"
            className="rounded px-2 py-1 text-xs font-medium text-white disabled:opacity-50 inline-flex items-center gap-1"
            style={{ background: "var(--mf-accent)" }}
            disabled={!trackValue.trim() || applying}
            onClick={handleApplyTrack}
          >
            <Check className="h-3 w-3" />
            {applying ? "..." : t("bulk.apply")}
          </button>
        </div>
      )}

      {message && <p className="text-[11px] text-green-600">{message}</p>}
      {error && <p className="text-[11px] text-red-500">{error}</p>}
    </div>
  );
}
