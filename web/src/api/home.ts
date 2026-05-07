import { apiGet } from "./client";
import type { HomeStatusResponse } from "./types";

export function getHomeStatus() {
  return apiGet<HomeStatusResponse>("/api/home/status");
}
