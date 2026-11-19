import { ReactNode } from "react";
import { errMsg } from "../services/api";
import { ErrorState, Skeleton } from "./States";

export interface Q<T> { data: T | null; error: unknown; reload: () => void }

/** Loading skeleton, friendly error with retry, or the content. Keeps previous data visible while refetching. */
export function Async<T>({ q, h = 160, children }: { q: Q<T>; h?: number; children: (d: T) => ReactNode }) {
  if (q.error && !q.data) return <ErrorState message={errMsg(q.error)} onRetry={q.reload} />;
  if (!q.data) return <Skeleton h={h} />;
  return <>{children(q.data)}</>;
}
