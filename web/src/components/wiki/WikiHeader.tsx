/**
 * Wiki Header component.
 *
 * Page-level title and description.
 *
 * SDD_WIKI_WEB_PRESENTATION_ADDENDUM §12.
 */

interface WikiHeaderProps {
  title?: string;
}

export function WikiHeader({ title = "Wiki" }: WikiHeaderProps) {
  return (
    <header>
      <h1 className="text-2xl font-semibold text-ink">{title}</h1>
      <p className="mt-1 text-sm text-muted">
        Your personal knowledge base, synthesized from approved knowledge
        cards. Browse sections, explore connections, and trace ideas back to
        their sources.
      </p>
    </header>
  );
}
