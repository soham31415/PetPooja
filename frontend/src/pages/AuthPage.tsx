import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useAuth } from "../auth";
import { ApiError } from "../api";

type Mode = "login" | "register" | "guest";

export function AuthPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { signIn, register, signInAsGuest } = useAuth();
  const next = params.get("next") || "/scan";

  const initialMode: Mode = params.get("mode") === "guest" ? "guest" : "login";
  const [mode, setMode] = useState<Mode>(initialMode);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === "login") await signIn(username, password);
      else if (mode === "register") await register(username, password);
      else await signInAsGuest(username);
      navigate(next, { replace: true });
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.detail : "Something went wrong.";
      setError(detail);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-[100dvh] bg-background flex flex-col">
      <header className="w-full top-0 sticky bg-surface z-40 flex items-center justify-between px-gutter py-stack-sm h-16">
        <button
          aria-label="Back"
          onClick={() => navigate(-1)}
          className="w-10 h-10 flex items-center justify-center rounded-full text-on-surface-variant hover:bg-surface-container-low transition-colors"
        >
          <span className="material-symbols-outlined">arrow_back</span>
        </button>
        <h1 className="font-headline-md text-headline-md-mobile text-primary font-bold">
          PetPooja
        </h1>
        <div className="w-10 h-10" />
      </header>

      <main className="flex-1 px-container-margin-mobile pt-8 max-w-md w-full mx-auto flex flex-col">
        <h2 className="font-headline-lg text-headline-lg-mobile text-on-surface mb-stack-sm">
          {mode === "register"
            ? "Create your account"
            : mode === "guest"
              ? "Continue as guest"
              : "Welcome back"}
        </h2>
        <p className="font-body-md text-body-md text-on-surface-variant mb-stack-lg">
          {mode === "guest"
            ? "Pick a name your friends will see at the table."
            : "Sign in with your username and password."}
        </p>

        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-2">
            <span className="font-label-sm text-label-sm text-on-surface-variant">
              Username
            </span>
            <input
              autoFocus
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="h-12 px-4 rounded-xl border border-outline/40 bg-surface-container-lowest focus:border-primary focus:ring-1 focus:ring-primary outline-none font-body-md text-body-md"
              placeholder="anu"
            />
          </label>
          {mode !== "guest" && (
            <label className="flex flex-col gap-2">
              <span className="font-label-sm text-label-sm text-on-surface-variant">
                Password
              </span>
              <input
                required
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="h-12 px-4 rounded-xl border border-outline/40 bg-surface-container-lowest focus:border-primary focus:ring-1 focus:ring-primary outline-none font-body-md text-body-md"
                placeholder="••••••••"
              />
            </label>
          )}
          {error && (
            <div className="bg-error-container text-on-error-container rounded-lg px-3 py-2 font-body-md text-[14px]">
              {error}
            </div>
          )}
          <button
            disabled={busy}
            className="mt-4 h-14 bg-primary text-on-primary rounded-full font-label-md text-label-md disabled:opacity-50 active:scale-95 transition-transform shadow-sm hover:shadow-md"
          >
            {busy
              ? "Please wait…"
              : mode === "register"
                ? "Create account"
                : mode === "guest"
                  ? "Continue"
                  : "Sign in"}
          </button>
        </form>

        <div className="mt-auto py-stack-lg flex flex-col items-center gap-3">
          {mode === "login" && (
            <button
              onClick={() => setMode("register")}
              className="font-label-sm text-label-sm text-on-surface-variant hover:text-primary"
            >
              New here? <span className="text-primary">Create an account</span>
            </button>
          )}
          {mode === "register" && (
            <button
              onClick={() => setMode("login")}
              className="font-label-sm text-label-sm text-on-surface-variant hover:text-primary"
            >
              Already have an account?{" "}
              <span className="text-primary">Sign in</span>
            </button>
          )}
          {mode !== "guest" && (
            <button
              onClick={() => setMode("guest")}
              className="font-label-sm text-label-sm text-on-surface-variant underline decoration-outline-variant underline-offset-4"
            >
              Continue as guest instead
            </button>
          )}
          {mode === "guest" && (
            <button
              onClick={() => setMode("login")}
              className="font-label-sm text-label-sm text-on-surface-variant underline decoration-outline-variant underline-offset-4"
            >
              I have an account — sign in
            </button>
          )}
        </div>
      </main>
    </div>
  );
}
