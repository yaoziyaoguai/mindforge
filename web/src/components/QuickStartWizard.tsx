import { useState } from "react";
import { CheckCircle, Lightbulb, Loader2, Play, Sparkles } from "lucide-react";
import { useLocale } from "../lib/i18n";

type WizardStep = "welcome" | "creating" | "done" | "error";

interface QuickStartWizardProps {
  onNavigate: (href: string) => void;
}

export function QuickStartWizard({ onNavigate }: QuickStartWizardProps) {
  const { t } = useLocale();
  const [step, setStep] = useState<WizardStep>("welcome");
  const [errorMsg, setErrorMsg] = useState("");

  const handleCreate = async () => {
    setStep("creating");
    try {
      const resp = await fetch("/api/sample-workspace", { method: "POST" });
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error((body as { detail?: string }).detail || `HTTP ${resp.status}`);
      }
      setStep("done");
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Unknown error");
      setStep("error");
    }
  };

  if (step === "done") {
    return (
      <section
        className="rounded-lg border-2 p-6 text-center"
        style={{
          borderColor: "var(--mf-success)40",
          background: `linear-gradient(to bottom, var(--mf-success)08, var(--mf-surface))`,
        }}
      >
        <CheckCircle className="mx-auto h-10 w-10 mb-3" style={{ color: "var(--mf-success)" }} aria-hidden="true" />
        <h2 className="text-lg font-semibold text-ink">{t("onboarding.wizard.done_title")}</h2>
        <p className="mt-2 text-sm text-muted max-w-md mx-auto">{t("onboarding.wizard.done_desc")}</p>
        <div className="mt-4 flex justify-center gap-3">
          <button
            className="inline-flex items-center gap-1.5 rounded-md px-4 py-2 text-sm font-medium text-white transition"
            style={{ background: "var(--mf-accent)" }}
            onClick={() => onNavigate("/library")}
            type="button"
          >
            {t("onboarding.wizard.view_library")} →
          </button>
          <button
            className="inline-flex items-center gap-1.5 rounded-md border border-line px-4 py-2 text-sm font-medium text-ink transition hover:bg-muted"
            onClick={() => onNavigate("/drafts")}
            type="button"
          >
            {t("onboarding.wizard.view_review")} →
          </button>
        </div>
      </section>
    );
  }

  if (step === "error") {
    return (
      <section
        className="rounded-lg border-2 border-red-200 p-6 text-center"
        style={{ background: "linear-gradient(to bottom, #fef2f2, var(--mf-surface))" }}
      >
        <div className="text-red-500 text-sm mb-2">{t("onboarding.wizard.error_title")}</div>
        <p className="text-xs text-muted mb-3">{errorMsg}</p>
        <button
          className="inline-flex items-center gap-1.5 rounded-md border border-line px-3 py-1.5 text-sm font-medium text-ink transition hover:bg-muted"
          onClick={() => { setStep("welcome"); setErrorMsg(""); }}
          type="button"
        >
          {t("onboarding.wizard.retry")}
        </button>
      </section>
    );
  }

  return (
    <section
      className="rounded-lg border-2 p-6"
      style={{
        borderColor: "var(--mf-accent)30",
        background: `linear-gradient(to bottom, var(--mf-accent)08, var(--mf-surface))`,
      }}
    >
      <div className="text-center mb-6">
        <div className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium mb-3"
          style={{ borderColor: "var(--mf-accent)30", color: "var(--mf-accent)" }}>
          <Sparkles className="h-3 w-3" aria-hidden="true" />
          {t("onboarding.wizard.demo_badge")}
        </div>
        <h2 className="text-xl font-semibold text-ink">{t("onboarding.wizard.welcome_title")}</h2>
        <p className="mt-2 text-sm text-muted max-w-lg mx-auto">{t("onboarding.wizard.welcome_desc")}</p>
      </div>

      {/* Step indicators */}
      <div className="flex items-center justify-center gap-2 mb-5">
        {[1, 2, 3].map((n) => (
          <div key={n} className="flex items-center gap-2">
            <div
              className="flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold"
              style={{
                background: n === 1 ? "var(--mf-accent)15" : "var(--mf-surface)",
                color: n === 1 ? "var(--mf-accent)" : "var(--mf-muted)",
                border: `1px solid ${n === 1 ? "var(--mf-accent)30" : "var(--mf-border)"}`,
              }}
            >
              {n}
            </div>
            <span className="text-xs text-muted">{t(`onboarding.wizard.step${n}`)}</span>
            {n < 3 && <div className="w-6 h-px" style={{ background: "var(--mf-border)" }} />}
          </div>
        ))}
      </div>

      {/* Step 1 content */}
      <div className="rounded-md border border-line bg-white p-4 mb-4">
        <div className="flex gap-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full" style={{ background: "var(--mf-accent)15" }}>
            <Lightbulb className="h-4 w-4" style={{ color: "var(--mf-accent)" }} aria-hidden="true" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-ink">{t("onboarding.wizard.step1_title")}</h3>
            <p className="mt-1 text-xs text-muted leading-relaxed">{t("onboarding.wizard.step1_desc")}</p>
          </div>
        </div>
      </div>

      {/* Step 2: Create sample workspace button */}
      <div className="rounded-md border p-4 mb-4"
        style={{ borderColor: "var(--mf-accent)20", background: "var(--mf-accent)04" }}>
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full" style={{ background: "var(--mf-accent)" }}>
            <Play className="h-4 w-4 text-white" aria-hidden="true" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-ink">{t("onboarding.wizard.step2_title")}</h3>
            <p className="mt-1 text-xs text-muted leading-relaxed">{t("onboarding.wizard.step2_desc")}</p>
          </div>
          <button
            className="shrink-0 inline-flex items-center gap-1.5 rounded-md px-4 py-2 text-sm font-medium text-white transition disabled:opacity-50"
            style={{ background: "var(--mf-accent)" }}
            onClick={handleCreate}
            disabled={step === "creating"}
            type="button"
          >
            {step === "creating" ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                {t("onboarding.wizard.creating")}
              </>
            ) : (
              <>
                <Play className="h-4 w-4" aria-hidden="true" />
                {t("onboarding.wizard.create_btn")}
              </>
            )}
          </button>
        </div>
      </div>

      {/* Step 3 preview */}
      <div className="rounded-md border border-line bg-white p-4">
        <div className="flex gap-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full" style={{ background: "var(--mf-muted)" }}>
            <CheckCircle className="h-4 w-4 text-muted" aria-hidden="true" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-ink">{t("onboarding.wizard.step3_title")}</h3>
            <p className="mt-1 text-xs text-muted leading-relaxed">{t("onboarding.wizard.step3_desc")}</p>
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-md bg-amber-50 border border-amber-200 p-3 text-xs text-muted leading-relaxed">
        {t("onboarding.wizard.safety_note")}
      </div>
    </section>
  );
}
