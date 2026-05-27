import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { LocaleProvider } from "../../lib/i18n";
import { Breadcrumb } from "../Breadcrumb";

// 用 LocaleProvider 包裹组件，解决 useLocale() 需要 i18n context 的问题
function renderWithLocale(ui: React.ReactElement) {
  return render(<LocaleProvider>{ui}</LocaleProvider>);
}

describe("Breadcrumb", () => {
  it("returns null for root path (no segments)", () => {
    const { container } = renderWithLocale(<Breadcrumb path="/" />);
    expect(container.innerHTML).toBe("");
  });

  it("renders nav with Breadcrumb aria-label", () => {
    renderWithLocale(<Breadcrumb path="/setup" />);
    expect(screen.getByRole("navigation", { name: "Breadcrumb" })).toBeInTheDocument();
  });

  it("renders Home link with Chinese label", () => {
    renderWithLocale(<Breadcrumb path="/setup" />);
    expect(screen.getByText("首页")).toBeInTheDocument();
  });

  it("renders single segment as current page (span, not anchor)", () => {
    renderWithLocale(<Breadcrumb path="/setup" />);
    // t("nav.setup") → "连接模型" in zh locale
    const label = screen.getByText("连接模型");
    expect(label).toBeInTheDocument();
    // 当前页渲染为 span，非链接
    expect(label.tagName).toBe("SPAN");
  });

  it("renders intermediate segment as link", () => {
    renderWithLocale(<Breadcrumb path="/setup/models" />);
    // "/setup" is not the current page, should be an anchor
    const link = screen.getByText("连接模型");
    expect(link.tagName).toBe("A");
  });

  it("renders last segment as current page", () => {
    renderWithLocale(<Breadcrumb path="/setup/models" />);
    // "models" 无对应 i18n key，t() 回退返回 key 本身
    const current = screen.getByText("models");
    expect(current.tagName).toBe("SPAN");
  });

  it("falls back to segment text for unknown routes", () => {
    renderWithLocale(<Breadcrumb path="/custom/path" />);
    expect(screen.getByText("custom")).toBeInTheDocument();
    expect(screen.getByText("path")).toBeInTheDocument();
  });

  it("renders /library path correctly", () => {
    renderWithLocale(<Breadcrumb path="/library" />);
    // t("nav.library") → "知识库"
    expect(screen.getByText("知识库")).toBeInTheDocument();
  });

  it("renders /recall/search path with known recall route", () => {
    renderWithLocale(<Breadcrumb path="/recall/search" />);
    // "/recall" maps to "nav.recall" → "搜索", "/recall/search" has no routeLabel → "search"
    expect(screen.getByText("搜索")).toBeInTheDocument();
    expect(screen.getByText("search")).toBeInTheDocument();
  });
});
