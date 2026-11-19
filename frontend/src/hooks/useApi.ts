import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../services/api";

/** GET with loading/error/reload. Refetches when params change and when the tab becomes visible again. */
export function useApi<T>(url: string, params?: Record<string, unknown>) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const latest = useRef(0);
  const key = JSON.stringify(params ?? {});

  const load = useCallback(async () => {
    const id = ++latest.current;
    setLoading(true);
    try {
      const r = await api.get<T>(url, { params: JSON.parse(key) });
      if (id === latest.current) { setData(r.data); setError(null); }
    } catch (e) {
      if (id === latest.current) setError(e);
    } finally {
      if (id === latest.current) setLoading(false);
    }
  }, [url, key]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    const onVisible = () => { if (document.visibilityState === "visible") load(); };
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, [load]);
  return { data, error, loading, reload: load };
}
