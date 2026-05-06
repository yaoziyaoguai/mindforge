export function cx(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

export function statusTone(status: string): string {
  if (status === "ok") return "text-safe bg-green-50 border-green-200";
  if (status === "warn") return "text-warn bg-amber-50 border-amber-200";
  if (status === "error") return "text-danger bg-red-50 border-red-200";
  return "text-muted bg-stone-50 border-line";
}

export function truncateMiddle(value: string, max = 72): string {
  if (value.length <= max) return value;
  const head = Math.ceil((max - 3) / 2);
  const tail = Math.floor((max - 3) / 2);
  return `${value.slice(0, head)}...${value.slice(-tail)}`;
}

export function friendlyStatus(status?: string | null): string {
  if (status === "ai_draft") return "Needs review";
  if (status === "human_approved") return "Approved";
  if (status === "processed") return "Processed";
  if (status === "skipped") return "Skipped";
  if (status === "failed") return "Failed";
  if (status === "pending") return "Pending";
  if (status === "imported") return "Imported";
  return status || "-";
}
