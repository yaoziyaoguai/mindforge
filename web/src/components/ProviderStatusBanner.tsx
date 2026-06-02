import { ArrowRight, ShieldCheck } from "lucide-react";
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

  if (isReady) return null; // In the new design, we don't show the banner if it's already Live/Ready. It's implicit.

  return (
    <div
      className="flex items-center gap-4 rounded-xl border p-4 shadow-sm"
      style={{
        background: "rgba(45,125,95,0.03)",
        borderColor: "rgba(45,125,95,0.1)"
      }}
    >
      <div className="flex flex-1 items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-md" style={{ background: "rgba(45,125,95,0.1)" }}>
          <ShieldCheck className="h-4 w-4" style={{ color: "var(--mf-accent)" }} />
        </div>
        <div>
          <div className="text-sm font-semibold text-ink">You are in Demo Mode</div>
          <div className="text-xs text-muted">AI outputs are simulated. Configure a real provider to generate real content.</div>
        </div>
      </div>
      <button
        onClick={() => onNavigate("/setup")}
        className="ml-2 inline-flex shrink-0 items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-medium text-white transition-opacity hover:opacity-90"
        style={{ background: "var(--mf-accent)" }}
      >
        Configure Real Model <ArrowRight className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
