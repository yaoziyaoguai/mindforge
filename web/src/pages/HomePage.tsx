import { useEffect, useState } from "react";
import { ArrowRight, BookOpen, CheckSquare, Inbox, ShieldCheck, Download, Settings } from "lucide-react";
import type { HomeStatusResponse, LifecycleResponse, WorkflowSummaryResponse } from "../api/types";
import type { HealthReportResponse } from "../api/types";
import { useLocale } from "../lib/i18n";
import { QuickStartWizard } from "../components/QuickStartWizard";
import { ProviderStatusBanner } from "../components/ProviderStatusBanner";
import { cssShadows } from "../design/tokens";

interface WikiStatus {
  section_count?: number;
  last_rebuilt_at?: string | null;
  stale?: boolean;
}

export function HomePage({ data, workflow, onNavigate }: { data: HomeStatusResponse; workflow?: WorkflowSummaryResponse; onNavigate: (href: string) => void }) {
  const { t } = useLocale();
  const [health, setHealth] = useState<HealthReportResponse | null>(null);
  const [wikiStatus, setWikiStatus] = useState<WikiStatus | null>(null);
  const [lifecycle, setLifecycle] = useState<LifecycleResponse | null>(null);

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
    fetch("/api/lifecycle")
      .then((r) => r.json())
      .then((lc: LifecycleResponse) => setLifecycle(lc))
      .catch(() => setLifecycle(null));
  }, []);

  const approvedCount = data.vault.approved_card_count;
  const pendingCount = workflow?.ai_draft_count ?? data.safety.pending_drafts_count;
  const totalCards = approvedCount + pendingCount;
  const sourceCount = workflow?.processed_source_count ?? 0;

  /* First-run: full onboarding wizard if no data at all */
  if (totalCards === 0 && sourceCount === 0) {
    return (
      <div className="space-y-8">
        <header className="page-header">
          <h1>{t("home.title")}</h1>
          <p>{t("home.subtitle")}</p>
        </header>
        <QuickStartWizard onNavigate={onNavigate} />
      </div>
    );
  }

  const isRealModel = data.safety.provider_state === "ready";

  return (
    <div className="space-y-10">
      {/* Top Section: Greeting and Status Banner */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <header>
          <h1
            className="text-[28px] font-medium text-ink leading-tight"
            style={{ fontFamily: "var(--mf-font-serif)" }}
          >
            {t("home.title") || "Good morning, MindForge"}
          </h1>
          <p className="mt-2 text-sm text-muted">
            {t("home.subtitle") || "Turn scattered information into your trusted knowledge."}
          </p>
        </header>

        {/* Setup Banner (replaces previous top-width banner) */}
        <ProviderStatusBanner providerState={data.safety.provider_state} onNavigate={onNavigate} />
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <MetricCard
          icon={Inbox}
          label={t("home.lifecycle.source") || "Sources"}
          value={sourceCount}
          sub="Connected"
          iconColor="text-indigo-600"
          iconBg="bg-indigo-50"
        />
        <MetricCard
          icon={Settings}
          label={t("home.lifecycle.draft") || "AI Drafts"}
          value={workflow?.ai_draft_count || 0}
          sub="Generated"
          iconColor="text-blue-600"
          iconBg="bg-blue-50"
        />
        <MetricCard
          icon={CheckSquare}
          label="Ready for Review"
          value={pendingCount}
          sub="Pending"
          iconColor="text-amber-600"
          iconBg="bg-amber-50"
          action={() => onNavigate("/drafts")}
        />
        <MetricCard
          icon={BookOpen}
          label={t("home.lifecycle.approved") || "Approved"}
          value={approvedCount}
          sub="Total"
          iconColor="text-emerald-700"
          iconBg="bg-emerald-50"
        />
      </div>

      {/* The Knowledge Flow visual pipeline */}
      <section>
        <h2 className="mb-4 text-base font-semibold text-ink">The MindForge Knowledge Flow</h2>
        <div
          className="flex flex-col gap-3 rounded-xl border p-6 md:flex-row md:items-center md:gap-4"
          style={{ background: "var(--mf-surface)", borderColor: "var(--mf-border)", boxShadow: cssShadows.raised }}
        >
          <FlowStep
            step="1"
            title="Import"
            desc="Bring in what matters from Cubox, files, or web."
            color="indigo"
          />
          <ArrowRight className="hidden text-line md:block" />
          <FlowStep
            step="2"
            title="AI Draft"
            desc="AI helps you summarize, structure and write."
            color="blue"
          />
          <ArrowRight className="hidden text-line md:block" />
          <FlowStep
            step="3"
            title="Human Review"
            desc="You review, edit and approve. Quality comes from you."
            color="amber"
          />
          <ArrowRight className="hidden text-line md:block" />
          <FlowStep
            step="4"
            title="Safe Export"
            desc="Export Markdown for Obsidian. We never write to your vault."
            color="emerald"
          />
        </div>
        <div className="mt-4 flex flex-wrap gap-4 text-[11px] font-medium text-muted/80">
          <div className="flex items-center gap-1.5"><ShieldCheck className="h-3 w-3" /> No auto-approval. You stay in control.</div>
          <div className="flex items-center gap-1.5"><Download className="h-3 w-3" /> No real Obsidian write. Export is always a safe copy.</div>
        </div>
      </section>

      {/* Needs Review / Recent Activity lists */}
      {pendingCount > 0 && (
        <section>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-semibold text-ink">Needs Your Review</h2>
            <button onClick={() => onNavigate("/drafts")} className="text-xs font-medium text-primary hover:underline">View all</button>
          </div>
          <div className="rounded-xl border border-line bg-panel p-2 shadow-subtle">
            {/* Mocking recent drafts for visual placeholder, actual data could be wired up if available */}
            <div className="flex items-center justify-between rounded-lg p-3 hover:bg-stone-50 transition-colors cursor-pointer" onClick={() => onNavigate("/drafts")}>
              <div className="flex items-center gap-3">
                <div className="rounded bg-amber-50 p-1.5 text-amber-600"><CheckSquare className="h-4 w-4" /></div>
                <div>
                  <div className="text-sm font-medium text-ink">Review pending cards</div>
                  <div className="text-xs text-muted">{pendingCount} items waiting for your approval</div>
                </div>
              </div>
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium uppercase text-amber-800 tracking-wider">review</span>
            </div>
          </div>
        </section>
      )}

    </div>
  );
}

