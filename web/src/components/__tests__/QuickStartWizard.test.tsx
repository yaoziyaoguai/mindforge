import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { LocaleProvider } from "../../lib/i18n";
import { QuickStartWizard } from "../QuickStartWizard";

function renderWithLocale(ui: React.ReactElement) {
  return render(<LocaleProvider>{ui}</LocaleProvider>);
}

describe("QuickStartWizard", () => {
  it("renders welcome state with demo badge", () => {
    renderWithLocale(<QuickStartWizard onNavigate={() => {}} />);
    // "onboarding.wizard.demo_badge" → "安全演示模式"
    expect(screen.getByText("安全演示模式")).toBeInTheDocument();
  });

  it("renders welcome title", () => {
    renderWithLocale(<QuickStartWizard onNavigate={() => {}} />);
    // "onboarding.wizard.welcome_title" → "欢迎使用 MindForge"
    expect(screen.getByText("欢迎使用 MindForge")).toBeInTheDocument();
  });

  it("renders 3 step indicators", () => {
    renderWithLocale(<QuickStartWizard onNavigate={() => {}} />);
    // Step labels
    expect(screen.getByText("了解")).toBeInTheDocument();
    expect(screen.getByText("创建")).toBeInTheDocument();
    expect(screen.getByText("探索")).toBeInTheDocument();
  });

  it("renders create button", () => {
    renderWithLocale(<QuickStartWizard onNavigate={() => {}} />);
    // "onboarding.wizard.create_btn" → "创建示例工作区" (出现在 step title 和 button)
    const buttons = screen.getAllByText("创建示例工作区");
    expect(buttons.length).toBeGreaterThanOrEqual(1);
  });

  it("renders safety note", () => {
    renderWithLocale(<QuickStartWizard onNavigate={() => {}} />);
    expect(screen.getByText(/演示卡片使用本地模拟模型/)).toBeInTheDocument();
  });

  it("renders step 1, 2, 3 content", () => {
    renderWithLocale(<QuickStartWizard onNavigate={() => {}} />);
    expect(screen.getByText("了解 MindForge")).toBeInTheDocument();
    // "创建示例工作区" 同时出现在 step2 title 和 button 中，用 getAllByText
    const btns = screen.getAllByText("创建示例工作区");
    expect(btns.length).toBe(2);
    expect(screen.getByText("探索你的知识库")).toBeInTheDocument();
  });

  it("renders Sparkles icon", () => {
    const { container } = renderWithLocale(<QuickStartWizard onNavigate={() => {}} />);
    const svgs = container.querySelectorAll("svg");
    expect(svgs.length).toBeGreaterThanOrEqual(3); // Sparkles, Lightbulb, Play, CheckCircle
  });
});
