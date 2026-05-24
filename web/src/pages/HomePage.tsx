import { useEffect, useState } from "react";
import { BookOpen, FileText, AlertCircle, Heart, Library, Upload, Search } from "lucide-react";
import type { HomeStatusResponse, WorkflowSummaryResponse } from "../api/types";
import type { HealthReportResponse } from "../api/types";
import { useLocale } from "../lib/i18n";

interface WikiStatus {
  section_count?: number;
  last_rebuilt_at?: string | null;
  stale?: boolean;
}

export function HomePage({ data, workflow, onNavigate }: { data: HomeStatusResponse; workflow?: WorkflowSummaryResponse; onNavigate: (href: string) => void }) {
  const { t } = useLocale();
  const [health, setHealth] = useState<HealthReportResponse | null>(null);
  const [wikiStatus, setWikiStatus] = useState<WikiStatus | null>(null);

  useEffect(() => {
    fetch("/api/knowledge/health")
      .then((r) => r.json())
      .then((h: HealthReportResponse) => setHealth(h))
      .catch(() => setHealth(null));
    fetch("/api/wiki/status")
      .then((r) => r.json())
      .then((w) => setWikiStatus({
        section_count: w.section_count,
        last_rebuilt_at: w.last_rebuilt_at,
        stale: w.stale,
      }))
      .catch(() => setWikiStatus(null));
  }, []);

  const approvedCount = data.vault.approved_card_count;
  const pendingCount = workflow?.ai_draft_count ?? data.safety.pending_drafts_count;
  const wikiSectionCount = wikiStatus?.section_count ?? 0;
  const healthIssueCount = health?.issues?.length ?? 0;
  const healthLevel: "good" | "warn" = healthIssueCount > 0 ? "warn" : "good";

  /* ── Attention Feed 计算 ── */
  interface AttentionItem {
    priority: "high" | "medium" | "low" | "info";
    message: string;
    affectedCount?: number;
    href?: string;
  }

  const attentionItems: AttentionItem[] = [];
  if (pendingCount > 0) {
    attentionItems.push({ priority: "high", message: t("home.attention.pending_approval").replace("{count}", String(pendingCount)), affectedCount: pendingCount, href: "/drafts" });
  }
  if (health?.issues) {
    const staleWikiIssues = health.issues.filter((i) => i.code === "wiki_stale" || i.code.includes("stale"));
    if (staleWikiIssues.length > 0) {
      attentionItems.push({ priority: "medium", message: t("home.attention.stale_wiki"), href: "/wiki" });
    }
    const lowQualityIssues = health.issues.filter((i) => i.code === "low_quality" || i.code.includes("quality"));
    if (lowQualityIssues.length > 0) {
      const count = lowQualityIssues.reduce((sum, i) => sum + i.affected_card_ids.length, 0);
      attentionItems.push({ priority: "medium", message: t("home.attention.low_quality").replace("{count}", String(count)), affectedCount: count, href: "/health" });
    }
    const orphanIssues = health.issues.filter((i) => i.code === "orphans" || i.code.includes("orphan"));
    if (orphanIssues.length > 0) {
      const count = orphanIssues.reduce((sum, i) => sum + i.affected_card_ids.length, 0);
      attentionItems.push({ priority: "low", message: t("home.attention.orphan_cards").replace("{count}", String(count)), affectedCount: count, href: "/health" });
    }
  }
  if (!data.recall.index_exists) {
    attentionItems.push({ priority: "info", message: t("home.attention.index_needed"), href: "/recall" });
  }
  attentionItems.sort((a, b) => ["high", "medium", "low", "info"].indexOf(a.priority) - ["high", "medium", "low", "info"].indexOf(b.priority));

  const priorityTone = (p: string) => p === "high" ? "text-danger bg-red-50 border-red-200" : p === "medium" ? "text-warn bg-amber-50 border-amber-200" : p === "low" ? "text-muted bg-stone-50 border-line" : "text-info bg-blue-50 border-blue-200";

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-ink">{t("home.title")}</h1>
        <p className="mt-1 text-sm text-muted">{t("home.subtitle")}</p>
      </header>

      {/* ── U1: Knowledge Overview Cards ── */}
      <section>
        <h2 className="mb-4 text-sm font-medium uppercase tracking-wide text-muted">{t("home.dashboard.overview_title")}</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <OverviewCard
            icon={BookOpen}
            label={t("home.dashboard.approved_label")}
            value={approvedCount}
            suffix={approvedCount > 0 ? t("home.dashboard.approved_suffix").replace("{count}", String(approvedCount)) : ""}
            status={approvedCount > 0 ? "ok" : "info"}
            href="/library"
            onNavigate={onNavigate}
          />
          <OverviewCard
            icon={FileText}
            label={t("home.dashboard.wiki_label")}
            value={wikiSectionCount}
            suffix={t("home.dashboard.wiki_suffix")}
            status={wikiSectionCount > 0 ? "ok" : "info"}
            href="/wiki"
            onNavigate={onNavigate}
          />
          <OverviewCard
            icon={AlertCircle}
            label={t("home.dashboard.pending_label")}
            value={pendingCount}
            suffix={pendingCount > 0 ? t("home.dashboard.pending_suffix").replace("{count}", String(pendingCount)) : ""}
            status={pendingCount > 0 ? "warn" : "ok"}
            href="/drafts"
            onNavigate={onNavigate}
          />
          <OverviewCard
            icon={Heart}
            label={t("home.dashboard.health_label")}
            value={healthLevel === "good" ? t("home.dashboard.health_good") : t("home.dashboard.health_warn")}
            suffix={healthLevel === "warn" ? t("home.dashboard.health_items").replace("{count}", String(healthIssueCount)) : ""}
            status={healthLevel}
            href="/health"
            onNavigate={onNavigate}
          />
        </div>
      </section>

      {/* ── U2: Attention Feed ── */}
      <section>
        <h2 className="mb-4 text-sm font-medium uppercase tracking-wide text-muted">{t("home.dashboard.attention_title")}</h2>
        {attentionItems.length === 0 ? (
          <div className="rounded-md border border-line bg-panel p-6 text-center text-sm text-muted">
            {t("home.dashboard.attention_empty")}
          </div>
        ) : (
          <div className="space-y-2">
            {attentionItems.map((item, idx) => (
              <button
                key={idx}
                className="flex w-full items-center justify-between rounded-md border border-line bg-panel p-4 text-left transition hover:border-primary"
                onClick={() => item.href && onNavigate(item.href)}
                type="button"
              >
                <div className="flex items-center gap-3">
                  <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${priorityTone(item.priority)}`}>
                    {item.priority === "high" ? "高" : item.priority === "medium" ? "中" : item.priority === "low" ? "低" : "信息"}
                  </span>
                  <span className="text-sm text-ink">{item.message}</span>
                </div>
                {item.href && <span className="text-xs text-primary">查看 →</span>}
              </button>
            ))}
          </div>
        )}
      </section>

      {/* ── U3: Quick Actions Bar ── */}
      <section>
        <h2 className="mb-4 text-sm font-medium uppercase tracking-wide text-muted">{t("home.dashboard.quick_actions")}</h2>
        <div className="grid gap-3 sm:grid-cols-3">
          <QuickAction icon={Library} label={t("home.dashboard.action_browse")} href="/library" onNavigate={onNavigate} />
          <QuickAction icon={Upload} label={t("home.dashboard.action_import")} href="/sources" onNavigate={onNavigate} />
          <QuickAction icon={Search} label={t("home.dashboard.action_search")} href="/recall" onNavigate={onNavigate} />
        </div>
      </section>
    </div>
  );
}

/* ── U1: Overview Card ── */
function OverviewCard({ icon: Icon, label, value, suffix, status, href, onNavigate }: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  suffix: string;
  status: string;
  href: string;
  onNavigate: (href: string) => void;
}) {
  const statusBorder = status === "ok" ? "border-l-green-400" : status === "warn" ? "border-l-amber-400" : status === "good" ? "border-l-green-400" : "border-l-blue-400";
  return (
    <button
      className={`flex flex-col rounded-md border border-line bg-panel p-4 text-left border-l-4 ${statusBorder} transition hover:shadow-subtle`}
      onClick={() => onNavigate(href)}
      type="button"
    >
      <div className="flex items-center gap-2 text-muted">
        <Icon className="h-4 w-4" aria-hidden="true" />
        <span className="text-xs font-medium uppercase tracking-wide">{label}</span>
      </div>
      <div className="mt-2 text-2xl font-semibold text-ink">{value}</div>
      {suffix ? <div className="mt-1 text-xs text-muted">{suffix}</div> : null}
    </button>
  );
}

/* ── U3: Quick Action ── */
function QuickAction({ icon: Icon, label, href, onNavigate }: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  href: string;
  onNavigate: (href: string) => void;
}) {
  return (
    <button
      className="flex items-center gap-3 rounded-md border border-line bg-panel p-4 text-left transition hover:border-primary hover:shadow-subtle"
      onClick={() => onNavigate(href)}
      type="button"
    >
      <Icon className="h-5 w-5 text-primary" aria-hidden="true" />
      <span className="text-sm font-medium text-ink">{label}</span>
    </button>
  );
}
