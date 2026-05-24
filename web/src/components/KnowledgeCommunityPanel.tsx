import { useEffect, useState } from "react";
import { BookOpen, ChevronDown, ChevronUp, FolderOpen, Hash, Layers, Loader2, Users } from "lucide-react";
import { getKnowledgeCommunities } from "../api/library";
import type { KnowledgeCommunitiesResponse, KnowledgeCommunityResponse } from "../api/types";
import { useLocale } from "../lib/i18n";

interface Props {
  onSelectCommunity?: (communityType: string, sharedEntity: string) => void;
}

const TYPE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  source: FolderOpen,
  tag: Hash,
  wiki_section: BookOpen,
};

const TYPE_I18N_KEY: Record<string, string> = {
  source: "community.type_source",
  tag: "community.type_tag",
  wiki_section: "community.type_wiki_section",
};

/** 质量评分 → 颜色指示器。 */
function qualityColor(score: number): string {
  if (score >= 0.7) return "bg-emerald-500";
  if (score >= 0.4) return "bg-amber-500";
  return "bg-slate-300";
}

export function KnowledgeCommunityPanel({ onSelectCommunity }: Props) {
  const [data, setData] = useState<KnowledgeCommunitiesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedItems, setExpandedItems] = useState<Record<string, boolean>>({});
  const [showAll, setShowAll] = useState<Record<string, boolean>>({});
  const { t } = useLocale();

  useEffect(() => {
    let cancelled = false;
    getKnowledgeCommunities()
      .then((d) => { if (!cancelled) { setData(d); setLoading(false); } })
      .catch(() => { if (!cancelled) { setError(t("community.load_error")); setLoading(false); } });
    return () => { cancelled = true; };
  }, [t]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 px-5 py-4 text-xs text-muted">
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
        {t("community.loading")}
      </div>
    );
  }

  if (error || !data || data.communities.length === 0) {
    return (
      <div className="px-5 py-4 text-xs text-muted">
        {error || t("community.empty")}
      </div>
    );
  }

  const grouped: Record<string, typeof data.communities> = {};
  for (const c of data.communities) {
    (grouped[c.community_type] ??= []).push(c);
  }

  const typeOrder = ["source", "tag", "wiki_section"];

  const toggleExpanded = (key: string) => {
    setExpandedItems((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const toggleShowAll = (ctype: string) => {
    setShowAll((prev) => ({ ...prev, [ctype]: !prev[ctype] }));
  };

  return (
    <div className="divide-y divide-line">
      {typeOrder.map((ctype) => {
        const items = grouped[ctype];
        if (!items || items.length === 0) return null;
        const Icon = TYPE_ICONS[ctype] ?? Users;
        const isShowAll = showAll[ctype] ?? false;
        const visibleItems = isShowAll ? items : items.slice(0, 5);
        return (
          <div key={ctype} className="px-4 py-3">
            {/* Type header */}
            <div className="flex items-center gap-1.5 mb-2">
              <Icon className="w-3.5 h-3.5 text-muted" />
              <span className="text-xs font-semibold text-muted">
                {t(TYPE_I18N_KEY[ctype] ?? `community.type_${ctype}`)}
              </span>
              <span className="text-[10px] text-muted/60">({items.length})</span>
            </div>

            <div className="flex flex-col gap-1">
              {visibleItems.map((c) => {
                const itemKey = `${c.community_type}:${c.shared_entity}`;
                const isExpanded = expandedItems[itemKey] ?? false;
                const hasSub = c.sub_communities && c.sub_communities.length > 0;
                const hasOverlap = c.overlap_with && c.overlap_with.length > 0;
                const hasExtra = hasSub || hasOverlap;

                return (
                  <div key={itemKey}>
                    {/* Main community row */}
                    <div className="flex items-center group">
                      {/* Expand toggle for sub-communities */}
                      {hasExtra ? (
                        <button
                          type="button"
                          className="shrink-0 p-0.5 text-muted/50 hover:text-muted"
                          onClick={(e) => { e.stopPropagation(); toggleExpanded(itemKey); }}
                          aria-label={isExpanded ? t("community.collapse_all") : t("community.expand_all")}
                        >
                          {isExpanded ? (
                            <ChevronDown className="w-3 h-3" />
                          ) : (
                            <ChevronUp className="w-3 h-3 rotate-270" />
                          )}
                        </button>
                      ) : (
                        <span className="w-4 shrink-0" />
                      )}

                      <button
                        key={itemKey}
                        type="button"
                        className="text-left text-xs px-2 py-1 rounded hover:bg-muted/10 flex items-center justify-between flex-1 min-w-0"
                        onClick={() => onSelectCommunity?.(c.community_type, c.shared_entity)}
                      >
                        <span className="text-ink/80 truncate flex-1 min-w-0" title={c.shared_entity}>
                          {c.shared_entity}
                        </span>
                        <span className="flex items-center gap-1.5 shrink-0 ml-2">
                          {/* Quality score indicator */}
                          <span
                            className={`inline-block w-1.5 h-1.5 rounded-full ${qualityColor(c.quality_score)}`}
                            title={`${t("community.quality_score")}: ${(c.quality_score * 100).toFixed(0)}%`}
                          />
                          <span className="text-[10px] text-muted">
                            {c.member_count} {t("community.cards_count")}
                          </span>
                        </span>
                      </button>
                    </div>

                    {/* Expanded sub-communities & overlaps */}
                    {isExpanded && hasExtra ? (
                      <div className="ml-5 mt-0.5 mb-1 pl-3 border-l-2 border-line/50 space-y-1">
                        {/* Sub-communities */}
                        {hasSub ? (
                          <div>
                            <span className="text-[10px] text-muted/70 font-medium">
                              {t("community.sub_communities")}
                            </span>
                            <div className="flex flex-col gap-0.5 mt-0.5">
                              {c.sub_communities.map((sub) => (
                                <button
                                  key={`sub-${sub.community_type}:${sub.shared_entity}`}
                                  type="button"
                                  className="text-left text-[11px] px-1.5 py-0.5 rounded hover:bg-muted/10 text-muted flex items-center justify-between"
                                  onClick={() => onSelectCommunity?.(sub.community_type, sub.shared_entity)}
                                >
                                  <span className="truncate flex-1 min-w-0">{sub.shared_entity}</span>
                                  <span className="text-[10px] text-muted/60 shrink-0 ml-2">
                                    {sub.member_count}
                                  </span>
                                </button>
                              ))}
                            </div>
                          </div>
                        ) : null}

                        {/* Overlap with */}
                        {hasOverlap ? (
                          <div>
                            <span className="text-[10px] text-muted/70 font-medium">
                              {t("community.overlap_with")}
                            </span>
                            <div className="flex flex-col gap-0.5 mt-0.5">
                              {c.overlap_with.map((ov) => (
                                <button
                                  key={`overlap-${ov.community_type}:${ov.shared_entity}`}
                                  type="button"
                                  className="text-left text-[11px] px-1.5 py-0.5 rounded hover:bg-muted/10 text-muted flex items-center justify-between"
                                  onClick={() => onSelectCommunity?.(ov.community_type, ov.shared_entity)}
                                >
                                  <span className="truncate flex-1 min-w-0">{ov.shared_entity}</span>
                                  <span className="text-[10px] text-muted/60 shrink-0 ml-2">
                                    {ov.shared_member_count} {t("community.shared_members")}
                                  </span>
                                </button>
                              ))}
                            </div>
                          </div>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                );
              })}

              {/* Show more / collapse toggle */}
              {items.length > 5 ? (
                <button
                  type="button"
                  className="text-[10px] text-muted/60 px-2 py-0.5 text-left hover:text-muted transition"
                  onClick={() => toggleShowAll(ctype)}
                >
                  {isShowAll
                    ? t("community.collapse_all")
                    : `+${items.length - 5} ${t("community.more")}`}
                </button>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );
}
