import { AlertTriangle, CheckCircle2, Lock, ShieldCheck } from "lucide-react";
import { truncateMiddle } from "../lib/utils";
import { useLocale } from "../lib/i18n";
import type { SafetySummary } from "../api/types";

export function SafetyBar({ safety }: { safety?: SafetySummary | null }) {
  const { t } = useLocale();

  if (!safety) {
    return <div className="border-b border-line bg-panel px-4 py-3 text-sm text-muted">{t("safety.loading")}</div>;
  }
  const hasWarning = safety.warnings.length > 0;
  return (
    <section className="border-b border-line bg-panel px-4 py-3" aria-label="Safety Bar">
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <span className="inline-flex items-center gap-1 text-safe">
          <ShieldCheck className="h-4 w-4" aria-hidden="true" />
          {safety.local_only ? t("safety.local_only") : t("safety.host_warning")}
        </span>
        <span className="text-muted">Vault: {truncateMiddle(safety.vault_path, 58)}</span>
        <span className={safety.provider_state === "ready" ? "text-safe" : safety.provider_state === "demo" ? "text-safe" : "text-warn"}>
          {t("safety.model_setup")}{safety.provider_state === "ready" ? t("safety.model_ready") : safety.provider_state === "demo" ? t("safety.model_demo") : t("safety.model_check")}
        </span>
        <span className="inline-flex items-center gap-1 text-warn">
          <Lock className="h-4 w-4" aria-hidden="true" />
          {safety.write_mode === "explicit_approval_required" ? t("safety.explicit_approval") : t("safety.read_only")}
        </span>
        <span className="text-muted">{t("safety.needs_review")}{safety.pending_drafts_count}</span>
        {hasWarning ? (
          <span className="inline-flex items-center gap-1 text-warn">
            <AlertTriangle className="h-4 w-4" aria-hidden="true" />
            {safety.warnings[0]}
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-safe">
            <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
            {t("safety.safe_local_read")}
          </span>
        )}
      </div>
    </section>
  );
}
