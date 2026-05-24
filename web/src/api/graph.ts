import type { GraphEdgeDetailResponse, GraphResponse } from "./types";

const BASE = "/api/graph";

export async function fetchGraphNode(
  ref: string,
  depth = 2,
): Promise<GraphResponse> {
  const url = `${BASE}/node?ref=${encodeURIComponent(ref)}&depth=${depth}`;
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`Graph node fetch failed: ${resp.status}`);
  }
  return resp.json() as Promise<GraphResponse>;
}

export async function fetchGraphExplore(
  nodeType: string,
  nodeId: string,
  depth = 1,
): Promise<GraphResponse> {
  const url = `${BASE}/explore?node_type=${encodeURIComponent(nodeType)}&node_id=${encodeURIComponent(nodeId)}&depth=${depth}`;
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`Graph explore fetch failed: ${resp.status}`);
  }
  return resp.json() as Promise<GraphResponse>;
}

export async function fetchGraphEdge(
  source: string,
  target: string,
): Promise<GraphEdgeDetailResponse> {
  const url = `${BASE}/edge?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}`;
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`Graph edge fetch failed: ${resp.status}`);
  }
  return resp.json() as Promise<GraphEdgeDetailResponse>;
}
