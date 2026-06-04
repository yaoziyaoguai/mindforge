import { describe, expect, it, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { LocaleProvider } from "../../lib/i18n";
import { Sidebar } from "../Sidebar";

function renderWithLocale(ui: React.ReactElement) {
  return render(<LocaleProvider>{ui}</LocaleProvider>);
}

describe("Sidebar", () => {
  beforeEach(() => {
    vi.stubGlobal("localStorage", {
      getItem: () => "en",
      setItem: vi.fn(),
    });
  });

  it("shows first-run model setup guidance without promoting lab features", () => {
    renderWithLocale(<Sidebar path="/" onNavigate={vi.fn()} providerState="blocked" />);

    expect(screen.getByText("MindForge")).toBeInTheDocument();
    expect(screen.getByText("Demo Mode")).toBeInTheDocument();
    expect(screen.getByText(/Demo Mode Active/)).toBeInTheDocument();
    expect(screen.getByText("Local Workspace")).toBeInTheDocument();
    expect(screen.queryByText("Knowledge Graph")).not.toBeInTheDocument();
  });
});
