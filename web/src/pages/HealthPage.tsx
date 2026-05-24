import { useEffect, useState } from "react";
import { AlertTriangle, ArrowRight, CheckCircle2, Heart, Info } from "lucide-react";
import { getKnowledgeHealth } from "../api/health";
import type { HealthReportResponse } from "../api/types";
import { useLocale } from "../lib/i18n";
import { cx } from "../lib/utils";

export function HealthPage({ onNavigate }: { onNavigate: (href: string) => void }) {
  const { t } = useLocale();
  const [report, setReport] = useState<HealthReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getKnowledgeHealth()
      .then((data) => { if (!cancelled) setReport(data); })
      .catch((err) => { if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load health report"); });
    return () => { cancelled = true; };
  }, []);

  const severityIcon = (s: string) => {
    switch (s) {
      case "critical": return <AlertTriangle className="h-4 w-4 text-red-600" />;
      case "warn": return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
      default: return <Info className="h-4 w-4 text-blue-600" />;
    }
  };

  const severityLabel = (s: string) => {
    switch (s) {
      case "critical": return t("health.severity_critical");
      case "warn": return t("health.severity_warn");
      default: return t("health.severity_info");
    }
  };

  const severityBadge = (s: string) => {
    switch (s) {
      case "critical": return "bg-red-100 text-red-700";
      case "warn": return "bg-yellow-100 text-yellow-700";
      default: return "bg-blue-100 text-blue-700";
    }
  };

  const statLabels: Record<string, string> = {
    total_cards: "health.stats_cards",
    approved: "health.stats_approved",
    pending_drafts: "health.stats_drafts",
    missing_provenance: "health.stats_missing_provenance",
    low_quality: "health.stats_low_quality",
    orphans: "health.stats_orphans",
    duplicates: "health.stats_duplicates",
    stale_wiki: "health.stats_wiki_stale",
    source_warnings: "health.stats_source_warnings",
  };

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6">
        <p className="text-red-700">{error}</p>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 animate-pulse rounded bg-muted/20" />
        <div className="h-4 w-96 animate-pulse rounded bg-muted/20" />
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-32 animate-pulse rounded-lg border border-line bg-white" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-ink">{t("health.page_title")}</h1>
      <p className="mt-1 text-sm text-muted">{t("health.page_desc")}</p>

      {/* Stats Grid */}
      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        {Object.entries(report.stats).map(([key, value]) => (
          <div key={key} className="rounded-md border border-line bg-white px-4 py-3">
            <div className="text-xs text-muted">{t(statLabels[key] ?? key)}</div>
            <div className="mt-1 text-xl font-semibold text-ink">{value}</div>
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="mt-5 flex items-center gap-2 rounded-md border border-line bg-white px-4 py-3">
        {report.issues.length === 0 ? (
          <>
            <CheckCircle2 className="h-5 w-5 text-green-600" />
            <p className="text-sm text-ink">{t("health.all_clear")}</p>
          </>
        ) : (
          <>
            <Heart className="h-5 w-5 text-primary" />
            <p className="text-sm font-medium text-ink">{t("health.summary_prefix")}{report.summary}</p>
          </>
        )}
      </div>

      {/* Issues */}
      {report.issues.length > 0 && (
        <div className="mt-6 space-y-4">
          {report.issues.map((issue) => (
            <div key={issue.code} className="rounded-lg border border-line bg-white p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  {severityIcon(issue.severity)}
                  <div>
                    <h3 className="text-sm font-semibold text-ink">{issue.message}</h3>
                    <p className="mt-1 text-xs text-muted">{issue.reason}</p>
                  </div>
                </div>
                <span className={cx("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium", severityBadge(issue.severity))}>
                  {severityLabel(issue.severity)}
                </span>
              </div>

              <div className="mt-3 flex flex-wrap items-center gap-3">
                <p className="text-sm text-muted">{issue.suggested_action}</p>
                {issue.affected_card_ids.length > 0 && (
                  <button
                    type="button"
                    className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-primary/90"
                    onClick={() => {
                      const ids = issue.affected_card_ids.slice(0, 10).join(",");
                      onNavigate(`/library?cards=${encodeURIComponent(ids)}`);
                    }}
                  >
                    {t("health.explore_affected")}
                    <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Maintenance Suggestions */}
      {report.maintenance_suggestions.length > 0 && (
        <div className="mt-6 rounded-lg border border-line bg-white p-5">
          <h2 className="text-sm font-semibold text-ink">{t("health.maintenance_title")}</h2>
          <ul className="mt-2 space-y-1.5">
            {report.maintenance_suggestions.map((s, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-muted">
                <span className="mt-1.5 block h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                {s}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
