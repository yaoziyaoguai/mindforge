import { useEffect, useMemo, useState } from "react";
import { Bookmark, Check, Plus, Save, Trash2, X } from "lucide-react";
import { deleteView, getViews, saveView } from "../api/library";
import type { SavedViewResponse, SaveViewRequest } from "../api/types";
import { useLocale } from "../lib/i18n";

interface ViewSwitcherProps {
  statusFilter: string;
  trackFilter: string;
  sourceTypeFilter: string;
  qualityFilter: string;
  sortBy: string;
  onApplyView: (v: SavedViewResponse) => void;
}

export function ViewSwitcher({
  statusFilter,
  trackFilter,
  sourceTypeFilter,
  qualityFilter,
  sortBy,
  onApplyView,
}: ViewSwitcherProps) {
  const { t } = useLocale();
  const [views, setViews] = useState<SavedViewResponse[]>([]);
  const [open, setOpen] = useState(false);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saveName, setSaveName] = useState("");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function refreshViews() {
    getViews()
      .then((r) => setViews(r.views))
      .catch(() => {});
  }

  useEffect(() => {
    refreshViews();
  }, []);

  const currentSignature = useMemo(
    () => JSON.stringify({ statusFilter, trackFilter, sourceTypeFilter, qualityFilter, sortBy }),
    [statusFilter, trackFilter, sourceTypeFilter, qualityFilter, sortBy],
  );

  const currentViewMatch = useMemo(() => {
    return views.find((v) => {
      const sig = JSON.stringify({
        statusFilter: v.status_filter,
        trackFilter: v.track_filter,
        sourceTypeFilter: v.source_type_filter,
        qualityFilter: v.quality_filter,
        sortBy: v.sort_by,
      });
      return sig === currentSignature;
    });
  }, [views, currentSignature]);

  const slug = (name: string) =>
    name
      .toLowerCase()
      .replace(/\s+/g, "-")
      .replace(/[^a-z0-9-]/g, "");

  async function handleSave() {
    if (!saveName.trim()) return;
    setSaving(true);
    const payload: SaveViewRequest = {
      id: slug(saveName),
      name: saveName.trim(),
      status_filter: statusFilter,
      track_filter: trackFilter,
      source_type_filter: sourceTypeFilter,
      quality_filter: qualityFilter,
      sort_by: sortBy,
    };
    try {
      await saveView(payload);
      setSaveName("");
      setShowSaveDialog(false);
      refreshViews();
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(viewId: string) {
    await deleteView(viewId);
    setShowDeleteConfirm(null);
    refreshViews();
  }

  return (
    <div className="relative inline-flex items-center gap-1">
      <button
        type="button"
        className="inline-flex items-center gap-1 rounded-md border border-line bg-white px-2 py-1 text-xs text-ink hover:bg-muted/10"
        onClick={() => setOpen(!open)}
        onBlur={(e) => {
          // Close on blur after a tick so click events on dropdown items fire first
          if (!e.currentTarget.contains(e.relatedTarget as Node)) {
            setTimeout(() => setOpen(false), 150);
          }
        }}
      >
        <Bookmark className="h-3.5 w-3.5" />
        {currentViewMatch ? currentViewMatch.name : t("views.all_cards")}
      </button>

      {!currentViewMatch && (
        <button
          type="button"
          className="inline-flex items-center gap-1 rounded-md border border-dashed border-line bg-white px-2 py-1 text-xs text-muted hover:text-ink"
          onClick={() => setShowSaveDialog(true)}
          title={t("views.save_current")}
        >
          <Save className="h-3 w-3" />
        </button>
      )}

      {open && (
        <div className="absolute top-full left-0 z-30 mt-1 w-56 rounded-md border border-line bg-white shadow-lg">
          <div className="p-1">
            {/* Built-in default */}
            <button
              type="button"
              className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-xs hover:bg-muted/10"
              onClick={() => {
                onApplyView({
                  id: "__all__",
                  name: t("views.all_cards"),
                  status_filter: "all",
                  track_filter: "all",
                  source_type_filter: "all",
                  quality_filter: "all",
                  sort_by: "newest",
                  created_at: "",
                });
                setOpen(false);
              }}
            >
              <Bookmark className="h-3 w-3 text-muted" />
              <span className="flex-1 text-left">{t("views.all_cards")}</span>
              {!currentViewMatch && <Check className="h-3 w-3 text-green-500" />}
            </button>

            {views.length === 0 ? (
              <p className="px-2 py-1.5 text-[11px] text-muted">{t("views.no_saved")}</p>
            ) : (
              views.map((v) => (
                <div key={v.id} className="flex items-center gap-1 rounded px-1 py-0.5 hover:bg-muted/10 group">
                  <button
                    type="button"
                    className="flex flex-1 items-center gap-2 rounded px-1 py-1 text-xs"
                    onClick={() => {
                      onApplyView(v);
                      setOpen(false);
                    }}
                  >
                    <Bookmark className="h-3 w-3 text-muted shrink-0" />
                    <span className="flex-1 text-left truncate">{v.name}</span>
                    {currentViewMatch?.id === v.id && <Check className="h-3 w-3 text-green-500 shrink-0" />}
                  </button>
                  <button
                    type="button"
                    className="shrink-0 rounded p-0.5 text-muted opacity-0 group-hover:opacity-100 hover:text-red-500"
                    onClick={(e) => {
                      e.stopPropagation();
                      setShowDeleteConfirm(v.id);
                    }}
                    title={t("views.delete")}
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Save dialog */}
      {showSaveDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20">
          <div className="w-80 rounded-lg border border-line bg-white p-4 shadow-xl">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-semibold text-ink">{t("views.save_title")}</h3>
              <button
                type="button"
                className="rounded p-0.5 text-muted hover:text-ink"
                onClick={() => setShowSaveDialog(false)}
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <input
              type="text"
              className="mt-3 w-full rounded border border-line px-2 py-1.5 text-xs text-ink placeholder:text-muted"
              placeholder={t("views.name_placeholder")}
              value={saveName}
              onChange={(e) => setSaveName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSave();
                if (e.key === "Escape") setShowSaveDialog(false);
              }}
              autoFocus
            />
            <p className="mt-1 text-[10px] text-muted">{t("views.save_desc")}</p>
            <div className="mt-3 flex items-center justify-end gap-2">
              <button
                type="button"
                className="rounded-md border border-line px-3 py-1 text-xs text-ink hover:bg-muted/10"
                onClick={() => setShowSaveDialog(false)}
              >
                {t("card.cancel")}
              </button>
              <button
                type="button"
                className="rounded-md px-3 py-1 text-xs font-medium text-white disabled:opacity-50"
                style={{ background: "var(--mf-accent)" }}
                disabled={!saveName.trim() || saving}
                onClick={handleSave}
              >
                <Save className="inline h-3 w-3 mr-1" />
                {saving ? "..." : t("views.save")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete confirmation */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20">
          <div className="w-72 rounded-lg border border-line bg-white p-4 shadow-xl">
            <h3 className="text-sm font-semibold text-ink">{t("views.delete_confirm_title")}</h3>
            <p className="mt-1 text-xs text-muted">{t("views.delete_confirm_desc")}</p>
            <div className="mt-3 flex items-center justify-end gap-2">
              <button
                type="button"
                className="rounded-md border border-line px-3 py-1 text-xs text-ink hover:bg-muted/10"
                onClick={() => setShowDeleteConfirm(null)}
              >
                {t("card.cancel")}
              </button>
              <button
                type="button"
                className="rounded-md bg-red-500 px-3 py-1 text-xs font-medium text-white hover:bg-red-600"
                onClick={() => handleDelete(showDeleteConfirm)}
              >
                {t("views.delete")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
