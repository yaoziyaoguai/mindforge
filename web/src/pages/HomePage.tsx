import type { HomeStatusResponse, WorkflowSummaryResponse } from "../api/types";
import { NextActionCard } from "../components/NextActionCard";
import { StatusCard } from "../components/StatusCard";

export function HomePage({ data, workflow, onNavigate }: { data: HomeStatusResponse; workflow?: WorkflowSummaryResponse; onNavigate: (href: string) => void }) {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">Home</h1>
        <p className="mt-1 text-sm text-muted">Choose the next step for your local knowledge workspace.</p>
      </header>
      <div className="grid gap-4 md:grid-cols-3">
        <StatusCard label="Review drafts" value={data.safety.pending_drafts_count} status={data.safety.pending_drafts_count > 0 ? "warn" : "ok"} detail="Draft knowledge waiting for your review." href="/drafts" onNavigate={onNavigate} />
        <StatusCard label="Add or review sources" value={workflow?.inbox_pending_count ?? "-"} status={(workflow?.inbox_pending_count ?? 0) > 0 ? "warn" : "ok"} detail="Bring in original material and see what has been processed." href="/sources" onNavigate={onNavigate} />
        <StatusCard label="Browse knowledge library" value={data.vault.approved_card_count} status={data.vault.approved_card_count > 0 ? "ok" : "info"} detail="Approved knowledge ready to read, edit, and search." href="/library" onNavigate={onNavigate} />
      </div>
      <section className="grid gap-4 md:grid-cols-2">
        <StatusCard label="Search approved knowledge" value={data.recall.index_exists ? "Ready" : "Needs index"} status={data.recall.index_exists ? "ok" : "warn"} detail="Search only looks at approved knowledge." nextAction={data.recall.next_action} href="/recall" onNavigate={onNavigate} />
        <StatusCard label="Check setup" value={data.provider.model_setup === "ready" ? "Ready" : "Review"} status={data.provider.model_setup === "ready" ? "ok" : "warn"} detail="Review local vault and model setup." href="/setup" onNavigate={onNavigate} />
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
