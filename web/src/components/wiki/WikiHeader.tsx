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
    <header>
      <h1 className="text-2xl font-semibold text-ink">{title ?? t("wiki.title")}</h1>
      <p className="mt-1 text-sm text-muted">{t("wiki.subtitle")}</p>
    </header>
  );
}
