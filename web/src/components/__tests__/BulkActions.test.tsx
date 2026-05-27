import { describe, expect, it } from "vitest";
import { act, render, screen } from "@testing-library/react";
import { LocaleProvider } from "../../lib/i18n";
import { BulkActions } from "../BulkActions";

function renderWithLocale(ui: React.ReactElement) {
  return render(<LocaleProvider>{ui}</LocaleProvider>);
}

describe("BulkActions", () => {
  it("returns null when selectedRefs is empty", () => {
    const { container } = renderWithLocale(
      <BulkActions selectedRefs={[]} onClearSelection={() => {}} onApplied={() => {}} />
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders select count with correct number", () => {
    renderWithLocale(
      <BulkActions selectedRefs={["card-1", "card-2", "card-3"]} onClearSelection={() => {}} onApplied={() => {}} />
    );
    expect(screen.getByText("已选 3 张")).toBeInTheDocument();
  });

  it("renders set tags button", () => {
    renderWithLocale(
      <BulkActions selectedRefs={["card-1"]} onClearSelection={() => {}} onApplied={() => {}} />
    );
    expect(screen.getByText("设置标签")).toBeInTheDocument();
  });

  it("renders set track button", () => {
    renderWithLocale(
      <BulkActions selectedRefs={["card-1"]} onClearSelection={() => {}} onApplied={() => {}} />
    );
    expect(screen.getByText("设置 Track")).toBeInTheDocument();
  });

  it("renders exit button", () => {
    renderWithLocale(
      <BulkActions selectedRefs={["card-1"]} onClearSelection={() => {}} onApplied={() => {}} />
    );
    expect(screen.getByText("退出多选")).toBeInTheDocument();
  });

  it("shows tags input when set tags button is clicked", () => {
    renderWithLocale(
      <BulkActions selectedRefs={["card-1"]} onClearSelection={() => {}} onApplied={() => {}} />
    );
    act(() => {
      screen.getByText("设置标签").click();
    });
    expect(screen.getByPlaceholderText("标签（逗号分隔）")).toBeInTheDocument();
  });

  it("shows track input when set track button is clicked", () => {
    renderWithLocale(
      <BulkActions selectedRefs={["card-1"]} onClearSelection={() => {}} onApplied={() => {}} />
    );
    act(() => {
      screen.getByText("设置 Track").click();
    });
    expect(screen.getByPlaceholderText("Track 名称")).toBeInTheDocument();
  });

  it("renders single count for one card", () => {
    renderWithLocale(
      <BulkActions selectedRefs={["card-1"]} onClearSelection={() => {}} onApplied={() => {}} />
    );
    expect(screen.getByText("已选 1 张")).toBeInTheDocument();
  });
});
