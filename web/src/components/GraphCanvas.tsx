import { useCallback, useEffect, useRef, useState } from "react";
import { Network } from "vis-network/standalone";
import type { GraphEdgeResponse, GraphNodeResponse } from "../api/types";
import { useLocale } from "../lib/i18n";

/** v3.7 ontology: 每种 NodeType 的颜色和形状映射 */
const NODE_STYLE: Record<string, { color: string; shape: string; icon?: string }> = {
  card: { color: "#4f46e5", shape: "box" },
  source: { color: "#0ea5e9", shape: "database" },
  wiki_section: { color: "#8b5cf6", shape: "square" },
  tag: { color: "#f59e0b", shape: "triangle" },
  community: { color: "#10b981", shape: "dot" },
  topic: { color: "#ef4444", shape: "star" },
  entity: { color: "#ec4899", shape: "diamond" },
  concept_candidate: { color: "#94a3b8", shape: "dot" },
};

interface Props {
  nodes: GraphNodeResponse[];
  edges: GraphEdgeResponse[];
  centerId: string;
  onSelectNode?: (node: GraphNodeResponse) => void;
}

export function GraphCanvas({ nodes, edges, centerId, onSelectNode }: Props) {
  const { t } = useLocale();
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNodeResponse | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<GraphEdgeResponse | null>(null);

  const nodeMapRef = useRef<Map<string, GraphNodeResponse>>(new Map());

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    const nodeMap = new Map<string, GraphNodeResponse>();
    nodes.forEach((n) => nodeMap.set(n.id, n));
    nodeMapRef.current = nodeMap;
  });

  const initGraph = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;

    if (networkRef.current) {
      networkRef.current.destroy();
      networkRef.current = null;
    }

    const visNodes = nodes.map((n) => {
      const style = NODE_STYLE[n.type] ?? { color: "#94a3b8", shape: "dot" };
      return {
        id: n.id,
        label: n.label.length > 40 ? n.label.slice(0, 38) + "…" : n.label,
        color: {
          background: style.color,
          border: n.id === centerId ? "#1e293b" : style.color,
        },
        borderWidth: n.id === centerId ? 3 : 1,
        shape: style.shape,
        font: { size: 12, color: "#334155" },
        // 中文学系型标注：缓存原始 node 数据供点击时查询
      };
    });

    const visEdges = edges.map((e) => {
      return {
        id: `${e.source_id}-${e.edge_type}-${e.target_id}`,
        from: e.source_id,
        to: e.target_id,
        label: t(`graph.${e.edge_type}` as any),
        arrows: "to",
        color: { color: "#94a3b8", highlight: "#4f46e5" },
        font: { size: 9, color: "#64748b", strokeWidth: 0 },
        width: Math.max(0.5, (e.evidence?.strength ?? 0.5) * 2),
        // 中文学系型标注：缓存原始 edge 数据供点击时展示 evidence
      };
    });

    const network = new Network(
      container,
      { nodes: visNodes, edges: visEdges },
      {
        physics: {
          solver: "forceAtlas2Based",
          forceAtlas2Based: {
            gravitationalConstant: -30,
            centralGravity: 0.005,
            springLength: 150,
            springConstant: 0.08,
          },
        },
        interaction: {
          hover: true,
          tooltipDelay: 200,
          zoomView: true,
          dragView: true,
        },
        edges: {
          smooth: { enabled: true, type: "continuous", roundness: 0.5 },
        },
      },
    );

    network.on("selectNode", (params) => {
      const nodeId = params.nodes[0] as string | undefined;
      if (!nodeId) return;
      const n = nodeMapRef.current.get((params.nodes[0] as string) ?? "");
      if (n) {
        setSelectedNode(n);
        setSelectedEdge(null);
        onSelectNode?.(n);
      }
    });

    network.on("selectEdge", (params) => {
      const edgeId = params.edges[0] as string | undefined;
      if (!edgeId) return;
      const e = edges.find(
        (ed) => `${ed.source_id}-${ed.edge_type}-${ed.target_id}` === edgeId,
      );
      if (e) {
        setSelectedEdge(e);
        setSelectedNode(null);
      }
    });

    network.on("deselectNode", () => setSelectedNode(null));
    network.on("deselectEdge", () => setSelectedEdge(null));

    networkRef.current = network;
  }, [nodes, edges, centerId, t, onSelectNode]);

  useEffect(() => {
    initGraph();
    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, edges, centerId]);

  const selectedNodeType = selectedNode ? t(`graph.node_type_${selectedNode.type}` as any) ?? selectedNode.type : "";

  return (
    <div className="flex h-full gap-0">
      {/* 图谱画布 */}
      <div
        ref={containerRef}
        className="flex-1 rounded-md border border-line bg-white"
        style={{ minHeight: 500 }}
      />

      {/* 右侧 info panel — 展示选中节点或边的证据 */}
      <div className="w-72 shrink-0 border-l border-line bg-panel p-4 overflow-y-auto">
        {selectedNode ? (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-ink">
              {selectedNodeType}
            </h3>
            <p className="text-base font-medium text-ink">{selectedNode.label}</p>
            <dl className="space-y-1 text-xs">
              <dt className="text-muted">ID</dt>
              <dd className="text-ink font-mono">{selectedNode.id}</dd>
              <dt className="text-muted">{t("graph.node_type_card")}</dt>
              <dd className="text-ink">{selectedNodeType}</dd>
              {selectedNode.card_count > 0 ? (
                <>
                  <dt className="text-muted">{t("graph.edge_count").replace("{count}", String(selectedNode.card_count))}</dt>
                  <dd className="text-ink">{selectedNode.card_count}</dd>
                </>
              ) : null}
            </dl>
            {selectedNode.href ? (
              <a
                href={selectedNode.href}
                className="mt-2 inline-block text-xs text-primary hover:underline"
              >
                {t("graph.open_graph_view")} →
              </a>
            ) : null}
          </div>
        ) : selectedEdge ? (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-ink">{t("graph.evidence")}</h3>
            <p className="text-xs font-medium text-ink">
              {t(`graph.${selectedEdge.edge_type}` as any)}
            </p>
            <dl className="space-y-1 text-xs">
              <dt className="text-muted">{t("graph.strength")}</dt>
              <dd className="text-ink">{selectedEdge.evidence.strength.toFixed(2)}</dd>
              <dt className="text-muted">{t("graph.evidence")}</dt>
              <dd className="text-ink">{selectedEdge.evidence.evidence}</dd>
              {selectedEdge.evidence.reason ? (
                <>
                  <dt className="text-muted">Reason</dt>
                  <dd className="text-ink">{selectedEdge.evidence.reason}</dd>
                </>
              ) : null}
            </dl>
          </div>
        ) : (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-ink">{t("graph.title")}</h3>
            <p className="text-xs text-muted">
              {t("graph.node_count").replace("{count}", String(nodes.length))}，{" "}
              {t("graph.edge_count").replace("{count}", String(edges.length))}
            </p>
            <p className="text-xs text-muted">
              点击节点或边查看详情与关系证据。
            </p>
            {/* 图例 */}
            <div className="space-y-1">
              <p className="text-xs font-medium text-ink mt-2">图例</p>
              {Object.entries(NODE_STYLE).map(([type, style]) => {
                const label = t(`graph.node_type_${type}` as any) ?? type;
                return (
                  <div key={type} className="flex items-center gap-1.5 text-xs">
                    <span
                      className="inline-block h-2.5 w-2.5 rounded-sm"
                      style={{ backgroundColor: style.color }}
                    />
                    <span className="text-muted">{label}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
