import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { LocaleProvider } from "../../lib/i18n";
import { CollectionPanel } from "../CollectionPanel";

vi.mock("../../api/library", () => ({
  getCollections: vi.fn().mockResolvedValue({ collections: [] }),
  createCollection: vi.fn().mockResolvedValue({ collection: { id: "test", name: "Test" } }),
  deleteCollection: vi.fn().mockResolvedValue({ ok: true }),
  addToCollection: vi.fn().mockResolvedValue({ ok: true }),
  removeFromCollection: vi.fn().mockResolvedValue({ ok: true }),
}));

function renderWithLocale(ui: React.ReactElement) {
  return render(<LocaleProvider>{ui}</LocaleProvider>);
}

describe("CollectionPanel", () => {
  it("renders collections title", async () => {
    renderWithLocale(<CollectionPanel selectedCardRefs={[]} />);
    await waitFor(() => {
      expect(screen.getByText("卡片集合")).toBeInTheDocument();
    });
  });

  it("shows empty state when no collections", async () => {
    renderWithLocale(<CollectionPanel selectedCardRefs={[]} />);
    await waitFor(() => {
      expect(screen.getByText("暂无已创建集合")).toBeInTheDocument();
    });
  });

  it("shows create button", async () => {
    renderWithLocale(<CollectionPanel selectedCardRefs={[]} />);
    await waitFor(() => {
      expect(screen.getByText("新建集合")).toBeInTheDocument();
    });
  });

  it("renders folder icon", async () => {
    const { container } = renderWithLocale(<CollectionPanel selectedCardRefs={[]} />);
    await waitFor(() => {
      expect(container.querySelector("svg")).toBeTruthy();
    });
  });
});
