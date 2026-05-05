import type { SourcesResponse } from "../api/types";
import { SourceList } from "../components/SourceList";
import { StatusCard } from "../components/StatusCard";

export function SourcesPage({ data }: { data: SourcesResponse }) {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">Sources</h1>
        <p className="mt-1 text-sm text-muted">Read-only source adapter and inbox status.</p>
      </header>
      <SourceList sources={data.sources} />
      <section className="grid gap-4 md:grid-cols-2">
        {data.available_imports.map((item) => (
          <StatusCard key={item.key} label={item.label} value={item.value} status={item.status} detail={item.detail} nextAction={item.next_action} />
        ))}
      </section>
    </div>
  );
}