function MetricCard({ icon: Icon, label, value, sub, iconColor, iconBg, action }: any) {
  return (
    <div
      className={`relative rounded-xl border p-5 transition-shadow hover:shadow-subtle ${action ? "cursor-pointer" : ""}`}
      style={{ background: "var(--mf-surface)", borderColor: "var(--mf-border)" }}
      onClick={action}
    >
      <div className="mb-3 flex items-center gap-3">
        <div className={`flex h-8 w-8 items-center justify-center rounded-md ${iconBg}`}>
          <Icon className={`h-4 w-4 ${iconColor}`} />
        </div>
        <span className="text-sm font-medium text-muted">{label}</span>
      </div>
      <div className="text-2xl font-semibold text-ink tracking-tight">{value}</div>
      <div className="mt-1 text-xs text-muted/80">{sub}</div>
    </div>
  );
}

function FlowStep({ step, title, desc, color }: any) {
  const colorMap: any = {
    indigo: { bg: "bg-indigo-50", text: "text-indigo-700", border: "border-indigo-100" },
    blue: { bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-100" },
    amber: { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-100" },
    emerald: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-100" }
  };
  const c = colorMap[color];
  return (
    <div className={`flex flex-1 flex-col rounded-lg border p-4 ${c.bg} ${c.border}`}>
      <div className="mb-2 flex items-center gap-2">
        <div className={`flex h-5 w-5 items-center justify-center rounded-full bg-white text-xs font-bold shadow-sm ${c.text}`}>{step}</div>
        <div className={`text-sm font-semibold ${c.text}`}>{title}</div>
      </div>
      <div className="text-xs text-muted/90 leading-relaxed">{desc}</div>
    </div>
  );
}
