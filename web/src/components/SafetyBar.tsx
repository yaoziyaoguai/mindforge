import { CheckCircle2, Clock3, FlaskConical, Settings, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import { truncateMiddle } from "../lib/utils";
import { useLocale } from "../lib/i18n";
import type { SafetySummary } from "../api/types";

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
    return <div className="px-10 py-5 text-xs text-muted">{t("safety.loading")}</div>;
  }

  const providerReady = safety.provider_state === "ready";
  const firstWarning = safety.warnings[0];

  return (
    <section
      className="flex flex-wrap items-center justify-end gap-2 px-6 py-5 md:px-10 lg:px-12"
      aria-label="Safety Bar"
    >
      <StatusPill title={t("safety.local_data")} detail={truncateMiddle(safety.vault_path, 44)} tone="local">
        <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
      </StatusPill>

      <button
        type="button"
        onClick={() => onNavigate?.("/setup")}
        className="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-bold transition-colors hover:bg-white"
        style={{
          borderColor: providerReady ? "rgba(50, 103, 214, 0.18)" : "rgba(91,70,246,0.18)",
          background: providerReady ? "rgba(50, 103, 214, 0.08)" : "var(--mf-accent-soft)",
          color: providerReady ? "var(--mf-info)" : "var(--mf-accent)",
        }}
      >
        {providerReady ? (
          <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
        ) : (
          <FlaskConical className="h-3.5 w-3.5" aria-hidden="true" />
        )}
        {providerReady ? t("safety.real_provider") : t("safety.demo_provider")}
        <Settings className="h-3.5 w-3.5 opacity-70" aria-hidden="true" />
      </button>

      {safety.pending_drafts_count > 0 ? (
        <StatusPill title={t("safety.needs_review")} detail={String(safety.pending_drafts_count)} tone="review">
          <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
        </StatusPill>
      ) : null}

      {firstWarning ? (
        <StatusPill title={t("safety.warning")} detail={firstWarning} tone="warning" />
      ) : (
        <StatusPill title={t("safety.safe_local_read")} detail={t("safety.explicit_approval")} tone="safe">
          <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
        </StatusPill>
      )}
    </section>
  );
}

function StatusPill({
  title,
  detail,
  tone,
  children,
}: {
  title: string;
  detail?: string;
  tone: "local" | "review" | "warning" | "safe";
  children?: ReactNode;
}) {
  const toneStyle = {
    local: { background: "rgba(255,255,255,0.78)", color: "var(--mf-text-secondary)" },
    review: { background: "rgba(216,135,34,0.1)", color: "var(--mf-warning)" },
    warning: { background: "rgba(216,135,34,0.12)", color: "var(--mf-warning)" },
    safe: { background: "rgba(20,150,107,0.08)", color: "var(--mf-approved)" },
  }[tone];

  return (
    <div
      className="inline-flex max-w-[360px] items-center gap-2 truncate rounded-full border px-3 py-1.5 text-xs font-semibold"
      style={{ ...toneStyle, borderColor: "var(--mf-border)" }}
      title={detail}
    >
      {children}
      <span className="whitespace-nowrap">{title}</span>
      {detail ? (
        <span className="truncate opacity-70">{detail}</span>
      ) : null}
    </div>
  );
}
