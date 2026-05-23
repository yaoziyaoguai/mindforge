import type { HomeStatusResponse, WorkflowSummaryResponse } from "../api/types";
import { NextActionCard } from "../components/NextActionCard";
import { StatusCard } from "../components/StatusCard";
import { useLocale } from "../lib/i18n";

export function HomePage({ data, workflow, onNavigate }: { data: HomeStatusResponse; workflow?: WorkflowSummaryResponse; onNavigate: (href: string) => void }) {
  const { locale, t } = useLocale();
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">{t("home.title")}</h1>
        <p className="mt-1 text-sm text-muted">{t("home.subtitle")}</p>
      </header>
      <div className="grid gap-4 md:grid-cols-3">
        <StatusCard label={t("home.review_drafts")} value={data.safety.pending_drafts_count} status={data.safety.pending_drafts_count > 0 ? "warn" : "ok"} detail={t("home.review_drafts_detail")} href="/drafts" onNavigate={onNavigate} locale={locale} />
        <StatusCard label={t("home.manage_sources")} value={workflow?.inbox_pending_count ?? "-"} status={(workflow?.inbox_pending_count ?? 0) > 0 ? "warn" : "ok"} detail={t("home.manage_sources_detail")} href="/sources" onNavigate={onNavigate} locale={locale} />
        <StatusCard label={t("home.browse_library")} value={data.vault.approved_card_count} status={data.vault.approved_card_count > 0 ? "ok" : "info"} detail={t("home.browse_library_detail")} href="/library" onNavigate={onNavigate} locale={locale} />
      </div>
      <section className="grid gap-4 md:grid-cols-2">
        <StatusCard label={t("home.search_knowledge")} value={data.recall.index_exists ? t("home.ready") : t("home.needs_setup")} status={data.recall.index_exists ? "ok" : "warn"} detail={t("home.search_knowledge_detail")} nextAction={data.recall.next_action} href="/recall" onNavigate={onNavigate} locale={locale} />
        <StatusCard label={t("home.check_setup")} value={data.provider.model_setup === "ready" ? t("home.ready") : t("home.pending_check")} status={data.provider.model_setup === "ready" ? "ok" : "warn"} detail={t("home.check_setup_detail")} href="/setup" onNavigate={onNavigate} locale={locale} />
      </section>
      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-ink">{t("home.next_actions")}</h2>
        <div className="grid gap-3 md:grid-cols-2">
          {data.next_actions.map((action) => (
            <NextActionCard action={action} key={action.label} onNavigate={onNavigate} />
          ))}
        </div>
      </section>
    </div>
  );
}
