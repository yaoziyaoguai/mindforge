import { useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronUp, GitBranch, Layers, Loader2 } from "lucide-react";
import { fetchGraphNode } from "../api/graph";
import type { GraphEdgeResponse, GraphEdgeType, GraphResponse } from "../api/types";
import { useLocale } from "../lib/i18n";

interface Props {
  cardRef: string;
  onSelectCard?: (ref: string) => void;
}

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

/** Edge type → accent bar color. */
const EDGE_TYPE_COLOR: Record<string, string> = {
  related_by_source: "border-l-safe",
  related_by_wiki_section: "border-l-blue-500",
  wiki_section_reference: "border-l-violet-500",
  shares_tag: "border-l-amber-500",
  similar_title_or_term: "border-l-cyan-500",
  links_to: "border-l-rose-500",
  derived_from: "border-l-emerald-500",
  mentions: "border-l-slate-500",
};

function strengthBar(s: number): string {
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
        const groups = groupEdgesByType(g.edges, g.center_id);
        const auto: Record<string, boolean> = {};
        Object.keys(groups).slice(0, 4).forEach((k) => { auto[k] = true; });
        setExpandedGroups(auto);
      })
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Graph load failed")
      )
      .finally(() => setLoading(false));
  }, [cardRef, depth]);

  if (loading) {
    return (
      <section className="border border-line rounded-lg bg-panel p-6">
        <div className="flex items-center gap-3 text-sm text-muted">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span>{t("graph.loading")}</span>
        </div>
      </section>
    );
  }

  if (error || !graph) {
    return (
      <section className="border border-line rounded-lg bg-panel p-6">
        <div className="flex items-center gap-2 mb-3">
          <GitBranch className="h-5 w-5 text-muted" />
          <h3 className="text-base font-semibold text-ink">{t("graph.title")}</h3>
        </div>
        <p className="text-sm text-muted">{t("graph.load_failed")}</p>
      </section>
    );
  }

  const cardEdges = graph.edges.filter(
    (e) => e.source_id === graph.center_id || e.target_id === graph.center_id,
  );
  const groups = groupEdgesByType(cardEdges, graph.center_id);

  const neighborCards = graph.nodes.filter(
    (n) => n.type === "card" && n.id !== graph.center_id,
  );

  // Edge type distribution for summary bar
  const typeDistribution = useMemo(() => {
    const dist: Record<string, number> = {};
    for (const [etype, entries] of Object.entries(groups)) {
      dist[etype] = entries?.length ?? 0;
    }
    return dist;
  }, [groups]);

  const sortedTypes = Object.keys(groups).sort(
    (a, b) => (EDGE_TYPE_SORT[a] ?? 99) - (EDGE_TYPE_SORT[b] ?? 99),
  );

  const totalEdges = Object.values(groups).reduce((sum, arr) => sum + (arr?.length ?? 0), 0);

  if (Object.keys(groups).length === 0 && neighborCards.length === 0) {
    return (
      <section className="border border-line rounded-lg bg-panel p-6">
        <div className="flex items-center gap-2 mb-3">
          <GitBranch className="h-5 w-5 text-muted" />
          <h3 className="text-base font-semibold text-ink">{t("graph.title")}</h3>
        </div>
        <p className="text-sm text-muted leading-relaxed">
          {t("graph.no_relationships")}
        </p>
      </section>
    );
  }

  return (
    <section className="border border-line rounded-lg bg-panel overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-line bg-stone-50/50">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span className="flex items-center justify-center w-8 h-8 rounded-md bg-primary/10 text-primary">
              <GitBranch className="h-4 w-4" />
            </span>
            <div>
              <h3 className="text-sm font-semibold text-ink">{t("graph.title")}</h3>
              <p className="text-xs text-muted mt-0.5">
                {neighborCards.length} {t("graph.neighbor_cards")} · {totalEdges} {t("graph.evidence")}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* Summary chips */}
            <div className="hidden sm:flex items-center gap-1.5">
              {sortedTypes.slice(0, 3).map((etype) => (
                <span
                  key={etype}
                  className="inline-flex items-center gap-1 rounded-full bg-white border border-line px-2 py-0.5 text-[10px] text-muted"
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${EDGE_TYPE_COLOR[etype] ? EDGE_TYPE_COLOR[etype].replace("border-l-", "bg-").replace("safe", "safe") : "bg-muted"}`} />
                  {t(EDGE_TYPE_LABEL_KEY[etype] ?? etype)}·{typeDistribution[etype]}
                </span>
              ))}
              {sortedTypes.length > 3 ? (
                <span className="text-[10px] text-muted">+{sortedTypes.length - 3}</span>
              ) : null}
            </div>
            {/* Depth toggle */}
            <button
              type="button"
              className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition ${
                depth >= 2
                  ? "bg-primary/10 text-primary"
                  : "bg-white border border-line text-muted hover:text-ink"
              }`}
              onClick={() => setDepth(depth >= 2 ? 1 : 2)}
            >
              <Layers className="h-3 w-3" />
              {depth >= 2 ? t("graph.collapse_2hop") : t("graph.expand_2hop")}
            </button>
          </div>
        </div>
      </div>

      {/* Relationship groups */}
      <div className="px-6 py-4 space-y-3">
        {sortedTypes.map((edgeType) => {
          const entries = groups[edgeType as GraphEdgeType];
          const isExpanded = expandedGroups[edgeType] ?? false;
          const labelKey = EDGE_TYPE_LABEL_KEY[edgeType] ?? edgeType;
          const accentBar = EDGE_TYPE_COLOR[edgeType] ?? "border-l-muted";
          return (
            <div key={edgeType}>
              <button
                type="button"
                className="flex w-full items-center justify-between rounded-md px-3 py-2 text-xs font-semibold text-muted hover:bg-muted/5 transition"
                onClick={() =>
                  setExpandedGroups((prev) => ({
                    ...prev,
                    [edgeType]: !isExpanded,
                  }))
                }
              >
                <span className="flex items-center gap-2">
                  {isExpanded ? (
                    <ChevronUp className="h-3 w-3" />
                  ) : (
                    <ChevronDown className="h-3 w-3" />
                  )}
                  {t(labelKey)}
                  <span className="font-normal text-muted/60">{entries?.length ?? 0}</span>
                </span>
              </button>
              {isExpanded && entries ? (
                <div className="mt-2 grid gap-2 sm:grid-cols-2">
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
                        className={`flex flex-col rounded-md border border-line bg-white hover:border-primary transition text-left border-l-2 ${accentBar}`}
                        onClick={() => onSelectCard?.(neighborId)}
                      >
                        <div className="p-3 flex-1">
                          <h4 className="text-sm font-medium text-ink line-clamp-2">
                            {neighborNode?.label ?? neighborId}
                          </h4>
                          {edge.evidence?.evidence ? (
                            <p className="mt-1.5 text-[11px] text-muted leading-relaxed line-clamp-2">
                              {edge.evidence.evidence}
                            </p>
                          ) : null}
                        </div>
                        {edge.evidence ? (
                          <div className="flex items-center gap-1.5 px-3 py-1.5 border-t border-line/50 bg-stone-50/30">
                            <span
                              className={`inline-block h-1.5 w-1.5 rounded-full ${strengthBar(edge.evidence.strength)}`}
                            />
                            <span className="text-[10px] text-muted">
                              {(edge.evidence.strength * 100).toFixed(0)}%
                            </span>
                          </div>
                        ) : null}
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

function groupEdgesByType(
  edges: GraphEdgeResponse[],
  centerId: string,
): Record<GraphEdgeType, GraphEdgeResponse[]> {
  const seen = new Set<string>();
  const groups: Record<string, GraphEdgeResponse[]> = {};
  for (const edge of edges) {
    const key = [edge.edge_type, edge.source_id, edge.target_id].sort().join("|");
    if (seen.has(key)) continue;
    seen.add(key);
    (groups[edge.edge_type] ??= []).push(edge);
  }
  return groups;
}
