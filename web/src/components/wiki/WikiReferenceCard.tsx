/**
 * Wiki Reference Card component.
 *
 * Single approved knowledge card reference with provenance metadata.
 * Visible by default — provenance is a first-class feature, not debug info.
 *
 * SDD_WIKI_WEB_PRESENTATION_ADDENDUM §7.
 */

import { FileText, Tag, Star, CheckCircle } from "lucide-react";
import { useLocale, type Locale } from "../../lib/i18n";
import { friendlyTrack } from "../../lib/utils";
import type { WikiReferenceView } from "../../api/wiki";

interface WikiReferenceCardProps {
  ref: WikiReferenceView;
}

/* 中文学习型说明：source_type 是 adapter 内部标识符（plain_markdown/txt/html/pdf/docx），
   属于技术分类标签而非用户 UI copy。此处仅做简短格式名映射，不进入 i18n 字典。
   未来如需完整本地化，可扩展为 sourceTypeLabel(ref.source_type, locale) 函数。 */
const sourceTypeLabels: Record<string, string> = {
  plain_markdown: "Markdown",
  txt: "Text",
  html: "HTML",
  pdf: "PDF",
  docx: "Word",
};

export function WikiReferenceCard({ ref }: WikiReferenceCardProps) {
  const { t, locale } = useLocale();

  const sourceLabel =
    (ref.source_type ? sourceTypeLabels[ref.source_type] : null) ??
    ref.source_type ??
    null;

  const cardRef = ref.card_id ?? ref.card_rel_path;

  const cardContent = (
    <div className="flex items-start gap-2.5">
      <FileText size={15} className="mt-0.5 shrink-0 text-muted" />
      <div className="min-w-0 flex-1">
        {/* Card title + approved indicator */}
        <div className="flex items-center gap-2">
          <span className="font-medium text-ink truncate">
            {ref.card_title}
          </span>
          <span
            className="inline-flex shrink-0 items-center gap-1 rounded bg-safe/10 px-1.5 py-0.5 text-[10px] font-medium text-safe"
            title={t("wiki.approved_tooltip")}
          >
            <CheckCircle size={10} />
            {t("wiki.approved_badge")}
          </span>
        </div>

        {/* Provenance metadata */}
        <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
          {sourceLabel && (
            <span className="inline-flex items-center rounded bg-muted/20 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide">
              {sourceLabel}
            </span>
          )}
          {ref.source_title && (
            <span className="truncate max-w-[200px]">
              {ref.source_title}
            </span>
          )}
          {ref.track && (
            <span className="inline-flex items-center gap-1">
              <Tag size={10} />
                            {friendlyTrack(ref.track, locale)}
            </span>
          )}
          {ref.value_score != null && (
            <span className="inline-flex items-center gap-1">
              <Star size={10} className="text-amber-500" />
              {ref.value_score}
            </span>
          )}
          {ref.tags.length > 0 && (
            <span className="flex items-center gap-1">
              {ref.tags.slice(0, 3).map((t) => (
                <span
                  key={t}
                  className="rounded bg-muted/20 px-1 py-0.5 text-[10px]"
                >
                  {t}
                </span>
              ))}
            </span>
          )}
        </div>
      </div>
    </div>
  );

  if (cardRef) {
    return (
      <li>
        <a
          href={`/library?card=${encodeURIComponent(cardRef)}`}
          className="block w-full rounded-md border border-line bg-panel p-3 text-left text-sm no-underline transition-colors hover:border-primary hover:bg-blue-50/40"
          aria-label={`${t("library.title")}: ${ref.card_title}`}
        >
          {cardContent}
        </a>
      </li>
    );
  }

  return (
    <li className="rounded-md border border-line bg-panel p-3 text-sm">
      {cardContent}
    </li>
  );
}
