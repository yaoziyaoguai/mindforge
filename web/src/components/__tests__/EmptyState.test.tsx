import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { EmptyState } from "../EmptyState";
import type { NextAction } from "../../api/types";

describe("EmptyState", () => {
  it("renders the title", () => {
    render(<EmptyState title="还没有知识卡片" />);
    expect(screen.getByText("还没有知识卡片")).toBeInTheDocument();
  });

  it("renders action label and description when action is provided", () => {
    const action: NextAction = {
      label: "添加知识源",
      description: "导入 Markdown 或粘贴内容开始构建知识库",
      href: "/sources",
    };
    render(<EmptyState title="空工作区" action={action} />);
    expect(screen.getByText("添加知识源")).toBeInTheDocument();
    expect(screen.getByText("导入 Markdown 或粘贴内容开始构建知识库")).toBeInTheDocument();
  });

  it("renders command as code element when action.command is set", () => {
    const action: NextAction = {
      label: "运行命令",
      description: "用 CLI 初始化",
      command: "mindforge init",
    };
    render(<EmptyState title="初始化" action={action} />);
    expect(screen.getByText("mindforge init")).toBeInTheDocument();
    expect(screen.getByText("mindforge init").tagName).toBe("CODE");
  });

  it("renders a link when action.href is set", () => {
    const action: NextAction = {
      label: "前往设置",
      description: "配置模型和 API",
      href: "/setup",
    };
    render(<EmptyState title="未配置" action={action} />);
    const link = screen.getByText("前往设置");
    expect(link.tagName).toBe("A");
    expect(link).toHaveAttribute("href", "/setup");
  });

  it("renders a button when action.onClick is set (no href)", () => {
    const action: NextAction = {
      label: "点击开始",
      description: "启动导入流程",
      onClick: () => {},
    };
    render(<EmptyState title="准备就绪" action={action} />);
    const button = screen.getByText("点击开始");
    expect(button.tagName).toBe("BUTTON");
  });

  it("does not render action elements when no action", () => {
    render(<EmptyState title="仅标题" />);
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
  });
});
