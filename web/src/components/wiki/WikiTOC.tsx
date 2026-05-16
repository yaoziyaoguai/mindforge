/**
 * Wiki TOC (Table of Contents) component.
 *
 * Sticky sidebar with section anchor links. Responsive:
 * - Desktop (lg+): always visible sticky sidebar, w-56
 * - Tablet (md): always visible, w-48
 * - Mobile (<md): toggle button → inline collapsible TOC
 *
 * SDD_WIKI_WEB_PRESENTATION_ADDENDUM §5.1, §12.
 */

import { useState } from "react";
import type { WikiSectionView } from "../../api/wiki";

interface WikiTOCProps {
  sections: WikiSectionView[];
}

export function WikiTOC({ sections }: WikiTOCProps) {
  const [expanded, setExpanded] = useState(false);

  if (sections.length === 0) return null;

  const tocContent = (
    <div className="rounded-md border border-line bg-panel p-4">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted">
        Contents
      </h2>
      <ul className="space-y-1">
        {sections.map((sec) => (
          <li key={sec.id}>
            <a
              href={sec.anchor}
              className="block rounded px-2 py-1 text-sm text-muted hover:bg-hover hover:text-ink transition-colors"
              onClick={() => setExpanded(false)}
            >
              {sec.title || "(untitled)"}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );

  return (
    <nav aria-label="Table of Contents">
      {/* Mobile toggle button */}
      <div className="md:hidden mb-3">
        <button
          type="button"
          className="inline-flex items-center gap-1.5 rounded-md border border-line bg-panel px-3 py-2 text-sm font-medium text-ink hover:bg-hover transition-colors"
          onClick={() => setExpanded((prev) => !prev)}
          aria-expanded={expanded}
          aria-controls="wiki-toc-content"
          aria-label="Toggle table of contents"
        >
          {expanded ? "Hide Contents" : "Contents"}
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
