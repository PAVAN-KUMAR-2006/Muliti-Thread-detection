import { Link, useNavigate } from "react-router-dom";
import { ScanSummary } from "../types";
import { ScanStatus, ThreatBadge } from "./ThreatBadge";

const ICON: Record<string, string> = { website: "🌐", email: "📧", message: "📱", qr: "📷", phone: "📞", file: "📁" };

export function ScanRow({ s }: { s: ScanSummary }) {
  const nav = useNavigate();
  return (
    <tr className="click" onClick={() => nav(`/history/${s.id}`)}>
      <td data-label="Date">{new Date(s.created_at).toLocaleString(undefined, { month: "short", day: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" })}</td>
      <td data-label="Type">{ICON[s.scan_type]} {s.scan_type}</td>
      <td data-label="Input" title={s.input_summary}><Link to={`/history/${s.id}`} onClick={(e) => e.stopPropagation()}>{s.input_summary}</Link></td>
      <td data-label="Result"><ThreatBadge label={s.label} /></td>
      <td data-label="Risk">{Math.round(s.risk_score)}/100</td>
      <td data-label="Status"><ScanStatus status={s.status} /></td>
    </tr>
  );
}

export function ScanTable({ items }: { items: ScanSummary[] }) {
  return (
    <table className="t">
      <thead><tr><th>Date</th><th>Type</th><th>Input</th><th>Result</th><th>Risk</th><th>Status</th></tr></thead>
      <tbody>{items.map((s) => <ScanRow key={s.id} s={s} />)}</tbody>
    </table>
  );
}
