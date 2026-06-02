import { ArrowRight, ShieldCheck } from "lucide-react";
import { useLocale } from "../lib/i18n";

/**
 * ProviderStatusBanner — 跨页面 provider 状态指示器
 *
 * 中文学习型说明：
 * 此组件保护 fake/real provider 边界可见性。
 * 1. 首页和关键页面展示当前 provider mode，让用户一眼知道是否在 demo 模式。
 * 2. sandbox 模式提供前往 Setup 的 CTA，降低"不知道怎么配置真实模型"的障碍。
 * 3. live 模式只展示确认信息，不做多余引导。
 *
 * 为什么 fake/real 不能混：fake provider 输出带 [fake] 前缀，
 * 用户必须知道当前输出不是真实模型生成的，避免误用。
 */
export function ProviderStatusBanner({
  providerState,
  onNavigate,
}: {
  providerState?: string;
  onNavigate: (href: string) => void;
}) {
  const { t } = useLocale();
  const isReady = providerState === "ready";

  return (
    <div
      className="flex flex-wrap items-center justify-between gap-3 rounded-lg border px-4 py-3"
      style={{
        background: isReady
          ? "rgba(45,125,95,0.06)"
          : "rgba(204,122,0,0.04)",
        borderColor: isReady
          ? "rgba(45,125,95,0.18)"
          : "rgba(204,122,0,0.15)",
      }}
    >
      <div className="flex items-center gap-2.5 min-w-0">
        <span
          className="inline-flex h-2 w-2 shrink-0 rounded-full"
          style={{
            background: isReady ? "var(--mf-approved)" : "var(--mf-warning)",
          }}
        />
        <span
          className="text-sm"
          style={{ color: "var(--mf-text-secondary)" }}
        >
          {isReady
            ? t("home.provider_live_label")
            : t("home.provider_sandbox_label")}
        </span>
      </div>
      {!isReady && (
        <button
          type="button"
          onClick={() => onNavigate("/setup")}
          className="inline-flex items-center gap-1.5 text-sm font-medium shrink-0 transition-colors hover:opacity-80"
          style={{ color: "var(--mf-accent)" }}
        >
          {t("home.provider_configure_cta")}
          <ArrowRight className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}
