import { useEffect, useState } from "react";
import { BarChart3, FileText, GitBranch, Heart, Search, TrendingUp, Upload, AlertCircle } from "lucide-react";
import type { DogfoodReportResponse } from "../api/types";
import { getDogfoodReport } from "../api/dogfood";
import { useLocale } from "../lib/i18n";

export function DogfoodPage({ onNavigate }: { onNavigate: (href: string) => void }) {
  const { locale, t } = useLocale();
  const [report, setReport] = useState<DogfoodReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDogfoodReport()
      .then(setReport)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed"));
  }, []);

  if (error) {
    return (
      <div className="space-y-4">
        <header>
          <h1 className="text-2xl font-semibold text-ink">{t("nav.dogfood")}</h1>
        </header>
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {t("dogfood.load_failed")}: {error}
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="space-y-4">
        <header>
          <h1 className="text-2xl font-semibold text-ink">{t("nav.dogfood")}</h1>
        </header>
        <div className="rounded-md border border-line bg-panel p-6 text-center text-sm text-muted">
          {t("dogfood.loading")}
        </div>
      </div>
    );
  }

  const approvalPct = Math.round(report.approval_rate * 100);
  const densityDisplay = report.graph_density.toFixed(1);

  return (
    <div className="space-y-8">
      {/* LAB/INTERNAL — Dogfood 是内部验证/工程证据，不是普通用户功能。 */}
      <div className="rounded-md border-2 border-amber-300 bg-amber-50 p-3 text-sm">
        <div className="flex items-center gap-2 font-bold text-amber-900">
          <span>⚠️</span> LAB / INTERNAL — 内部开发验证
        </div>
        <p className="mt-1 text-xs text-amber-700">
          本页面展示的是工程团队的内部使用数据和维护建议，用于验证 MindForge pipeline 运行状态。
          不是面向普通用户的产品功能，数据仅在本地聚合，不调用外部服务或 LLM。
        </p>
      </div>
      <header>
        <h1 className="text-2xl font-semibold text-ink">{t("nav.dogfood")}</h1>
        <p className="mt-1 text-sm text-muted">{t("dogfood.subtitle")}</p>
      </header>

      {/* ── 趋势总结 ── */}
      <section className="rounded-md border border-line bg-panel p-4">
        <div className="flex items-start gap-3">
          <TrendingUp className="h-5 w-5 text-primary mt-0.5" />
          <div>
            <h2 className="text-sm font-medium text-ink">{t("dogfood.trend_title")}</h2>
            <p className="mt-1 text-sm text-muted">{report.trend_summary}</p>
          </div>
        </div>
      </section>

      {/* ── 关键指标卡片 ── */}
      <section>
        <h2 className="mb-4 text-sm font-medium uppercase tracking-wide text-muted">{t("dogfood.metrics_title")}</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            icon={FileText}
            label={t("dogfood.total_cards")}
            value={report.total_cards}
            detail={`${t("dogfood.approved")}: ${report.approved_count} · ${t("dogfood.draft")}: ${report.draft_count}`}
            status={report.total_cards > 0 ? "ok" : "info"}
            href="/library"
            onNavigate={onNavigate}
          />
          <MetricCard
            icon={TrendingUp}
            label={t("dogfood.approval_rate_label")}
            value={`${approvalPct}%`}
            detail={`${report.approved_count}/${report.total_cards}`}
            status={approvalPct >= 50 ? "ok" : "warn"}
            href="/drafts"
            onNavigate={onNavigate}
          />
          <MetricCard
            icon={GitBranch}
            label={t("dogfood.graph_density_label")}
            value={densityDisplay}
            detail={`${report.graph_total_relations} ${t("dogfood.relations")} · ${report.community_count} ${t("dogfood.communities")}`}
            status={report.graph_total_relations > 0 ? "ok" : "info"}
            href="/graph"
            onNavigate={onNavigate}
          />
          <MetricCard
            icon={Heart}
            label={t("dogfood.health_label")}
            value={report.health_issue_count === 0 ? t("home.dashboard.health_good") : report.health_issue_count}
            detail={report.health_issue_count === 0 ? t("dogfood.health_clear") : t("dogfood.health_items").replace("{count}", String(report.health_issue_count))}
            status={report.health_issue_count > 0 ? "warn" : "ok"}
            href="/health"
            onNavigate={onNavigate}
          />
        </div>
      </section>

      {/* ── 数据源与基础设施 ── */}
      <section>
        <h2 className="mb-4 text-sm font-medium uppercase tracking-wide text-muted">{t("dogfood.infra_title")}</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            icon={Upload}
            label={t("dogfood.sources_label")}
            value={report.source_count}
            detail={`${t("dogfood.imported")}: ${report.imported_card_count}`}
            status={report.source_count > 0 ? "ok" : "info"}
            href="/sources"
            onNavigate={onNavigate}
          />
          <MetricCard
            icon={FileText}
            label={t("dogfood.wiki_label")}
            value={report.wiki_section_count}
            detail={report.wiki_stale ? t("dogfood.wiki_stale_yes") : t("dogfood.wiki_stale_no")}
            status={report.wiki_stale ? "warn" : report.wiki_section_count > 0 ? "ok" : "info"}
            href="/wiki"
            onNavigate={onNavigate}
          />
          <MetricCard
            icon={Search}
            label={t("dogfood.search_label")}
            value={report.search_index_exists ? t("dogfood.search_ready") : t("dogfood.search_missing")}
            detail={report.search_index_path || "-"}
            status={report.search_index_exists ? "ok" : "warn"}
            href="/recall"
            onNavigate={onNavigate}
          />
          <MetricCard
            icon={AlertCircle}
            label={t("dogfood.errors_label")}
            value={report.import_error_count}
            detail={report.import_error_count > 0 ? t("dogfood.errors_found") : t("dogfood.errors_none")}
            status={report.import_error_count > 0 ? "warn" : "ok"}
            href="/health"
            onNavigate={onNavigate}
          />
        </div>
      </section>

      {/* ── 维护建议 ── */}
      {report.maintenance_suggestions.length > 0 && (
        <section>
          <h2 className="mb-4 text-sm font-medium uppercase tracking-wide text-muted">{t("dogfood.suggestions_title")}</h2>
          <div className="rounded-md border border-line bg-panel p-4">
            <ul className="space-y-2">
              {report.maintenance_suggestions.map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-muted">
                  <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-primary flex-shrink-0" />
                  {s}
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {/* ── 生成时间 ── */}
      <p className="text-xs text-muted/60">
        {t("dogfood.generated_at")}: {new Date(report.generated_at).toLocaleString(locale === "zh" ? "zh-CN" : "en-US", { dateStyle: "medium", timeStyle: "short" })}
      </p>
    </div>
  );
}

/* ── Metric Card ── */
function MetricCard({ icon: Icon, label, value, detail, status, href, onNavigate }: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  detail: string;
  status: string;
  href: string;
  onNavigate: (href: string) => void;
}) {
  const statusBorder = status === "ok" ? "border-l-green-400" : status === "warn" ? "border-l-amber-400" : "border-l-blue-400";
  return (
    <button
      className={`flex flex-col rounded-md border border-line bg-white p-4 text-left border-l-4 ${statusBorder} transition hover:shadow-subtle`}
      onClick={() => onNavigate(href)}
      type="button"
    >
      <div className="flex items-center gap-2 text-muted">
        <Icon className="h-4 w-4" aria-hidden="true" />
        <span className="text-xs font-medium uppercase tracking-wide">{label}</span>
      </div>
      <div className="mt-2 text-2xl font-semibold text-ink">{value}</div>
      <div className="mt-1 text-xs text-muted">{detail}</div>
    </button>
  );
}
