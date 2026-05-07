import { statusTone } from "../lib/utils";
import type { EnvKeyStatus, StatusItem } from "../api/types";

export function ConfigChecklist({ items, keys }: { items: StatusItem[]; keys: EnvKeyStatus[] }) {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-ink">Configuration checklist</h2>
      <div className="divide-y divide-line rounded-md border border-line bg-panel">
        {items.map((item) => (
          <details key={item.key} className="group p-4">
            <summary className="flex cursor-pointer list-none items-start justify-between gap-4">
              <span>
                <span className="font-medium text-ink">{item.label}</span>
                <span className="mt-1 block text-sm text-muted">{item.detail ?? item.value}</span>
              </span>
              <span className={`rounded-full border px-2 py-0.5 text-xs ${statusTone(item.status)}`}>{item.value}</span>
            </summary>
            <div className="mt-3 rounded-md bg-stone-50 p-3 text-sm text-muted">
              <p>{explainItem(item)}</p>
              {item.next_action ? (
                <p className="mt-2 text-primary">{item.next_action.command ?? item.next_action.description}</p>
              ) : null}
            </div>
          </details>
        ))}
      </div>
      <details className="rounded-md border border-line bg-panel p-4">
        <summary className="cursor-pointer font-medium text-ink">Environment variable presence</summary>
        <p className="mt-2 text-sm text-muted">Process environment diagnostics for configured env names. Config defaults may still provide effective non-secret values.</p>
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {keys.map((key) => (
            <div key={key.name} className="flex items-center justify-between rounded border border-line px-3 py-2 text-sm">
              <code>{key.name}</code>
              <span className={key.configured ? "text-safe" : "text-muted"}>
                {key.configured ? `present (${key.sources.join(", ")})` : "missing"}
              </span>
            </div>
          ))}
        </div>
      </details>
    </section>
  );
}

function explainItem(item: StatusItem): string {
  if (item.key === "provider") return "Model provider readiness is shown without exposing API key values. Keys are present, missing, or hidden.";
  if (item.key === "env") return "Process environment diagnostics are separate from config defaults and effective provider values.";
  if (item.key === "vault") return "Vault writes require explicit local actions such as saving a card body or approving a draft.";
  if (item.key === "config") return "MindForge loaded this config file for local use. Web does not edit provider secrets.";
  return item.detail ?? item.value;
}
