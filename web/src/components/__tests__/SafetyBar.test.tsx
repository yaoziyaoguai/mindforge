import { describe, expect, it, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { LocaleProvider } from "../../lib/i18n";
import { SafetyBar } from "../SafetyBar";
import type { SafetySummary } from "../../api/types";

function renderWithLocale(ui: React.ReactElement) {
  return render(<LocaleProvider>{ui}</LocaleProvider>);
}

const baseSafety: SafetySummary = {
  local_only: true,
  host: "http://127.0.0.1:8765",
  vault_path: "/Users/test/mindforge-vault",
  vault_status: "ok",
  provider_state: "ready",
  env_status: "ok",
  write_mode: "explicit_approval_required",
  pending_drafts_count: 3,
  warnings: [],
};

describe("SafetyBar", () => {
  beforeEach(() => {
    vi.stubGlobal("localStorage", {
      getItem: () => "en",
      setItem: vi.fn(),
    });
  });

  it("renders loading text when safety is missing", () => {
    renderWithLocale(<SafetyBar safety={null} />);
    expect(screen.getByText("Loading safety state...")).toBeInTheDocument();
  });

  it("shows calm local, provider, review, and approval status pills", () => {
    renderWithLocale(<SafetyBar safety={baseSafety} />);

    expect(screen.getByText("Local vault")).toBeInTheDocument();
    expect(screen.getByText("/Users/test/mindforge-vault")).toBeInTheDocument();
    expect(screen.getByText("Real Provider")).toBeInTheDocument();
    expect(screen.getByText("Needs review:")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("Safe local read")).toBeInTheDocument();
    expect(screen.getByText("Explicit approval required")).toBeInTheDocument();
  });

  it("shows demo provider as a setup action without noisy warning bars", () => {
    const onNavigate = vi.fn();
    renderWithLocale(<SafetyBar safety={{ ...baseSafety, provider_state: "blocked" }} onNavigate={onNavigate} />);

    screen.getByRole("button", { name: /Demo Mode/i }).click();
    expect(onNavigate).toHaveBeenCalledWith("/setup");
  });

  it("shows the first warning as a muted note", () => {
    renderWithLocale(<SafetyBar safety={{ ...baseSafety, warnings: ["Wiki may be stale"] }} />);

    expect(screen.getByText("Note")).toBeInTheDocument();
    expect(screen.getByText("Wiki may be stale")).toBeInTheDocument();
    expect(screen.queryByText("Safe local read")).not.toBeInTheDocument();
  });
});
