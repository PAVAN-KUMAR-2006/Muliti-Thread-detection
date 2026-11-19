import { ReactNode } from "react";
import { AlertTriangle } from "lucide-react";

export function Skeleton({ h = 90 }: { h?: number }) {
  return <div className="skel" style={{ height: h }} aria-hidden="true" />;
}

export function EmptyState({ title, text, children }: { title: string; text: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <h2>{title}</h2>
      <p>{text}</p>
      {children && <div className="cta-row" style={{ justifyContent: "center" }}>{children}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="empty" role="alert">
      <AlertTriangle color="var(--risk)" />
      <h2>Something went wrong</h2>
      <p>{message}</p>
      {onRetry && <div className="cta-row" style={{ justifyContent: "center" }}><button className="btn primary" onClick={onRetry}>Try again</button></div>}
    </div>
  );
}
