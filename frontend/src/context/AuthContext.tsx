import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, tokens } from "../services/api";

export interface User { id: string; name: string; email: string; created_at: string }
interface Ctx {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}
const AuthCtx = createContext<Ctx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      if (tokens.access || tokens.refresh) {
        try {
          setUser((await api.get<User>("/auth/me")).data);
        } catch {
          tokens.clear();
        }
      }
      setLoading(false);
    })();
    const expired = () => setUser(null);
    window.addEventListener("auth:expired", expired);
    return () => window.removeEventListener("auth:expired", expired);
  }, []);

  const accept = (d: { access_token: string; refresh_token: string; user: User }) => {
    tokens.set(d.access_token, d.refresh_token);
    setUser(d.user);
  };
  const login = useCallback(async (email: string, password: string) => accept((await api.post("/auth/login", { email, password })).data), []);
  const register = useCallback(async (name: string, email: string, password: string) => accept((await api.post("/auth/register", { name, email, password })).data), []);
  const logout = useCallback(async () => {
    const r = tokens.refresh;
    try { if (r) await api.post("/auth/logout", { refresh_token: r }); } catch { /* token cleared locally regardless */ }
    tokens.clear();
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, loading, login, register, logout }), [user, loading, login, register, logout]);
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth() {
  const c = useContext(AuthCtx);
  if (!c) throw new Error("useAuth must be used inside AuthProvider");
  return c;
}
