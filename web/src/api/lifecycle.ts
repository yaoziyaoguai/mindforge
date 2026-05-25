import type { LifecycleResponse } from "./types";

export async function getLifecycle(): Promise<LifecycleResponse> {
  const resp = await fetch("/api/lifecycle");
  if (!resp.ok) throw new Error("Failed to load lifecycle data");
  return resp.json();
}
