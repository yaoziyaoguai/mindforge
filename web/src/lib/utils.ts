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
