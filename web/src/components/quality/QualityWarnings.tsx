/** M1 QualityWarnings — SDD §5.3, RFC §7 FR1.3 */

import type { QualityWarning } from "../../api/quality";

interface QualityWarningsProps {
  warnings: QualityWarning[];
}

const SEVERITY_ICONS: Record<string, string> = {
  critical: "⚠️",
  warn: "⚡",
  info: "ℹ️",
};

export function QualityWarnings({ warnings }: QualityWarningsProps) {
  if (!warnings.length) return null;

  return (
    <div className="space-y-1.5">
      <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide">
        质量提醒
      </h4>
      <ul className="space-y-1">
        {warnings.map((w) => (
          <li
            key={w.code}
            className="flex items-start gap-2 text-xs text-gray-600 bg-gray-50 border border-gray-100 rounded px-2.5 py-1.5"
            title={w.suggestion || w.message}
          >
            <span className="mt-px shrink-0">{SEVERITY_ICONS[w.severity] ?? "•"}</span>
            <span>{w.message}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
