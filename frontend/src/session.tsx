import { useEffect, useRef, useState } from "react";

import {
  restaurantWebSocketUrl,
  sessionWebSocketUrl,
  type Order,
  type UUID,
  type WsOrderEvent,
} from "./api";

/** Shared connect/reconnect logic for the session and restaurant order feeds. */
function useOrderEventSocket(
  url: string | null,
  onEvent: (event: WsOrderEvent) => void
): { connected: boolean } {
  const [connected, setConnected] = useState(false);
  const onEventRef = useRef(onEvent);

  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    if (!url) return;

    let ws: WebSocket | null = null;
    let retry = 0;
    let cancelled = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      if (cancelled) return;
      ws = new WebSocket(url);

      ws.onopen = () => {
        setConnected(true);
        retry = 0;
      };

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data) as WsOrderEvent;
          onEventRef.current(data);
        } catch {
          // ignore malformed frames
        }
      };

      ws.onerror = () => {
        // surface as a close — the onclose handler will reconnect
      };

      ws.onclose = (e) => {
        setConnected(false);
        if (cancelled) return;
        // 4401/4403 are auth failures; don't loop trying
        if (e.code === 4401 || e.code === 4403) return;
        retry = Math.min(retry + 1, 5);
        const delay = Math.min(1000 * 2 ** retry, 16000);
        reconnectTimer = setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws && ws.readyState <= 1) ws.close();
    };
  }, [url]);

  return { connected };
}

/**
 * Subscribe to the live order feed for a dining session.
 *
 * Connects to `WS /api/v1/sessions/{id}/ws?token=` and pushes order
 * events ("order_created" / "order_status_updated" / "order_item_added" /
 * "order_item_removed" / "order_item_assigned") to onEvent.
 * Auto-reconnects with exponential backoff on transient drops.
 */
export function useSessionWebSocket(
  sessionId: UUID | null,
  token: string | null,
  onEvent: (event: WsOrderEvent) => void
): { connected: boolean } {
  const url = sessionId && token ? sessionWebSocketUrl(sessionId, token) : null;
  return useOrderEventSocket(url, onEvent);
}

/**
 * Subscribe to a restaurant's live order dashboard feed. Owner-only;
 * connects to `WS /api/v1/restaurants/{id}/ws/orders?token=`.
 */
export function useRestaurantWebSocket(
  restaurantId: number | null,
  token: string | null,
  onEvent: (event: WsOrderEvent) => void
): { connected: boolean } {
  const url =
    restaurantId != null && token
      ? restaurantWebSocketUrl(restaurantId, token)
      : null;
  return useOrderEventSocket(url, onEvent);
}

/** Sum order totals (server doesn't return totals, only items). */
export function orderSubtotal(order: Order): number {
  return order.items.reduce(
    (sum, i) => sum + i.quantity * i.menu_item.price,
    0
  );
}

const LAST_SESSION_KEY = "petpooja.lastSession";

export function rememberSession(sessionId: UUID): void {
  localStorage.setItem(LAST_SESSION_KEY, sessionId);
}

export function getRememberedSession(): UUID | null {
  return localStorage.getItem(LAST_SESSION_KEY);
}

export function forgetSession(): void {
  localStorage.removeItem(LAST_SESSION_KEY);
}
