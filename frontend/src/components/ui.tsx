import { ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import NetworkBackground from "./NetworkBackground";
import Nav from "./Nav";
import { Indicator } from "../lib/types";

export const labelColor: Record<string, string> = { Safe: "#34d399", Suspicious: "#fbbf24", Phishing: "#f87171", Spam: "#8b7cff", Scam: "#fb923c" };
export const levelColor: Record<string, string> = { LOW: "#34d399", MEDIUM: "#fbbf24", HIGH: "#f87171", CRITICAL: "#ef4444" };
export const typeLabel: Record<string, string> = { website: "Website", email: "Email", message: "Message", qr: "QR", phone: "Phone", file: "File" };

export function Page({ children }: { children: ReactNode }) {
  return (<><NetworkBackground /><div className="glow" /><Nav /><main className="wrap">{children}</main></>);
}
export const ThreatBadge = ({ label }: { label: string }) => <span className="badge" style={{ color: labelColor[label] ?? "#4cc9f0" }}>{label}</span>;
export const ScanStatus = ({ status }: { status: string }) => (
  <span className="badge" style={{ color: status === "completed" ? "var(--safe)" : status === "failed" ? "var(--risk)" : "var(--warn)" }}>{status}</span>
);
export const Skeleton = ({ h = 90 }: { h?: number }) => <div className="skel" style={{ height: h }} aria-hidden="true" />;
export function EmptyState({ title, text, children }: { title: string; text: string; children?: ReactNode }) {
  return <div className="empty"><h2>{title}</h2><p>{text}</p><div className="cta-row" style={{ justifyContent: "center" }}>{children}</div></div>;
}
export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="empty" role="alert"><AlertTriangle color="var(--risk)" /><h2>Could not load this</h2><p>{message}</p>
      <div className="cta-row" style={{ justifyContent: "center" }}><button className="btn primary" onClick={onRetry}>Try again</button></div></div>
  );
}
export function IndicatorList({ items }: { items: Indicator[] }) {
  if (!items.length) return <p className="sub" style={{ fontSize: 14 }}>No indicators were recorded for this scan.</p>;
  return (
    <div className="why">{items.map((i) => (
      <div key={i.name}><div className="row"><span>{i.name}</span><span>{i.severity}</span></div>
        <div className="bar"><i style={{ width: `${Math.min(100, i.weight <= 1 ? i.weight * 100 : i.weight)}%` }} /></div></div>
    ))}</div>
  );
}
