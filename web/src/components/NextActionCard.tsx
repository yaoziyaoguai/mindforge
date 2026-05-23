import { ArrowRight } from "lucide-react";
import type { NextAction } from "../api/types";
import type { Locale } from "../lib/i18n";
import { nextActionLabel } from "../lib/utils";

/* 中文学习型说明：action_key 是稳定的展示映射键，优先用于本地化。
 * label/description 是兼容 fallback，缺 action_key 时直接展示原始文案。
 * i18n 只改变 presentation，不改变 action 行为（href/command 不变）。 */
export function NextActionCard({ action, onNavigate, locale }: { action: NextAction; onNavigate?: (href: string) => void; locale?: Locale }) {
  const displayLabel = nextActionLabel(action.action_key, locale) ?? action.label;

  return (
    <button
      className="flex w-full items-start justify-between rounded-md border border-blue-200 bg-blue-50 p-4 text-left text-primary transition hover:border-primary"
      onClick={() => action.href && onNavigate?.(action.href)}
      type="button"
    >
      <span>
        <span className="block font-semibold">{displayLabel}</span>
        <span className="mt-1 block text-sm text-muted">{action.description}</span>
        {action.command ? <code className="mt-2 block text-xs text-ink">{action.command}</code> : null}
      </span>
      <ArrowRight aria-hidden="true" className="mt-1 h-4 w-4" />
    </button>
  );
}
