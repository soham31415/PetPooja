import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  api,
  ApiError,
  type MenuItem,
  type Order,
  type OrderStatus,
  type Restaurant,
  type RestaurantAnalytics,
  type RestaurantTable,
} from "../api";
import { useAuth } from "../auth";
import { useRestaurantWebSocket } from "../session";
import { Layout } from "../components/Layout";
import { OrderStatusPill } from "../components/OrderStatusPill";
import { useToast } from "../components/LiveToast";

type Tab = "orders" | "analytics" | "tables" | "menu";

const TABS: { key: Tab; label: string; icon: string }[] = [
  { key: "orders", label: "Live Orders", icon: "receipt_long" },
  { key: "analytics", label: "Analytics", icon: "monitoring" },
  { key: "tables", label: "Tables", icon: "qr_code_2" },
  { key: "menu", label: "Menu", icon: "restaurant_menu" },
];

export function RestaurantDashboardPage() {
  const { restaurantId = "" } = useParams<{ restaurantId: string }>();
  const navigate = useNavigate();
  const { token } = useAuth();
  const { showToast } = useToast();
  const id = Number(restaurantId);

  const [restaurant, setRestaurant] = useState<Restaurant | null>(null);
  const [analytics, setAnalytics] = useState<RestaurantAnalytics | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [tables, setTables] = useState<RestaurantTable[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("orders");

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    (async () => {
      try {
        const [mine, a, o, t] = await Promise.all([
          api.listMyRestaurants(),
          api.getRestaurantAnalytics(id),
          api.getRestaurantOrders(id),
          api.listRestaurantTables(id),
        ]);
        if (cancelled) return;
        const found = mine.find((r) => r.id === id) ?? null;
        if (!found) {
          navigate("/dashboard", { replace: true });
          return;
        }
        setRestaurant(found);
        setAnalytics(a);
        setOrders(o);
        setTables(t);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 403) {
          navigate("/dashboard", { replace: true });
          return;
        }
        const detail =
          err instanceof ApiError ? err.detail : "Could not load dashboard.";
        showToast(detail, "error");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id, navigate, showToast]);

  // Live order feed for the dashboard
  useRestaurantWebSocket(id || null, token, (evt) => {
    setOrders((prev) => {
      const idx = prev.findIndex((o) => o.id === evt.order.id);
      if (idx === -1) return [evt.order, ...prev];
      const next = prev.slice();
      next[idx] = evt.order;
      return next;
    });
    if (evt.event === "order_created") {
      showToast("New order placed", "celebration");
    }
  });

  const advanceStatus = async (order: Order) => {
    const next: OrderStatus | null =
      order.status === "pending"
        ? "confirmed"
        : order.status === "confirmed"
          ? "paid"
          : null;
    if (!next) return;
    try {
      const updated = await api.updateOrderStatus(order.id, next);
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

  if (loading || !restaurant) {
    return (
      <Layout title="Dashboard" back="/dashboard">
        <div className="flex items-center justify-center py-20">
          <span className="material-symbols-outlined animate-spin text-on-surface-variant">
            progress_activity
          </span>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title={restaurant.name} back="/dashboard">
      <section className="sticky top-16 z-30 bg-surface/95 backdrop-blur-md py-stack-sm -mx-gutter px-gutter md:mx-0 md:-mx-container-margin-desktop md:px-container-margin-desktop border-b border-surface-variant/20">
        <div className="flex overflow-x-auto hide-scrollbar gap-2 py-2">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`flex-shrink-0 flex items-center gap-1 px-4 py-2 rounded-full font-label-md text-label-md whitespace-nowrap transition-colors ${
                tab === t.key
                  ? "bg-primary text-on-primary shadow-sm"
                  : "bg-surface-container text-on-surface-variant hover:bg-surface-variant"
              }`}
            >
              <span
                className="material-symbols-outlined text-[18px]"
                aria-hidden
              >
                {t.icon}
              </span>
              {t.label}
            </button>
          ))}
        </div>
      </section>

      <div className="py-stack-md">
        {tab === "orders" && (
          <OrdersTab orders={orders} onAdvance={advanceStatus} />
        )}
        {tab === "analytics" && <AnalyticsTab analytics={analytics} />}
        {tab === "tables" && (
          <TablesTab restaurantId={id} tables={tables} setTables={setTables} />
        )}
        {tab === "menu" && (
          <MenuTab
            restaurantId={id}
            menuItems={restaurant.menu_items}
            setRestaurant={setRestaurant}
          />
        )}
      </div>
    </Layout>
  );
}

