import { useEffect, useState } from "react";
import { AlertTriangle, ArrowRight, CheckCircle2, Heart, Info, Loader2 } from "lucide-react";
import { getKnowledgeHealth } from "../api/health";
import type { HealthReportResponse } from "../api/types";
import { useLocale } from "../lib/i18n";

function navigateTo(href: string) {
  window.location.href = href;
}

function severityColor(s: string): string {
  switch (s) {
    case "critical": return "text-red-600 bg-red-50 border-red-200";
    case "warn": return "text-amber-600 bg-amber-50 border-amber-200";
    default: return "text-blue-600 bg-blue-50 border-blue-200";
  }
}

export function HealthStatusBar() {
  const { t } = useLocale();
  const [health, setHealth] = useState<HealthReportResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getKnowledgeHealth()
      .then((h) => { if (!cancelled) setHealth(h); })
      .catch(() => { if (!cancelled) setHealth(null); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-line bg-panel px-4 py-3 text-xs text-muted">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        {t("health.checking")}
      </div>
    );
  }

  if (!health) return null;

  const criticalCount = health.issues.filter((i) => i.severity === "critical").length;
  const warnCount = health.issues.filter((i) => i.severity === "warn").length;
  const infoCount = health.issues.filter((i) => i.severity === "info").length;

  const allClear = health.issues.length === 0;

  return (
    <div className={`rounded-md border px-4 py-3 transition ${
      allClear ? "border-green-200 bg-green-50/30" : "border-line bg-panel"
    }`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className={`flex items-center justify-center w-7 h-7 rounded-full ${
            allClear ? "bg-green-100 text-green-600" : "bg-primary/10 text-primary"
          }`}>
            {allClear ? <CheckCircle2 className="h-4 w-4" /> : <Heart className="h-4 w-4" />}
          </span>
          <div>
            <p className="text-sm font-medium text-ink">
              {allClear ? t("health.all_clear") : health.summary}
            </p>
            {!allClear ? (
              <div className="flex items-center gap-2 mt-0.5">
                {criticalCount > 0 ? (
                  <span className="inline-flex items-center gap-1 text-[11px] text-red-600">
                    <AlertTriangle className="h-3 w-3" />{criticalCount} {t("health.severity_critical")}
                  </span>
                ) : null}
                {warnCount > 0 ? (
                  <span className="inline-flex items-center gap-1 text-[11px] text-amber-600">
                    <AlertTriangle className="h-3 w-3" />{warnCount} {t("health.severity_warn")}
                  </span>
                ) : null}
                {infoCount > 0 ? (
                  <span className="inline-flex items-center gap-1 text-[11px] text-blue-600">
                    <Info className="h-3 w-3" />{infoCount} {t("health.severity_info")}
                  </span>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>

        {!allClear ? (
          <div className="flex flex-wrap items-center gap-2">
            {health.issues.slice(0, 2).map((issue) => (
              <span
                key={issue.code}
                className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium ${severityColor(issue.severity)}`}
                title={issue.reason}
              >
                {issue.message}
              </span>
            ))}
            {health.issues.length > 2 ? (
              <span className="text-[11px] text-muted">+{health.issues.length - 2} more</span>
            ) : null}
            <button
              type="button"
              className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-primary hover:bg-primary/5 transition"
              onClick={() => navigateTo("/health")}
            >
              {t("health.view_details")}
              <ArrowRight className="h-3 w-3" />
            </button>
          </div>
        ) : (
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-muted hover:text-ink transition"
            onClick={() => navigateTo("/health")}
          >
            {t("health.view_details")}
            <ArrowRight className="h-3 w-3" />
          </button>
        )}
      </div>
    </div>
  );
}
