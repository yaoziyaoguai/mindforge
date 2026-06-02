import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  CheckSquare,
  Download,
  FileText,
  FlaskConical,
  Inbox,
  Settings,
  ShieldCheck,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import type { HomeStatusResponse, WorkflowSummaryResponse } from "../api/types";
import { ProviderStatusBanner } from "../components/ProviderStatusBanner";
import { useLocale } from "../lib/i18n";

type MetricTone = "purple" | "blue" | "amber" | "green";

export function HomePage({
  data,
  workflow,
  onNavigate,
}: {
  data: HomeStatusResponse;
  workflow?: WorkflowSummaryResponse;
  onNavigate: (href: string) => void;
}) {
  const { t } = useLocale();
  const sourceCount = workflow?.processed_source_count ?? sumRecord(data.workspace.source_counts);
  const aiDraftCount = workflow?.ai_draft_count ?? data.vault.draft_card_count ?? data.safety.pending_drafts_count;
  const readyForReviewCount = data.safety.pending_drafts_count ?? aiDraftCount;
  const approvedCount = workflow?.human_approved_count ?? data.vault.approved_card_count;
  const providerReady = data.safety.provider_state === "ready";
  const statsAreLive = Boolean(workflow);

  return (
    <div className="space-y-8">
      <section className="grid gap-5 lg:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.8fr)]">
        <div className="mf-card-soft overflow-hidden p-7 md:p-8">
          <div className="flex flex-wrap items-center gap-2">
            <span className={providerReady ? "mf-chip mf-chip-success" : "mf-chip mf-chip-accent"}>
              {providerReady ? (
                <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
              ) : (
                <FlaskConical className="h-3.5 w-3.5" aria-hidden="true" />
              )}
              {providerReady ? t("home.real_mode") : t("home.demo_mode")}
            </span>
            <span className="mf-chip">
              <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
              {t("home.local_first")}
            </span>
          </div>

          <div className="mt-7 max-w-3xl">
            <p className="text-sm font-bold uppercase tracking-[0.14em]" style={{ color: "var(--mf-accent)" }}>
              {t("home.welcome_eyebrow")}
            </p>
            <h1 className="mt-3 text-4xl font-black leading-[1.05] tracking-tight text-ink md:text-5xl">
              {t("home.welcome_title")}
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-muted">
              {providerReady ? t("home.welcome_desc_real") : t("home.welcome_desc_demo")}
            </p>
          </div>

          <div className="mt-7 flex flex-wrap gap-3">
            <button
              type="button"
              className="mf-primary-button px-5 py-3 text-sm"
              onClick={() => onNavigate("/setup")}
            >
              <Settings className="h-4 w-4" aria-hidden="true" />
              {t("home.configure_real_model")}
            </button>
            <button
              type="button"
              className="mf-secondary-button px-5 py-3 text-sm"
              onClick={() => onNavigate(sourceCount > 0 ? "/drafts" : "/sources")}
            >
              {sourceCount > 0 ? t("home.review_drafts") : t("home.add_sources")}
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>

          <div className="mt-7 grid gap-3 text-xs text-muted md:grid-cols-3">
            <BoundaryNote icon={ShieldCheck} text={t("home.boundary_ai_draft")} />
            <BoundaryNote icon={CheckSquare} text={t("home.boundary_human_review")} />
            <BoundaryNote icon={Download} text={t("home.boundary_safe_export")} />
          </div>
        </div>

        <div className="space-y-4">
          <ProviderStatusBanner providerState={data.safety.provider_state} onNavigate={onNavigate} />
          <section className="mf-card p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-base font-bold text-ink">{t("home.first_run_title")}</h2>
                <p className="mt-1 text-sm leading-6 text-muted">{t("home.first_run_desc")}</p>
              </div>
              <Sparkles className="h-5 w-5 shrink-0" style={{ color: "var(--mf-accent)" }} aria-hidden="true" />
            </div>
            <div className="mt-4 space-y-2">
              <MiniAction
                label={t("home.first_run_model")}
                done={providerReady}
                onClick={() => onNavigate("/setup")}
              />
              <MiniAction
                label={t("home.first_run_source")}
                done={sourceCount > 0}
                onClick={() => onNavigate("/sources")}
              />
              <MiniAction
                label={t("home.first_run_review")}
                done={approvedCount > 0}
                onClick={() => onNavigate("/drafts")}
              />
            </div>
          </section>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        <MetricCard
          icon={Inbox}
          label={t("home.metric_sources")}
          value={sourceCount}
          detail={statsAreLive ? t("home.metric_sources_live") : t("home.metric_fallback")}
          tone="purple"
          onClick={() => onNavigate("/sources")}
        />
        <MetricCard
          icon={FileText}
          label={t("home.metric_ai_drafts")}
          value={aiDraftCount}
          detail={t("home.metric_ai_drafts_desc")}
          tone="blue"
          onClick={() => onNavigate("/drafts")}
        />
        <MetricCard
          icon={CheckSquare}
          label="Ready for Review"
          value={readyForReviewCount}
          detail={t("home.metric_ready_desc")}
          tone="amber"
          onClick={() => onNavigate("/drafts")}
        />
        <MetricCard
          icon={BookOpen}
          label={t("home.metric_approved")}
          value={approvedCount}
          detail={t("home.metric_approved_desc")}
          tone="green"
          onClick={() => onNavigate("/library")}
        />
      </section>

      {/* 中文学习型说明：
          Knowledge Flow 明确保护产品边界：AI 只能产出 ai_draft，
          human_approved 必须来自显式人工审阅，Export 只消费已确认知识且是安全副本。 */}
      <section className="mf-card p-6">
        <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.14em]" style={{ color: "var(--mf-accent)" }}>
              MindForge
            </p>
            <h2 className="mt-1 text-xl font-black text-ink">Knowledge Flow</h2>
          </div>
          <span className="mf-chip">
            <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
            {t("home.flow_boundary")}
          </span>
        </div>

        <div className="grid gap-3 lg:grid-cols-5">
          <FlowStep icon={Inbox} title="Import" desc={t("home.flow_import")} />
          <FlowStep icon={FileText} title="AI Draft" desc={t("home.flow_draft")} />
          <FlowStep icon={CheckSquare} title="Human Review" desc={t("home.flow_review")} />
          <FlowStep icon={BookOpen} title="Approved Knowledge" desc={t("home.flow_approved")} />
          <FlowStep icon={Download} title="Export" desc={t("home.flow_export")} />
        </div>
      </section>
    </div>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
  detail,
  tone,
  onClick,
}: {
  icon: LucideIcon;
  label: string;
  value: number;
  detail: string;
  tone: MetricTone;
  onClick: () => void;
}) {
  const toneStyle = toneMap[tone];

  return (
    <button
      type="button"
      className="mf-card group min-h-[154px] p-5 text-left transition-all hover:-translate-y-0.5"
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl" style={{ background: toneStyle.bg }}>
          <Icon className="h-5 w-5" style={{ color: toneStyle.text }} aria-hidden={true} />
        </div>
        <ArrowRight className="h-4 w-4 opacity-0 transition-opacity group-hover:opacity-60" aria-hidden="true" />
      </div>
      <div className="mt-5 text-3xl font-black tracking-tight text-ink">{value}</div>
      <div className="mt-1 text-sm font-bold text-ink">{label}</div>
      <p className="mt-2 text-xs leading-5 text-muted">{detail}</p>
    </button>
  );
}

