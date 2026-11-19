import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

const A = "sentinel.access";
const R = "sentinel.refresh";

export const tokens = {
  get access() { return localStorage.getItem(A); },
  get refresh() { return localStorage.getItem(R); },
  set(access: string, refresh: string) { localStorage.setItem(A, access); localStorage.setItem(R, refresh); },
  clear() { localStorage.removeItem(A); localStorage.removeItem(R); },
};

export const api = axios.create({ baseURL: "/api" });

api.interceptors.request.use((config) => {
  const t = tokens.access;
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

let pending: Promise<string | null> | null = null;

async function refreshTokens(): Promise<string | null> {
  const refresh = tokens.refresh;
  if (!refresh) return null;
  try {
    const { data } = await axios.post("/api/auth/refresh", { refresh_token: refresh });
    tokens.set(data.access_token, data.refresh_token);
    return data.access_token as string;
  } catch {
    tokens.clear();
    return null;
  }
}

api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const cfg = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;
    const url = cfg?.url ?? "";
    const isAuthCall = url.startsWith("/auth/") && !url.startsWith("/auth/me");
    if (error.response?.status === 401 && cfg && !cfg._retry && !isAuthCall) {
      cfg._retry = true;
      pending ??= refreshTokens().finally(() => { pending = null; });
      const t = await pending;
      if (t) {
        cfg.headers.Authorization = `Bearer ${t}`;
        return api(cfg);
      }
      window.dispatchEvent(new Event("auth:expired"));
    }
    return Promise.reject(error);
  }
);

export function errMsg(e: unknown): string {
  if (axios.isAxiosError(e)) {
    if (!e.response) return "Cannot reach the server. Check your connection and try again.";
    if (e.response.status === 429) return "Too many attempts. Wait a minute and try again.";
    const d = e.response.data?.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d) && d[0]?.msg) return String(d[0].msg).replace(/^Value error, /, "");
  }
  return "Something went wrong. Please try again.";
}
