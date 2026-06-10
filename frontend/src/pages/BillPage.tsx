import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  api,
  ApiError,
  type BillSummary,
  type UserBillShare,
  type User,
} from "../api";
import { useAuth } from "../auth";
import { useSessionWebSocket } from "../session";
import { Layout } from "../components/Layout";
import { AvatarStack } from "../components/AvatarStack";
import { useToast } from "../components/LiveToast";

const SERVICE_CHARGE_RATE = 0.1;

export function BillPage() {
  const { sessionId = "" } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const { showToast } = useToast();

  const [bill, setBill] = useState<BillSummary | null>(null);
  const [participants, setParticipants] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchBill = async () => {
    if (!sessionId) return;
    try {
      const [b, ppl] = await Promise.all([
        api.getBill(sessionId),
        api.getParticipants(sessionId),
      ]);
      setBill(b);
      setParticipants(ppl);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        navigate("/scan", { replace: true });
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBill();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  useSessionWebSocket(sessionId, token, (evt) => {
    if (evt.order.session_id !== sessionId) return;
    if (evt.event === "order_status_updated") {
      fetchBill();
      if (evt.order.status === "paid")
        showToast("Bill settled — enjoy!", "celebration");
    }
  });

  const myShare = useMemo<UserBillShare | null>(() => {
    if (!bill || !user) return null;
    return bill.per_person.find((p) => p.user_id === user.id) ?? null;
  }, [bill, user]);

  const mySubtotal = myShare?.total ?? 0;
  const myServiceCharge =
    Math.round(mySubtotal * SERVICE_CHARGE_RATE * 100) / 100;
  const myTotal = Math.round((mySubtotal + myServiceCharge) * 100) / 100;

  const grandSubtotal = bill?.grand_total ?? 0;
  const grandServiceCharge =
    Math.round(grandSubtotal * SERVICE_CHARGE_RATE * 100) / 100;
  const grandTotal =
    Math.round((grandSubtotal + grandServiceCharge) * 100) / 100;

  const othersCount = participants.length > 1 ? participants.length - 1 : 0;

  if (loading) {
    return (
      <Layout
        title="Bill"
        back={`/sessions/${sessionId}/cart`}
        sessionId={sessionId}
      >
        <div className="flex items-center justify-center py-20">
          <span className="material-symbols-outlined animate-spin text-on-surface-variant">
            progress_activity
          </span>
        </div>
      </Layout>
    );
  }

  if (!bill) {
    return (
      <Layout
        title="Bill"
        back={`/sessions/${sessionId}/cart`}
        sessionId={sessionId}
      >
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <span className="material-symbols-outlined text-on-surface-variant text-[48px]">
            receipt_long
          </span>
          <p className="font-body-md text-body-md text-on-surface-variant text-center">
            No bill available yet.{" "}
            <button
              onClick={() => navigate(`/sessions/${sessionId}/cart`)}
              className="text-primary underline"
            >
              Go back to cart
            </button>
          </p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout
      title="Your Bill"
      back={`/sessions/${sessionId}/cart`}
      sessionId={sessionId}
    >
      {/* Header summary */}
      <section className="py-stack-md space-y-1">
        <h2 className="font-headline-md text-headline-md-mobile text-on-surface">
          Transparent Bill Split
        </h2>
        <p className="font-body-md text-body-md text-on-surface-variant">
          You only pay for what you ordered.
        </p>
      </section>

      {/* Per-person breakdown card */}
      {myShare && (
        <section className="bg-surface-container-lowest rounded-2xl shadow-sm border border-outline-variant/10 overflow-hidden mb-stack-md">
          {/* Card header */}
          <div className="px-stack-md pt-stack-md pb-3 border-b border-surface-variant/30">
            <p className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider mb-1">
              Your items
            </p>
            <p className="font-headline-sm text-on-surface font-semibold">
              {user?.username}
            </p>
          </div>

          {/* Item list */}
          <ul className="divide-y divide-surface-variant/20">
            {myShare.items.map((item, idx) => (
              <li
                key={idx}
                className={`flex items-start gap-3 px-stack-md py-3 ${
                  item.is_shared ? "border-l-4 border-tertiary" : ""
                }`}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-body-md text-body-md text-on-surface truncate">
                      {item.menu_item_name}
                    </span>
                    {item.is_shared && (
                      <span className="flex items-center gap-0.5 font-label-sm text-label-sm text-tertiary shrink-0">
                        <span
                          className="material-symbols-outlined text-[14px]"
                          aria-hidden
                        >
                          group
                        </span>
                        Shared
                      </span>
                    )}
                  </div>
                  <p className="font-label-sm text-label-sm text-on-surface-variant mt-0.5">
                    {item.is_shared
                      ? `Split ${participants.length} ways · $${item.unit_price.toFixed(2)} each`
                      : `Qty: ${item.quantity} · $${item.unit_price.toFixed(2)} each`}
                  </p>
                </div>
                <span className="font-body-md text-body-md text-on-surface shrink-0">
                  ${item.share_amount.toFixed(2)}
                </span>
              </li>
            ))}
          </ul>

          {/* Subtotals */}
          <div className="px-stack-md py-3 space-y-2 border-t border-surface-variant/30">
            <div className="flex justify-between font-body-md text-body-md text-on-surface-variant">
              <span>Subtotal</span>
              <span>${mySubtotal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between font-body-md text-body-md text-on-surface-variant">
              <span>Service charge (10%)</span>
              <span>${myServiceCharge.toFixed(2)}</span>
            </div>
            <div className="flex justify-between pt-2 border-t border-surface-variant/30">
              <span className="font-headline-md text-headline-md-mobile text-primary font-bold">
                Your Total
              </span>
              <span className="font-headline-md text-headline-md-mobile text-primary font-bold">
                ${myTotal.toFixed(2)}
              </span>
            </div>
          </div>

          {/* Splitting with */}
          {participants.length > 1 && (
            <div className="px-stack-md py-3 border-t border-surface-variant/20 flex items-center gap-3 bg-surface-container-low/50">
              <AvatarStack
                users={participants.filter((p) => p.id !== user?.id)}
                size="sm"
                max={4}
              />
              <p className="font-label-sm text-label-sm text-on-surface-variant">
                Splitting with {othersCount}{" "}
                {othersCount === 1 ? "other" : "others"}
              </p>
            </div>
          )}
        </section>
      )}

      {/* Full table summary (collapsed) */}
      {bill.per_person.length > 1 && (
        <section className="mb-stack-md">
          <details className="group bg-surface-container-lowest rounded-2xl shadow-sm border border-outline-variant/10 overflow-hidden">
            <summary className="flex items-center justify-between px-stack-md py-4 cursor-pointer select-none list-none">
              <span className="font-label-md text-label-md text-on-surface">
                Full table breakdown
              </span>
              <div className="flex items-center gap-2">
                <span className="font-body-md text-body-md text-on-surface-variant">
                  ${grandTotal.toFixed(2)} total
                </span>
                <span className="material-symbols-outlined text-on-surface-variant transition-transform group-open:rotate-180">
                  expand_more
                </span>
              </div>
            </summary>
            <div className="border-t border-surface-variant/20">
              {bill.per_person.map((person) => {
                const personServiceCharge =
                  Math.round(person.total * SERVICE_CHARGE_RATE * 100) / 100;
                const personTotal =
                  Math.round((person.total + personServiceCharge) * 100) / 100;
                return (
                  <div
                    key={person.user_id}
                    className="px-stack-md py-3 border-b border-surface-variant/10 last:border-0 flex items-center justify-between"
                  >
                    <span className="font-body-md text-body-md text-on-surface">
                      {person.username}
                      {person.user_id === user?.id && (
                        <span className="ml-2 font-label-sm text-label-sm text-primary">
                          (you)
                        </span>
                      )}
                    </span>
                    <span className="font-body-md text-body-md text-on-surface">
                      ${personTotal.toFixed(2)}
                    </span>
                  </div>
                );
              })}
              <div className="px-stack-md py-3 flex justify-between bg-surface-container-low/50">
                <span className="font-label-md text-label-md text-on-surface font-semibold">
                  Grand total (incl. service)
                </span>
                <span className="font-label-md text-label-md text-on-surface font-semibold">
                  ${grandTotal.toFixed(2)}
                </span>
              </div>
            </div>
          </details>
        </section>
      )}

      {/* CTA panel */}
      <div className="fixed bottom-16 md:bottom-0 left-0 right-0 z-40 px-4 pb-4">
        <div className="glass-panel rounded-2xl p-4 shadow-[0_-8px_30px_rgba(0,0,0,0.08)] border border-outline-variant/20 max-w-md mx-auto flex flex-col gap-3">
          <button
            onClick={() => showToast("Payment flow coming soon!", "payments")}
            className="w-full bg-primary text-on-primary py-4 rounded-xl font-label-md text-label-md flex justify-center items-center gap-2 active:scale-[0.98] transition-transform shadow-md"
          >
            <span className="material-symbols-outlined" aria-hidden>
              payments
            </span>
            Pay my share (${myTotal.toFixed(2)})
          </button>
          <button
            onClick={() => showToast("Payment flow coming soon!", "payments")}
            className="w-full border border-outline/40 text-on-surface py-3 rounded-xl font-label-md text-label-md flex justify-center items-center gap-2 active:scale-[0.98] transition-transform hover:bg-surface-container-low"
          >
            Pay for everyone (${grandTotal.toFixed(2)})
          </button>
        </div>
      </div>
    </Layout>
  );
}
