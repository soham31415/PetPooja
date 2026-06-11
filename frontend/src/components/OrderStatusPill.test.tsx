import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { OrderStatusPill } from "./OrderStatusPill";

describe("OrderStatusPill", () => {
  it("renders the pending label", () => {
    render(<OrderStatusPill status="pending" />);
    expect(screen.getByText("Pending")).toBeInTheDocument();
  });

  it("renders the confirmed label", () => {
    render(<OrderStatusPill status="confirmed" />);
    expect(screen.getByText("Confirmed")).toBeInTheDocument();
  });

  it("renders the paid label", () => {
    render(<OrderStatusPill status="paid" />);
    expect(screen.getByText("Paid")).toBeInTheDocument();
  });
});
