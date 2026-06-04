/**
 * TopicView — center panel: approved cards for the selected topic.
 *
 * Shows type_counts summary and card list.
 */

import { useLocale } from "../../lib/i18n";
import type { TopicCardView, TopicViewResponse } from "../../api/topics";
import { TopicCard } from "./TopicCard";

interface TopicViewProps {
  data: TopicViewResponse;
  selectedCard: TopicCardView | null;
  onSelectCard: (card: TopicCardView) => void;
}

export function TopicView({ data, selectedCard, onSelectCard }: TopicViewProps) {
  const { locale, t } = useLocale();

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h2 className="text-lg font-bold text-ink">{data.topic}</h2>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted">
          <span>
            {data.total_approved_cards}{" "}
            {locale === "zh" ? "张已确认卡片" : "approved cards"}
          </span>
          {Object.entries(data.type_counts).map(([type, count]) => (
            <span
              key={type}
              className="rounded bg-muted/10 px-1.5 py-0.5 text-[10px]"
            >
              {type}: {count}
            </span>
          ))}
        </div>
        {/* Approval boundary notice */}
        <p className="mt-2 text-[10px] text-muted/60">
          {locale === "zh"
            ? "以下仅展示人工确认的知识卡片（human_approved）。AI 草稿不在此列。"
            : "Showing only human-approved knowledge cards. AI drafts are excluded."}
        </p>
      </div>

      {/* Card list */}
      {data.cards.length === 0 ? (
        <div className="rounded-lg border border-line bg-white/60 p-6 text-center">
          <p className="text-sm text-muted">
            {locale === "zh"
              ? "此主题下暂无已确认卡片"
              : "No approved cards in this topic"}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {data.cards.map((card) => (
            <TopicCard
              key={card.id ?? card.title}
              card={card}
              selected={selectedCard?.id === card.id}
              onSelect={onSelectCard}
            />
          ))}
        </div>
      )}
    </div>
  );
}
