import { CheckCircle, Circle, Clock, Edit3, GitCommit } from "lucide-react";
import { useLocale } from "../lib/i18n";

interface Props {
  created_at?: string | null;
  approved_at?: string | null;
  updated_at?: string | null;
}

function parseMs(iso: string): number {
  const t = new Date(iso).getTime();
  return Number.isNaN(t) ? 0 : t;
}

function durationBetween(fromIso: string, toIso: string, t: (key: string) => string): string {
  const from = parseMs(fromIso);
  const to = parseMs(toIso);
  if (!from || !to || to <= from) return "";
  const diff = to - from;
  const days = Math.floor(diff / 86_400_000);
  const hours = Math.floor((diff % 86_400_000) / 3_600_000);
  if (days > 0 && hours > 0) return t("timeline.duration_days_hours").replace("{d}", String(days)).replace("{h}", String(hours));
  if (days > 0) return t("timeline.duration_days").replace("{d}", String(days));
  if (hours > 0) return t("timeline.duration_hours").replace("{h}", String(hours));
  const mins = Math.floor((diff % 3_600_000) / 60_000);
  return t("timeline.duration_minutes").replace("{m}", String(mins));
}

function relativeTime(iso: string, t: (key: string) => string): string {
  const now = Date.now();
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const diff = now - then;
  if (diff < 60_000) return t("timeline.relative_just_now");
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 60) return t("timeline.relative_minutes").replace("{n}", String(minutes));
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return t("timeline.relative_hours").replace("{n}", String(hours));
  const days = Math.floor(hours / 24);
  if (days < 30) return t("timeline.relative_days").replace("{n}", String(days));
  return new Date(iso).toLocaleDateString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit" });
}

function absoluteDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

interface TimelineNode {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  timestamp: string | null;
  pending: boolean;
  active: boolean;
}

export function ApprovalTimeline({ created_at, approved_at, updated_at }: Props) {
  const { t } = useLocale();

  const hasModification = updated_at && created_at && updated_at !== created_at;
  const isApproved = !!approved_at;

  // Calculate durations
  const approvalDuration = created_at && approved_at
    ? durationBetween(created_at, approved_at, t)
    : "";
  const modificationDuration = approved_at && updated_at && updated_at !== approved_at
    ? durationBetween(approved_at, updated_at, t)
    : "";

  const nodes: TimelineNode[] = [
    { icon: Circle, label: t("timeline.created"), timestamp: created_at ?? null, pending: false, active: true },
    { icon: approved_at ? CheckCircle : Clock, label: approved_at ? t("timeline.approved") : t("timeline.pending_approval"), timestamp: approved_at ?? null, pending: !approved_at, active: !!approved_at },
  ];

  if (hasModification && approved_at) {
    nodes.push({ icon: Edit3, label: t("timeline.modified"), timestamp: updated_at!, pending: false, active: true });
  }

  return (
    <div className="mt-4 border border-line rounded-lg bg-panel overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 border-b border-line bg-stone-50/50 flex items-center gap-2.5">
        <span className="flex items-center justify-center w-7 h-7 rounded-md text-[var(--mf-accent)]" style={{ background: "var(--mf-accent)15" }}>
          <GitCommit className="h-3.5 w-3.5" />
        </span>
        <div>
          <h4 className="text-xs font-semibold text-ink">{t("timeline.title")}</h4>
          <p className="text-[11px] text-muted mt-0.5">
            {isApproved ? t("timeline.approved_status") : t("timeline.pending_status")}
          </p>
        </div>
        {/* Status badge */}
        <span className={`ml-auto inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-medium ${
          isApproved ? "bg-safe/10 text-safe" : "bg-warn/10 text-warn"
        }`}>
          <span className={`w-1.5 h-1.5 rounded-full ${isApproved ? "bg-safe" : "bg-warn"}`} />
          {isApproved ? t("timeline.approved") : t("timeline.pending_approval")}
        </span>
      </div>

      {/* Timeline */}
      <div className="px-5 py-4 space-y-0">
        {nodes.map((node, idx) => {
          const isLast = idx === nodes.length - 1;
          return (
            <div key={idx} className="flex gap-3">
              {/* Connector line + dot */}
              <div className="flex flex-col items-center">
                <div className={`flex h-6 w-6 items-center justify-center rounded-full ${
                  node.pending
                    ? "border-2 border-dashed border-muted text-muted"
                    : node.active
                    ? "text-[var(--mf-accent)]"
                    : "bg-muted/10 text-muted"
                }`} style={node.active && !node.pending ? { background: "var(--mf-accent)15" } : undefined}>
                  <node.icon className="h-3.5 w-3.5" aria-hidden="true" />
                </div>
                {!isLast ? (
                  <div className={`w-0.5 flex-1 min-h-[20px] ${node.pending ? "border-l-2 border-dashed border-muted/50" : ""}`} style={!node.pending ? { background: "var(--mf-accent)30" } : undefined} />
                ) : null}
              </div>
              {/* Content */}
              <div className={`pb-3 ${isLast ? "" : ""}`}>
                <span className={`text-sm font-medium ${node.pending ? "text-muted" : "text-ink"}`}>
                  {node.label}
                </span>
                {node.timestamp ? (
                  <div className="mt-0.5 text-xs text-muted">
                    {relativeTime(node.timestamp, t)} — {absoluteDate(node.timestamp)}
                  </div>
                ) : node.pending ? (
                  <div className="mt-0.5 text-xs text-muted">{t("timeline.pending_approval")}</div>
                ) : null}

                {/* Duration between stages */}
                {idx === 1 && approvalDuration ? (
                  <div className="mt-1 text-[10px] text-muted/70">
                    {t("timeline.took")}: {approvalDuration}
                  </div>
                ) : null}
                {idx === 2 && modificationDuration ? (
                  <div className="mt-1 text-[10px] text-muted/70">
                    {t("timeline.took")}: {modificationDuration}
                  </div>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
