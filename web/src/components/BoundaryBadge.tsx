import { cx } from "../lib/utils";
import { useLocale } from "../lib/i18n";

/**
 * MindForge Boundary Badge
 * 
 * 中文学习型说明：
 * 此组件用于明确表达产品边界（Boundary Clarity）。
 * 它保护以下不变量：
 * 1. Sandbox vs Live：明确 LLM 调用是否为真实扣费/联网。
 * 2. Source vs Provider：区分“资料来源”与“加工能力”。
 * 3. Staging vs Production：明确“导出预审”与“正式写入”。
 */

export type BoundaryType = "sandbox" | "live" | "source" | "provider" | "staging";

interface BoundaryBadgeProps {
  type: BoundaryType;
  className?: string;
}

export function BoundaryBadge({ type, className }: BoundaryBadgeProps) {
  const { t } = useLocale();
  
  const config: Record<BoundaryType, { label: string; style: string }> = {
    sandbox: {
      label: t("boundary.sandbox"),
      style: "bg-stone-100 text-stone-600 border-stone-200",
    },
    live: {
      label: t("boundary.live"),
      style: "bg-amber-100 text-amber-800 border-amber-200",
    },
    source: {
      label: t("boundary.source"),
      style: "bg-blue-50 text-blue-700 border-blue-100",
    },
    provider: {
      label: t("boundary.provider"),
      style: "bg-purple-50 text-purple-700 border-purple-100",
    },
    staging: {
      label: t("boundary.staging"),
      style: "bg-green-50 text-green-700 border-green-100",
    },
  };

  const { label, style } = config[type];

  return (
    <span className={cx(
      "inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-tight",
      style,
      className
    )}>
      {label}
    </span>
  );
}
