import { useNavigate } from "react-router-dom";

import { useAuth } from "../auth";
import { getRememberedSession } from "../session";

export function OnboardingPage() {
  const navigate = useNavigate();
  const { user, loading } = useAuth();

  // If the user previously joined a session, jump straight back to its menu —
  // less friction on every cold start.
  if (!loading && user) {
    const remembered = getRememberedSession();
    if (remembered) {
      navigate(`/sessions/${remembered}/menu`, { replace: true });
      return null;
    }
  }

  return (
    <div className="flex flex-col h-[100dvh] bg-surface-container-lowest">
      {/* Hero */}
      <div className="relative w-full h-3/5 rounded-b-[2rem] overflow-hidden shadow-sm bg-gradient-to-br from-primary via-primary-container to-surface-tint">
        <div className="absolute inset-0 opacity-30 bg-[radial-gradient(circle_at_30%_20%,#fff_0%,transparent_50%),radial-gradient(circle_at_70%_80%,#ffdbcf_0%,transparent_40%)]" />
        <div className="absolute inset-0 bg-gradient-to-t from-surface-container-lowest via-surface-container-lowest/30 to-transparent" />
        <div className="absolute top-12 left-1/2 -translate-x-1/2 bg-surface/90 backdrop-blur-md px-6 py-3 rounded-full shadow-sm flex items-center gap-2 border border-outline-variant/20">
          <span
            className="material-symbols-outlined filled text-primary"
            aria-hidden
          >
            restaurant_menu
          </span>
          <h1 className="font-headline-md text-headline-md-mobile text-on-surface">
            PetPooja
          </h1>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 px-container-margin-mobile pb-8 pt-6 flex flex-col justify-end">
        <div className="mb-stack-lg text-center">
          <h2 className="font-headline-lg text-headline-lg-mobile text-on-surface mb-stack-sm">
            Welcome to the Table
          </h2>
          <p className="font-body-md text-body-md text-on-surface-variant max-w-[280px] mx-auto">
            Scan your table&rsquo;s QR code to view the menu, join friends, and
            share the meal.
          </p>
        </div>

        <div className="flex flex-col gap-stack-md">
          <button
            onClick={() => navigate(user ? "/scan" : "/auth?next=/scan")}
            className="w-full h-14 bg-primary text-on-primary rounded-full font-label-md text-label-md shadow-sm hover:shadow-md hover:-translate-y-0.5 active:scale-95 transition-all flex items-center justify-center gap-2"
          >
            <span
              className="material-symbols-outlined text-[20px]"
              aria-hidden
            >
              qr_code_scanner
            </span>
            Scan Table QR
          </button>

          <button
            onClick={() => navigate("/auth")}
            className="w-full h-14 bg-transparent border border-outline text-on-surface rounded-full font-label-md text-label-md hover:bg-surface-container-low active:bg-surface-variant transition-colors"
          >
            {user ? `Continue as ${user.username}` : "Sign in / Create account"}
          </button>
        </div>

        {!user && (
          <div className="mt-6 text-center">
            <button
              onClick={() => navigate("/auth?mode=guest")}
              className="font-label-sm text-label-sm text-on-surface-variant hover:text-primary transition-colors underline decoration-outline-variant underline-offset-4"
            >
              Continue as guest
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
