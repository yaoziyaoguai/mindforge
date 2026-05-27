import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ErrorState } from "../ErrorState";

describe("ErrorState", () => {
  it("renders the error heading and message", () => {
    render(<ErrorState message="Something went wrong" />);

    expect(
      screen.getByRole("heading", { name: "Something needs attention" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("renders with a different message", () => {
    render(<ErrorState message="Connection lost" />);

    expect(screen.getByText("Connection lost")).toBeInTheDocument();
  });
});
