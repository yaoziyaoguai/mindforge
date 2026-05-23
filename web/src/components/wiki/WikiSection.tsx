/**
 * Wiki Section component.
 *
 * Renders a single wiki section: title as heading, body as Markdown → safe HTML.
 *
 * SDD_WIKI_PRESENTATION_V2 §4.4.
 */

import { renderMarkdown } from "../../lib/wiki-renderer";
import { useLocale } from "../../lib/i18n";
import type { WikiSectionView } from "../../api/wiki";
import { WikiReferencePanel } from "./WikiReferencePanel";
import { WikiSectionRelationshipPreview } from "./WikiSectionRelationshipPreview";

interface WikiSectionProps {
  section: WikiSectionView;
}

export function WikiSection({ section }: WikiSectionProps) {
  const { t } = useLocale();

  return (
    <section id={section.anchor.replace("#", "")} className="scroll-mt-6">
      <h2 className="mb-3 text-xl font-semibold text-ink">{section.title}</h2>
      <div
        className="prose prose-sm max-w-[720px] text-ink leading-relaxed"
        dangerouslySetInnerHTML={{ __html: renderMarkdown(section.body) }}
      />
      <WikiSectionRelationshipPreview sectionTitle={section.title} refs={section.card_refs} />
      {section.card_refs.length > 0 && (
        <WikiReferencePanel
          refs={section.card_refs}
          title={t("wiki.knowledge_sources")}
        />
      )}
    </section>
  );
}
