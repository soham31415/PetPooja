import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { api, ApiError, type TableInfo, type User } from "../api";
import { rememberSession } from "../session";

export function TableConfirmPage() {
  const { qrToken } = useParams<{ qrToken: string }>();
  const navigate = useNavigate();
  const [info, setInfo] = useState<TableInfo | null>(null);
  const [participants, setParticipants] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [joining, setJoining] = useState(false);

  useEffect(() => {
    if (!qrToken) return;
    let cancelled = false;
    (async () => {
      try {
        const t = await api.getTableInfo(qrToken);
        if (cancelled) return;
        setInfo(t);
        if (t.active_session_id) {
          const ppl = await api.getParticipants(t.active_session_id);
          if (!cancelled) setParticipants(ppl);
        }
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.detail : "Table not found.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [qrToken]);

  const joinOrStart = async () => {
    if (!qrToken) return;
    setJoining(true);
    try {
      const session = await api.startOrJoinTableSession(qrToken);
      rememberSession(session.id);
      navigate(`/sessions/${session.id}/menu`, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not join table.");
    } finally {
      setJoining(false);
    }
  };

  if (error) {
    return (
      <div className="min-h-[100dvh] flex flex-col items-center justify-center px-container-margin-mobile gap-6">
        <span className="material-symbols-outlined text-error text-[48px]">
          error
        </span>
        <p className="font-body-md text-body-md text-on-surface-variant text-center">
          {error}
        </p>
        <button
          onClick={() => navigate("/scan", { replace: true })}
          className="px-6 h-12 rounded-full bg-primary text-on-primary font-label-md text-label-md"
        >
          Try again
        </button>
      </div>
    );
  }

  if (!info) {
    return (
      <div className="min-h-[100dvh] flex items-center justify-center text-on-surface-variant">
        <span className="material-symbols-outlined animate-spin">
          progress_activity
        </span>
      </div>
    );
  }

  const hasActive = !!info.active_session_id;

  return (
    <div className="relative min-h-[100dvh] bg-surface-container-low">
      <div className="absolute inset-0 bg-gradient-to-br from-primary-fixed via-surface-bright to-tertiary-fixed opacity-40" />
      <div className="absolute inset-0 bg-surface/80 backdrop-blur-xl" />

      <div className="relative z-10 flex flex-col min-h-[100dvh] px-container-margin-mobile pt-16 pb-8 max-w-md mx-auto">
        <div className="w-20 h-20 bg-tertiary-container rounded-full flex items-center justify-center mx-auto mb-stack-lg shadow-sm border-4 border-surface">
          <span
            className="material-symbols-outlined filled text-on-tertiary-container text-[36px]"
            aria-hidden
          >
            check
          </span>
        </div>

        <div className="text-center mb-stack-xl">
          <span className="inline-block px-3 py-1 bg-secondary-container text-on-secondary-container rounded-full font-label-sm text-label-sm mb-4">
            Code Scanned
          </span>
          <h2 className="font-headline-lg text-headline-lg-mobile text-on-surface mb-2">
            {info.label}
          </h2>
          <p className="font-body-md text-body-md text-on-surface-variant flex items-center justify-center gap-1">
            <span className="material-symbols-outlined text-[18px]" aria-hidden>
              storefront
            </span>
            {info.restaurant_name}
          </p>
        </div>

        {hasActive ? (
          <div className="bg-surface/60 backdrop-blur-md rounded-3xl p-6 border border-outline-variant/30 shadow-sm mb-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-label-md text-label-md text-on-surface">
                Already at this table
              </h3>
              <span className="font-label-sm text-label-sm text-primary">
                {participants.length}{" "}
                {participants.length === 1 ? "person" : "people"}
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              {participants.slice(0, 5).map((p) => (
                <span
                  key={p.id}
                  className="px-3 py-1 rounded-full bg-primary-fixed text-on-primary-fixed font-label-sm text-label-sm"
                >
                  {p.username}
                </span>
              ))}
              {participants.length > 5 && (
                <span className="px-3 py-1 rounded-full bg-surface-container-high text-on-surface-variant font-label-sm text-label-sm">
                  +{participants.length - 5} more
                </span>
              )}
            </div>
          </div>
        ) : (
          <div className="bg-surface/60 backdrop-blur-md rounded-3xl p-6 border border-outline-variant/30 shadow-sm mb-auto text-center">
            <p className="font-body-md text-body-md text-on-surface-variant">
              No one&rsquo;s here yet. Start a new dining session and invite
              your friends.
            </p>
          </div>
        )}

        <div className="mt-8 flex flex-col gap-4">
          <button
            disabled={joining}
            onClick={joinOrStart}
            className="w-full h-14 bg-primary text-on-primary rounded-full font-label-md text-label-md shadow-sm hover:shadow-md hover:-translate-y-0.5 active:scale-95 transition-all disabled:opacity-50"
          >
            {joining
              ? "Joining…"
              : hasActive
                ? `Join table & view menu`
                : `Start session & view menu`}
          </button>
          <button
            onClick={() => navigate("/scan")}
            className="w-full h-12 rounded-full bg-transparent text-on-surface-variant font-label-md text-label-md hover:bg-surface-variant/50 transition-colors"
          >
            Scan a different code
          </button>
        </div>
      </div>
    </div>
  );
}