function OrdersTab({
  orders,
  onAdvance,
}: {
  orders: Order[];
  onAdvance: (order: Order) => void;
}) {
  if (orders.length === 0) {
    return (
      <p className="font-body-md text-body-md text-on-surface-variant text-center py-8">
        No orders yet. They&rsquo;ll show up here in real time.
      </p>
    );
  }
  return (
    <ul className="space-y-3">
      {orders.map((order) => {
        const total = order.items.reduce(
          (s, i) => s + i.quantity * i.menu_item.price,
          0
        );
        const nextLabel =
          order.status === "pending"
            ? "Mark confirmed"
            : order.status === "confirmed"
              ? "Mark paid"
              : null;
        return (
          <li
            key={order.id}
            className="bg-surface-container-lowest rounded-2xl p-stack-md shadow-sm border border-outline-variant/10"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-label-md text-label-md text-on-surface-variant">
                Order #{order.id}
              </span>
              <OrderStatusPill status={order.status} />
            </div>
            <ul className="space-y-1 mb-3">
              {order.items.map((it) => (
                <li
                  key={it.id}
                  className="flex justify-between font-body-md text-body-md text-on-surface"
                >
                  <span>
                    {it.quantity}× {it.menu_item.name}
                  </span>
                  <span className="text-on-surface-variant">
                    ${(it.quantity * it.menu_item.price).toFixed(2)}
                  </span>
                </li>
              ))}
            </ul>
            <div className="flex items-center justify-between pt-2 border-t border-surface-variant/30">
              <span className="font-label-md text-label-md text-on-surface font-semibold">
                ${total.toFixed(2)}
              </span>
              {nextLabel && (
                <button
                  onClick={() => onAdvance(order)}
                  className="text-primary font-label-md text-label-md hover:underline"
                >
                  {nextLabel}
                </button>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function AnalyticsTab({
  analytics,
}: {
  analytics: RestaurantAnalytics | null;
}) {
  if (!analytics) {
    return (
      <p className="font-body-md text-body-md text-on-surface-variant text-center py-8">
        Analytics unavailable.
      </p>
    );
  }
  const stats = [
    { label: "Total orders", value: analytics.total_orders.toString() },
    {
      label: "Total revenue",
      value: `$${analytics.total_revenue.toFixed(2)}`,
    },
    {
      label: "Avg. group size",
      value: analytics.average_participants_per_session.toFixed(1),
    },
  ];
  return (
    <div className="space-y-stack-md">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {stats.map((s) => (
          <div
            key={s.label}
            className="bg-surface-container-lowest rounded-2xl p-stack-md shadow-sm border border-outline-variant/10"
          >
            <p className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider mb-1">
              {s.label}
            </p>
            <p className="font-headline-md text-headline-md-mobile text-on-surface font-bold">
              {s.value}
            </p>
          </div>
        ))}
      </div>

      <div className="bg-surface-container-lowest rounded-2xl p-stack-md shadow-sm border border-outline-variant/10">
        <h3 className="font-body-lg text-body-lg font-semibold text-on-surface mb-stack-sm">
          Orders by status
        </h3>
        <ul className="space-y-1">
          {Object.entries(analytics.orders_by_status).map(([status, count]) => (
            <li
              key={status}
              className="flex justify-between font-body-md text-body-md text-on-surface"
            >
              <span className="capitalize">{status}</span>
              <span className="text-on-surface-variant">{count}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="bg-surface-container-lowest rounded-2xl p-stack-md shadow-sm border border-outline-variant/10">
        <h3 className="font-body-lg text-body-lg font-semibold text-on-surface mb-stack-sm">
          Top menu items
        </h3>
        {analytics.top_menu_items.length === 0 ? (
          <p className="font-body-md text-body-md text-on-surface-variant">
            No orders yet.
          </p>
        ) : (
          <ul className="space-y-1">
            {analytics.top_menu_items.map((item) => (
              <li
                key={item.menu_item_id}
                className="flex justify-between font-body-md text-body-md text-on-surface"
              >
                <span>{item.name}</span>
                <span className="text-on-surface-variant">
                  {item.quantity_ordered} sold · ${item.revenue.toFixed(2)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function TablesTab({
  restaurantId,
  tables,
  setTables,
}: {
  restaurantId: number;
  tables: RestaurantTable[];
  setTables: React.Dispatch<React.SetStateAction<RestaurantTable[]>>;
}) {
  const { showToast } = useToast();
  const [label, setLabel] = useState("");
  const [creating, setCreating] = useState(false);

  const createTable = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!label.trim()) return;
    setCreating(true);
    try {
      const created = await api.createRestaurantTable(
        restaurantId,
        label.trim()
      );
      setTables((prev) => [...prev, created]);
      setLabel("");
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.detail : "Could not create table.";
      showToast(detail, "error");
    } finally {
      setCreating(false);
    }
  };

  const copyLink = async (qrToken: string) => {
    const url = `${location.origin}/scan/${qrToken}`;
    try {
      await navigator.clipboard.writeText(url);
      showToast("Table link copied", "content_copy");
    } catch {
      showToast(url, "content_copy");
    }
  };

  return (
    <div className="space-y-stack-md">
      <ul className="space-y-3">
        {tables.map((t) => (
          <li
            key={t.id}
            className="bg-surface-container-lowest rounded-2xl p-stack-md shadow-sm border border-outline-variant/10 flex items-center justify-between gap-3"
          >
            <div className="min-w-0">
              <h3 className="font-body-lg text-body-lg font-semibold text-on-surface">
                {t.label}
              </h3>
              <p className="font-label-sm text-label-sm text-on-surface-variant mt-0.5 truncate">
                /scan/{t.qr_token}
              </p>
            </div>
            <button
              onClick={() => copyLink(t.qr_token)}
              className="shrink-0 flex items-center gap-1 px-3 py-2 rounded-full bg-surface-container text-on-surface-variant hover:bg-surface-variant font-label-sm text-label-sm transition-colors"
            >
              <span
                className="material-symbols-outlined text-[16px]"
                aria-hidden
              >
                content_copy
              </span>
              Copy link
            </button>
          </li>
        ))}
        {tables.length === 0 && (
          <p className="font-body-md text-body-md text-on-surface-variant text-center py-8">
            No tables yet. Add one to generate its QR code link.
          </p>
        )}
      </ul>

      <section className="bg-surface-container-lowest rounded-2xl p-stack-md shadow-sm border border-outline-variant/10">
        <h3 className="font-body-lg text-body-lg font-semibold text-on-surface mb-stack-sm">
          Add a table
        </h3>
        <form onSubmit={createTable} className="flex gap-3">
          <input
            required
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="Table 12"
            className="flex-1 h-12 px-4 rounded-xl border border-outline/40 bg-background focus:border-primary focus:ring-1 focus:ring-primary outline-none font-body-md text-body-md"
          />
          <button
            disabled={creating}
            className="h-12 px-6 bg-primary text-on-primary rounded-full font-label-md text-label-md disabled:opacity-50 active:scale-95 transition-transform shadow-sm hover:shadow-md"
          >
            {creating ? "Adding…" : "Add"}
          </button>
        </form>
      </section>
    </div>
  );
}

function MenuTab({
  restaurantId,
  menuItems,
  setRestaurant,
}: {
  restaurantId: number;
  menuItems: MenuItem[];
  setRestaurant: React.Dispatch<React.SetStateAction<Restaurant | null>>;
}) {
  const { showToast } = useToast();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("");
  const [tags, setTags] = useState("");
  const [creating, setCreating] = useState(false);

  const total = useMemo(() => menuItems.length, [menuItems]);

  const createItem = async (e: React.FormEvent) => {
    e.preventDefault();
    const priceNum = Number(price);
    if (!name.trim() || !description.trim() || !Number.isFinite(priceNum)) {
      return;
    }
    setCreating(true);
    try {
      const created = await api.createMenuItem(restaurantId, {
        name: name.trim(),
        description: description.trim(),
        price: priceNum,
        tags: tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
      });
      setRestaurant((prev) =>
        prev ? { ...prev, menu_items: [...prev.menu_items, created] } : prev
      );
      setName("");
      setDescription("");
      setPrice("");
      setTags("");
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.detail : "Could not add menu item.";
      showToast(detail, "error");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-stack-md">
      <ul className="space-y-3">
        {menuItems.map((m) => (
          <li
            key={m.id}
            className="bg-surface-container-lowest rounded-2xl p-stack-md shadow-sm border border-outline-variant/10 flex items-start justify-between gap-3"
          >
            <div>
              <h3 className="font-body-lg text-body-lg font-semibold text-on-surface">
                {m.name}
              </h3>
              <p className="font-label-sm text-label-sm text-on-surface-variant mt-0.5">
                {m.description}
              </p>
              {m.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {m.tags.map((t) => (
                    <span
                      key={t}
                      className="px-2 py-0.5 rounded-full bg-surface-container text-on-surface-variant font-label-sm text-label-sm"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <span className="font-body-md text-body-md text-on-surface shrink-0">
              ${m.price.toFixed(2)}
            </span>
          </li>
        ))}
        {total === 0 && (
          <p className="font-body-md text-body-md text-on-surface-variant text-center py-8">
            No menu items yet. Add your first dish below.
          </p>
        )}
      </ul>

      <section className="bg-surface-container-lowest rounded-2xl p-stack-md shadow-sm border border-outline-variant/10">
        <h3 className="font-body-lg text-body-lg font-semibold text-on-surface mb-stack-sm">
          Add a menu item
        </h3>
        <form onSubmit={createItem} className="flex flex-col gap-3">
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Name"
            className="h-12 px-4 rounded-xl border border-outline/40 bg-background focus:border-primary focus:ring-1 focus:ring-primary outline-none font-body-md text-body-md"
          />
          <input
            required
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Description"
            className="h-12 px-4 rounded-xl border border-outline/40 bg-background focus:border-primary focus:ring-1 focus:ring-primary outline-none font-body-md text-body-md"
          />
          <div className="flex gap-3">
            <input
              required
              type="number"
              step="0.01"
              min="0"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="Price"
              className="flex-1 h-12 px-4 rounded-xl border border-outline/40 bg-background focus:border-primary focus:ring-1 focus:ring-primary outline-none font-body-md text-body-md"
            />
            <input
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="Tags (comma separated)"
              className="flex-[2] h-12 px-4 rounded-xl border border-outline/40 bg-background focus:border-primary focus:ring-1 focus:ring-primary outline-none font-body-md text-body-md"
            />
          </div>
          <button
            disabled={creating}
            className="h-12 bg-primary text-on-primary rounded-full font-label-md text-label-md disabled:opacity-50 active:scale-95 transition-transform shadow-sm hover:shadow-md"
          >
            {creating ? "Adding…" : "Add menu item"}
          </button>
        </form>
      </section>
    </div>
  );
}
