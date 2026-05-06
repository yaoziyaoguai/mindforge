import { AlertTriangle, CheckCircle2, Lock, ShieldCheck } from "lucide-react";
import { truncateMiddle } from "../lib/utils";
import type { SafetySummary } from "../api/types";

export function SafetyBar({ safety }: { safety?: SafetySummary | null }) {
  if (!safety) {
    return <div className="border-b border-line bg-panel px-4 py-3 text-sm text-muted">Loading safety state...</div>;
  }
  const hasWarning = safety.warnings.length > 0;
  return (
    <section className="border-b border-line bg-panel px-4 py-3" aria-label="Safety Bar">
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <span className="inline-flex items-center gap-1 text-safe">
          <ShieldCheck className="h-4 w-4" aria-hidden="true" />
          {safety.local_only ? "Local only" : "Host warning"}
        </span>
        <span className="text-muted">Vault: {truncateMiddle(safety.vault_path, 58)}</span>
        <span className={safety.provider_state === "env_only" ? "text-safe" : "text-warn"}>
          Provider: {safety.provider_state}
        </span>
        <span className="text-muted">.env: {safety.env_status}</span>
        <span className="inline-flex items-center gap-1 text-warn">
          <Lock className="h-4 w-4" aria-hidden="true" />
          {safety.write_mode === "explicit_approval_required" ? "Explicit approval required" : "Read-only"}
        </span>
        <span className="text-muted">Drafts: {safety.pending_drafts_count}</span>
        {hasWarning ? (
          <span className="inline-flex items-center gap-1 text-warn">
            <AlertTriangle className="h-4 w-4" aria-hidden="true" />
            {safety.warnings[0]}
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-safe">
            <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
            Safe local read
          </span>
        )}
      </div>
    </section>
  );
}
