import { AlertTriangle, CheckCircle, X } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { Locale } from "./i18n";
import { t } from "./i18n";

export function cx(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

export function statusTone(status: string): string {
  if (status === "ok") return "text-safe bg-green-50 border-green-200";
  if (status === "warn") return "text-warn bg-amber-50 border-amber-200";
  if (status === "error") return "text-danger bg-red-50 border-red-200";
  return "text-muted bg-stone-50 border-line";
}

/** 状态图标映射 —— 色盲用户可通过图标形状区分状态，不依赖颜色。
 *  不改 statusTone() 签名，在 badge 渲染处组合调用。
 *  返回 LucideIcon 组件或 null（未知状态不渲染图标）。 */
export function statusIcon(status: string): LucideIcon | null {
  if (status === "ok") return CheckCircle;
  if (status === "warn") return AlertTriangle;
  if (status === "error") return X;
  return null;
}

/** 状态标签 —— locale 参数可选，默认 zh；传入 locale 时返回对应语言标签。 */
export function statusLabel(status: string, locale?: Locale): string {
  const key = status === "ok" ? "status.ok" : status === "warn" ? "status.warn" : status === "error" ? "status.error" : null;
  if (!key) return "";
  return locale ? t(key, locale) : t(key, "zh");
}

export function truncateMiddle(value: string, max = 72): string {
  if (value.length <= max) return value;
  const head = Math.ceil((max - 3) / 2);
  const tail = Math.floor((max - 3) / 2);
  return `${value.slice(0, head)}...${value.slice(-tail)}`;
}

/** 用户侧状态文案映射 —— 把内部状态码（ai_draft、human_approved 等）转成用户可理解的标签。
 *  不改数据字段、不改 API 返回值、不改 approval 语义。
 *  locale 参数可选，默认 zh；传入 locale 时返回对应语言标签。
 *  技术原始状态通过 CardWorkspace 的 "Technical details" 折叠区保留，满足开发排查需要。 */
export function friendlyStatus(status?: string | null, locale?: Locale): string {
  const keyMap: Record<string, string> = {
    ai_draft: "status.ai_draft",
    human_approved: "status.human_approved",
    processed: "status.processed",
    skipped: "status.skipped",
    failed: "status.failed",
    pending: "status.pending",
    imported: "status.imported",
  };
  if (status && keyMap[status]) {
    return locale ? t(keyMap[status], locale) : t(keyMap[status], "zh");
  }
  return status || "-";
}
