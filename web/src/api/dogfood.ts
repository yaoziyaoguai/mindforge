import type { DogfoodReportResponse } from "./types";

export async function getDogfoodReport(): Promise<DogfoodReportResponse> {
  const resp = await fetch("/api/dogfood/report");
  if (!resp.ok) throw new Error("Failed to load dogfood report");
  return resp.json();
}
