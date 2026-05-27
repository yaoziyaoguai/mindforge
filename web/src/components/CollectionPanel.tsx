import { useEffect, useState } from "react";
import { Check, FolderOpen, Plus, Trash2, X } from "lucide-react";
import { addToCollection, createCollection, deleteCollection, getCollections, removeFromCollection } from "../api/library";
import type { CollectionResponse, CreateCollectionRequest } from "../api/types";
import { useLocale } from "../lib/i18n";

interface CollectionPanelProps {
  selectedCardRefs: string[];
  onRefresh?: () => void;
}

export function CollectionPanel({ selectedCardRefs, onRefresh }: CollectionPanelProps) {
  const { t } = useLocale();
  const [collections, setCollections] = useState<CollectionResponse[]>([]);
  const [open, setOpen] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createDesc, setCreateDesc] = useState("");
  const [creating, setCreating] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null);
  const [showAddMenu, setShowAddMenu] = useState(false);

  function refresh() {
    getCollections()
      .then((r) => setCollections(r.collections))
      .catch(() => {});
  }

  useEffect(() => {
    refresh();
  }, []);

  const slug = (name: string) =>
    name
      .toLowerCase()
      .replace(/\s+/g, "-")
      .replace(/[^a-z0-9-]/g, "");

  async function handleCreate() {
    if (!createName.trim()) return;
    setCreating(true);
    const payload: CreateCollectionRequest = {
      id: slug(createName),
      name: createName.trim(),
      description: createDesc.trim(),
    };
    try {
      await createCollection(payload);
      setCreateName("");
      setCreateDesc("");
      setShowCreate(false);
      refresh();
      onRefresh?.();
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(colId: string) {
    await deleteCollection(colId);
    setShowDeleteConfirm(null);
    refresh();
    onRefresh?.();
  }

  async function handleAddToCollection(colId: string) {
    if (selectedCardRefs.length === 0) return;
    await addToCollection(colId, { card_refs: selectedCardRefs });
    setShowAddMenu(false);
    refresh();
    onRefresh?.();
  }

  async function handleRemoveFromCollection(colId: string, cardRef: string) {
    await removeFromCollection(colId, { card_refs: [cardRef] });
    refresh();
    onRefresh?.();
  }

  return (
    <details className="border border-line rounded-md bg-panel" open={open} onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}>
      <summary className="px-5 py-3 cursor-pointer select-none text-sm font-medium text-ink hover:text-primary flex items-center gap-2">
        <FolderOpen className="h-4 w-4 text-muted" />
        {t("collections.title")}
        {collections.length > 0 && (
          <span className="text-[11px] text-muted">({collections.length})</span>
        )}
      </summary>

      <div className="px-4 pb-3 space-y-2">
        {collections.length === 0 ? (
          <p className="text-[11px] text-muted px-1">{t("collections.no_saved")}</p>
        ) : (
          collections.map((col) => (
            <div key={col.id} className="rounded border border-line bg-white p-2">
              <div className="flex items-center justify-between gap-1">
                <span className="text-xs font-medium text-ink truncate flex-1">{col.name}</span>
                <span className="text-[10px] text-muted shrink-0">
                  {t("collections.card_count").replace("{count}", String(col.card_refs.length))}
                </span>
                <button
                  type="button"
                  className="shrink-0 rounded p-0.5 text-muted hover:text-red-500"
                  onClick={() => setShowDeleteConfirm(col.id)}
                  title={t("collections.delete")}
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              </div>
              {col.description && (
                <p className="text-[10px] text-muted mt-0.5">{col.description}</p>
              )}
              {col.card_refs.length > 0 && (
                <div className="mt-1 space-y-0.5 max-h-32 overflow-y-auto">
                  {col.card_refs.slice(0, 10).map((ref) => (
                    <div key={ref} className="flex items-center gap-1 text-[10px] text-muted">
                      <span className="truncate flex-1">{ref}</span>
                      <button
                        type="button"
                        className="shrink-0 text-muted hover:text-red-500"
                        onClick={() => handleRemoveFromCollection(col.id, ref)}
                        title={t("collections.remove")}
                      >
                        <X className="h-2.5 w-2.5" />
                      </button>
                    </div>
                  ))}
                  {col.card_refs.length > 10 && (
                    <p className="text-[10px] text-muted">... and {col.card_refs.length - 10} more</p>
                  )}
                </div>
              )}
            </div>
          ))
        )}

        <button
          type="button"
          className="flex w-full items-center gap-1.5 rounded-md border border-dashed border-line px-2 py-1.5 text-xs text-muted hover:text-ink hover:border-ink/30"
          onClick={() => setShowCreate(true)}
        >
          <Plus className="h-3 w-3" />
          {t("collections.create")}
        </button>
      </div>

      {/* Create dialog */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20">
          <div className="w-80 rounded-lg border border-line bg-white p-4 shadow-xl">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-semibold text-ink">{t("collections.create")}</h3>
              <button
                type="button"
                className="rounded p-0.5 text-muted hover:text-ink"
                onClick={() => setShowCreate(false)}
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <input
              type="text"
              className="mt-3 w-full rounded border border-line px-2 py-1.5 text-xs text-ink placeholder:text-muted"
              placeholder={t("collections.name_placeholder")}
              value={createName}
              onChange={(e) => setCreateName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleCreate();
                if (e.key === "Escape") setShowCreate(false);
              }}
              autoFocus
            />
            <input
              type="text"
              className="mt-2 w-full rounded border border-line px-2 py-1.5 text-xs text-ink placeholder:text-muted"
              placeholder={t("collections.desc_placeholder")}
              value={createDesc}
              onChange={(e) => setCreateDesc(e.target.value)}
            />
            <div className="mt-3 flex items-center justify-end gap-2">
              <button
                type="button"
                className="rounded-md border border-line px-3 py-1 text-xs text-ink hover:bg-muted/10"
                onClick={() => setShowCreate(false)}
              >
                {t("card.cancel")}
              </button>
              <button
                type="button"
                className="rounded-md px-3 py-1 text-xs font-medium text-white disabled:opacity-50"
                style={{ background: "var(--mf-accent)" }}
                disabled={!createName.trim() || creating}
                onClick={handleCreate}
              >
                <Plus className="inline h-3 w-3 mr-1" />
                {creating ? "..." : t("collections.create")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete confirmation */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20">
          <div className="w-72 rounded-lg border border-line bg-white p-4 shadow-xl">
            <h3 className="text-sm font-semibold text-ink">{t("collections.delete_confirm_title")}</h3>
            <p className="mt-1 text-xs text-muted">{t("collections.delete_confirm_desc")}</p>
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
                {t("collections.delete")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add to collection menu */}
      {showAddMenu && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20" onClick={() => setShowAddMenu(false)}>
          <div className="w-64 rounded-lg border border-line bg-white p-3 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-xs font-semibold text-ink mb-2">{t("collections.add_cards")}</h3>
            {collections.length === 0 ? (
              <p className="text-[11px] text-muted">{t("collections.no_saved")}</p>
            ) : (
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {collections.map((col) => (
                  <button
                    key={col.id}
                    type="button"
                    className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-xs hover:bg-muted/10"
                    onClick={() => handleAddToCollection(col.id)}
                  >
                    <FolderOpen className="h-3 w-3 text-muted" />
                    <span className="flex-1 text-left truncate">{col.name}</span>
                    <span className="text-[10px] text-muted">{col.card_refs.length}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </details>
  );
}
