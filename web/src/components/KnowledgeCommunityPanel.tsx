import { useEffect, useState } from "react";
import { BookOpen, FolderOpen, Hash, Loader2, Users } from "lucide-react";
import { getKnowledgeCommunities } from "../api/library";
import type { KnowledgeCommunitiesResponse } from "../api/types";
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

export function KnowledgeCommunityPanel({ onSelectCommunity }: Props) {
  const [data, setData] = useState<KnowledgeCommunitiesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
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

  // Group by community type
  const grouped: Record<string, typeof data.communities> = {};
  for (const c of data.communities) {
    (grouped[c.community_type] ??= []).push(c);
  }

  const typeOrder = ["source", "tag", "wiki_section"];

  return (
    <div className="divide-y divide-line">
      {typeOrder.map((ctype) => {
        const items = grouped[ctype];
        if (!items || items.length === 0) return null;
        const Icon = TYPE_ICONS[ctype] ?? Users;
        return (
          <div key={ctype} className="px-4 py-3">
            <div className="flex items-center gap-1.5 mb-2">
              <Icon className="w-3.5 h-3.5 text-muted" />
              <span className="text-xs font-semibold text-muted">
                {t(TYPE_I18N_KEY[ctype] ?? `community.type_${ctype}`)}
              </span>
              <span className="text-[10px] text-muted/60">({items.length})</span>
            </div>
            <div className="flex flex-col gap-1">
              {items.slice(0, 5).map((c) => (
                <button
                  key={`${c.community_type}:${c.shared_entity}`}
                  type="button"
                  className="text-left text-xs px-2 py-1 rounded hover:bg-muted/10 flex items-center justify-between group"
                  onClick={() => onSelectCommunity?.(c.community_type, c.shared_entity)}
                >
                  <span className="text-ink/80 truncate flex-1" title={c.shared_entity}>
                    {c.shared_entity}
                  </span>
                  <span className="text-[10px] text-muted shrink-0 ml-2">
                    {c.member_count} {t("community.cards_count")}
                  </span>
                </button>
              ))}
              {items.length > 5 ? (
                <span className="text-[10px] text-muted/60 px-2">
                  +{items.length - 5} {t("community.more")}
                </span>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );
}
