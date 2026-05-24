import { ChevronRight, Home } from "lucide-react";
import { useLocale } from "../lib/i18n";

const routeLabels: Record<string, string> = {
  "/": "breadcrumb.home",
  "/setup": "nav.setup",
  "/sources": "nav.sources",
  "/drafts": "nav.drafts",
  "/review": "nav.drafts",
  "/library": "nav.library",
  "/recall": "nav.recall",
  "/search": "nav.recall",
  "/wiki": "nav.wiki",
  "/health": "nav.health",
  "/trash": "nav.trash",
};

export function Breadcrumb({ path }: { path: string }) {
  const { t } = useLocale();

  const segments = path
    .split("/")
    .filter(Boolean)
    .reduce<{ href: string; labelKey: string }[]>(
      (acc, seg) => {
        const href = acc.length === 0 ? `/${seg}` : `${acc[acc.length - 1].href}/${seg}`;
        const labelKey = routeLabels[href] ?? seg;
        acc.push({ href, labelKey });
        return acc;
      },
      [],
    );

  if (segments.length === 0) return null;

  return (
    <nav aria-label="Breadcrumb" className="mb-4 flex items-center gap-1.5 text-sm text-muted">
      <a
        href="/"
        className="inline-flex items-center gap-1 transition-colors hover:text-ink"
        onClick={(e) => {
          e.preventDefault();
          window.history.pushState({}, "", "/");
          window.dispatchEvent(new PopStateEvent("popstate"));
        }}
      >
        <Home className="h-3.5 w-3.5" aria-hidden="true" />
        {t("breadcrumb.home")}
      </a>
      {segments.map((seg) => (
        <span key={seg.href} className="inline-flex items-center gap-1.5">
          <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
          {seg.href === path ? (
            <span className="text-ink">{t(seg.labelKey)}</span>
          ) : (
            <a
              href={seg.href}
              className="transition-colors hover:text-ink"
              onClick={(e) => {
                e.preventDefault();
                window.history.pushState({}, "", seg.href);
                window.dispatchEvent(new PopStateEvent("popstate"));
              }}
            >
              {t(seg.labelKey)}
            </a>
          )}
        </span>
      ))}
    </nav>
  );
}
