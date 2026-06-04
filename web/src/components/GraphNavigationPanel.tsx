import { useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronUp, ExternalLink, GitBranch, Layers, Loader2, Users } from "lucide-react";
import { fetchGraphNode } from "../api/graph";
import { getKnowledgeCommunities } from "../api/library";
import type { GraphEdgeResponse, GraphEdgeType, GraphResponse, KnowledgeCommunityResponse } from "../api/types";
import { useLocale } from "../lib/i18n";

interface Props {
  cardRef: string;
  onSelectCard?: (ref: string) => void;
  embedded?: boolean;
}

const EDGE_TYPE_LABEL_KEY: Record<string, string> = {
  related_by_source: "graph.related_by_source",
  shares_tag: "graph.shares_tag",
  related_by_wiki_section: "graph.related_by_wiki_section",
  wiki_section_reference: "graph.wiki_section_reference",
  related_by_source_generic: "graph.related_by_source_generic",
  derived_from: "graph.derived_from",
  has_tag: "graph.has_tag",
  in_section: "graph.in_section",
  contains: "graph.contains",
  includes: "graph.includes",
  belongs_to_topic: "graph.belongs_to_topic",
  mentions_candidate: "graph.mentions_candidate",
  resolves_to: "graph.resolves_to",
  similar_title_or_term: "graph.similar_title_or_term",
  links_to: "graph.links_to",
};

const EDGE_TYPE_SORT: Record<string, number> = {
  derived_from: 0,
  related_by_source: 1,
  related_by_wiki_section: 2,
  wiki_section_reference: 3,
  in_section: 4,
  shares_tag: 5,
  has_tag: 6,
  contains: 7,
  includes: 8,
  belongs_to_topic: 9,
  similar_title_or_term: 10,
  links_to: 11,
  mentions_candidate: 12,
  resolves_to: 13,
};

const EDGE_TYPE_COLOR: Record<string, string> = {
  related_by_source: "border-l-safe",
  related_by_wiki_section: "border-l-blue-500",
  wiki_section_reference: "border-l-violet-500",
  shares_tag: "border-l-amber-500",
  has_tag: "border-l-amber-500",
  in_section: "border-l-indigo-500",
  contain: "border-l-emerald-500",
  includes: "border-l-red-500",
  belongs_to_topic: "border-l-red-400",
  similar_title_or_term: "border-l-cyan-500",
  links_to: "border-l-rose-500",
  derived_from: "border-l-emerald-500",
  mentions_candidate: "border-l-slate-500",
  resolves_to: "border-l-pink-500",
};

/** 社区类型的颜色编码（用于 community grouping 视图）。 */
const COMMUNITY_TYPE_COLOR: Record<string, { bar: string; dot: string }> = {
  source: { bar: "border-l-emerald-400", dot: "bg-emerald-500" },
  tag: { bar: "border-l-amber-400", dot: "bg-amber-500" },
  wiki_section: { bar: "border-l-violet-400", dot: "bg-violet-500" },
};

type GroupingMode = "by_type" | "by_community";

function strengthBar(s: number): string {
  if (s >= 0.8) return "bg-safe";
  if (s >= 0.5) return "bg-amber-500";
  return "bg-muted";
}

function qualityColor(score: number): string {
  if (score >= 0.7) return "bg-emerald-500";
  if (score >= 0.4) return "bg-amber-500";
  return "bg-slate-300";
}

