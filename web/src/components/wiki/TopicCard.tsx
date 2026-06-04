/**
 * TopicCard — single approved card display in topic view.
 *
 * Shows title, knowledge_type, summary, tags, source info, approval metadata.
 * Click to select for context panel.
 */

import { useLocale } from "../../lib/i18n";
import type { TopicCardView } from "../../api/topics";

interface TopicCardProps {
  card: TopicCardView;
  selected: boolean;
  onSelect: (card: TopicCardView) => void;
}

export function TopicCard({ card, selected, onSelect }: TopicCardProps) {
  const { locale, t } = useLocale();

  return (
    <button
      type="button"
      onClick={() => onSelect(card)}
      className={`w-full rounded-lg border p-4 text-left transition-colors ${
        selected
          ? "border-[var(--mf-accent)] bg-[var(--mf-accent)]/5"
          : "border-line bg-white/60 hover:border-[var(--mf-accent)]/30"
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-1">
        <h3 className="text-sm font-semibold text-ink">
          {card.title ?? t("card.untitled")}
        </h3>
        <span className="shrink-0 rounded-full bg-safe/10 px-2 py-0.5 text-[10px] font-medium text-safe">
          {t("wiki.approved_badge")}
        </span>
      </div>

      {card.summary && (
        <p className="text-xs text-muted leading-relaxed mt-1 line-clamp-3">
          {card.summary}
        </p>
      )}

      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        <span className="rounded bg-muted/10 px-1.5 py-0.5 text-[10px] text-muted">
          {card.knowledge_type}
        </span>
        {card.tags.map((tag) => (
          <span
            key={tag}
            className="rounded bg-[var(--mf-accent)]/5 px-1.5 py-0.5 text-[10px] text-[var(--mf-accent)]"
          >
            {tag}
          </span>
        ))}
      </div>

      {(card.source_title || card.source_type) && (
        <div className="mt-2 text-[10px] text-muted/70">
          {locale === "zh" ? "来源" : "Source"}: {card.source_title ?? card.source_type}
        </div>
      )}

      {card.human_note && (
        <div className="mt-1.5 rounded bg-warn/5 px-2 py-1 text-[10px] text-warn">
          {card.human_note}
        </div>
      )}
    </button>
  );
}
