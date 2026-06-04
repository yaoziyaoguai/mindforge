/**
 * TopicBrowser — top-level orchestration for the Topic View page.
 *
 * Loads topic list from GET /api/topics, loads topic detail from
 * GET /api/topics/{name} on selection. Manages selected card for
 * the context panel.
 */

import { useCallback, useEffect, useState } from "react";
import { listTopics, getTopic } from "../../api/topics";
import type { TopicCardView, TopicViewResponse } from "../../api/topics";
import { useLocale } from "../../lib/i18n";
import { TopicList } from "./TopicList";
import { TopicView } from "./TopicView";
import { TopicContextPanel } from "./TopicContextPanel";

export function TopicBrowser() {
  const { locale, t } = useLocale();

  const [topics, setTopics] = useState<string[] | null>(null);
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [topicData, setTopicData] = useState<TopicViewResponse | null>(null);
  const [selectedCard, setSelectedCard] = useState<TopicCardView | null>(null);
  const [loading, setLoading] = useState(true);
  const [topicLoading, setTopicLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load topic list
  const loadTopics = useCallback(async () => {
    setError(null);
    try {
      const data = await listTopics();
      setTopics(data.topics);
    } catch {
      setError(
        locale === "zh"
          ? "加载主题列表失败"
          : "Failed to load topics",
      );
    } finally {
      setLoading(false);
    }
  }, [locale]);

  useEffect(() => {
    void loadTopics();
  }, [loadTopics]);

  // Load topic detail when selection changes
  const handleSelectTopic = useCallback(
    async (name: string) => {
      setSelectedTopic(name);
      setTopicData(null);
      setSelectedCard(null);
      setTopicLoading(true);
      setError(null);
      try {
        const data = await getTopic(name);
        setTopicData(data);
      } catch {
        setError(
          locale === "zh"
            ? `加载主题 "${name}" 失败`
            : `Failed to load topic "${name}"`,
        );
      } finally {
        setTopicLoading(false);
      }
    },
    [locale],
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16 text-sm text-muted">
        {locale === "zh" ? "正在加载..." : "Loading..."}
      </div>
    );
  }

  if (error && !topics) {
    return (
      <div className="rounded-lg border border-[var(--mf-warn)]/30 bg-[var(--mf-warn)]/5 p-8 text-center">
        <p className="text-sm text-[var(--mf-warn)]">{error}</p>
        <button
          type="button"
          onClick={() => {
            setLoading(true);
            void loadTopics();
          }}
          className="mt-3 text-sm font-medium text-[var(--mf-accent)] hover:underline"
        >
          {t("wiki.retry")}
        </button>
      </div>
    );
  }

  const topicList = topics ?? [];

  return (
    <div className="space-y-6">
      {/* Page header */}
      <header className="page-header">
        <h1>{locale === "zh" ? "知识主题" : "Knowledge Topics"}</h1>
        <p className="mt-1 text-sm text-muted">
          {locale === "zh"
            ? "按主题浏览已确认的知识卡片。仅展示人工确认的内容，AI 草稿不在此列。"
            : "Browse approved knowledge cards by topic. Only human-approved content is shown."}
        </p>
      </header>

      {/* Deprecation notice */}
      <section className="rounded-md border border-stone-200/70 bg-stone-50/50 px-4 py-3">
        <p className="text-xs text-muted leading-relaxed">
          {locale === "zh"
            ? "LLM Wiki synthesis（Generate Wiki）已在 v0.5 废弃。当前页面为运行时 Topic View，直接从已审批卡片构建，不调用 LLM，不生成合成文本。"
            : "LLM Wiki synthesis (Generate Wiki) is deprecated in v0.5. This page shows a runtime Topic View built directly from approved cards — no LLM calls, no synthesized text."}
        </p>
      </section>

      {/* Three-column layout */}
      <div className="grid grid-cols-12 gap-4">
        {/* Left: Topic list */}
        <div className="col-span-3">
          <TopicList
            topics={topicList}
            selectedTopic={selectedTopic}
            onSelect={(name) => {
              void handleSelectTopic(name);
            }}
          />
        </div>

        {/* Center: Topic view */}
        <div className="col-span-6">
          {!selectedTopic && (
            <div className="rounded-lg border border-line bg-white/60 p-8 text-center">
              <p className="text-sm text-muted">
                {locale === "zh"
                  ? "从左侧选择一个主题查看已确认卡片"
                  : "Select a topic from the left to view approved cards"}
              </p>
            </div>
          )}

          {topicLoading && (
            <div className="flex items-center justify-center py-8 text-sm text-muted">
              {locale === "zh" ? "正在加载..." : "Loading..."}
            </div>
          )}

          {error && selectedTopic && (
            <div className="rounded-lg border border-[var(--mf-warn)]/30 bg-[var(--mf-warn)]/5 p-6 text-center">
              <p className="text-sm text-[var(--mf-warn)]">{error}</p>
            </div>
          )}

          {topicData && !topicLoading && (
            <TopicView
              data={topicData}
              selectedCard={selectedCard}
              onSelectCard={setSelectedCard}
            />
          )}
        </div>

        {/* Right: Context panel */}
        <div className="col-span-3">
          <TopicContextPanel card={selectedCard} />
        </div>
      </div>
    </div>
  );
}
