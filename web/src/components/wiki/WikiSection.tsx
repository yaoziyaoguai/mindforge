/**
 * Wiki Section component.
 *
 * Renders a single wiki section: title as heading, body as Markdown → safe HTML.
 *
 * SDD_WIKI_PRESENTATION_V2 §4.4.
 */

import { renderMarkdown } from "../../lib/wiki-renderer";
import { useLocale } from "../../lib/i18n";
import type { WikiSectionView, WikiRelatedSection } from "../../api/wiki";
import { WikiReferencePanel } from "./WikiReferencePanel";
import { WikiSectionRelationshipPreview } from "./WikiSectionRelationshipPreview";

interface WikiSectionProps {
  section: WikiSectionView;
  readerMode?: boolean;
  relatedSections?: WikiRelatedSection[];
}

export function WikiSection({ section, readerMode, relatedSections }: WikiSectionProps) {
  const { t } = useLocale();

  return (
    <section id={section.anchor.replace("#", "")} className="scroll-mt-6">
      <div className="flex items-baseline gap-2 mb-3 flex-wrap">
        <h2 className="text-xl font-semibold text-ink">{section.title}</h2>
        {!readerMode && relatedSections && relatedSections.length > 0 && (
          <span className="text-xs text-muted">
            {t("wiki.related_sections")}:{" "}
            {relatedSections.map((rs, i) => (
              <span key={rs.title}>
                <a
                  href={`#${rs.title.toLowerCase().replace(/[^\w\s-]/g, "").replace(/\s+/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "") || "untitled"}`}
                  className="text-primary hover:underline"
                >
                  {rs.title}
                </a>
                {i < relatedSections.length - 1 && ", "}
              </span>
            ))}
          </span>
        )}
      </div>
      <div
        className={`prose prose-sm max-w-[680px] text-ink ${readerMode ? "max-w-[800px]" : ""}`}
        dangerouslySetInnerHTML={{ __html: renderMarkdown(section.body) }}
      />
      {!readerMode && (
        <WikiSectionRelationshipPreview sectionTitle={section.title} refs={section.card_refs} />
      )}
      {!readerMode && section.card_refs.length > 0 && (
        <WikiReferencePanel
          refs={section.card_refs}
          title={t("wiki.knowledge_sources")}
        />
      )}
    </section>
  );
}
