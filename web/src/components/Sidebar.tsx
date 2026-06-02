import { useState } from "react";
import {
  BarChart3,
  BookMarked,
  BookOpen,
  Brain,
  CheckSquare,
  ChevronDown,
  Download,
  FlaskConical,
  Globe,
  Heart,
  Home,
  Inbox,
  Library,
  Network,
  Search,
  Settings,
  Trash2,
} from "lucide-react";
import { cx } from "../lib/utils";
import { useLocale } from "../lib/i18n";

export function Sidebar({ path, onNavigate, providerState }: { path: string; onNavigate: (href: string) => void; providerState?: string }) {
  const { locale, setLocale, t } = useLocale();
  const [labOpen, setLabOpen] = useState(false);

  const groups = [
    {
      label: t("nav.group.pipeline"),
      items: [
        { href: "/sources", label: t("nav.sources"), icon: Inbox },
        { href: "/drafts", label: t("nav.drafts"), icon: CheckSquare },
        { href: "/library", label: t("nav.library"), icon: Library },
        { href: "/recall", label: t("nav.recall"), icon: Search },
        { href: "/wiki", label: t("nav.wiki"), icon: BookMarked },
        { href: "/export", label: t("nav.export"), icon: Download },
      ],
    },
    {
      label: t("nav.group.system"),
      items: [
        { href: "/", label: t("nav.home"), icon: Home },
        { href: "/setup", label: t("nav.setup"), icon: Settings },
        { href: "/health", label: t("nav.health"), icon: Heart },
        { href: "/trash", label: t("nav.trash"), icon: Trash2 },
      ],
    },
  ];

  const labItems = [
    { href: "/graph", label: t("nav.graph"), icon: Network },
    { href: "/sensemaking", label: t("nav.sensemaking"), icon: Brain },
    { href: "/dogfood", label: t("nav.dogfood"), icon: BarChart3 },
  ];

  return (
    <nav
      className="flex w-60 shrink-0 flex-col border-r border-line px-3 py-5"
      style={{ background: "var(--mf-surface-alt)" }}
      aria-label="Main navigation"
    >
      <div
        className="mb-8 px-2 text-lg font-medium text-ink tracking-tight"
        style={{ fontFamily: "var(--mf-font-serif)" }}
      >
        MindForge
      </div>

      <div className="flex-1 space-y-5">
        {groups.map((group) => (
          <div key={group.label}>
            <p className="mb-1.5 px-2 text-[11px] font-medium text-muted/70">
              {group.label}
            </p>
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const active =
                  path === item.href || (item.href !== "/" && path.startsWith(item.href));
                const Icon = item.icon;
                return (
                  <button
                    key={item.href}
                    type="button"
                    onClick={() => onNavigate(item.href)}
                    className={cx(
                      "flex w-full items-center gap-2.5 rounded-md px-2.5 py-1.5 text-left text-sm transition-colors",
                      active
                        ? "bg-white/80 text-ink font-medium shadow-sm"
                        : "text-muted hover:bg-white/50 hover:text-ink",
                    )}
                  >
                    <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                    <span className="flex-1">{item.label}</span>
                    {/* provider 状态指示灯 — 仅在 setup 条目上显示 */}
                    {item.href === "/setup" && (
                      <span
                        className="inline-block h-2 w-2 shrink-0 rounded-full"
                        style={{
                          background: providerState === "ready"
                            ? "var(--mf-approved)"
                            : "var(--mf-warning)",
                        }}
                        title={providerState === "ready" ? "Live" : "Sandbox"}
                      />
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}

        {/* Lab Section */}
        <div>
          <button
            type="button"
            onClick={() => setLabOpen(!labOpen)}
            className="flex w-full items-center gap-1.5 px-2 py-1 text-[11px] font-medium text-muted/60 hover:text-muted"
            aria-expanded={labOpen}
          >
            <ChevronDown
              className={cx("h-3 w-3 transition-transform", labOpen ? "rotate-0" : "-rotate-90")}
              aria-hidden="true"
            />
            {t("nav.group.lab")}
          </button>
          {labOpen && (
            <div className="mt-0.5 space-y-0.5">
              {labItems.map((item) => {
                const active = path === item.href || path.startsWith(item.href);
                const Icon = item.icon;
                return (
                  <button
                    key={item.href}
                    type="button"
                    onClick={() => onNavigate(item.href)}
                    className={cx(
                      "flex w-full items-center gap-2.5 rounded-md px-2.5 py-1.5 text-left text-sm transition-colors",
                      active
                        ? "bg-white/80 text-ink font-medium shadow-sm"
                        : "text-muted/70 hover:bg-white/50 hover:text-ink",
                    )}
                  >
                    <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                    {item.label}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      <div className="mt-auto space-y-0.5 border-t border-line/60 pt-3">
        <button
          type="button"
          className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-1.5 text-left text-sm text-muted hover:bg-white/50 hover:text-ink"
          onClick={() => setLocale(locale === "zh" ? "en" : "zh")}
          title={locale === "zh" ? "Switch to English" : "切换到中文"}
        >
          <Globe className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          <span>{locale === "zh" ? "English" : "简体中文"}</span>
        </button>
        <a
          href="https://github.com/yaoziyaoguai/mindforge/issues"
          target="_blank"
          rel="noopener noreferrer"
          className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-1.5 text-left text-xs text-muted/70 hover:bg-white/50 hover:text-ink no-underline"
        >
          <Heart className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          <span>{t("nav.feedback")}</span>
        </a>
      </div>
    </nav>
  );
}
