import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusCard } from "../StatusCard";
import type { NextAction } from "../../api/types";

describe("StatusCard", () => {
  it("renders label and value", () => {
    render(<StatusCard label="知识卡片总数" value={42} />);
    expect(screen.getByText("知识卡片总数")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders status badge", () => {
    render(<StatusCard label="状态" value={42} status="ok" />);
    // statusLabel("ok") maps to Chinese label "正常"
    const badge = screen.getByText("正常");
    expect(badge).toBeInTheDocument();
    // 确认 value "42" 也在文档中
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders detail text when provided", () => {
    render(<StatusCard label="索引" value="就绪" detail="BM25 索引已加载 80 张卡片" />);
    expect(screen.getByText("BM25 索引已加载 80 张卡片")).toBeInTheDocument();
  });

  it("renders nextAction when provided", () => {
    const nextAction: NextAction = {
      label: "重建索引",
      description: "重新构建 BM25 索引",
      action_key: "rebuild_index",
    };
    render(<StatusCard label="索引" value="过期" status="warn" nextAction={nextAction} />);
    // nextActionLabel maps action_key → Chinese label
    expect(screen.getByText("重建索引")).toBeInTheDocument();
  });

  it("renders as a button when href is set", () => {
    render(<StatusCard label="点击查看" value={10} href="/library" onNavigate={() => {}} />);
    const button = screen.getByRole("button");
    expect(button).toBeInTheDocument();
    expect(button).toHaveTextContent("点击查看");
  });

  it("renders as a section when no href", () => {
    const { container } = render(<StatusCard label="静态卡片" value={5} />);
    const section = container.querySelector("section");
    expect(section).toBeInTheDocument();
    expect(screen.getByText("静态卡片")).toBeInTheDocument();
  });
});
