import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { LocaleProvider } from "../../lib/i18n";
import { HomePage } from "../HomePage";
import type { HomeStatusResponse, WorkflowSummaryResponse } from "../../api/types";

function renderWithLocale(ui: React.ReactElement) {
  return render(<LocaleProvider>{ui}</LocaleProvider>);
}

const homeStatus: HomeStatusResponse = {
  safety: {
    local_only: true,
    host: "127.0.0.1",
    vault_path: "/tmp/mindforge-vault",
    vault_status: "ok",
    provider_state: "blocked",
    env_status: "ok",
    write_mode: "explicit_approval_required",
    pending_drafts_count: 0,
    warnings: [],
  },
  workspace: {
    config_path: "/tmp/mindforge.yaml",
    state_path: "/tmp/state.json",
    state_exists: false,
    state_item_count: 0,
    source_counts: {},
    status_counts: {},
  },
  vault: {
    path: "/tmp/mindforge-vault",
    exists: true,
    inbox_exists: true,
    cards_exists: true,
    projects_exists: true,
    approved_card_count: 0,
    draft_card_count: 0,
    scan_error_count: 0,
    is_real_environment: false,
  },
  provider: {
    active_profile: "fake",
    opt_in_state: "fake_default",
    model_setup: "needs_setup",
    model_setup_label: "Needs setup",
    can_run_real_smoke: false,
    provider_mode: "fake",
    aliases: [],
    blockers: [],
  },
  env_keys: [],
  recall: {
    index_path: "/tmp/index.jsonl",
    index_exists: false,
    approved_card_count: 0,
    available: false,
  },
  cards_by_status: {},
  next_actions: [],
};

const workflow: WorkflowSummaryResponse = {
  vault_root: "/tmp/mindforge-vault",
  cards_dir: "20-Knowledge-Cards",
  inbox_pending_count: 0,
  processed_source_count: 0,
  ai_draft_count: 0,
  human_approved_count: 0,
  index: homeStatus.recall,
  provider: homeStatus.provider,
  source_bucket_counts: {},
  next_actions: [],
};

describe("HomePage", () => {
  beforeEach(() => {
    vi.stubGlobal("localStorage", {
      getItem: () => "en",
      setItem: vi.fn(),
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        json: () => Promise.resolve({}),
      }),
    );
  });

  it("keeps configure real model and knowledge flow visible on first run", () => {
    renderWithLocale(<HomePage data={homeStatus} workflow={workflow} onNavigate={vi.fn()} />);

    expect(screen.getAllByRole("button", { name: /Configure Real Model/i }).length).toBeGreaterThan(0);
    expect(screen.getByText("Knowledge Flow")).toBeInTheDocument();
    expect(screen.getByText("Sources")).toBeInTheDocument();
    expect(screen.getByText("AI Drafts")).toBeInTheDocument();
    expect(screen.getByText("Ready for Review")).toBeInTheDocument();
    expect(screen.getAllByText("Approved Knowledge").length).toBeGreaterThan(0);
  });
});
