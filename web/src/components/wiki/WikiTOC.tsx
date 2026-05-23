/**
 * Wiki TOC (Table of Contents) component.
 *
 * Sticky sidebar with section anchor links. Responsive:
 * - Desktop (lg+): always visible sticky sidebar, w-56
 * - Tablet (md): always visible, w-48
 * - Mobile (<md): toggle button → inline collapsible TOC
 *
 * Milestone G U2: TOC scroll spy via IntersectionObserver —
 * highlights the current section as the user scrolls.
 *
 * SDD_WIKI_WEB_PRESENTATION_ADDENDUM §5.1, §12.
 */

import { useEffect, useRef, useState } from "react";
import { useLocale } from "../../lib/i18n";
import type { WikiSectionView } from "../../api/wiki";

interface WikiTOCProps {
  sections: WikiSectionView[];
}

export function WikiTOC({ sections }: WikiTOCProps) {
  const [expanded, setExpanded] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const { t } = useLocale();

  useEffect(() => {
    const sectionIds = sections.map((sec) => sec.anchor.replace("#", ""));
    const elements = sectionIds
      .map((id) => document.getElementById(id))
      .filter(Boolean) as HTMLElement[];

    if (elements.length === 0) return;

    observerRef.current = new IntersectionObserver(
      (entries) => {
        let maxRatio = 0;
        let maxId: string | null = null;
        for (const entry of entries) {
          if (entry.intersectionRatio > maxRatio) {
            maxRatio = entry.intersectionRatio;
            maxId = entry.target.id;
          }
        }
        if (maxId) setActiveId(maxId);
      },
      { threshold: [0, 0.25, 0.5, 0.75, 1] },
    );

    elements.forEach((el) => observerRef.current!.observe(el));

    return () => {
      observerRef.current?.disconnect();
      observerRef.current = null;
    };
  }, [sections]);

  if (sections.length === 0) return null;

  const tocContent = (
    <div className="rounded-md border border-line bg-panel p-4">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted">
        {t("wiki.contents")}
      </h2>
      <ul className="space-y-1">
        {sections.map((sec) => {
          const id = sec.anchor.replace("#", "");
          const isActive = activeId === id;
          return (
            <li key={sec.id}>
              <a
                href={sec.anchor}
                className={`block rounded px-2 py-1 text-sm transition-colors hover:bg-hover hover:text-ink ${
                  isActive ? "bg-primary/10 text-primary font-medium" : "text-muted"
                }`}
                onClick={() => setExpanded(false)}
              >
                {sec.title || t("wiki.untitled_section")}
              </a>
            </li>
          );
        })}
      </ul>
    </div>
  );

  return (
    <nav aria-label={t("wiki.contents")}>
      {/* Mobile toggle button */}
      <div className="wiki-chrome md:hidden mb-3">
        <button
          type="button"
          className="inline-flex items-center gap-1.5 rounded-md border border-line bg-panel px-3 py-2 text-sm font-medium text-ink hover:bg-hover transition-colors"
          onClick={() => setExpanded((prev) => !prev)}
          aria-expanded={expanded}
          aria-controls="wiki-toc-content"
          aria-label={t("wiki.toc_toggle")}
        >
          {expanded ? t("wiki.hide_contents") : t("wiki.contents")}
          <span className="text-xs text-muted">({sections.length})</span>
        </button>
      </div>

      {/* Desktop: always visible sticky sidebar */}
      <div
        id="wiki-toc-content"
        className="hidden shrink-0 md:block lg:w-56 md:w-48"
      >
        <div className="sticky top-4">{tocContent}</div>
      </div>

      {/* Mobile: inline collapsible (below the toggle button) */}
      {expanded && <div className="md:hidden">{tocContent}</div>}
    </nav>
  );
}
