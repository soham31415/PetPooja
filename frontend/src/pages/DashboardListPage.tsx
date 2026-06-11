import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, ApiError, type Restaurant } from "../api";
import { Layout } from "../components/Layout";
import { useToast } from "../components/LiveToast";

export function DashboardListPage() {
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const mine = await api.listMyRestaurants();
        if (!cancelled) setRestaurants(mine);
      } catch (err) {
        const detail =
          err instanceof ApiError ? err.detail : "Could not load restaurants.";
        showToast(detail, "error");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [showToast]);

  const createRestaurant = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !address.trim()) return;
    setCreating(true);
    try {
      const created = await api.createRestaurant(name.trim(), address.trim());
      setRestaurants((prev) => [...prev, created]);
      setName("");
      setAddress("");
      navigate(`/dashboard/${created.id}`);
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.detail : "Could not create restaurant.";
      showToast(detail, "error");
    } finally {
      setCreating(false);
    }
  };

  return (
    <Layout title="My Restaurants" back="/">
      <section className="py-stack-md space-y-1">
        <h2 className="font-headline-md text-headline-md-mobile text-on-surface">
          Restaurant Dashboard
        </h2>
        <p className="font-body-md text-body-md text-on-surface-variant">
          Manage your menus, tables, and live orders.
        </p>
      </section>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <span className="material-symbols-outlined animate-spin text-on-surface-variant">
            progress_activity
          </span>
        </div>
      ) : (
        <section className="space-y-3 mb-stack-lg">
          {restaurants.length === 0 && (
            <p className="font-body-md text-body-md text-on-surface-variant">
              You don&rsquo;t own any restaurants yet. Create one below.
            </p>
          )}
          {restaurants.map((r) => (
            <button
              key={r.id}
              onClick={() => navigate(`/dashboard/${r.id}`)}
              className="w-full text-left bg-surface-container-lowest rounded-2xl p-stack-md shadow-sm border border-outline-variant/10 flex items-center justify-between hover:border-primary/40 transition-colors"
            >
              <div>
                <h3 className="font-body-lg text-body-lg font-semibold text-on-surface">
                  {r.name}
                </h3>
                <p className="font-label-sm text-label-sm text-on-surface-variant mt-0.5">
                  {r.address}
                </p>
                <p className="font-label-sm text-label-sm text-on-surface-variant mt-0.5">
                  {r.menu_items.length} menu items
                </p>
              </div>
              <span
                className="material-symbols-outlined text-on-surface-variant"
                aria-hidden
              >
                chevron_right
              </span>
            </button>
          ))}
        </section>
      )}

      <section className="bg-surface-container-lowest rounded-2xl p-stack-md shadow-sm border border-outline-variant/10">
        <h3 className="font-body-lg text-body-lg font-semibold text-on-surface mb-stack-sm">
          Create a restaurant
        </h3>
        <form onSubmit={createRestaurant} className="flex flex-col gap-3">
          <label className="flex flex-col gap-1">
            <span className="font-label-sm text-label-sm text-on-surface-variant">
              Name
            </span>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="h-12 px-4 rounded-xl border border-outline/40 bg-background focus:border-primary focus:ring-1 focus:ring-primary outline-none font-body-md text-body-md"
              placeholder="The Tasty Spoon"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="font-label-sm text-label-sm text-on-surface-variant">
              Address
            </span>
            <input
              required
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              className="h-12 px-4 rounded-xl border border-outline/40 bg-background focus:border-primary focus:ring-1 focus:ring-primary outline-none font-body-md text-body-md"
              placeholder="123 Main St"
            />
          </label>
          <button
            disabled={creating}
            className="h-12 bg-primary text-on-primary rounded-full font-label-md text-label-md disabled:opacity-50 active:scale-95 transition-transform shadow-sm hover:shadow-md"
          >
            {creating ? "Creating…" : "Create restaurant"}
          </button>
        </form>
      </section>
    </Layout>
  );
}
