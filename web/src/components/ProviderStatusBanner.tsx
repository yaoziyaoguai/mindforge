import { ArrowRight, CheckCircle2, FlaskConical, ShieldCheck } from "lucide-react";
import { useLocale } from "../lib/i18n";

/**
 * ProviderStatusBanner — 跨页面 provider 状态指示器
 *
 * 中文学习型说明：
 * 此组件保护 fake/real provider 边界可见性。
 * 为什么 first-run 用户必须看得懂真实模型配置：
 * 本地知识库的灵魂是拥有真实的知识处理能力。Demo模式仅仅是沙盒，必须让用户一眼看到并明白如何配置真实的 LLM。
 * 为什么 fake/real 不能混：fake provider 产生的数据是模拟的，不应与真实用户的思考混淆。
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
      className="mf-card-soft flex flex-col gap-4 p-5 md:flex-row md:items-center md:justify-between"
      style={{
        background: isReady
          ? "linear-gradient(135deg, rgba(50, 103, 214, 0.05), rgba(255,255,255,0.96))"
          : undefined,
      }}
    >
      <div className="flex flex-1 items-center gap-3">
        <div
          className="flex h-10 w-10 items-center justify-center rounded-2xl"
          style={{ background: isReady ? "rgba(50, 103, 214, 0.1)" : "var(--mf-accent-soft)" }}
        >
          {isReady ? (
            <ShieldCheck className="h-5 w-5" style={{ color: "var(--mf-info)" }} aria-hidden="true" />
          ) : (
            <FlaskConical className="h-5 w-5" style={{ color: "var(--mf-accent)" }} aria-hidden="true" />
          )}
        </div>
        <div>
          <div className="flex flex-wrap items-center gap-2 text-sm font-bold text-ink">
            {isReady ? t("provider_banner.real_title") : t("provider_banner.demo_title")}
            <span className={isReady ? "mf-chip !px-2 !py-1 !text-[11px]" : "mf-chip mf-chip-accent !px-2 !py-1 !text-[11px]"} style={isReady ? { background: "rgba(50, 103, 214, 0.1)", color: "var(--mf-info)" } : {}}>
              <ShieldCheck className="h-3 w-3" aria-hidden="true" />
              {isReady ? t("provider_banner.real_chip") : t("provider_banner.demo_chip")}
            </span>
          </div>
          <div className="mt-1 text-xs leading-relaxed text-muted">
            {isReady ? t("provider_banner.real_desc") : t("provider_banner.demo_desc")}
          </div>
        </div>
      </div>
      <button
        onClick={() => onNavigate("/setup")}
        className={isReady ? "mf-secondary-button shrink-0 px-4 py-2 text-xs" : "mf-primary-button shrink-0 px-4 py-2 text-xs"}
        type="button"
      >
        {isReady ? t("provider_banner.manage") : t("provider_banner.configure")}
        <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
      </button>
    </div>
  );
}
