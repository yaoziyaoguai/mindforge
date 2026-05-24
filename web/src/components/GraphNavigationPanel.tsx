import { useEffect, useState } from "react";
import { ChevronDown, ChevronUp, GitBranch, Loader2 } from "lucide-react";
import { fetchGraphNode } from "../api/graph";
import type { GraphEdgeResponse, GraphEdgeType, GraphResponse } from "../api/types";
import { useLocale } from "../lib/i18n";

interface Props {
  cardRef: string;
  onSelectCard?: (ref: string) => void;
}

/** EdgeType → i18n key mapping for group labels. */
const EDGE_TYPE_LABEL_KEY: Record<string, string> = {
  related_by_source: "graph.related_by_source",
  shares_tag: "graph.shares_tag",
  related_by_wiki_section: "graph.related_by_wiki_section",
  wiki_section_reference: "graph.wiki_section_reference",
  related_by_source_generic: "graph.related_by_source_generic",
  derived_from: "graph.derived_from",
  mentions: "graph.mentions",
  similar_title_or_term: "graph.similar_title_or_term",
  links_to: "graph.links_to",
};

/** EdgeType → sort order. */
const EDGE_TYPE_SORT: Record<string, number> = {
  related_by_source: 0,
  related_by_wiki_section: 1,
  wiki_section_reference: 2,
  shares_tag: 3,
  similar_title_or_term: 4,
  links_to: 5,
  derived_from: 6,
  mentions: 7,
};

/** Strength → CSS color. */
function strengthColor(s: number): string {
  if (s >= 0.8) return "bg-safe";
  if (s >= 0.5) return "bg-amber-500";
  return "bg-muted";
}

export function GraphNavigationPanel({ cardRef, onSelectCard }: Props) {
  const { t } = useLocale();
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [depth, setDepth] = useState(1);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchGraphNode(cardRef, depth)
      .then((g) => {
        setGraph(g);
        // Auto-expand first 3 groups
        const groups = groupEdgesByType(g.edges, g.center_id);
        const auto: Record<string, boolean> = {};
        Object.keys(groups).slice(0, 3).forEach((k) => { auto[k] = true; });
        setExpandedGroups(auto);
      })
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Graph load failed")
      )
      .finally(() => setLoading(false));
  }, [cardRef, depth]);

  if (loading) {
    return (
      <section className="border-t border-line p-5">
        <div className="flex items-center gap-2 text-sm text-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          {t("graph.loading")}
        </div>
      </section>
    );
  }

  if (error || !graph) {
    return (
      <section className="border-t border-line p-5">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-ink">
          <GitBranch className="h-4 w-4" /> {t("graph.title")}
        </h3>
        <p className="mt-2 text-sm text-muted">{t("graph.load_failed")}</p>
      </section>
    );
  }

  const cardEdges = graph.edges.filter(
    (e) => e.source_id === graph.center_id || e.target_id === graph.center_id,
  );
  const groups = groupEdgesByType(cardEdges, graph.center_id);

  // Get neighbor card nodes
  const neighborCards = graph.nodes.filter(
    (n) => n.type === "card" && n.id !== graph.center_id,
  );

  if (Object.keys(groups).length === 0 && neighborCards.length === 0) {
    return (
      <section className="border-t border-line p-5">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-ink">
          <GitBranch className="h-4 w-4" /> {t("graph.title")}
        </h3>
        <p className="mt-3 text-sm text-muted leading-relaxed">
          {t("graph.no_relationships")}
        </p>
      </section>
    );
  }

  const sortedTypes = Object.keys(groups).sort(
    (a, b) => (EDGE_TYPE_SORT[a] ?? 99) - (EDGE_TYPE_SORT[b] ?? 99),
  );

  return (
    <section className="border-t border-line p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-ink">
          <GitBranch className="h-4 w-4" /> {t("graph.title")}
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted">
            {neighborCards.length} {t("graph.neighbor_cards")}
          </span>
          <button
            type="button"
            className={`rounded px-2 py-0.5 text-xs font-medium transition ${
              depth >= 2
                ? "bg-primary/10 text-primary"
                : "bg-muted/10 text-muted hover:text-ink"
            }`}
            onClick={() => setDepth(depth >= 2 ? 1 : 2)}
          >
            {depth >= 2 ? t("graph.collapse_2hop") : t("graph.expand_2hop")}
          </button>
        </div>
      </div>

      <div className="mt-4 space-y-4">
        {sortedTypes.map((edgeType) => {
          const entries = groups[edgeType as GraphEdgeType];
          const isExpanded = expandedGroups[edgeType] ?? false;
          const labelKey = EDGE_TYPE_LABEL_KEY[edgeType] ?? edgeType;
          return (
            <div key={edgeType}>
              <button
                type="button"
                className="flex w-full items-center justify-between text-xs font-semibold uppercase tracking-wide text-muted hover:text-ink"
                onClick={() =>
                  setExpandedGroups((prev) => ({
                    ...prev,
                    [edgeType]: !isExpanded,
                  }))
                }
              >
                <span>
                  {t(labelKey)} · {entries.length}
                </span>
                {isExpanded ? (
                  <ChevronUp className="h-3 w-3" />
                ) : (
                  <ChevronDown className="h-3 w-3" />
                )}
              </button>
              {isExpanded && entries ? (
                <div className="mt-2 flex gap-3 overflow-x-auto pb-1">
                  {entries.map((edge: GraphEdgeResponse) => {
                    const neighborId =
                      edge.source_id === graph.center_id
                        ? edge.target_id
                        : edge.source_id;
                    const neighborNode = graph.nodes.find(
                      (n) => n.id === neighborId && n.type === "card",
                    );
                    return (
                      <button
                        key={`${edge.edge_type}-${edge.source_id}-${edge.target_id}`}
                        type="button"
                        className="flex-shrink-0 w-52 rounded-md border border-line bg-white p-3 text-left hover:border-primary transition"
                        onClick={() => onSelectCard?.(neighborId)}
                      >
                        <h4 className="text-sm font-medium text-ink line-clamp-2">
                          {neighborNode?.label ?? neighborId}
                        </h4>
                        {edge.evidence && (
                          <div className="mt-2 space-y-1">
                            <p className="text-[10px] text-muted leading-relaxed">
                              {edge.evidence.evidence}
                            </p>
                            <div className="flex items-center gap-1">
                              <span
                                className={`inline-block h-1.5 w-1.5 rounded-full ${strengthColor(edge.evidence.strength)}`}
                              />
                              <span className="text-[10px] text-muted">
                                {t("graph.strength")}:{" "}
                                {(edge.evidence.strength * 100).toFixed(0)}%
                              </span>
                            </div>
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}

/** Group edges by their edge_type, deduplicating by (source,target,type) tuple. */
function groupEdgesByType(
  edges: GraphEdgeResponse[],
  centerId: string,
): Record<GraphEdgeType, GraphEdgeResponse[]> {
  const seen = new Set<string>();
  const groups: Record<string, GraphEdgeResponse[]> = {};
  for (const edge of edges) {
    // Deduplicate: normalize direction relative to center
    const key = [edge.edge_type, edge.source_id, edge.target_id].sort().join("|");
    if (seen.has(key)) continue;
    seen.add(key);
    (groups[edge.edge_type] ??= []).push(edge);
  }
  return groups;
}
