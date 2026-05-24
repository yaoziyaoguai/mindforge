import { useEffect, useState } from "react";
import {
  BookOpen,
  FolderOpen,
  GitBranch,
  Hash,
  Loader2,
  Search,
} from "lucide-react";
import { fetchGraphExplore } from "../api/graph";
import type { GraphNodeResponse, GraphResponse } from "../api/types";
import { useLocale } from "../lib/i18n";

interface Props {
  onSelectCard?: (ref: string) => void;
}

const NODE_TYPE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  source: FolderOpen,
  tag: Hash,
  wiki_section: BookOpen,
};

export function GraphExplorer({ onSelectCard }: Props) {
  const { t } = useLocale();
  const [nodeType, setNodeType] = useState("source");
  const [nodeId, setNodeId] = useState("");
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  function explore() {
    if (!nodeId.trim()) return;
    setLoading(true);
    setError(null);
    fetchGraphExplore(nodeType, nodeId.trim(), 1)
      .then((g) => {
        setGraph(g);
        setOpen(true);
      })
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Explore failed")
      )
      .finally(() => setLoading(false));
  }

  // Reset when switching type
  useEffect(() => {
    setGraph(null);
    setOpen(false);
    setError(null);
  }, [nodeType]);

  const cardNodes = graph?.nodes.filter((n) => n.type === "card") ?? [];
  const otherNodes = graph?.nodes.filter((n) => n.type !== "card") ?? [];

  return (
    <section className="rounded-md border border-line bg-panel p-5">
      <div className="flex items-center gap-2">
        <GitBranch className="h-5 w-5 text-primary" />
        <h2 className="text-lg font-semibold text-ink">
          {t("graph.title")}
        </h2>
      </div>
      <p className="mt-1 text-sm text-muted">
        {t("graph.explore_graph")} — {t("library.subtitle")}
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        {(["source", "tag", "wiki_section"] as const).map((nt) => (
          <button
            key={nt}
            type="button"
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
              nodeType === nt
                ? "bg-primary text-white"
                : "bg-muted/10 text-muted hover:text-ink"
            }`}
            onClick={() => setNodeType(nt)}
          >
            {(() => {
              const Icon = NODE_TYPE_ICONS[nt];
              return Icon ? <Icon className="mr-1 inline h-3 w-3" /> : null;
            })()}
            {nt.replace("_", " ")}
          </button>
        ))}
      </div>

      <div className="mt-3 flex gap-2">
        <input
          className="flex-1 rounded-md border border-line px-3 py-2 text-sm text-ink placeholder:text-muted"
          placeholder={
            nodeType === "source"
              ? "source_id ..."
              : nodeType === "tag"
                ? "tag name ..."
                : "wiki section title ..."
          }
          value={nodeId}
          onChange={(e) => setNodeId(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && explore()}
        />
        <button
          type="button"
          className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          onClick={explore}
          disabled={loading || !nodeId.trim()}
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Search className="h-4 w-4" />
          )}
          {t("graph.explore_graph")}
        </button>
      </div>

      {error ? (
        <p className="mt-3 text-sm text-danger">{error}</p>
      ) : null}

      {open && graph ? (
        <div className="mt-4 space-y-3">
          {otherNodes.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {otherNodes.map((n) => (
                <span
                  key={`${n.type}-${n.id}`}
                  className="inline-flex items-center gap-1 rounded bg-muted/10 px-2 py-1 text-xs text-muted"
                >
                  <span className="uppercase">{n.type.replace("_", " ")}</span>
                  {n.label}
                  {n.card_count > 0 ? (
                    <span className="text-primary">({n.card_count})</span>
                  ) : null}
                </span>
              ))}
            </div>
          ) : null}

          {cardNodes.length > 0 ? (
            <div className="grid gap-2 sm:grid-cols-2">
              {cardNodes.map((n) => (
                <button
                  key={n.id}
                  type="button"
                  className="rounded-md border border-line bg-white p-3 text-left hover:border-primary transition"
                  onClick={() => onSelectCard?.(n.id)}
                >
                  <h4 className="text-sm font-medium text-ink">{n.label}</h4>
                </button>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted">
              {t("graph.no_relationships")}
            </p>
          )}

          {graph.edges.length > 0 ? (
            <div className="flex flex-wrap gap-1">
              {graph.edges.map((e, i) => (
                <span
                  key={`${e.edge_type}-${i}`}
                  className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary"
                  title={e.evidence?.evidence}
                >
                  {e.edge_type.replace(/_/g, " ")}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
