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

export function SafetyBar({ safety }: { safety?: SafetySummary | null }) {
  const { t } = useLocale();

  if (!safety) {
    return <div className="border-b border-line bg-stone-50/50 px-4 py-2 text-xs text-muted">{t("safety.loading")}</div>;
  }

  return (
    <section
      className="border-b border-line bg-stone-50/50 px-4 py-2"
      aria-label="Safety Bar"
    >
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
        <span className="inline-flex items-center gap-1.5">
          <ShieldCheck className="h-3.5 w-3.5 text-stone-400" aria-hidden="true" />
          <span className="text-stone-500">Vault: {truncateMiddle(safety.vault_path, 36)}</span>
        </span>

        <span className="inline-flex items-center gap-1.5">
          <span>{t("safety.model_setup")}</span>
          {safety.provider_state === "ready" ? (
            <BoundaryBadge type="live" />
          ) : (
            <BoundaryBadge type="sandbox" />
          )}
        </span>

        <span className="inline-flex items-center gap-1">
          <span>{t("safety.needs_review")}{safety.pending_drafts_count}</span>
        </span>

        {safety.warnings.length > 0 ? (
          <span className="text-warn">{safety.warnings[0]}</span>
        ) : (
          <span className="inline-flex items-center gap-1 text-stone-400">
            <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
            {t("safety.safe_local_read")}
          </span>
        )}
      </div>
    </section>
  );
}
