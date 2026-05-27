import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { LoadingSkeleton } from "../LoadingSkeleton";

describe("LoadingSkeleton", () => {
  it("renders the default variant", () => {
    const { container } = render(<LoadingSkeleton />);
    const root = container.firstElementChild as HTMLElement;
    expect(root.className).toContain("animate-pulse");
  });

  const variants = [
    "default",
    "wiki",
    "library",
    "drafts",
    "search",
    "sources",
    "health",
    "trash",
    "setup",
    "dogfood",
  ] as const;

  it.each(variants)("renders variant %s without error", (variant) => {
    const { container } = render(<LoadingSkeleton variant={variant} />);
    const root = container.firstElementChild as HTMLElement;
    expect(root.className).toContain("animate-pulse");
  });
});
