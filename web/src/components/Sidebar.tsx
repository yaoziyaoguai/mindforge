import { useState } from "react";
import {
  BarChart3,
  BookMarked,
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
  ShieldCheck,
  Trash2,
  User,
  type LucideIcon,
} from "lucide-react";
import { cx } from "../lib/utils";
import { useLocale } from "../lib/i18n";

export function Sidebar({
  path,
  onNavigate,
  providerState,
}: {
  path: string;
  onNavigate: (href: string) => void;
  providerState?: string;
}) {
  const { locale, setLocale, t } = useLocale();
  const [labOpen, setLabOpen] = useState(false);
  const providerReady = providerState === "ready";

  const primaryItems = [
    { href: "/", label: t("nav.home"), icon: Home },
    { href: "/sources", label: t("nav.sources"), icon: Inbox },
    { href: "/drafts", label: t("nav.drafts"), icon: CheckSquare },
    { href: "/review", label: t("nav.review"), icon: BarChart3 },
    { href: "/library", label: t("nav.library"), icon: Library },
    { href: "/recall", label: t("nav.recall"), icon: Search },
    { href: "/wiki", label: t("nav.wiki"), icon: BookMarked },
    { href: "/export", label: t("nav.export"), icon: Download },
  ];

  const utilityItems = [
    { href: "/setup", label: t("nav.setup"), icon: Settings },
    { href: "/health", label: t("nav.health"), icon: Heart },
    { href: "/trash", label: t("nav.trash"), icon: Trash2 },
  ];

  const labItems = [
    { href: "/graph", label: t("nav.graph"), icon: Network },
    { href: "/sensemaking", label: t("nav.sensemaking"), icon: Brain },
    { href: "/dogfood", label: t("nav.dogfood"), icon: BarChart3 },
  ];

  return (
    <nav
      className="flex w-[280px] shrink-0 flex-col px-5 py-6"
      style={{ background: "var(--mf-sidebar)" }}
      aria-label="Main navigation"
    >
      <div
        className="mb-6 flex items-center gap-3 px-2 text-xl font-bold tracking-tight text-ink"
      >
        <div
          className="flex h-10 w-10 items-center justify-center rounded-2xl text-white shadow-sm"
          style={{
            background: "linear-gradient(135deg, var(--mf-accent), #7968ff)",
            boxShadow: "0 14px 30px rgba(91, 70, 246, 0.28)",
          }}
        >
          <span className="text-lg font-black">M</span>
        </div>
        <div>
          <div>MindForge</div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.12em]" style={{ color: "var(--mf-text-tertiary)" }}>
            {t("sidebar.product_subtitle")}
          </div>
        </div>
      </div>

      {/* 中文学习型说明：
          这个卡片只展示 provider 边界和配置入口，不会自动开启真实模型。
          first-run 用户必须第一眼明白当前是 Demo/Fake 还是 Real Provider；
          fake/real 不能混用，否则用户会把模拟草稿误认为真实模型产物。 */}
      <section className="mb-5 rounded-2xl border p-4 shadow-sm" style={{
        borderColor: providerReady ? "rgba(20, 150, 107, 0.18)" : "rgba(91, 70, 246, 0.16)",
        background: providerReady
          ? "linear-gradient(135deg, rgba(20,150,107,0.1), rgba(255,255,255,0.92))"
          : "linear-gradient(135deg, rgba(91,70,246,0.1), rgba(255,255,255,0.92))",
      }}>
        <div className="mb-3 flex items-center gap-2">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-xl"
            style={{ background: providerReady ? "rgba(20,150,107,0.12)" : "var(--mf-accent-soft)" }}
          >
            {providerReady ? (
              <ShieldCheck className="h-4 w-4" style={{ color: "var(--mf-approved)" }} aria-hidden="true" />
            ) : (
              <FlaskConical className="h-4 w-4" style={{ color: "var(--mf-accent)" }} aria-hidden="true" />
            )}
          </div>
          <div>
            <div className="text-sm font-bold text-ink">
              {providerReady ? t("sidebar.real_title") : t("sidebar.demo_title")}
            </div>
            <p className="text-[11px] leading-snug" style={{ color: "var(--mf-text-tertiary)" }}>
              {providerReady ? t("sidebar.real_desc") : t("sidebar.demo_desc")}
            </p>
          </div>
        </div>
        <div
          className={cx(
            "flex w-full items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm font-bold",
            providerReady
              ? "border border-white/70 bg-white/80 text-ink"
              : "text-white/80",
          )}
          style={providerReady ? undefined : { background: "linear-gradient(135deg, var(--mf-accent), #6f5cff)", opacity: 0.7 }}
        >
          <FlaskConical className="h-3.5 w-3.5" aria-hidden="true" style={{ opacity: 0.6 }} />
          {providerReady ? t("sidebar.manage_model") : t("sidebar.demo_mode_chip")}
        </div>
      </section>

      <div className="flex-1 space-y-5 overflow-y-auto pr-1">
        <div>
          <p className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.14em]" style={{ color: "var(--mf-text-tertiary)" }}>
            {t("nav.group.pipeline")}
          </p>
          <div className="space-y-1">
            {primaryItems.map((item) => (
              <SidebarItem key={item.href} path={path} item={item} onNavigate={onNavigate} />
            ))}
          </div>
        </div>

        <div>
          <p className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.14em]" style={{ color: "var(--mf-text-tertiary)" }}>
            {t("nav.group.system")}
          </p>
          <div className="space-y-1">
            {utilityItems.map((item) => (
              <SidebarItem
                key={item.href}
                path={path}
                item={item}
                onNavigate={onNavigate}
                badge={item.href === "/setup" ? (providerReady ? t("sidebar.real_badge") : t("sidebar.demo_badge")) : undefined}
              />
            ))}
          </div>
        </div>

        {/* Lab Section */}
        <div>
          <button
            type="button"
            onClick={() => setLabOpen(!labOpen)}
            className="group flex w-full items-center gap-2 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.14em] hover:text-muted"
            style={{ color: "var(--mf-text-tertiary)" }}
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
                return (
                  <SidebarItem key={item.href} path={path} item={item} onNavigate={onNavigate} compact />
                );
              })}
            </div>
          )}
        </div>
      </div>

      <div className="mt-auto space-y-3 pt-4">
        <div className="rounded-2xl border border-white/70 bg-white/70 p-3 shadow-sm">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-full" style={{ background: "var(--mf-accent-soft)", color: "var(--mf-accent)" }}>
              <User className="h-4 w-4" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <div className="truncate text-sm font-bold text-ink">Jinkun</div>
              <div className="truncate text-xs" style={{ color: "var(--mf-text-tertiary)" }}>{t("sidebar.workspace")}</div>
            </div>
          </div>
        </div>
        <button
          type="button"
          className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left text-sm text-muted hover:bg-white/70 hover:text-ink"
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
          className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left text-xs text-muted/70 no-underline hover:bg-white/70 hover:text-ink"
        >
          <Heart className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          <span>{t("nav.feedback")}</span>
        </a>
      </div>
    </nav>
  );
}

