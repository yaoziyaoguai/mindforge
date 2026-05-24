import { BookOpen, BookMarked, CheckSquare, Globe, Heart, Home, Inbox, Library, Search, Settings, Trash2 } from "lucide-react";
import { cx } from "../lib/utils";
import { useLocale } from "../lib/i18n";

export function Sidebar({ path, onNavigate }: { path: string; onNavigate: (href: string) => void }) {
  const { locale, setLocale, t } = useLocale();

  const groups = [
    {
      label: t("nav.group.processing"),
      items: [
        { href: "/setup", label: t("nav.setup"), icon: Settings },
        { href: "/sources", label: t("nav.sources"), icon: Inbox },
        { href: "/drafts", label: t("nav.drafts"), icon: CheckSquare },
        { href: "/trash", label: t("nav.trash"), icon: Trash2 },
      ],
    },
    {
      label: t("nav.group.using"),
      items: [
        { href: "/", label: t("nav.home"), icon: Home },
        { href: "/library", label: t("nav.library"), icon: Library },
        { href: "/wiki", label: t("nav.wiki"), icon: BookMarked },
        { href: "/recall", label: t("nav.recall"), icon: Search },
        { href: "/health", label: t("nav.health"), icon: Heart },
      ],
    },
  ];

  return (
    <nav className="flex w-64 shrink-0 flex-col border-r border-line bg-[#efebe3] px-3 py-4" aria-label="Main navigation">
      <div className="mb-6 flex items-center gap-2 px-2 text-lg font-semibold text-ink">
        <BookOpen className="h-5 w-5" aria-hidden="true" />
        MindForge
      </div>
      <div className="flex-1 space-y-2">
        {groups.map((group) => (
          <div key={group.label}>
            <p className="mb-1 px-2 text-xs font-semibold uppercase tracking-wider text-muted">{group.label}</p>
            <div className="space-y-1">
              {group.items.map((item) => {
                const active = path === item.href || (item.href !== "/" && path.startsWith(item.href));
                const Icon = item.icon;
                return (
                  <button
                    key={item.href}
                    type="button"
                    onClick={() => onNavigate(item.href)}
                    className={cx(
                      "flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm",
                      active ? "bg-panel text-ink shadow-subtle" : "text-muted hover:bg-white/60 hover:text-ink",
                    )}
                  >
                    <Icon className="h-4 w-4" aria-hidden="true" />
                    {item.label}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      {/* 语言切换 —— sidebar footer，最小改动路径 */}
      <div className="mt-auto border-t border-line pt-3">
        <button
          type="button"
          className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-sm text-muted hover:bg-white/60 hover:text-ink"
          onClick={() => setLocale(locale === "zh" ? "en" : "zh")}
          title={locale === "zh" ? "Switch to English" : "切换到中文"}
        >
          <Globe className="h-4 w-4" aria-hidden="true" />
          <span>{locale === "zh" ? "English" : "简体中文"}</span>
        </button>
      </div>
    </nav>
  );
}
