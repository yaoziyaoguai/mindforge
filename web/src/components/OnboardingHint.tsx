import { useState } from "react";
import { Lightbulb, X } from "lucide-react";
import { useLocale } from "../lib/i18n";

interface OnboardingHintProps {
  pageKey: string;
}

const STORAGE_KEY_PREFIX = "mf-hint-dismissed-";

function isHintDismissed(pageKey: string): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY_PREFIX + pageKey) === "1";
  } catch {
    return false;
  }
}

export function OnboardingHint({ pageKey }: OnboardingHintProps) {
  const { t } = useLocale();
  const [dismissed, setDismissed] = useState(() => isHintDismissed(pageKey));

  if (dismissed) return null;

  const hintKey = `onboarding.hint.${pageKey}`;
  const hintText = t(hintKey);

  if (hintText === hintKey) return null;

  const handleDismiss = () => {
    setDismissed(true);
    try {
      localStorage.setItem(STORAGE_KEY_PREFIX + pageKey, "1");
    } catch {
      // localStorage may be unavailable (private browsing, quota exceeded)
    }
  };

  return (
    <div
      className="flex items-center gap-3 rounded-md border px-4 py-2.5 mb-3"
      style={{
        borderColor: "var(--mf-accent)30",
        background: "var(--mf-accent)08",
      }}
    >
      <Lightbulb
        className="h-4 w-4 shrink-0"
        style={{ color: "var(--mf-accent)" }}
        aria-hidden="true"
      />
      <span className="flex-1 text-xs leading-relaxed text-ink">{hintText}</span>
      <button
        className="shrink-0 rounded p-0.5 transition hover:bg-black/5"
        onClick={handleDismiss}
        type="button"
        aria-label={t("onboarding.hint.dismiss")}
      >
        <X className="h-3.5 w-3.5 text-muted" aria-hidden="true" />
      </button>
    </div>
  );
}
