import type { ConfigStatusResponse } from "../api/types";
import { ConfigChecklist } from "../components/ConfigChecklist";
import { StatusCard } from "../components/StatusCard";

export function SetupPage({ data }: { data: ConfigStatusResponse }) {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">Setup</h1>
        <p className="mt-1 text-sm text-muted">Local configuration status and safe repair guidance. Secret values are never shown.</p>
      </header>
      <div className="grid gap-4 md:grid-cols-3">
        <StatusCard label="Local vault" value={data.vault.exists ? "Ready" : "Missing"} status={data.vault.exists ? "ok" : "warn"} detail={data.vault.path} />
        <StatusCard label="Model provider" value={data.provider.opt_in_state === "env_only" ? "Configured" : "Check setup"} status={data.provider.opt_in_state === "env_only" ? "ok" : "warn"} detail="API key status is shown as present/missing only." />
        <StatusCard label="Config file" value="Loaded" status="ok" detail={data.config_path} />
      </div>
      <ConfigChecklist items={data.checklist} keys={[...data.configured_keys, ...data.missing_keys]} />
    </div>
  );
}
