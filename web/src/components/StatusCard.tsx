import { statusTone } from "../lib/utils";
import type { NextAction, StatusLevel } from "../api/types";

interface Props {
  label: string;
  value: string | number;
  status?: StatusLevel;
  detail?: string | null;
  nextAction?: NextAction | null;
}

export function StatusCard({ label, value, status = "info", detail, nextAction }: Props) {
  return (
    <section className="rounded-md border border-line bg-panel p-4 shadow-subtle">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-medium text-muted">{label}</h3>
        <span className={`rounded-full border px-2 py-0.5 text-xs ${statusTone(status)}`}>{status}</span>
      </div>
      <div className="mt-2 text-2xl font-semibold text-ink">{value}</div>
      {detail ? <p className="mt-2 text-sm text-muted">{detail}</p> : null}
      {nextAction ? (
        <p className="mt-3 text-sm text-primary">
          {nextAction.command ?? nextAction.description}
        </p>
      ) : null}
    </section>
  );
}
