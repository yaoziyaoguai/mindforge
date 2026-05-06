import type { HomeStatusResponse, WorkflowSummaryResponse } from "../api/types";
import { NextActionCard } from "../components/NextActionCard";
import { StatusCard } from "../components/StatusCard";

export function HomePage({ data, workflow, onNavigate }: { data: HomeStatusResponse; workflow?: WorkflowSummaryResponse; onNavigate: (href: string) => void }) {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">Home</h1>
        <p className="mt-1 text-sm text-muted">Local workspace status and next actions.</p>
      </header>
      <div className="grid gap-4 md:grid-cols-3">
        <StatusCard label="Workspace items" value={data.workspace.state_item_count} status={data.workspace.state_exists ? "ok" : "warn"} detail={data.workspace.state_path} />
        <StatusCard label="Pending sources" value={workflow?.inbox_pending_count ?? "-"} status={(workflow?.inbox_pending_count ?? 0) > 0 ? "warn" : "ok"} detail="Default 00-Inbox and watched sources are the user ingestion entry." />
        <StatusCard label="Pending drafts" value={data.safety.pending_drafts_count} status={data.safety.pending_drafts_count > 0 ? "warn" : "ok"} detail="ai_draft waiting for review" />
        <StatusCard label="Approved cards" value={data.vault.approved_card_count} status={data.vault.approved_card_count > 0 ? "ok" : "info"} detail="human_approved available to recall" />
      </div>
      <section className="grid gap-4 md:grid-cols-2">
        <StatusCard label="Provider" value={data.provider.opt_in_state} status={data.provider.opt_in_state === "fake_default" ? "ok" : "warn"} detail={`active_profile=${data.provider.active_profile}`} />
        <StatusCard label="Recall index" value={data.recall.index_exists ? "present" : "missing"} status={data.recall.index_exists ? "ok" : "warn"} detail={data.recall.index_path} nextAction={data.recall.next_action} />
      </section>
      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-ink">Next actions</h2>
        <div className="grid gap-3 md:grid-cols-2">
          {data.next_actions.map((action) => (
            <NextActionCard action={action} key={action.label} onNavigate={onNavigate} />
          ))}
        </div>
      </section>
    </div>
  );
}
