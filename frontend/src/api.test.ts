import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";

import { api, ApiError, getToken, setToken } from "./api";

describe("token storage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("stores and clears the auth token", () => {
    expect(getToken()).toBeNull();
    setToken("abc123");
    expect(getToken()).toBe("abc123");
    setToken(null);
    expect(getToken()).toBeNull();
  });
});

describe("api requests", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("sends the bearer token on authenticated requests", async () => {
    setToken("test-token");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ id: "u1", username: "anu", is_guest: false }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }
      )
    );

    const user = await api.me();
    expect(user.username).toBe("anu");

    const [, init] = fetchMock.mock.calls[0]!;
    expect((init?.headers as Record<string, string>).Authorization).toBe(
      "Bearer test-token"
    );
  });

  it("does not send a bearer token on unauthenticated requests", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ access_token: "tok", token_type: "bearer" }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }
      )
    );

    await api.login("anu", "pw");

    const [, init] = fetchMock.mock.calls[0]!;
    expect(
      (init?.headers as Record<string, string>).Authorization
    ).toBeUndefined();
  });

  it("throws an ApiError with the response detail on failure", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Not found" }), {
        status: 404,
        statusText: "Not Found",
        headers: { "Content-Type": "application/json" },
      })
    );

    await expect(api.getSession("missing-session")).rejects.toMatchObject({
      status: 404,
      detail: "Not found",
    });
  });

  it("ApiError carries status and detail", () => {
    const err = new ApiError(403, "forbidden");
    expect(err.status).toBe(403);
    expect(err.detail).toBe("forbidden");
    expect(err).toBeInstanceOf(Error);
  });
});