export function GraphNavigationPanel({ cardRef, onSelectCard, embedded }: Props) {
  const { t } = useLocale();
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [communities, setCommunities] = useState<KnowledgeCommunityResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [depth, setDepth] = useState(1);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});
  const [groupingMode, setGroupingMode] = useState<GroupingMode>("by_type");

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      fetchGraphNode(cardRef, depth),
      getKnowledgeCommunities(),
    ]).then(([g, commData]) => {
      setGraph(g);
      setCommunities(commData.communities);
    }).catch((err: unknown) =>
      setError(err instanceof Error ? err.message : "Graph load failed")
    ).finally(() => setLoading(false));
  }, [cardRef, depth]);

  /* 中文学习型说明：所有 useMemo 必须在 early return 之前调用，
   * 否则 loading → loaded 状态切换时 hook 数量变化会触发
   * "Rendered more hooks than during the previous render"。 */

  const cardEdges = useMemo(() => {
    if (!graph) return [];
    return graph.edges.filter(
      (e) => e.source_id === graph.center_id || e.target_id === graph.center_id,
    );
  }, [graph]);

  const groups = useMemo((): Record<GraphEdgeType, GraphEdgeResponse[]> => {
    if (!graph) return {} as Record<GraphEdgeType, GraphEdgeResponse[]>;
    return groupEdgesByType(cardEdges, graph.center_id);
  }, [cardEdges, graph]);

  // Auto-expand groups when graph data first arrives (separate effect, not in useMemo)
  useEffect(() => {
    if (!graph) return;
    const g = groupEdgesByType(
      graph.edges.filter((e) => e.source_id === graph.center_id || e.target_id === graph.center_id),
      graph.center_id,
    );
    if (Object.keys(g).length === 0) return;
    setExpandedGroups((prev) => {
      // Only auto-expand if nothing is expanded yet
      if (Object.values(prev).some(Boolean)) return prev;
      const auto: Record<string, boolean> = {};
      Object.keys(g).slice(0, 4).forEach((k) => { auto[k] = true; });
      return auto;
    });
  }, [graph]);

  const neighborCards = useMemo(() => {
    if (!graph) return [];
    return graph.nodes.filter(
      (n) => n.type === "card" && n.id !== graph.center_id,
    );
  }, [graph]);

  const neighborIds = useMemo(() => new Set(neighborCards.map((n) => n.id)), [neighborCards]);

  const communityGroups = useMemo(() => {
    if (groupingMode !== "by_community") return null;
    const result: { community: KnowledgeCommunityResponse; cardIds: string[] }[] = [];
    for (const comm of communities) {
      const matchingIds = comm.member_card_ids.filter((mid) => neighborIds.has(mid));
      if (matchingIds.length > 0) {
        result.push({ community: comm, cardIds: matchingIds });
      }
    }
    result.sort((a, b) => b.community.member_count - a.community.member_count);
    return result;
  }, [communities, neighborIds, groupingMode]);

  const typeDistribution = useMemo(() => {
    const dist: Record<string, number> = {};
    for (const [etype, entries] of Object.entries(groups)) {
      dist[etype] = entries?.length ?? 0;
    }
    return dist;
  }, [groups]);

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
    <section className={embedded ? "" : "border border-line rounded-lg bg-panel overflow-hidden"}>
      {/* Header — suppressed when embedded (parent section provides context) */}
      {!embedded ? (
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
              {/* Grouping mode toggle */}
              <div className="flex items-center rounded-md border border-line bg-white overflow-hidden">
                <button
                  type="button"
                  className={`inline-flex items-center gap-1 px-2 py-1 text-[10px] font-medium transition ${
                    groupingMode === "by_type"
                      ? "bg-primary/10 text-primary"
                      : "text-muted hover:text-ink"
                  }`}
                  onClick={() => setGroupingMode("by_type")}
                  title={t("graph.group_by_type") ?? "By relation type"}
                >
                  <Layers className="h-3 w-3" />
                </button>
                <button
                  type="button"
                  className={`inline-flex items-center gap-1 px-2 py-1 text-[10px] font-medium transition ${
                    groupingMode === "by_community"
                      ? "bg-primary/10 text-primary"
                      : "text-muted hover:text-ink"
                  }`}
                  onClick={() => setGroupingMode("by_community")}
                  title={t("graph.group_by_community") ?? "By community"}
                >
                  <Users className="h-3 w-3" />
                </button>
              </div>
              {/* Summary chips (type mode only) */}
              {groupingMode === "by_type" ? (
                <div className="hidden sm:flex items-center gap-1.5">
                  {sortedTypes.slice(0, 3).map((etype) => (
                    <span
                      key={etype}
                      className="inline-flex items-center gap-1 rounded-full bg-white border border-line px-2 py-0.5 text-[10px] text-muted"
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${EDGE_TYPE_COLOR[etype] ? EDGE_TYPE_COLOR[etype].replace("border-l-", "bg-").replace("safe", "bg-safe") : "bg-muted"}`} />
                      {t(EDGE_TYPE_LABEL_KEY[etype] ?? etype)}·{typeDistribution[etype]}
                    </span>
                  ))}
                  {sortedTypes.length > 3 ? (
                    <span className="text-[10px] text-muted">+{sortedTypes.length - 3}</span>
                  ) : null}
                </div>
              ) : null}
              {/* Open in full graph view */}
              <a
                href={`/graph?card=${encodeURIComponent(cardRef)}`}
                className="inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium bg-primary text-white hover:bg-primary/90 transition"
                title={t("graph.open_graph_view")}
                onClick={(e) => {
                  e.preventDefault();
                  window.history.pushState({}, "", `/graph?card=${encodeURIComponent(cardRef)}`);
                  window.dispatchEvent(new PopStateEvent("popstate"));
                }}
              >
                <ExternalLink className="h-3 w-3" />
                {t("graph.open_graph_view")}
              </a>
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
      ) : (
        /* Compact embedded toolbar */
        <div className="flex items-center justify-end gap-2 mb-3">
          <div className="flex items-center rounded-md border border-line bg-white overflow-hidden">
            <button
              type="button"
              className={`inline-flex items-center gap-1 px-2 py-1 text-[10px] font-medium transition ${
                groupingMode === "by_type" ? "bg-primary/10 text-primary" : "text-muted hover:text-ink"
              }`}
              onClick={() => setGroupingMode("by_type")}
              title={t("graph.group_by_type") ?? "By relation type"}
            >
              <Layers className="h-3 w-3" />
            </button>
            <button
              type="button"
              className={`inline-flex items-center gap-1 px-2 py-1 text-[10px] font-medium transition ${
                groupingMode === "by_community" ? "bg-primary/10 text-primary" : "text-muted hover:text-ink"
              }`}
              onClick={() => setGroupingMode("by_community")}
              title={t("graph.group_by_community") ?? "By community"}
            >
              <Users className="h-3 w-3" />
            </button>
          </div>
          <a
            href={`/graph?card=${encodeURIComponent(cardRef)}`}
            className="inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-[10px] font-medium bg-primary text-white hover:bg-primary/90 transition"
            title={t("graph.open_graph_view")}
            onClick={(e) => {
              e.preventDefault();
              window.history.pushState({}, "", `/graph?card=${encodeURIComponent(cardRef)}`);
              window.dispatchEvent(new PopStateEvent("popstate"));
            }}
          >
            <ExternalLink className="h-3 w-3" />
            {t("graph.open_graph_view")}
          </a>
          <button
            type="button"
            className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-[10px] font-medium transition ${
              depth >= 2 ? "bg-primary/10 text-primary" : "bg-white border border-line text-muted hover:text-ink"
            }`}
            onClick={() => setDepth(depth >= 2 ? 1 : 2)}
          >
            <Layers className="h-3 w-3" />
            {depth >= 2 ? t("graph.collapse_2hop") : t("graph.expand_2hop")}
          </button>
        </div>
      )}

      {/* Content */}
      <div className={embedded ? "space-y-3" : "px-6 py-4 space-y-3"}>
        {groupingMode === "by_type" ? (
          /* ── By relation type ── */
          sortedTypes.map((edgeType) => {
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
                    {entries.map((edge: GraphEdgeResponse) => (
                      <NeighborCardButton
                        key={`${edge.edge_type}-${edge.source_id}-${edge.target_id}`}
                        edge={edge}
                        graph={graph}
                        accentBar={accentBar}
                        onSelectCard={onSelectCard}
                      />
                    ))}
                  </div>
                ) : null}
              </div>
            );
          })
        ) : (
          /* ── By community ── */
          (communityGroups ?? []).map(({ community, cardIds }) => {
            const commKey = `${community.community_type}:${community.shared_entity}`;
            const isExpanded = expandedGroups[commKey] ?? (communityGroups?.length ?? 0) <= 4;
            const colors = COMMUNITY_TYPE_COLOR[community.community_type] ?? { bar: "border-l-muted", dot: "bg-muted" };
            return (
              <div key={commKey}>
                <button
                  type="button"
                  className="flex w-full items-center justify-between rounded-md px-3 py-2 text-xs font-semibold text-muted hover:bg-muted/5 transition"
                  onClick={() =>
                    setExpandedGroups((prev) => ({
                      ...prev,
                      [commKey]: !isExpanded,
                    }))
                  }
                >
                  <span className="flex items-center gap-2 min-w-0">
                    {isExpanded ? (
                      <ChevronUp className="h-3 w-3 shrink-0" />
                    ) : (
                      <ChevronDown className="h-3 w-3 shrink-0" />
                    )}
                    <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${colors.dot}`} />
                    <span className="truncate">{community.shared_entity}</span>
                    <span className="font-normal text-muted/60 shrink-0">
                      {cardIds.length}/{community.member_count}
                    </span>
                    <span
                      className={`inline-block w-1.5 h-1.5 rounded-full shrink-0 ${qualityColor(community.quality_score)}`}
                      title={`Quality: ${(community.quality_score * 100).toFixed(0)}%`}
                    />
                  </span>
                </button>
                {isExpanded ? (
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    {cardIds.map((cardId) => {
                      const edge = cardEdges.find(
                        (e) => e.source_id === cardId || e.target_id === cardId,
                      );
                      return (
                        <NeighborCardButton
                          key={`comm-${commKey}-${cardId}`}
                          edge={edge ?? {
                            edge_type: "links_to" as GraphEdgeType,
                            source_id: graph.center_id,
                            target_id: cardId,
                            evidence: { reason: "community", evidence: community.description, strength: community.quality_score, detail: {} },
                          }}
                          graph={graph}
                          accentBar={colors.bar}
                          onSelectCard={onSelectCard}
                        />
                      );
                    })}
                  </div>
                ) : null}
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}

/** 单个邻居卡片按钮（复用组件）。仅展示 card 类型节点，过滤 source/tag 等非卡片节点。 */
function NeighborCardButton({
  edge,
  graph,
  accentBar,
  onSelectCard,
}: {
  edge: GraphEdgeResponse;
  graph: GraphResponse;
  accentBar: string;
  onSelectCard?: (ref: string) => void;
}) {
  const neighborId =
    edge.source_id === graph.center_id
      ? edge.target_id
      : edge.source_id;
  const neighborNode = graph.nodes.find(
    (n) => n.id === neighborId && n.type === "card",
  );
  // 非 card 类型节点（如 source/tag）不渲染，避免 sha1 等技术标识暴露
  if (!neighborNode) return null;

  // 人话化 evidence 文本：截断 sha1 前缀，取实际描述
  const evidenceText = edge.evidence?.evidence
    ?.replace(/^sha1:[a-f0-9]{40}\s*/, "")
    .replace(/same source document:\s*sha1:[a-f0-9]{40}\s*/, "") || null;

  return (
    <button
      key={`${edge.edge_type}-${edge.source_id}-${edge.target_id}`}
      type="button"
      className={`flex flex-col rounded-md border border-line bg-white hover:border-primary transition text-left border-l-2 ${accentBar}`}
      onClick={() => onSelectCard?.(neighborId)}
    >
      <div className="p-3 flex-1">
        <h4 className="text-sm font-medium text-ink line-clamp-2">
          {neighborNode.label}
        </h4>
        {evidenceText ? (
          <p className="mt-1.5 text-[11px] text-muted leading-relaxed line-clamp-2">
            {evidenceText}
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
