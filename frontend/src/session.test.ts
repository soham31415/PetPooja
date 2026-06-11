import { describe, it, expect, beforeEach } from "vitest";

import {
  orderSubtotal,
  rememberSession,
  getRememberedSession,
  forgetSession,
} from "./session";
import type { Order } from "./api";

function makeOrder(overrides: Partial<Order> = {}): Order {
  return {
    id: 1,
    session_id: "session-1",
    status: "pending",
    items: [],
    ...overrides,
  };
}

describe("orderSubtotal", () => {
  it("returns 0 for an order with no items", () => {
    expect(orderSubtotal(makeOrder())).toBe(0);
  });

  it("sums quantity * price across items", () => {
    const order = makeOrder({
      items: [
        {
          id: 1,
          menu_item_id: 1,
          quantity: 2,
          assigned_user_id: null,
          menu_item: {
            id: 1,
            restaurant_id: 1,
            name: "Pizza",
            description: "",
            price: 10,
            tags: [],
          },
        },
        {
          id: 2,
          menu_item_id: 2,
          quantity: 1,
          assigned_user_id: "user-1",
          menu_item: {
            id: 2,
            restaurant_id: 1,
            name: "Soda",
            description: "",
            price: 2.5,
            tags: [],
          },
        },
      ],
    });
    expect(orderSubtotal(order)).toBe(22.5);
  });
});

describe("session remembrance helpers", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("returns null when no session is remembered", () => {
    expect(getRememberedSession()).toBeNull();
  });

  it("remembers and forgets a session id", () => {
    rememberSession("session-123");
    expect(getRememberedSession()).toBe("session-123");

    forgetSession();
    expect(getRememberedSession()).toBeNull();
  });
});
