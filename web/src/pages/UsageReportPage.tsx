import { useEffect, useState } from "react";
import { getUsageReport } from "../api/provider";
import type { UsageReportResponse } from "../api/provider";
import { BoundaryBadge } from "../components/BoundaryBadge";
import { useLocale } from "../lib/i18n";

export function UsageReportPage() {
  const { t } = useLocale();
  const [report, setReport] = useState<UsageReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadReport();
  }, []);

  async function loadReport() {
    setError(null);
    try {
      const data = await getUsageReport();
      setReport(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load report");
    }
  }

  if (error) {
    return (
      <div className="space-y-4">
        <header className="page-header">
          <h1>{t("usage_report.title")}</h1>
        </header>
        <div className="rounded border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
        <button className="rounded-md border border-line px-3 py-1.5 text-sm font-medium text-ink hover:bg-stone-50" onClick={loadReport} type="button">
          重试
        </button>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="space-y-4">
        <header className="page-header">
          <h1>{t("usage_report.title")}</h1>
        </header>
        <p className="text-sm text-muted">加载中...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="page-header">
        <h1>{t("usage_report.title")}</h1>
        <p className="text-xs text-muted mt-1">{t("usage_report.subtitle")}</p>
      </header>

      {/* 安全声明 */}
      <section className="flex flex-wrap gap-2 text-[11px]">
        <span className="rounded-full bg-green-100 text-green-700 px-2 py-0.5 font-medium">
          <BoundaryBadge type="provider" />
          <span className="ml-1">{t("usage_report.local_only")}</span>
        </span>
        <span className="rounded-full bg-green-100 text-green-700 px-2 py-0.5 font-medium">
          {t("usage_report.secret_safe")}
        </span>
      </section>

      {/* Provider 状态 */}
      <section className="rounded-md border border-line p-4">
        <h2 className="text-sm font-semibold text-ink mb-3">{t("usage_report.provider_status")}</h2>
        <div className="grid gap-2 text-xs md:grid-cols-3">
          <div className="rounded bg-stone-50 px-3 py-2">
            <span className="text-muted">mode: </span>
            <span className={`font-medium ${report.provider_mode === "real" ? "text-green-700" : "text-muted"}`}>
              {report.provider_mode}
            </span>
          </div>
          <div className="rounded bg-stone-50 px-3 py-2">
            <span className="text-muted">configured: </span>
            <span className={`font-medium ${report.provider_configured ? "text-green-700" : "text-muted"}`}>
              {report.provider_configured ? t("usage_report.provider_configured") : t("usage_report.provider_not_configured")}
            </span>
          </div>
          <div className="rounded bg-stone-50 px-3 py-2">
            <span className="text-muted">verified: </span>
            <span className={`font-medium ${
              report.provider_verified ? "text-green-700"
              : report.provider_verification_status === "failed" ? "text-red-700"
              : "text-amber-700"
            }`}>
              {report.provider_verified ? t("usage_report.verified") : t("usage_report.not_verified")}
            </span>
          </div>
        </div>
      </section>

      {/* 知识统计 */}
      <section className="rounded-md border border-line p-4">
        <h2 className="text-sm font-semibold text-ink mb-3">{t("usage_report.knowledge_stats")}</h2>
        <div className="grid gap-3 md:grid-cols-4">
          <MetricCard label={t("usage_report.total_cards")} value={report.total_cards} />
          <MetricCard label={t("usage_report.approved")} value={report.approved_count} />
          <MetricCard label={t("usage_report.drafts")} value={report.draft_count} />
          <MetricCard label={t("usage_report.sources")} value={report.total_sources} />
        </div>
      </section>

      {/* 基础设施 */}
      <section className="rounded-md border border-line p-4">
        <h2 className="text-sm font-semibold text-ink mb-3">{t("usage_report.infrastructure")}</h2>
        <div className="grid gap-3 md:grid-cols-4">
          <MetricCard label={t("usage_report.wiki_sections")} value={report.wiki_sections} />
          <MetricCard label={t("usage_report.search_available")} value={report.search_available ? t("shared.yes") : t("shared.no")} />
          <MetricCard label={t("usage_report.recent_runs")} value={report.recent_runs} />
          <div className="rounded bg-stone-50 px-3 py-2 text-xs">
            <div className="text-muted">{t("usage_report.export_formats")}</div>
            <div className="mt-0.5 text-muted">{t("usage_report.export_not_available")}</div>
          </div>
        </div>
      </section>

      {/* Backend gaps */}
      {report.backend_gaps && report.backend_gaps.length > 0 ? (
        <section className="rounded-md border border-amber-200 bg-amber-50 p-3">
          <h3 className="text-xs font-semibold text-amber-900 mb-1">{t("usage_report.backend_gap")}</h3>
          <ul className="space-y-0.5">
            {report.backend_gaps.map((gap, i) => (
              <li key={i} className="text-[11px] text-amber-700">{gap}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {/* 生成时间 */}
      <p className="text-[11px] text-muted">generated at: {report.generated_at}</p>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded bg-stone-50 px-3 py-2 text-xs">
      <div className="text-muted">{label}</div>
      <div className="mt-0.5 font-semibold text-ink text-lg">{value}</div>
    </div>
  );
}