function FlowStep({
  icon: Icon,
  title,
  desc,
}: {
  icon: LucideIcon;
  title: string;
  desc: string;
}) {
  return (
    <article className="relative rounded-2xl border border-line bg-white/80 p-4">
      <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-2xl" style={{ background: "var(--mf-accent-faint)" }}>
        <Icon className="h-5 w-5" style={{ color: "var(--mf-accent)" }} aria-hidden={true} />
      </div>
      <h3 className="text-sm font-black text-ink">{title}</h3>
      <p className="mt-2 text-xs leading-5 text-muted">{desc}</p>
    </article>
  );
}

function BoundaryNote({
  icon: Icon,
  text,
}: {
  icon: LucideIcon;
  text: string;
}) {
  return (
    <div className="flex items-start gap-2 rounded-2xl border border-white/70 bg-white/62 px-3 py-2">
      <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0" style={{ color: "var(--mf-accent)" }} aria-hidden={true} />
      <span className="leading-5">{text}</span>
    </div>
  );
}

function MiniAction({
  label,
  done,
  onClick,
}: {
  label: string;
  done: boolean;
  onClick: () => void;
}) {
  const { t } = useLocale();

  return (
    <button
      type="button"
      className="flex w-full items-center justify-between gap-3 rounded-2xl border border-line bg-white/72 px-3 py-2.5 text-left text-sm transition-colors hover:bg-white"
      onClick={onClick}
    >
      <span className="font-bold text-ink">{label}</span>
      <span className={done ? "mf-chip mf-chip-success !px-2 !py-1 !text-[11px]" : "mf-chip !px-2 !py-1 !text-[11px]"}>
        {done ? t("shared.done") : t("shared.open")}
      </span>
    </button>
  );
}

function sumRecord(values: Record<string, number>) {
  return Object.values(values).reduce((total, item) => total + item, 0);
}

const toneMap: Record<MetricTone, { bg: string; text: string }> = {
  purple: { bg: "var(--mf-accent-soft)", text: "var(--mf-accent)" },
  blue: { bg: "rgba(50, 103, 214, 0.1)", text: "var(--mf-info)" },
  amber: { bg: "rgba(216, 135, 34, 0.12)", text: "var(--mf-warning)" },
  green: { bg: "rgba(20, 150, 107, 0.1)", text: "var(--mf-approved)" },
};
