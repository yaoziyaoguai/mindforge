import { statusIcon, statusLabel, statusTone } from "../lib/utils";
import type { NextAction, StatusLevel } from "../api/types";

interface Props {
  label: string;
  value: string | number;
  status?: StatusLevel;
  detail?: string | null;
  nextAction?: NextAction | null;
  href?: string;
  onNavigate?: (href: string) => void;
}

export function StatusCard({ label, value, status = "info", detail, nextAction, href, onNavigate }: Props) {
  const content = (
    <section className="rounded-md border border-line bg-panel p-4 shadow-subtle">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-medium text-muted">{label}</h3>
        <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs ${statusTone(status)}`}>
          {(() => { const Icon = statusIcon(status); return Icon ? <Icon className="h-3 w-3" aria-hidden="true" /> : null; })()}
          {statusLabel(status) || status}
        </span>
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
  if (!href) return content;
  return (
    <button className="block w-full text-left" onClick={() => onNavigate?.(href)} type="button">
      {content}
    </button>
  );
}
