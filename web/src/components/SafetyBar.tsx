import { CheckCircle2, ShieldCheck } from "lucide-react";
import { truncateMiddle } from "../lib/utils";
import { useLocale } from "../lib/i18n";
import type { SafetySummary } from "../api/types";
import { BoundaryBadge } from "./BoundaryBadge";

/**
 * SafetyBar — 全局安全状态条（calm status bar, not system alert）
 *
 * 视觉方向：低调的状态指示器，像编辑器底部的 mode line，
 * 不像监控面板的告警条。安全语义通过安静的文字 + shield icon 传达，
 * 不靠颜色轰炸。
 */

export function SafetyBar({ safety, onNavigate }: { safety?: SafetySummary | null; onNavigate?: (href: string) => void }) {
  const { t } = useLocale();

  if (!safety) {
    return <div className="border-b border-line bg-stone-50/50 px-4 py-2 text-xs text-muted">{t("safety.loading")}</div>;
  }

  const providerReady = safety.provider_state === "ready";

  return (
    <section
      className="flex items-center justify-end gap-4 px-10 py-5"
      aria-label="Safety Bar"
    >
      <div className="flex items-center gap-3 text-[13px] font-medium text-muted">
        {!providerReady && (
          <button
            type="button"
            onClick={() => onNavigate && onNavigate("/setup")}
            className="flex items-center gap-1.5 rounded-full border border-indigo-100 bg-indigo-50/50 px-3 py-1.5 text-indigo-700 transition-colors hover:bg-indigo-100/50"
          >
            <ShieldCheck className="h-4 w-4" aria-hidden="true" />
            Demo Mode
          </button>
        )}

        <div className="flex items-center gap-1.5 rounded-full border border-stone-200 bg-stone-50 px-3 py-1.5 text-stone-600">
          <div className="h-2 w-2 rounded-full" style={{ background: "var(--mf-approved)" }} />
          Your data stays local
        </div>

        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-stone-800 text-sm font-semibold text-white shadow-sm">
          U
        </div>
      </div>
    </section>
  );
}
