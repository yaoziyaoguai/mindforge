/**
 * Wiki TOC (Table of Contents) component.
 *
 * Fixed sidebar showing section titles with anchor links.
 *
 * SDD_WIKI_PRESENTATION_V2 §9.
 */

import type { WikiSectionView } from "../../api/wiki";

interface WikiTOCProps {
  sections: WikiSectionView[];
}

export function WikiTOC({ sections }: WikiTOCProps) {
  if (sections.length === 0) return null;

  return (
    <nav className="w-56 shrink-0" aria-label="Table of Contents">
      <div className="sticky top-4 rounded-md border border-line bg-panel p-4">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted">
          Contents
        </h2>
        <ul className="space-y-1">
          {sections.map((sec) => (
            <li key={sec.id}>
              <a
                href={sec.anchor}
                className="block rounded px-2 py-1 text-sm text-muted hover:bg-hover hover:text-ink transition-colors"
              >
                {sec.title || "(untitled)"}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </nav>
  );
}
