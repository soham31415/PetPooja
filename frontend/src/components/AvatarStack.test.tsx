import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { AvatarStack, Avatar } from "./AvatarStack";
import type { User } from "../api";

function makeUser(id: string, username: string): User {
  return { id, username, is_guest: false };
}

describe("AvatarStack", () => {
  it("renders initials for each user up to max", () => {
    const users = [
      makeUser("1", "Alice"),
      makeUser("2", "Bob"),
      makeUser("3", "Carol"),
    ];
    render(<AvatarStack users={users} max={2} />);
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("B")).toBeInTheDocument();
    expect(screen.getByText("+1")).toBeInTheDocument();
  });

  it("renders no overflow badge when under the max", () => {
    const users = [makeUser("1", "Alice")];
    render(<AvatarStack users={users} max={4} />);
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.queryByText(/^\+/)).not.toBeInTheDocument();
  });
});

describe("Avatar", () => {
  it("renders initials for a multi-word username", () => {
    render(<Avatar user={{ username: "Anu Kapoor" }} />);
    expect(screen.getByText("AK")).toBeInTheDocument();
  });
});
