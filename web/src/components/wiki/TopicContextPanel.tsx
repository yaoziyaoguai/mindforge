/**
 * TopicContextPanel — shows selected card's relations and provenance.
 *
 * Right panel in the topic browser layout.
 */

import { useLocale } from "../../lib/i18n";
import type { TopicCardView } from "../../api/topics";

interface TopicContextPanelProps {
  card: TopicCardView | null;
}

export function TopicContextPanel({ card }: TopicContextPanelProps) {
  const { locale, t } = useLocale();

  if (!card) {
    return (
      <div className="rounded-lg border border-line bg-white/60 p-6 text-center">
        <p className="text-xs text-muted">
          {locale === "zh"
            ? "选择一张卡片查看关系和来源信息"
            : "Select a card to view relations and provenance"}
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-line bg-white/60 divide-y">
      {/* Header */}
      <div className="p-4">
        <h4 className="text-sm font-semibold text-ink">
          {card.title ?? t("card.untitled")}
        </h4>
        <div className="mt-1 flex items-center gap-2">
          <span className="rounded-full bg-safe/10 px-2 py-0.5 text-[10px] font-medium text-safe">
            {card.approval_state === "human_approved"
              ? t("wiki.approved_badge")
              : card.approval_state}
          </span>
          {card.value_score != null && (
            <span className="text-[10px] text-muted">
              {t("approval.value_score")}: {card.value_score}
            </span>
          )}
        </div>
      </div>

      {/* Relations */}
      <div className="p-4">
        <h5 className="mb-2 text-xs font-semibold text-muted uppercase tracking-wide">
          {locale === "zh" ? "关系" : "Relations"}
        </h5>
        {card.relations.length === 0 ? (
          <p className="text-xs text-muted">
            {locale === "zh"
              ? "暂无关联卡片"
              : "No related cards"}
          </p>
        ) : (
          <ul className="space-y-1.5">
            {card.relations.map((rel, i) => (
              <li key={i} className="flex items-center gap-1.5 text-xs text-muted">
                <span className="rounded bg-muted/10 px-1.5 py-0.5 text-[10px] font-medium">
                  {rel.type}
                </span>
                <span className="truncate">{rel.target_id}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Provenance */}
      <div className="p-4">
        <h5 className="mb-2 text-xs font-semibold text-muted uppercase tracking-wide">
          {locale === "zh" ? "来源与时间" : "Provenance"}
        </h5>
        <dl className="space-y-1 text-xs">
          {card.source_title && (
            <div className="flex justify-between">
              <dt className="text-muted">
                {locale === "zh" ? "来源" : "Source"}
              </dt>
              <dd className="text-ink">{card.source_title}</dd>
            </div>
          )}
          {card.source_type && (
            <div className="flex justify-between">
              <dt className="text-muted">
                {locale === "zh" ? "类型" : "Type"}
              </dt>
              <dd className="text-ink">{card.source_type}</dd>
            </div>
          )}
          {card.created_at && (
            <div className="flex justify-between">
              <dt className="text-muted">
                {locale === "zh" ? "创建" : "Created"}
              </dt>
              <dd className="text-ink">
                {new Date(card.created_at).toLocaleDateString(
                  locale === "zh" ? "zh-CN" : "en-US",
                  { year: "numeric", month: "short", day: "numeric" },
                )}
              </dd>
            </div>
          )}
          {card.approved_at && (
            <div className="flex justify-between">
              <dt className="text-muted">
                {locale === "zh" ? "确认于" : "Approved"}
              </dt>
              <dd className="text-ink">
                {new Date(card.approved_at).toLocaleDateString(
                  locale === "zh" ? "zh-CN" : "en-US",
                  { year: "numeric", month: "short", day: "numeric" },
                )}
              </dd>
            </div>
          )}
          {card.track && (
            <div className="flex justify-between">
              <dt className="text-muted">
                {locale === "zh" ? "主题" : "Track"}
              </dt>
              <dd className="text-ink">{card.track}</dd>
            </div>
          )}
        </dl>
      </div>

      {/* Human note, if any */}
      {card.human_note && (
        <div className="p-4">
          <h5 className="mb-2 text-xs font-semibold text-muted uppercase tracking-wide">
            {locale === "zh" ? "人工备注" : "Human Note"}
          </h5>
          <p className="text-xs text-ink leading-relaxed">{card.human_note}</p>
        </div>
      )}
    </div>
  );
}
