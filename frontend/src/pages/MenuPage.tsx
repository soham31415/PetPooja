import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  api,
  ApiError,
  type DiningSession,
  type MenuItem,
  type Order,
  type User,
} from "../api";
import { useAuth } from "../auth";
import { useSessionWebSocket, orderSubtotal, rememberSession } from "../session";
import { Layout } from "../components/Layout";
import { MenuItemCard } from "../components/MenuItemCard";
import { AvatarStack } from "../components/AvatarStack";
import { useToast } from "../components/LiveToast";

export function MenuPage() {
  const { sessionId = "" } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const { showToast } = useToast();

  const [session, setSession] = useState<DiningSession | null>(null);
  const [participants, setParticipants] = useState<User[]>([]);
  const [menu, setMenu] = useState<MenuItem[]>([]);
  const [recommendations, setRecommendations] = useState<MenuItem[]>([]);
  const [category, setCategory] = useState<string>("all");
  const [activeOrder, setActiveOrder] = useState<Order | null>(null);
  const [busy, setBusy] = useState<number | null>(null);

  // Initial load
  useEffect(() => {
    if (!sessionId) return;
    rememberSession(sessionId);
    let cancelled = false;
    (async () => {
      try {
        const [s, ppl, recs] = await Promise.all([
          api.getSession(sessionId),
          api.getParticipants(sessionId),
          api.getRecommendations(sessionId).catch(() => [] as MenuItem[]),
        ]);
        if (cancelled) return;
        setSession(s);
        setParticipants(ppl);
        setRecommendations(recs);

        if (s.restaurant_id) {
          const m = await api.getMenu(s.restaurant_id);
          if (!cancelled) setMenu(m);
        }
        const orders = await api.getOrdersForSession(sessionId);
        if (cancelled) return;
        // The "live" group order is the most recent pending order; if none,
        // we'll create one when the first item is added.
        const pending = orders.find((o) => o.status === "pending") || null;
        setActiveOrder(pending);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          navigate("/scan", { replace: true });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sessionId, navigate]);

  // Live updates: someone added/removed an item, kitchen confirmed, etc.
  useSessionWebSocket(sessionId, token, (evt) => {
    if (evt.order.session_id !== sessionId) return;
    if (evt.event === "order_created") {
      setActiveOrder(evt.order);
      showToast("New order placed at the table", "celebration");
    } else if (evt.event === "order_item_added") {
      setActiveOrder(evt.order);
      const last = evt.order.items[evt.order.items.length - 1];
      if (last) showToast(`${last.menu_item.name} added to the table`, "add");
    } else if (evt.event === "order_item_removed") {
      setActiveOrder(evt.order);
    } else if (evt.event === "order_status_updated") {
      setActiveOrder(evt.order.status === "pending" ? evt.order : null);
      if (evt.order.status === "confirmed")
        showToast("Your order is confirmed!", "skillet");
      if (evt.order.status === "paid")
        showToast("Bill settled — enjoy!", "celebration");
    }
  });

  const categories = useMemo(() => {
    const all = new Set<string>();
    for (const m of menu) for (const t of m.tags) all.add(t);
    return ["all", ...Array.from(all).slice(0, 6)];
  }, [menu]);

  const filtered = useMemo(() => {
    if (category === "all") return menu;
    return menu.filter((m) => m.tags.includes(category));
  }, [menu, category]);

  const addToCart = useCallback(
    async (item: MenuItem) => {
      if (!user) return;
      setBusy(item.id);
      try {
        if (activeOrder) {
          const updated = await api.addOrderItem(activeOrder.id, {
            menu_item_id: item.id,
            quantity: 1,
          });
          setActiveOrder(updated);
        } else {
          const created = await api.createOrder(sessionId, [
            { menu_item_id: item.id, quantity: 1 },
          ]);
          setActiveOrder(created);
        }
        showToast(`${item.name} added`, "add_shopping_cart");
      } catch (err) {
        const detail =
          err instanceof ApiError ? err.detail : "Could not add item.";
        showToast(detail, "error");
      } finally {
        setBusy(null);
      }
    },
    [activeOrder, sessionId, user, showToast]
  );

  const total = activeOrder ? orderSubtotal(activeOrder) : 0;

  return (
    <Layout
      title="Menu"
      back="/"
      sessionId={sessionId}
      rightSlot={
        <button
          onClick={() => navigate(`/sessions/${sessionId}/cart`)}
          aria-label="Group cart"
          className="relative w-10 h-10 flex items-center justify-center rounded-full hover:bg-surface-container-low transition-colors"
        >
          <span className="material-symbols-outlined text-primary">
            shopping_basket
          </span>
          {activeOrder && activeOrder.items.length > 0 && (
            <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-primary text-on-primary text-[10px] font-bold flex items-center justify-center">
              {activeOrder.items.reduce((s, i) => s + i.quantity, 0)}
            </span>
          )}
        </button>
      }
    >
      {/* Communal table */}
      <section className="py-stack-md">
        <h2 className="font-label-md text-label-md text-on-surface-variant mb-unit uppercase tracking-wider">
          The Communal Table
        </h2>
        <div className="flex items-center gap-3">
          <AvatarStack users={participants} size="lg" max={4} />
          <p className="font-body-md text-body-md text-on-surface-variant">
            {participants.length}{" "}
            {participants.length === 1 ? "person" : "people"} at the table
          </p>
        </div>
      </section>

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <section className="py-stack-md">
          <div className="flex items-center justify-between mb-stack-md">
            <h2 className="font-headline-md text-headline-md-mobile text-on-surface">
              Recommended for the group
            </h2>
            <span
              className="material-symbols-outlined text-primary"
              aria-hidden
            >
              auto_awesome
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2">
              <MenuItemCard
                variant="featured"
                item={recommendations[0]!}
                matchScore={1}
                onAdd={addToCart}
                busy={busy === recommendations[0]!.id}
              />
            </div>
            {recommendations[1] && (
              <MenuItemCard
                variant="featured"
                item={recommendations[1]}
                matchScore={0.85}
                onAdd={addToCart}
                busy={busy === recommendations[1].id}
              />
            )}
          </div>
        </section>
      )}

      {/* Category chips */}
      <section className="sticky top-16 z-30 bg-surface/95 backdrop-blur-md py-stack-sm -mx-gutter px-gutter md:mx-0 md:-mx-container-margin-desktop md:px-container-margin-desktop border-b border-surface-variant/20">
        <div className="flex overflow-x-auto hide-scrollbar gap-2 py-2">
          {categories.map((c) => (
            <button
              key={c}
              onClick={() => setCategory(c)}
              className={`flex-shrink-0 px-4 py-2 rounded-full font-label-md text-label-md whitespace-nowrap transition-colors ${
                category === c
                  ? "bg-primary text-on-primary shadow-sm"
                  : "bg-surface-container text-on-surface-variant hover:bg-surface-variant"
              }`}
            >
              {c === "all" ? "All items" : c}
            </button>
          ))}
        </div>
      </section>

      {/* Full menu */}
      <section className="py-stack-md flex flex-col gap-2">
        {filtered.length === 0 && (
          <p className="font-body-md text-body-md text-on-surface-variant text-center py-8">
            No items match this filter.
          </p>
        )}
        {filtered.map((m, idx) => (
          <div key={m.id}>
            <MenuItemCard
              item={m}
              onAdd={addToCart}
              busy={busy === m.id}
            />
            {idx < filtered.length - 1 && (
              <div className="h-px w-full bg-surface-variant/30 my-1" />
            )}
          </div>
        ))}
      </section>

      {/* Floating cart bar */}
      {activeOrder && activeOrder.items.length > 0 && (
        <div className="fixed bottom-16 md:bottom-4 left-0 right-0 z-40 px-gutter pb-2">
          <button
            onClick={() => navigate(`/sessions/${sessionId}/cart`)}
            className="w-full max-w-md mx-auto h-14 bg-primary text-on-primary rounded-full flex items-center justify-between px-6 shadow-lg active:scale-[0.98] transition-transform"
          >
            <span className="font-label-md text-label-md">
              {activeOrder.items.reduce((s, i) => s + i.quantity, 0)} items
            </span>
            <span className="font-label-md text-label-md">View cart</span>
            <span className="font-label-md text-label-md">
              ${total.toFixed(2)}
            </span>
          </button>
        </div>
      )}

      {session?.status !== "active" && session && (
        <div className="fixed top-16 left-0 right-0 z-30 bg-error-container text-on-error-container text-center py-2 font-label-md text-label-md">
          This session is {session.status}.
        </div>
      )}
    </Layout>
  );
}
