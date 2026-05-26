/**
 * Wiki Header component.
 *
 * Page-level title and description.
 *
 * SDD_WIKI_WEB_PRESENTATION_ADDENDUM §12.
 */

import { useLocale } from "../../lib/i18n";

interface WikiHeaderProps {
  title?: string;
}

export function WikiHeader({ title }: WikiHeaderProps) {
  const { t } = useLocale();
  return (
    <header className="page-header">
      <h1>{title ?? t("wiki.title")}</h1>
      <p className="mt-1 text-sm text-muted">{t("wiki.subtitle")}</p>
    </header>
  );
}
