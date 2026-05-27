import { describe, expect, it } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { LocaleProvider } from "../../lib/i18n";
import { OnboardingHint } from "../OnboardingHint";

function renderWithLocale(ui: React.ReactElement) {
  return render(<LocaleProvider>{ui}</LocaleProvider>);
}

describe("OnboardingHint", () => {
  it("renders hint text for a known page key", () => {
    renderWithLocale(<OnboardingHint pageKey="home" />);
    // zh key: "onboarding.hint.home" → "欢迎！这是你的知识全景页面..."
    expect(screen.getByText(/知识全景页面/)).toBeInTheDocument();
  });

  it("renders dismiss button with aria-label", () => {
    renderWithLocale(<OnboardingHint pageKey="home" />);
    const dismissBtn = screen.getByRole("button");
    expect(dismissBtn).toBeInTheDocument();
    // zh key: "onboarding.hint.dismiss" → "关闭"
    expect(dismissBtn.getAttribute("aria-label")).toBe("关闭");
  });

  it("hides after dismiss button click", () => {
    renderWithLocale(<OnboardingHint pageKey="home" />);
    const dismissBtn = screen.getByRole("button");
    fireEvent.click(dismissBtn);
    expect(screen.queryByText(/知识全景页面/)).toBeNull();
  });

  it("returns null for unknown page key (no i18n text)", () => {
    const { container } = renderWithLocale(<OnboardingHint pageKey="unknown_page" />);
    expect(container.firstChild).toBeNull();
  });

  it("renders Lightbulb icon", () => {
    const { container } = renderWithLocale(<OnboardingHint pageKey="library" />);
    const svgs = container.querySelectorAll("svg");
    expect(svgs.length).toBeGreaterThanOrEqual(1);
  });

  it("renders hint for setup page", () => {
    renderWithLocale(<OnboardingHint pageKey="setup" />);
    expect(screen.getByText(/演示模式/)).toBeInTheDocument();
  });
});
