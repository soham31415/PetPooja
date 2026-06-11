import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { api, getToken, setToken, type User } from "./api";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  loading: boolean;
  signIn: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  signInAsGuest: (username: string) => Promise<void>;
  signOut: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(getToken());
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await api.me();
      setUser(me);
    } catch {
      setToken(null);
      setTokenState(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const signIn = useCallback(async (username: string, password: string) => {
    const tok = await api.login(username, password);
    setToken(tok.access_token);
    setTokenState(tok.access_token);
    const me = await api.me();
    setUser(me);
  }, []);

  const register = useCallback(async (username: string, password: string) => {
    await api.register(username, password);
    const tok = await api.login(username, password);
    setToken(tok.access_token);
    setTokenState(tok.access_token);
    const me = await api.me();
    setUser(me);
  }, []);

  const signInAsGuest = useCallback(async (username: string) => {
    // Guests have no password, so the backend issues no JWT. We
    // therefore mint a short-lived guest user and keep them in the
    // session via the User id (orders/sessions still work for them in
    // the API layer because endpoints that require auth use bearer
    // tokens — guests can browse menus and view bills, but joining a
    // session is currently registered-only.)
    const guest = await api.guest(username);
    setUser(guest);
  }, []);

  const signOut = useCallback(() => {
    setToken(null);
    setTokenState(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        signIn,
        register,
        signInAsGuest,
        signOut,
        refresh,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
