import type { SourceStatus } from "../api/types";

export function SourceList({
  sources,
  onCopyPath,
  onRevealPath,
  onOpenCards,
}: {
  sources: SourceStatus[];
  onCopyPath?: (path: string) => void;
  onRevealPath?: (path: string) => void;
  onOpenCards?: () => void;
}) {
  return (
    <div className="overflow-hidden rounded-md border border-line bg-panel">
      <table className="w-full text-left text-sm">
        <thead className="bg-stone-100 text-muted">
          <tr>
            <th className="px-4 py-3 font-medium">Source</th>
            <th className="px-4 py-3 font-medium">Path</th>
            <th className="px-4 py-3 font-medium">Files</th>
            <th className="px-4 py-3 font-medium">Processed</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {sources.map((source) => {
            const pathView = source.source_path_view;
            const displayPath = pathView?.display_path ?? "Source path not available";
            const copyTarget = pathView?.can_copy_full_path ? source.path : pathView?.display_path;
            return (
            <tr key={source.source_type}>
              <td className="px-4 py-3">
                <div className="font-medium text-ink">{source.source_type}</div>
                <div className="text-xs text-muted">{source.adapter}</div>
              </td>
              <td className="max-w-[280px] px-4 py-3 text-muted">
                <div className="truncate">{displayPath}</div>
              </td>
              <td className="px-4 py-3">{source.file_count}</td>
              <td className="px-4 py-3">{source.processed_count}</td>
              <td className={source.exists ? "px-4 py-3 text-safe" : "px-4 py-3 text-warn"}>
                <div>{source.display_status}</div>
                <div className="mt-1 text-xs text-muted">Adapter ready</div>
                <div className="mt-1 text-xs text-muted">{source.generated_knowledge_status || generatedKnowledgeLabel(source.generated_card_count)}</div>
              </td>
              <td className="px-4 py-3">
                <div className="flex flex-wrap gap-2">
                  <button className="rounded-md border border-line px-2 py-1 text-xs text-ink disabled:opacity-50" disabled={!copyTarget || !pathView?.can_copy_display_path} onClick={() => copyTarget && onCopyPath?.(copyTarget)} type="button">
                    {pathView?.can_copy_full_path ? "Copy path" : "Copy display path"}
                  </button>
                  <button className="rounded-md border border-line px-2 py-1 text-xs text-ink disabled:opacity-50" disabled={!pathView?.can_reveal_in_finder} onClick={() => pathView?.can_reveal_in_finder && onRevealPath?.(source.path)} type="button">
                    Reveal in Finder
                  </button>
                  <button className="rounded-md border border-line px-2 py-1 text-xs text-primary" onClick={onOpenCards} type="button">
                    Open related knowledge
                  </button>
                </div>
                {source.generated_card_paths.length ? (
                  <div className="mt-2 space-y-1">
                    {source.generated_card_paths.slice(0, 3).map((path) => (
                      <button key={path} className="block max-w-[220px] truncate text-xs text-primary" onClick={() => onCopyPath?.(path)} type="button">
                        Copy related knowledge path
                      </button>
                    ))}
                  </div>
                ) : null}
              </td>
            </tr>
          );
          })}
        </tbody>
      </table>
    </div>
  );
}

function generatedKnowledgeLabel(count: number) {
  return count > 0 ? "Has generated knowledge" : "No generated knowledge";
}
