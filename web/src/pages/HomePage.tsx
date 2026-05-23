import type { HomeStatusResponse, WorkflowSummaryResponse } from "../api/types";
import { NextActionCard } from "../components/NextActionCard";
import { StatusCard } from "../components/StatusCard";
import { useLocale } from "../lib/i18n";

export function HomePage({ data, workflow, onNavigate }: { data: HomeStatusResponse; workflow?: WorkflowSummaryResponse; onNavigate: (href: string) => void }) {
  const { locale, t } = useLocale();

  const pendingDrafts = data.safety.pending_drafts_count;
  const inboxPending = workflow?.inbox_pending_count ?? 0;
  const approvedCards = data.vault.approved_card_count;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">{t("home.title")}</h1>
        <p className="mt-1 text-sm text-muted">{t("home.subtitle")}</p>
      </header>

      {/* ── 系统状态 ── */}
      <section>
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-muted">{t("home.section_system_status")}</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <StatusCard
            label={t("home.review_drafts")}
            value={pendingDrafts}
            status={pendingDrafts > 0 ? "warn" : "ok"}
            detail={pendingDrafts > 0 ? t("home.review_drafts_pending").replace("{count}", String(pendingDrafts)) : t("home.review_drafts_clear")}
            href="/drafts"
            onNavigate={onNavigate}
            locale={locale}
          />
          <StatusCard
            label={t("home.manage_sources")}
            value={inboxPending > 0 ? inboxPending : "-"}
            status={inboxPending > 0 ? "warn" : "ok"}
            detail={inboxPending > 0 ? t("home.inbox_pending_detail").replace("{count}", String(inboxPending)) : t("home.inbox_clear")}
            href="/sources"
            onNavigate={onNavigate}
            locale={locale}
          />
          <StatusCard
            label={t("home.browse_library")}
            value={approvedCards}
            status={approvedCards > 0 ? "ok" : "info"}
            detail={approvedCards > 0 ? t("home.library_approved_detail").replace("{count}", String(approvedCards)) : t("home.library_empty_detail")}
            href="/library"
            onNavigate={onNavigate}
            locale={locale}
          />
        </div>
      </section>

      {/* ── 配置检查 ── */}
      <section>
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-muted">{t("home.section_config_check")}</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <StatusCard
            label={t("home.search_knowledge")}
            value={data.recall.index_exists ? t("home.ready") : t("home.needs_setup")}
            status={data.recall.index_exists ? "ok" : "warn"}
            detail={t("home.search_knowledge_detail")}
            nextAction={data.recall.next_action}
            href="/recall"
            onNavigate={onNavigate}
            locale={locale}
          />
          <StatusCard
            label={t("home.check_setup")}
            value={data.provider.model_setup === "ready" ? t("home.ready") : t("home.pending_check")}
            status={data.provider.model_setup === "ready" ? "ok" : "warn"}
            detail={t("home.check_setup_detail")}
            href="/setup"
            onNavigate={onNavigate}
            locale={locale}
          />
        </div>
      </section>

      {/* ── 下一步行动 ── */}
      {data.next_actions.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-sm font-medium uppercase tracking-wide text-muted">{t("home.section_next_actions")}</h2>
          <div className="grid gap-3 md:grid-cols-2">
            {data.next_actions.map((action) => (
              <NextActionCard action={action} key={action.action_key ?? action.label} onNavigate={onNavigate} locale={locale} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
