/**
 * WikiPage tests — Topic Browser (v0.5).
 *
 * Verifies the runtime Topic View replaces deprecated LLM Wiki synthesis.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { LocaleProvider } from "../../lib/i18n";
import { WikiPage } from "../WikiPage";

function renderWithLocale(ui: React.ReactElement) {
  return render(<LocaleProvider>{ui}</LocaleProvider>);
}

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

function mockTopicsResponse(topics: string[]) {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ topics }),
  });
}

function mockTopicDetailResponse(data: Record<string, unknown>) {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: async () => data,
  });
}

function mockFetchError(status: number, detail: string) {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    status,
    json: async () => ({ detail }),
  });
}

beforeEach(() => {
  mockFetch.mockReset();
});

describe("WikiPage / TopicBrowser", () => {
  it("shows loading state initially", () => {
    mockFetch.mockImplementation(() => new Promise(() => {})); // never resolves
    renderWithLocale(<WikiPage />);
    expect(screen.getByText(/加载/i)).toBeTruthy();
  });

  it("renders topic list from API", async () => {
    mockTopicsResponse(["Python", "React", "TypeScript"]);
    renderWithLocale(<WikiPage />);

    await waitFor(() => {
      expect(screen.getByText("Python")).toBeTruthy();
    });
    expect(screen.getByText("React")).toBeTruthy();
    expect(screen.getByText("TypeScript")).toBeTruthy();
  });

  it("shows empty state when no topics", async () => {
    mockTopicsResponse([]);
    renderWithLocale(<WikiPage />);

    await waitFor(() => {
      expect(screen.getByText(/暂无主题/)).toBeTruthy();
    });
  });

  it("shows select prompt before topic chosen", async () => {
    mockTopicsResponse(["Python"]);
    renderWithLocale(<WikiPage />);

    await waitFor(() => {
      expect(screen.getByText("Python")).toBeTruthy();
    });
    expect(screen.getByText(/选择一个主题/)).toBeTruthy();
  });

  it("loads and displays topic detail on selection", async () => {
    mockTopicsResponse(["Python"]);
    mockTopicDetailResponse({
      topic: "Python",
      total_approved_cards: 2,
      type_counts: { concept: 1, claim: 1 },
      cards: [
        {
          id: "card-1",
          title: "Python Decorators",
          knowledge_type: "concept",
          relations: [],
          tags: ["python", "decorators"],
          summary: "Python decorators are a powerful pattern for modifying functions.",
          human_note: null,
          approval_state: "human_approved",
          value_score: 5,
          source_title: "Python Docs",
          source_type: "web_page",
          track: "Python",
          created_at: "2026-05-10T00:00:00",
          approved_at: "2026-06-01T12:00:00",
        },
        {
          id: "card-2",
          title: "GIL in Python",
          knowledge_type: "claim",
          relations: [{ type: "supports", target_id: "card-1" }],
          tags: ["python", "concurrency"],
          summary: "The Global Interpreter Lock limits Python thread parallelism.",
          human_note: "Approved with minor edits",
          approval_state: "human_approved",
          value_score: 4,
          source_title: null,
          source_type: null,
          track: "Python",
          created_at: null,
          approved_at: "2026-06-02T10:00:00",
        },
      ],
    });

    renderWithLocale(<WikiPage />);

    await waitFor(() => {
      expect(screen.getByText("Python")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Python"));

    await waitFor(() => {
      expect(screen.getByText("Python Decorators")).toBeTruthy();
    });
    expect(screen.getByText("GIL in Python")).toBeTruthy();
    expect(screen.getByText(/2\s*(张已确认卡片|approved cards)/)).toBeTruthy();
  });

  it("shows deprecation notice for LLM Wiki synthesis", async () => {
    mockTopicsResponse(["Python"]);
    renderWithLocale(<WikiPage />);

    await waitFor(() => {
      expect(screen.getByText(/v0\.5/)).toBeTruthy();
    });
  });

  it("shows approval boundary notice in topic view", async () => {
    mockTopicsResponse(["Python"]);
    mockTopicDetailResponse({
      topic: "Python",
      total_approved_cards: 1,
      type_counts: { concept: 1 },
      cards: [
        {
          id: "card-1",
          title: "Test Card",
          knowledge_type: "concept",
          relations: [],
          tags: [],
          summary: "Test summary",
          human_note: null,
          approval_state: "human_approved",
          value_score: null,
          source_title: null,
          source_type: null,
          track: "Python",
          created_at: null,
          approved_at: null,
        },
      ],
    });

    renderWithLocale(<WikiPage />);

    await waitFor(() => {
      expect(screen.getByText("Python")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Python"));

    await waitFor(() => {
      expect(screen.getByText(/human_approved/)).toBeTruthy();
    });
  });

  it("shows human note when present", async () => {
    mockTopicsResponse(["Python"]);
    mockTopicDetailResponse({
      topic: "Python",
      total_approved_cards: 1,
      type_counts: { concept: 1 },
      cards: [
        {
          id: "card-1",
          title: "Test Card",
          knowledge_type: "concept",
          relations: [],
          tags: [],
          summary: "Test summary",
          human_note: "Needs further review",
          approval_state: "human_approved",
          value_score: null,
          source_title: null,
          source_type: null,
          track: "Python",
          created_at: null,
          approved_at: null,
        },
      ],
    });

    renderWithLocale(<WikiPage />);

    await waitFor(() => {
      expect(screen.getByText("Python")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Python"));

    await waitFor(() => {
      expect(screen.getByText("Needs further review")).toBeTruthy();
    });
  });

  it("shows relations in context panel when card selected", async () => {
    mockTopicsResponse(["React"]);
    mockTopicDetailResponse({
      topic: "React",
      total_approved_cards: 1,
      type_counts: { concept: 1 },
      cards: [
        {
          id: "card-1",
          title: "React Hooks",
          knowledge_type: "concept",
          relations: [
            { type: "supports", target_id: "card-2" },
            { type: "related_to", target_id: "card-3" },
          ],
          tags: [],
          summary: "React hooks summary",
          human_note: null,
          approval_state: "human_approved",
          value_score: null,
          source_title: null,
          source_type: null,
          track: "React",
          created_at: null,
          approved_at: null,
        },
      ],
    });

    renderWithLocale(<WikiPage />);

    await waitFor(() => {
      expect(screen.getByText("React")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("React"));

    await waitFor(() => {
      expect(screen.getByText("React Hooks")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("React Hooks"));

    await waitFor(() => {
      expect(screen.getByText("supports")).toBeTruthy();
      expect(screen.getByText("card-2")).toBeTruthy();
      expect(screen.getByText("related_to")).toBeTruthy();
    });
  });

  it("shows error state when API fails", async () => {
    mockFetchError(500, "Internal Server Error");
    renderWithLocale(<WikiPage />);

    await waitFor(() => {
      expect(screen.getByText(/加载主题列表失败/)).toBeTruthy();
    });
  });

  it("shows error when topic detail fails", async () => {
    mockTopicsResponse(["Python"]);
    mockFetchError(404, "Topic 'Python' not found");

    renderWithLocale(<WikiPage />);

    await waitFor(() => {
      expect(screen.getByText("Python")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Python"));

    await waitFor(() => {
      expect(screen.getByText(/加载主题.*失败/)).toBeTruthy();
    });
  });

  it("does not contain Generate Wiki button", async () => {
    mockTopicsResponse(["Python"]);
    renderWithLocale(<WikiPage />);

    await waitFor(() => {
      expect(screen.getByText("Python")).toBeTruthy();
    });

    // Verify no button calls to action for Generate Wiki
    expect(
      screen.queryByRole("button", { name: /Generate Wiki/i }),
    ).toBeNull();
    expect(
      screen.queryByRole("button", { name: /生成 Wiki/i }),
    ).toBeNull();
  });
});
