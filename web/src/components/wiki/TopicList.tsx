/**
 * TopicList — left sidebar: list of topic names from GET /api/topics.
 *
 * Shows topic name and selects one for display.
 */

import { useLocale } from "../../lib/i18n";

interface TopicListProps {
  topics: string[];
  selectedTopic: string | null;
  onSelect: (topic: string) => void;
}

export function TopicList({ topics, selectedTopic, onSelect }: TopicListProps) {
  const { locale, t } = useLocale();

  if (topics.length === 0) {
    return (
      <div className="rounded-lg border border-line bg-white/60 p-4 text-center">
        <p className="text-xs text-muted">
          {locale === "zh"
            ? "暂无主题。确认知识卡片后将自动按主题分组展示。"
            : "No topics yet. Approved cards are grouped by topic automatically."}
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-line bg-white/60 divide-y">
      <div className="px-4 py-2.5">
        <h3 className="text-xs font-semibold text-muted uppercase tracking-wide">
          {locale === "zh" ? "主题" : "Topics"} ({topics.length})
        </h3>
      </div>
      {topics.map((topic) => (
        <button
          key={topic}
          type="button"
          onClick={() => onSelect(topic)}
          className={`w-full px-4 py-2.5 text-left text-sm transition-colors ${
            selectedTopic === topic
              ? "bg-[var(--mf-accent)]/5 text-[var(--mf-accent)] font-medium border-l-2 border-[var(--mf-accent)]"
              : "text-ink hover:bg-muted/20"
          }`}
        >
          {topic}
        </button>
      ))}
    </div>
  );
}
