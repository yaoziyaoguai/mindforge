import { ArrowRight } from "lucide-react";
import type { NextAction } from "../api/types";

export function NextActionCard({ action, onNavigate }: { action: NextAction; onNavigate?: (href: string) => void }) {
  return (
    <button
      className="flex w-full items-start justify-between rounded-md border border-blue-200 bg-blue-50 p-4 text-left text-primary transition hover:border-primary"
      onClick={() => action.href && onNavigate?.(action.href)}
      type="button"
    >
      <span>
        <span className="block font-semibold">{action.label}</span>
        <span className="mt-1 block text-sm text-muted">{action.description}</span>
        {action.command ? <code className="mt-2 block text-xs text-ink">{action.command}</code> : null}
      </span>
      <ArrowRight aria-hidden="true" className="mt-1 h-4 w-4" />
    </button>
  );
}
