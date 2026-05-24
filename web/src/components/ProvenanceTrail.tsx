import { ArrowRight, BookOpen, FileText, FolderOpen, GitBranch, Hash } from "lucide-react";
import type { ProvenanceTrailResponse } from "../api/types";
import { useLocale } from "../lib/i18n";

interface Props {
  trail: ProvenanceTrailResponse;
  onSelectCard?: (ref: string) => void;
}

function TrailStep({ icon: Icon, label, children, muted }: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  children: React.ReactNode;
  muted?: boolean;
}) {
  return (
    <div className="flex gap-3">
      {/* Timeline connector */}
      <div className="flex flex-col items-center">
        <span className={`flex items-center justify-center w-7 h-7 rounded-full border-2 ${muted ? "border-line bg-white text-muted" : "border-primary/30 bg-primary/5 text-primary"}`}>
          <Icon className="h-3.5 w-3.5" />
        </span>
        <div className="w-px flex-1 min-h-[12px] bg-line/50 my-0.5" />
      </div>
      {/* Content */}
      <div className="flex-1 pb-3">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted mb-1.5">{label}</p>
        <div className="space-y-1">
          {children}
        </div>
      </div>
    </div>
  );
}

export function ProvenanceTrail({ trail, onSelectCard }: Props) {
  const { t } = useLocale();

  const hasSource = !!trail.source.source_title;
  const hasSiblings = trail.sibling_cards.length > 0;
  const hasSections = trail.wiki_sections.length > 0;
  const hasRelatedSources = trail.related_sources && trail.related_sources.length > 0;

  if (!hasSource && !hasSiblings && !hasSections && !hasRelatedSources) {
    return null;
  }

  return (
    <section className="border border-line rounded-lg bg-panel overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-line bg-stone-50/50">
        <div className="flex items-center gap-2.5">
          <span className="flex items-center justify-center w-8 h-8 rounded-md bg-primary/10 text-primary">
            <GitBranch className="h-4 w-4" />
          </span>
          <div>
            <h3 className="text-sm font-semibold text-ink">{t("card.provenance_trail")}</h3>
            <p className="text-xs text-muted mt-0.5">{t("card.provenance_trail_desc") ?? "Trace knowledge from source through organization to related discoveries"}</p>
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div className="px-6 py-4">
        {/* Step 1: Source Document */}
        {hasSource ? (
          <TrailStep icon={FileText} label={t("card.provenance_source")}>
            <span className="inline-flex items-center gap-1.5 rounded-md bg-white border border-line px-3 py-1.5 text-sm">
              <FolderOpen className="h-3.5 w-3.5 text-muted" />
              <span className="font-medium text-ink">{trail.source.source_title}</span>
            </span>
          </TrailStep>
        ) : null}

        {/* Step 2: Sibling Cards */}
        {hasSiblings ? (
          <TrailStep icon={BookOpen} label={t("card.provenance_siblings")}>
            <div className="flex flex-wrap gap-1.5">
              {trail.sibling_cards.map((sc) => (
                <button
                  key={sc.card_id}
                  type="button"
                  className="inline-flex items-center gap-1 rounded-md bg-white border border-line px-2.5 py-1 text-sm text-primary hover:bg-primary/5 transition"
                  onClick={() => onSelectCard?.(sc.card_id)}
                >
                  {sc.title}
                  <ArrowRight className="h-3 w-3" />
                </button>
              ))}
            </div>
          </TrailStep>
        ) : null}

        {/* Step 3: Wiki Sections */}
        {hasSections ? (
          <TrailStep icon={Hash} label={t("card.provenance_sections")}>
            <div className="flex flex-wrap gap-1.5">
              {trail.wiki_sections.map((sec) => (
                <span
                  key={sec.title}
                  className="inline-flex items-center gap-1 rounded-md bg-white border border-line px-2.5 py-1 text-sm"
                >
                  <span className="font-medium text-ink">{sec.title}</span>
                  <span className="text-xs text-muted">({sec.card_count})</span>
                </span>
              ))}
            </div>
          </TrailStep>
        ) : null}

        {/* Step 4: Related Sources */}
        {hasRelatedSources ? (
          <TrailStep icon={FolderOpen} label={t("card.provenance_related_sources")} muted={!hasSiblings && !hasSections}>
            <div className="flex flex-col gap-1.5">
              {trail.related_sources!.map((rs) => (
                <span key={rs.source_id} className="inline-flex flex-wrap items-center gap-x-2 gap-y-0.5 rounded-md bg-white border border-line px-3 py-1.5 text-sm">
                  <span className="font-medium text-ink">{rs.source_title || rs.source_id}</span>
                  <span className="text-xs text-muted">
                    {rs.card_count} {t("card.provenance_cards")}
                  </span>
                  {rs.shared_tags.length > 0 ? (
                    <span className="text-xs text-muted">
                      {rs.shared_tags.map((tag) => `#${tag}`).join(" ")}
                    </span>
                  ) : null}
                  {rs.shared_wiki_sections.length > 0 ? (
                    <span className="text-xs text-muted">
                      {rs.shared_wiki_sections.join(", ")}
                    </span>
                  ) : null}
                </span>
              ))}
            </div>
          </TrailStep>
        ) : null}
      </div>
    </section>
  );
}
