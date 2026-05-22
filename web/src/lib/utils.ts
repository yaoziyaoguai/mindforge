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

/** 用户侧状态文案映射 —— 把内部状态码（ai_draft、human_approved 等）转成用户可理解的标签。
 *  不改数据字段、不改 API 返回值、不改 approval 语义。
 *  技术原始状态通过 CardWorkspace 的 "Technical details" 折叠区保留，满足开发排查需要。 */
export function friendlyStatus(status?: string | null): string {
  if (status === "ai_draft") return "待确认";
  if (status === "human_approved") return "已确认";
  if (status === "processed") return "已处理";
  if (status === "skipped") return "已跳过";
  if (status === "failed") return "失败";
  if (status === "pending") return "等待中";
  if (status === "imported") return "已导入";
  return status || "-";
}
