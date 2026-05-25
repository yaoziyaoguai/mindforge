import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, GitBranch, Loader2, Search } from "lucide-react";
import { fetchGraphExplore } from "../api/graph";
import type { GraphNodeType, GraphResponse } from "../api/types";
import { GraphCanvas } from "../components/GraphCanvas";
import { useLocale } from "../lib/i18n";

/** v4.2.1 truth reset: 仅展示当前 backend 正式支持的 4 种 NodeType 作为可选项。
    community / topic / entity / concept_candidate 尚未实现，仅作 lab note 展示。 */
const SUPPORTED_TYPES: { type: GraphNodeType; icon: string }[] = [
  { type: "card", icon: "📄" },
  { type: "source", icon: "📁" },
  { type: "tag", icon: "#" },
  { type: "wiki_section", icon: "📖" },
];

/** 尚未实现的 NodeType — 仅作为 lab/internal 说明，不可选择 */
const UNSUPPORTED_TYPES = ["community", "topic", "entity", "concept_candidate"];

interface Props {
  initialCardId?: string;
  onNavigateBack?: () => void;
}

export function GraphPage({ initialCardId, onNavigateBack }: Props) {
  const { t } = useLocale();

  // 从 URL query param 读取初始卡片 ID（支持 ?card=xxx）
  const urlCardId = new URLSearchParams(window.location.search).get("card") ?? undefined;
  const effectiveCardId = initialCardId ?? urlCardId;

  const [nodeType, setNodeType] = useState<GraphNodeType>(effectiveCardId ? "card" : "source");
  const [nodeId, setNodeId] = useState(effectiveCardId ?? "");
  const [depth, setDepth] = useState(2);
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoExplored, setAutoExplored] = useState(false);

  // 自动探索：如果有 effectiveCardId，页面加载时立即查询
  useEffect(() => {
    if (effectiveCardId && !autoExplored) {
      setAutoExplored(true);
      setNodeId(effectiveCardId);
      setNodeType("card");
      explore(effectiveCardId, "card", depth);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [effectiveCardId]);

  function explore(overrideId?: string, overrideType?: GraphNodeType, overrideDepth?: number) {
    const id = overrideId ?? nodeId;
    const type = overrideType ?? nodeType;
    const d = overrideDepth ?? depth;
    if (!id.trim()) return;
    setLoading(true);
    setError(null);
    fetchGraphExplore(type, id.trim(), d)
      .then((g) => setGraph(g))
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Explore failed"),
      )
      .finally(() => setLoading(false));
  }

  const handleSelectNode = useCallback(
    (targetNode: { id: string; type: string }) => {
      // 点击节点时，以该节点为中心重新探索
      if (targetNode.type === "card" || targetNode.type === "source" || targetNode.type === "tag") {
        setNodeId(targetNode.id);
        setNodeType(targetNode.type as GraphNodeType);
        explore(targetNode.id, targetNode.type as GraphNodeType, 2);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [depth],
  );

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {onNavigateBack ? (
            <button
              type="button"
              className="rounded-md p-1.5 hover:bg-muted/10 transition"
              onClick={onNavigateBack}
              title={t("graph.back_to_library")}
            >
              <ArrowLeft className="h-5 w-5 text-muted" />
            </button>
          ) : null}
          <GitBranch className="h-5 w-5 text-primary" />
          <h1 className="text-lg font-semibold text-ink">{t("graph.title")}</h1>
        </div>
        {graph ? (
          <p className="text-xs text-muted">
            {t("graph.node_count").replace("{count}", String(graph.nodes.length))} /{" "}
            {t("graph.edge_count").replace("{count}", String(graph.edges.length))}
          </p>
        ) : null}
      </div>

      {/* Explore controls */}
      <div className="flex flex-wrap items-end gap-2">
        {/* Node type selector — 仅展示正式支持的 4 种 */}
        <div className="flex flex-wrap gap-1">
          {SUPPORTED_TYPES.map(({ type, icon }) => (
            <button
              key={type}
              type="button"
              className={`rounded-md px-2.5 py-1.5 text-xs font-medium transition ${
                nodeType === type
                  ? "bg-primary text-white"
                  : "bg-muted/10 text-muted hover:text-ink"
              }`}
              onClick={() => {
                setNodeType(type);
                setGraph(null);
                setError(null);
              }}
              title={t(`graph.node_type_${type}` as any) ?? type}
            >
              {icon}{" "}
              <span className="hidden sm:inline">
                {t(`graph.node_type_${type}` as any) ?? type}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* v4.2.1: Lab/Internal — 尚未实现的 NodeType */}
      <div className="text-xs text-muted/70 border border-dashed border-muted/20 rounded-md p-2 space-y-0.5">
        <span className="font-medium">Lab / Internal — 尚未实现的节点类型：</span>{" "}
        {UNSUPPORTED_TYPES.join(", ")}
        <br />
        <span>
          这些类型在 ontology 中定义但 backend 尚未实现，API 会返回 422。
          仅作为未来规划参考，不可选择。
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        <input
          className="flex-1 min-w-[200px] rounded-md border border-line px-3 py-2 text-sm text-ink placeholder:text-muted"
          placeholder={
            nodeType === "card"
              ? "卡片 ID..."
              : nodeType === "source"
                ? "来源文件路径..."
                : nodeType === "tag"
                  ? "标签名..."
                  : "节点标识符..."
          }
          value={nodeId}
          onChange={(e) => setNodeId(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && explore()}
        />
        <select
          className="rounded-md border border-line bg-white px-2 py-2 text-sm text-ink"
          value={depth}
          onChange={(e) => setDepth(Number(e.target.value))}
        >
          <option value={1}>1-hop</option>
          <option value={2}>2-hop</option>
          <option value={3}>3-hop</option>
        </select>
        <button
          type="button"
          className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          onClick={() => explore()}
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

      {/* Error */}
      {error ? (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {/* Loading */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="mr-2 h-5 w-5 animate-spin text-primary" />
          <span className="text-sm text-muted">{t("graph.loading")}</span>
        </div>
      ) : null}

      {/* Graph canvas */}
      {!loading && graph ? (
        <GraphCanvas
          nodes={graph.nodes}
          edges={graph.edges}
          centerId={graph.center_id}
          onSelectNode={(n) => {
            if (n.type === "card" || n.type === "source" || n.type === "tag") {
              handleSelectNode(n);
            }
          }}
        />
      ) : !loading && !error ? (
        <div className="flex items-center justify-center py-16">
          <p className="text-sm text-muted">
            选择一个节点类型（当前支持 4 种：card / source / tag / wiki_section）并输入标识符，点击探索即可查看子图。
            community / topic / entity / concept_candidate 尚未实现，仅供 lab 参考。
          </p>
        </div>
      ) : null}
    </div>
  );
}
