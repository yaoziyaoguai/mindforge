import { statusTone } from "../lib/utils";
import type { EnvKeyStatus, StatusItem } from "../api/types";

export function ConfigChecklist({ items, keys }: { items: StatusItem[]; keys: EnvKeyStatus[] }) {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-ink">Configuration checklist</h2>
      <div className="divide-y divide-line rounded-md border border-line bg-panel">
        {items.map((item) => (
          <div key={item.key} className="flex items-start justify-between gap-4 p-4">
            <div>
              <div className="font-medium text-ink">{item.label}</div>
              <div className="mt-1 text-sm text-muted">{item.detail ?? item.value}</div>
            </div>
            <span className={`rounded-full border px-2 py-0.5 text-xs ${statusTone(item.status)}`}>{item.value}</span>
          </div>
        ))}
      </div>
      <div className="rounded-md border border-line bg-panel p-4">
        <h3 className="font-medium text-ink">Env keys</h3>
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {keys.map((key) => (
            <div key={key.name} className="flex items-center justify-between rounded border border-line px-3 py-2 text-sm">
              <code>{key.name}</code>
              <span className={key.configured ? "text-safe" : "text-muted"}>
                {key.configured ? `configured (${key.sources.join(", ")})` : "missing"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