type SidebarEntry = {
  href: string;
  label: string;
  icon: LucideIcon;
};

function SidebarItem({
  path,
  item,
  onNavigate,
  badge,
  compact,
}: {
  path: string;
  item: SidebarEntry;
  onNavigate: (href: string) => void;
  badge?: string;
  compact?: boolean;
}) {
  const active = path === item.href || (item.href !== "/" && path.startsWith(item.href));
  const Icon = item.icon;

  return (
    <button
      type="button"
      onClick={() => onNavigate(item.href)}
      className={cx(
        "group relative flex w-full items-center gap-3 rounded-2xl px-3 text-left text-sm transition-all",
        compact ? "py-2" : "py-2.5",
        active
          ? "bg-white font-bold text-ink shadow-sm ring-1 ring-black/5"
          : "text-muted hover:bg-white/70 hover:text-ink",
      )}
      style={active ? { boxShadow: "0 12px 28px rgba(17, 26, 58, 0.07)" } : undefined}
    >
      {active ? (
        <span
          className="absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full"
          style={{ background: "var(--mf-accent)" }}
          aria-hidden="true"
        />
      ) : null}
      <Icon
        className="h-4 w-4 shrink-0 transition-colors"
        style={{ color: active ? "var(--mf-accent)" : "var(--mf-text-tertiary)" }}
        aria-hidden={true}
      />
      <span className="min-w-0 flex-1 truncate">{item.label}</span>
      {badge ? (
        <span
          className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide"
          style={{
            background: active ? "var(--mf-accent-soft)" : "rgba(255,255,255,0.72)",
            color: active ? "var(--mf-accent)" : "var(--mf-text-tertiary)",
          }}
        >
          {badge}
        </span>
      ) : null}
    </button>
  );
}
