import { AlertTriangle, CheckCircle2, Lock, ShieldCheck } from "lucide-react";
import { truncateMiddle } from "../lib/utils";
import { useLocale } from "../lib/i18n";
import type { SafetySummary } from "../api/types";
import { BoundaryBadge } from "./BoundaryBadge";

/**
 * SafetyBar - 全局安全状态条
 *
 * 中文学习型说明：
 * 此组件是 MindForge 安全语义的核心载体。
 * 1. 强制展示 Vault 路径，体现 Local-first。
 * 2. 使用 BoundaryBadge 明确 Sandbox/Live 状态，保护 Provider 边界。
 * 3. 明确 Explicit Approval 要求，防止自动写入。
 */

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
        <span className="text-muted border-r border-line pr-3 mr-1">Vault: {truncateMiddle(safety.vault_path, 40)}</span>

        <div className="flex items-center gap-2 border-r border-line pr-3 mr-1">
          <span className="text-muted">{t("safety.model_setup")}</span>
          {safety.provider_state === "ready" ? (
            <BoundaryBadge type="live" />
          ) : (
            <BoundaryBadge type="sandbox" />
          )}
        </div>

        <span className="inline-flex items-center gap-1 text-warn border-r border-line pr-3 mr-1">
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
