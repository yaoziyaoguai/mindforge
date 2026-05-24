import { CheckCircle, Circle, Clock, Edit3 } from "lucide-react";
import { useLocale } from "../lib/i18n";

interface Props {
  created_at?: string | null;
  approved_at?: string | null;
  updated_at?: string | null;
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
}

export function ApprovalTimeline({ created_at, approved_at, updated_at }: Props) {
  const { t } = useLocale();

  const hasModification = updated_at && created_at && updated_at !== created_at;

  const nodes: TimelineNode[] = [
    { icon: Circle, label: t("timeline.created"), timestamp: created_at ?? null, pending: false },
    { icon: approved_at ? CheckCircle : Clock, label: approved_at ? t("timeline.approved") : t("timeline.pending_approval"), timestamp: approved_at ?? null, pending: !approved_at },
  ];

  if (hasModification) {
    nodes.push({ icon: Edit3, label: t("timeline.modified"), timestamp: updated_at!, pending: false });
  }

  return (
    <div className="mt-4 space-y-0">
      {nodes.map((node, idx) => {
        const isLast = idx === nodes.length - 1;
        return (
          <div key={idx} className="flex gap-3">
            {/* Connector line + dot */}
            <div className="flex flex-col items-center">
              <div className={`flex h-6 w-6 items-center justify-center rounded-full ${node.pending ? "border-2 border-dashed border-muted text-muted" : "bg-primary/10 text-primary"}`}>
                <node.icon className="h-3.5 w-3.5" aria-hidden="true" />
              </div>
              {!isLast ? <div className={`w-0.5 flex-1 ${node.pending ? "border-l-2 border-dashed border-muted" : "bg-primary/20"}`} /> : null}
            </div>
            {/* Content */}
            <div className={`pb-4 ${isLast ? "" : ""}`}>
              <span className={`text-sm font-medium ${node.pending ? "text-muted" : "text-ink"}`}>{node.label}</span>
              {node.timestamp ? (
                <div className="mt-0.5 text-xs text-muted">
                  {relativeTime(node.timestamp, t)} — {absoluteDate(node.timestamp)}
                </div>
              ) : node.pending ? (
                <div className="mt-0.5 text-xs text-muted">{t("timeline.pending_approval")}</div>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );
}
