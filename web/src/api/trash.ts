/** Trash API client —— 卡片安全移到回收站 / 恢复。 */

import type { TrashActionResponse, TrashDetailResponse, TrashListResponse } from "./types";

const base = "/api/trash";

export async function getTrashCards(): Promise<TrashListResponse> {
  const response = await fetch(`${base}`);
  if (!response.ok) throw new Error("Failed to load trash");
  return response.json();
}

export async function getTrashDetail(trashRelPath: string): Promise<TrashDetailResponse> {
  const response = await fetch(`${base}/${encodeURIComponent(trashRelPath)}`);
  if (!response.ok) throw new Error("Trash card not found");
  return response.json();
}

export async function moveDraftToTrash(draftId: string): Promise<TrashActionResponse> {
  const response = await fetch(`${base}/drafts/${encodeURIComponent(draftId)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confirm: true, trash_rel_path: draftId }),
  });
  if (!response.ok) throw new Error("Failed to move draft to trash");
  return response.json();
}

export async function moveLibraryCardToTrash(cardRef: string): Promise<TrashActionResponse> {
  const response = await fetch(`${base}/library/${encodeURIComponent(cardRef)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confirm: true, trash_rel_path: cardRef }),
  });
  if (!response.ok) throw new Error("Failed to move card to trash");
  return response.json();
}

export async function restoreTrashCard(trashRelPath: string): Promise<TrashActionResponse> {
  const response = await fetch(`${base}/restore`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confirm: true, trash_rel_path: trashRelPath }),
  });
  if (!response.ok) throw new Error("Failed to restore card");
  return response.json();
}
