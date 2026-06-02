import { useEffect, useState } from "react";
import { ArrowRight, BookOpen, FileText } from "lucide-react";
import type { HomeStatusResponse, LifecycleResponse, WorkflowSummaryResponse } from "../api/types";
import type { HealthReportResponse } from "../api/types";
import { useLocale } from "../lib/i18n";
import { QuickStartWizard } from "../components/QuickStartWizard";
import { ProviderStatusBanner } from "../components/ProviderStatusBanner";

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

  /* ── Attention items (calm, no priority badges) ── */
  interface AttentionItem {
    message: string;
    href?: string;
  }
  const attentionItems: AttentionItem[] = [];
  if (pendingCount > 0) {
    attentionItems.push({
      message: t("home.attention.pending_approval").replace("{count}", String(pendingCount)),
      href: "/drafts",
    });
  }
  if (health?.issues) {
    for (const issue of health.issues) {
      if (issue.code === "wiki_stale" || issue.code.includes("stale")) {
        attentionItems.push({ message: t("home.attention.stale_wiki"), href: "/wiki" });
        break;
      }
    }
  }
  if (!data.recall.index_exists) {
    attentionItems.push({ message: t("home.attention.index_needed"), href: "/recall" });
  }

  /* ── First-run: full onboarding wizard ── */
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

  return (
    <div className="space-y-12">
      {/* Hero: Welcome + primary action */}
      <section className="pt-4">
        <h1
          className="text-3xl font-medium text-ink leading-tight"
          style={{ fontFamily: "var(--mf-font-serif)" }}
        >
          {approvedCount > 0
            ? t("home.title")
            : t("home.onboarding.title")}
        </h1>
        <p className="mt-3 text-base text-muted max-w-xl leading-relaxed">
          {approvedCount > 0
            ? `${t("home.dashboard.approved_label")}: ${approvedCount} 张卡片 · Wiki: ${wikiStatus?.section_count ?? 0} 章节`
            : t("home.onboarding.subtitle")}
        </p>

        {/* Primary next action */}
        {pendingCount > 0 && (
          <button
            type="button"
            onClick={() => onNavigate("/drafts")}
            className="mt-6 inline-flex items-center gap-2 rounded-lg px-5 py-3 text-sm font-medium text-white transition-colors hover:opacity-90"
            style={{ background: "var(--mf-accent)" }}
          >
            {t("home.dashboard.pending_label")}: {pendingCount} 张待审阅
            <ArrowRight className="h-4 w-4" />
          </button>
        )}
      </section>

      {/* Provider status: always visible, lets user know demo/real mode at a glance */}
      <ProviderStatusBanner
        providerState={data.safety.provider_state}
        onNavigate={onNavigate}
      />

      {/* Lifecycle: calm horizontal flow */}
      {totalCards > 0 && (
        <section>
          <h2 className="text-xs font-medium text-muted/70 mb-4">{t("home.lifecycle.title")}</h2>
          <div className="flex items-center gap-6 flex-wrap text-sm">
            <LifecycleStat icon={FileText} label={t("home.lifecycle.source")} value={sourceCount} />
            <span className="text-muted/30">→</span>
            <LifecycleStat icon={FileText} label={t("home.lifecycle.draft")} value={pendingCount} />
            <span className="text-muted/30">→</span>
            <LifecycleStat icon={BookOpen} label={t("home.lifecycle.approved")} value={approvedCount} />
          </div>
        </section>
      )}

      {/* Per-source breakdown */}
      {lifecycle && lifecycle.sources.length > 0 && (
        <section>
          <h2 className="text-xs font-medium text-muted/70 mb-3">{t("home.lifecycle.by_source")}</h2>
          <div className="space-y-1">
            {lifecycle.sources.map((src) => {
              const srcApprovalRate = src.total_cards > 0 ? Math.round((src.human_approved_count / src.total_cards) * 100) : 0;
              return (
                <div key={src.source_id} className="flex items-center gap-4 py-2 text-sm">
                  <span className="flex-1 text-ink truncate">{src.source_title}</span>
                  <span className="text-xs text-muted">
                    <span className="inline-block w-2 h-2 rounded-full mr-1.5" style={{ background: "var(--mf-draft)" }} />
                    {src.ai_draft_count}
                  </span>
                  <span className="text-xs text-muted">
                    <span className="inline-block w-2 h-2 rounded-full mr-1.5" style={{ background: "var(--mf-approved)" }} />
                    {src.human_approved_count}
                  </span>
                  <span className="text-xs text-muted min-w-[3rem] text-right">{srcApprovalRate}%</span>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Attention: calm nudges */}
      {attentionItems.length > 0 && (
        <section>
          <h2 className="text-xs font-medium text-muted/70 mb-3">{t("home.dashboard.attention_title")}</h2>
          <div className="space-y-1">
            {attentionItems.map((item, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => item.href && onNavigate(item.href)}
                className="block text-sm text-muted hover:text-ink transition-colors py-0.5"
              >
                {item.message} {item.href ? "→" : ""}
              </button>
            ))}
          </div>
        </section>
      )}

      {attentionItems.length === 0 && (
        <p className="text-sm text-muted">{t("home.dashboard.attention_empty")}</p>
      )}
    </div>
  );
}

function LifecycleStat({ icon: Icon, label, value }: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number;
}) {
  return (
    <div className="flex items-center gap-2">
      <Icon className="h-4 w-4 text-muted/50" aria-hidden="true" />
      <span className="text-muted">{label}</span>
      <span className="font-medium text-ink tabular-nums">{value}</span>
    </div>
  );
}
