import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  api,
  ApiError,
  type DiningSession,
  type Order,
  type User,
} from "../api";
import { useAuth } from "../auth";
import { useSessionWebSocket, orderSubtotal } from "../session";
import { Layout } from "../components/Layout";
import { Avatar } from "../components/AvatarStack";
import { OrderStatusPill } from "../components/OrderStatusPill";
import { useToast } from "../components/LiveToast";

interface Bucket {
  key: string;
  title: string;
  user: User | null; // null for the "shared" bucket
  items: Order["items"];
  paletteIndex: number;
}

export function CartPage() {
  const { sessionId = "" } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const { showToast } = useToast();

  const [session, setSession] = useState<DiningSession | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [participants, setParticipants] = useState<User[]>([]);

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;
    (async () => {
      try {
        const [s, ppl, o] = await Promise.all([
          api.getSession(sessionId),
          api.getParticipants(sessionId),
          api.getOrdersForSession(sessionId),
        ]);
        if (cancelled) return;
        setSession(s);
        setParticipants(ppl);
        setOrders(o);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          navigate("/scan", { replace: true });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sessionId, navigate]);

  useSessionWebSocket(sessionId, token, (evt) => {
    if (evt.order.session_id !== sessionId) return;
    setOrders((prev) => {
      const idx = prev.findIndex((o) => o.id === evt.order.id);
      if (idx === -1) return [...prev, evt.order];
      const next = prev.slice();
      next[idx] = evt.order;
      return next;
    });
    if (evt.event === "order_status_updated") {
      if (evt.order.status === "confirmed")
        showToast("Order confirmed by the kitchen", "skillet");
      if (evt.order.status === "paid")
        showToast("Bill settled — enjoy!", "celebration");
    }
  });

  // Single "live" order = the pending one (or the most recent overall, for
  // post-payment view). All status transitions happen on this order.
  const liveOrder = useMemo(() => {
    return orders.find((o) => o.status === "pending") || orders.at(-1) || null;
  }, [orders]);

  const buckets = useMemo<Bucket[]>(() => {
    if (!liveOrder) return [];
    const userMap = new Map<string, User>(participants.map((p) => [p.id, p]));
    const sharedItems = liveOrder.items.filter((i) => !i.assigned_user_id);
    const ownedBy = new Map<string, Order["items"]>();
    for (const it of liveOrder.items) {
      if (!it.assigned_user_id) continue;
      const arr = ownedBy.get(it.assigned_user_id) || [];
      arr.push(it);
      ownedBy.set(it.assigned_user_id, arr);
    }
    const out: Bucket[] = [];
    if (sharedItems.length > 0) {
      out.push({
        key: "shared",
        title: "Shared for the table",
        user: null,
        items: sharedItems,
        paletteIndex: 2,
      });
    }
    // Current user first, then everyone else
    const orderedIds = [
      user?.id,
      ...participants.map((p) => p.id).filter((id) => id !== user?.id),
    ].filter(Boolean) as string[];
    for (const uid of orderedIds) {
      const items = ownedBy.get(uid);
      if (!items?.length) continue;
      const u = userMap.get(uid);
      if (!u) continue;
      out.push({
        key: uid,
        title: u.id === user?.id ? "Your items" : `${u.username}'s items`,
        user: u,
        items,
        paletteIndex: uid === user?.id ? 0 : 1,
      });
    }
    return out;
  }, [liveOrder, participants, user]);

  const totalCents = useMemo(() => {
    if (!liveOrder) return 0;
    return Math.round(orderSubtotal(liveOrder) * 100);
  }, [liveOrder]);

  const removeItem = async (orderId: number, itemId: number) => {
    try {
      const updated = await api.removeOrderItem(orderId, itemId);
      setOrders((prev) => {
        const idx = prev.findIndex((o) => o.id === updated.id);
        if (idx === -1) return prev;
        const next = prev.slice();
        next[idx] = updated;
        return next;
      });
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.detail : "Could not remove item.";
      showToast(detail, "error");
    }
  };

  const assignItem = async (
    orderId: number,
    itemId: number,
    assignedUserId: string | null
  ) => {
    try {
      const updated = await api.assignOrderItem(
        orderId,
        itemId,
        assignedUserId
      );
      setOrders((prev) => {
        const idx = prev.findIndex((o) => o.id === updated.id);
        if (idx === -1) return prev;
        const next = prev.slice();
        next[idx] = updated;
        return next;
      });
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.detail : "Could not reassign item.";
      showToast(detail, "error");
    }
  };

  const isOwner = session && user ? session.host_id === user.id : false; // host check is the closest proxy on the diner app

  const advanceStatus = async () => {
    if (!liveOrder) return;
    const next =
      liveOrder.status === "pending"
        ? "confirmed"
        : liveOrder.status === "confirmed"
          ? "paid"
          : null;
    if (!next) return;
    try {
      const updated = await api.updateOrderStatus(liveOrder.id, next);
      setOrders((prev) => {
        const idx = prev.findIndex((o) => o.id === updated.id);
        if (idx === -1) return prev;
        const c = prev.slice();
        c[idx] = updated;
        return c;
      });
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.detail : "Could not update status.";
      showToast(detail, "error");
    }
  };

  return (
    <Layout
      title="Group Cart"
      back={`/sessions/${sessionId}/menu`}
      sessionId={sessionId}
    >
      {/* Live status */}
      <section className="space-y-stack-sm py-stack-md">
        <div className="flex items-center justify-between">
          <h2 className="font-headline-md text-headline-md-mobile text-on-surface">
            Live order
          </h2>
          <span className="font-label-md text-label-md text-on-surface-variant flex items-center gap-1">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-tertiary opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-tertiary" />
            </span>
            Live
          </span>
        </div>
        {liveOrder ? (
          <div className="flex items-center gap-2">
            <OrderStatusPill status={liveOrder.status} size="md" />
            {isOwner && liveOrder.status !== "paid" && (
              <button
                onClick={advanceStatus}
                className="ml-auto text-primary font-label-md text-label-md hover:underline"
              >
                Mark as {liveOrder.status === "pending" ? "confirmed" : "paid"}
              </button>
            )}
          </div>
        ) : (
          <p className="font-body-md text-body-md text-on-surface-variant">
            Nothing in the cart yet. Add items from the{" "}
            <button
              onClick={() => navigate(`/sessions/${sessionId}/menu`)}
              className="text-primary underline"
            >
              menu
            </button>
            .
          </p>
        )}
      </section>

      {/* Buckets */}
      {buckets.length > 0 && (
        <section className="grid grid-cols-1 md:grid-cols-2 gap-stack-md">
          {buckets.map((b) => (
            <div
              key={b.key}
              className="bg-surface-container-lowest rounded-2xl p-stack-md shadow-sm border border-outline-variant/10"
            >
              <div className="flex items-center justify-between mb-4 pb-2 border-b border-surface-variant">
                <div className="flex items-center gap-2">
                  {b.user ? (
                    <Avatar
                      user={b.user}
                      size="sm"
                      paletteIndex={b.paletteIndex}
                    />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-secondary-container flex items-center justify-center">
                      <span
                        className="material-symbols-outlined text-[18px] text-on-secondary-container"
                        aria-hidden
                      >
                        group
                      </span>
                    </div>
                  )}
                  <h3 className="font-body-lg text-body-lg font-semibold text-on-surface">
                    {b.title}
                  </h3>
                </div>
                <span className="font-label-md text-label-md text-on-surface-variant">
                  $
                  {b.items
                    .reduce((s, i) => s + i.quantity * i.menu_item.price, 0)
                    .toFixed(2)}
                </span>
              </div>
              <ul className="space-y-4">
                {b.items.map((it) => (
                  <li
                    key={it.id}
                    className="flex items-start justify-between gap-3"
                  >
                    <div className="flex-1">
                      <h4 className="font-body-md text-body-md font-medium text-on-surface">
                        {it.menu_item.name}
                      </h4>
                      <p className="font-label-sm text-label-sm text-on-surface-variant mt-0.5">
                        Qty: {it.quantity}
                      </p>
                      {liveOrder?.status === "pending" && (
                        <label className="sr-only" htmlFor={`assign-${it.id}`}>
                          Assign {it.menu_item.name}
                        </label>
                      )}
                      {liveOrder?.status === "pending" && (
                        <select
                          id={`assign-${it.id}`}
                          value={it.assigned_user_id ?? ""}
                          onChange={(e) =>
                            assignItem(
                              liveOrder.id,
                              it.id,
                              e.target.value || null
                            )
                          }
                          className="mt-1 font-label-sm text-label-sm text-on-surface-variant bg-surface-container-low rounded-md px-2 py-1 border border-outline-variant/30"
                        >
                          <option value="">Shared</option>
                          {participants.map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.id === user?.id ? "Me" : p.username}
                            </option>
                          ))}
                        </select>
                      )}
                    </div>
                    <span className="font-body-md text-body-md text-on-surface">
                      ${(it.quantity * it.menu_item.price).toFixed(2)}
                    </span>
                    {liveOrder?.status === "pending" && (
                      <button
                        onClick={() => removeItem(liveOrder.id, it.id)}
                        aria-label="Remove"
                        className="text-on-surface-variant hover:text-error transition-colors"
                      >
                        <span className="material-symbols-outlined text-[18px]">
                          close
                        </span>
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </section>
      )}

      {/* Checkout */}
      {liveOrder && (
        <div className="fixed bottom-16 md:bottom-0 left-0 right-0 z-40 px-4 pb-4">
          <div className="glass-panel rounded-2xl p-4 shadow-[0_-8px_30px_rgba(0,0,0,0.08)] border border-outline-variant/20 max-w-md mx-auto flex flex-col gap-3">
            <div className="flex justify-between items-end px-1">
              <div className="space-y-1">
                <p className="font-label-sm text-label-sm text-on-surface-variant">
                  Table total
                </p>
                <p className="font-headline-lg text-headline-lg-mobile text-on-surface">
                  ${(totalCents / 100).toFixed(2)}
                </p>
              </div>
              <span className="font-label-sm text-label-sm text-on-surface-variant">
                {liveOrder.items.length} items
              </span>
            </div>
            <button
              onClick={() => navigate(`/sessions/${sessionId}/bill`)}
              className="w-full bg-primary text-on-primary py-4 rounded-xl font-label-md text-label-md flex justify-center items-center gap-2 active:scale-[0.98] transition-transform shadow-md"
            >
              Split bill &amp; checkout
              <span className="material-symbols-outlined" aria-hidden>
                arrow_forward
              </span>
            </button>
          </div>
        </div>
      )}
    </Layout>
  );
}
