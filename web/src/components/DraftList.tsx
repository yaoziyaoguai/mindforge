import type { DraftSummary } from "../api/types";
import { friendlyStatus } from "../lib/utils";

export function DraftList({
  drafts,
  selected,
  onSelect,
}: {
  drafts: DraftSummary[];
  selected?: string;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="space-y-2">
      {drafts.map((draft) => {
        const id = draft.id ?? draft.rel_path;
        return (
          <button
            key={draft.rel_path}
            className={`w-full rounded-md border p-4 text-left transition ${
              selected === id ? "border-primary bg-blue-50" : "border-line bg-panel hover:border-primary"
            }`}
            onClick={() => onSelect(id)}
            type="button"
          >
            <div className="flex items-center justify-between gap-3">
              <h3 className="font-medium text-ink">{draft.title ?? draft.rel_path}</h3>
              <span className="text-xs text-warn">{friendlyStatus(draft.status)}</span>
            </div>
            <p className="mt-1 text-sm text-muted">{draft.source_title ?? draft.source_type ?? "No source title"}</p>
            <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted">
              {draft.strategy_label ? <span>{draft.strategy_label}</span> : null}
              {draft.strategy_note ? <span>{draft.strategy_note}</span> : null}
              {draft.source_title || draft.source_path_view?.display_path ? <span>source:{draft.source_title ?? draft.source_path_view?.display_path}</span> : null}
              {draft.track ? <span>track:{draft.track}</span> : null}
              {draft.projects.map((project) => (
                <span key={project}>project:{project}</span>
              ))}
            </div>
          </button>
        );
      })}
    </div>
  );
}
