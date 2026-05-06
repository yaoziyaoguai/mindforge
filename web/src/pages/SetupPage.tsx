import type { ConfigStatusResponse } from "../api/types";
import { ConfigChecklist } from "../components/ConfigChecklist";
import { StatusCard } from "../components/StatusCard";

export function SetupPage({ data }: { data: ConfigStatusResponse }) {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">Setup / Config</h1>
        <p className="mt-1 text-sm text-muted">Secret-safe configuration status. Values are never shown.</p>
      </header>
      <div className="grid gap-4 md:grid-cols-3">
        <StatusCard label="Config" value="loaded" status="ok" detail={data.config_path} />
        <StatusCard label="Provider" value={data.provider.opt_in_state} status={data.provider.opt_in_state === "env_only" ? "ok" : "warn"} detail={`active_profile=${data.provider.active_profile}; keys are present/missing only`} />
        <StatusCard label="Vault" value={data.vault.exists ? "exists" : "missing"} status={data.vault.exists ? "ok" : "warn"} detail={data.vault.path} />
      </div>
      <ConfigChecklist items={data.checklist} keys={[...data.configured_keys, ...data.missing_keys]} />
    </div>
  );
}
