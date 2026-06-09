/* eslint-disable @typescript-eslint/no-explicit-any */
// Single-file API client + types. Mirrors the FastAPI backend at
// /api/v1/* — see app/api/v1/endpoints/* for the source of truth.

const API_BASE: string =
  (import.meta as any).env?.VITE_API_BASE_URL?.replace(/\/$/, "") || "/api/v1";

// ---------------- Types ----------------

export type UUID = string;

export type SessionStatus = "active" | "closed" | "cancelled";
export type OrderStatus = "pending" | "confirmed" | "paid";

export interface TasteProfile {
  id: number;
  user_id: UUID;
  preferences: string[];
  daringness: number;
  dietary_restrictions: string[];
}

export interface User {
  id: UUID;
  username: string;
  is_guest: boolean;
  taste_profile?: TasteProfile | null;
}

export interface MenuItem {
  id: number;
  restaurant_id: number;
  name: string;
  description: string;
  price: number;
  tags: string[];
}

export interface Restaurant {
  id: number;
  name: string;
  address: string;
  owner_id?: UUID | null;
  menu_items: MenuItem[];
}

export interface RestaurantTable {
  id: number;
  restaurant_id: number;
  label: string;
  qr_token: string;
}

export interface TableInfo {
  table_id: number;
  label: string;
  restaurant_id: number;
  restaurant_name: string;
  active_session_id: UUID | null;
}

export interface DiningSession {
  id: UUID;
  host_id: UUID;
  restaurant_id: number | null;
  table_id: number | null;
  status: SessionStatus;
  created_at: string;
}

export interface OrderItem {
  id: number;
  menu_item_id: number;
  quantity: number;
  assigned_user_id: UUID | null;
  menu_item: MenuItem;
}

export interface Order {
  id: number;
  session_id: UUID;
  status: OrderStatus;
  items: OrderItem[];
}

export interface BillItemDetail {
  menu_item_name: string;
  quantity: number;
  unit_price: number;
  share_amount: number;
  is_shared: boolean;
}

export interface UserBillShare {
  user_id: UUID;
  username: string;
  items: BillItemDetail[];
  total: number;
}

export interface BillSummary {
  session_id: UUID;
  grand_total: number;
  per_person: UserBillShare[];
}

export interface Token {
  access_token: string;
  token_type: string;
}

export type WsOrderEvent = {
  event:
    | "order_created"
    | "order_status_updated"
    | "order_item_added"
    | "order_item_removed";
  order: Order;
};

// ---------------- Token storage ----------------

const TOKEN_KEY = "petpooja.token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

// ---------------- Fetch wrapper ----------------

export class ApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  opts: { auth?: boolean } = { auth: true }
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
  };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (opts.auth !== false) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const payload = await res.json();
      if (typeof payload.detail === "string") detail = payload.detail;
      else if (Array.isArray(payload.detail))
        detail = payload.detail.map((d: any) => d.msg || d).join(", ");
    } catch {
      // ignore
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ---------------- Endpoints ----------------

export const api = {
  // Users / auth
  register: (username: string, password: string) =>
    request<User>("POST", "/users/", { username, password }, { auth: false }),
  login: (username: string, password: string) =>
    request<Token>(
      "POST",
      "/users/login",
      { username, password },
      { auth: false }
    ),
  guest: (username: string) =>
    request<User>(
      "POST",
      "/users/guest",
      { username, taste_profile: null },
      { auth: false }
    ),
  me: () => request<User>("GET", "/users/me"),
  getUser: (userId: UUID) => request<User>("GET", `/users/${userId}`),

  // Restaurants
  listRestaurants: () => request<Restaurant[]>("GET", "/restaurants/"),
  getMenu: (restaurantId: number) =>
    request<MenuItem[]>("GET", `/restaurants/${restaurantId}/menu`),

  // Tables (QR)
  getTableInfo: (qrToken: string) =>
    request<TableInfo>("GET", `/tables/${qrToken}`, undefined, { auth: false }),
  startOrJoinTableSession: (qrToken: string) =>
    request<DiningSession>("POST", `/tables/${qrToken}/session`),

  // Sessions
  createSession: (restaurantId?: number | null) =>
    request<DiningSession>("POST", "/sessions/", {
      restaurant_id: restaurantId ?? null,
    }),
  joinSession: (sessionId: UUID) =>
    request<DiningSession>("POST", `/sessions/${sessionId}/join`),
  getSession: (sessionId: UUID) =>
    request<DiningSession>("GET", `/sessions/${sessionId}`, undefined, {
      auth: false,
    }),
  getParticipants: (sessionId: UUID) =>
    request<User[]>("GET", `/sessions/${sessionId}/participants`, undefined, {
      auth: false,
    }),
  getRecommendations: (sessionId: UUID) =>
    request<MenuItem[]>(
      "GET",
      `/sessions/${sessionId}/recommendations`,
      undefined,
      { auth: false }
    ),
  getBill: (sessionId: UUID) =>
    request<BillSummary>("GET", `/sessions/${sessionId}/bill`, undefined, {
      auth: false,
    }),
  closeSession: (sessionId: UUID) =>
    request<DiningSession>("PATCH", `/sessions/${sessionId}/status`, {
      status: "closed",
    }),

  // Orders
  createOrder: (
    sessionId: UUID,
    items: Array<{
      menu_item_id: number;
      quantity?: number;
      assigned_user_id?: UUID | null;
    }>
  ) =>
    request<Order>("POST", "/orders/", {
      session_id: sessionId,
      items: items.map((i) => ({ quantity: 1, ...i })),
    }),
  getOrdersForSession: (sessionId: UUID) =>
    request<Order[]>("GET", `/orders/session/${sessionId}`, undefined, {
      auth: false,
    }),
  updateOrderStatus: (orderId: number, status: OrderStatus) =>
    request<Order>("PATCH", `/orders/${orderId}/status`, { status }),
  addOrderItem: (
    orderId: number,
    item: {
      menu_item_id: number;
      quantity?: number;
      assigned_user_id?: UUID | null;
    }
  ) =>
    request<Order>("POST", `/orders/${orderId}/items`, {
      quantity: 1,
      ...item,
    }),
  removeOrderItem: (orderId: number, itemId: number) =>
    request<Order>("DELETE", `/orders/${orderId}/items/${itemId}`),
};

// ---------------- WebSocket URL helper ----------------

export function sessionWebSocketUrl(sessionId: UUID, token: string): string {
  // In dev, /ws is proxied to /api/v1/* on the backend. In prod, we hit
  // the API host directly (same-origin in most deploys).
  const base = API_BASE.startsWith("http")
    ? API_BASE.replace(/^http/, "ws")
    : `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}${API_BASE}`;
  return `${base}/sessions/${sessionId}/ws?token=${encodeURIComponent(token)}`;
}
