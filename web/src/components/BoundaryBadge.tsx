import { cx } from "../lib/utils";
import { useLocale } from "../lib/i18n";

/**
 * MindForge Boundary Badge -- calm semantic chip
 *
 * Visual direction: low-saturation neutral background + thin border + readable size.
 * Reads like metadata on a knowledge card, not a Jira ticket label or AWS resource tag.
 *
 * Invariants protected:
 * 1. Sandbox vs Live: clear whether LLM calls are real
 * 2. Source vs Provider: distinguish data origin from processing capability
 * 3. Staging vs Production: distinguish pre-export review from real write
 */

export type BoundaryType = "sandbox" | "live" | "source" | "provider" | "staging";

interface BoundaryBadgeProps {
  type: BoundaryType;
  className?: string;
}

export function BoundaryBadge({ type, className }: BoundaryBadgeProps) {
  const { t } = useLocale();

  /* Only live badge uses a warm tone to signal real mode.
   * The other four share a neutral chip -- their semantic differences
   * are expressed through the label text, not 5 different colors. */
  const isLive = type === "live";

  return (
    <span
      className={cx(
        "inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-medium",
        isLive
          ? "bg-amber-50/60 text-amber-700 border border-amber-200/60"
          : "bg-stone-100/70 text-stone-500 border border-stone-200/60",
        className,
      )}
    >
      {t(`boundary.${type}`)}
    </span>
  );
}
