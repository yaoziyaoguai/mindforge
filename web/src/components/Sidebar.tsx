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
      className="flex w-64 shrink-0 flex-col px-4 py-6"
      style={{ background: "var(--mf-surface-alt)" }}
      aria-label="Main navigation"
    >
      <div
        className="mb-8 px-3 text-xl font-semibold text-ink tracking-tight flex items-center gap-2"
        style={{ fontFamily: "var(--mf-font-serif)" }}
      >
        <div className="flex h-8 w-8 items-center justify-center rounded-lg" style={{ background: "var(--mf-accent)" }}>
          <span className="text-white text-lg font-bold">M</span>
        </div>
        MindForge
      </div>

      <div className="flex-1 space-y-6">
        {groups.map((group) => (
          <div key={group.label}>
            <p className="mb-2 px-3 text-[10px] font-bold uppercase tracking-wider text-muted/50">
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
                      "group flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-all",
                      active
                        ? "bg-white text-ink font-semibold shadow-sm ring-1 ring-black/5"
                        : "text-muted hover:bg-white/60 hover:text-ink",
                    )}
                  >
                    <Icon className={cx("h-4 w-4 shrink-0 transition-colors", active ? "text-indigo-600" : "text-muted/70 group-hover:text-ink")} aria-hidden="true" />
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
            className="group flex w-full items-center gap-2 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-muted/50 hover:text-muted"
            aria-expanded={labOpen}
          >
            {t("nav.group.lab")}
            <ChevronDown
              className={cx("h-3 w-3 transition-transform", labOpen ? "rotate-180" : "rotate-0")}
              aria-hidden="true"
            />
          </button>
          {labOpen && (
            <div className="mt-1 space-y-0.5">
              {labItems.map((item) => {
                const active = path === item.href || path.startsWith(item.href);
                const Icon = item.icon;
                return (
                  <button
                    key={item.href}
                    type="button"
                    onClick={() => onNavigate(item.href)}
                    className={cx(
                      "group flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-all",
                      active
                        ? "bg-white text-ink font-semibold shadow-sm ring-1 ring-black/5"
                        : "text-muted/70 hover:bg-white/60 hover:text-ink",
                    )}
                  >
                    <Icon className={cx("h-4 w-4 shrink-0 transition-colors", active ? "text-indigo-600" : "text-muted/50 group-hover:text-ink")} aria-hidden="true" />
                    {item.label}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      <div className="mt-auto space-y-0.5 pt-4">
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
