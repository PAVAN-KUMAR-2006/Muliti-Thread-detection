import { Link } from "react-router-dom";
import { DashboardCard } from "./Charts";
import { Async } from "./Async";
import { ScanStatus, ThreatBadge } from "./ThreatBadge";
import { useApi } from "../hooks/useApi";
import { AlertsResponse } from "../dashboardTypes";

const ICON: Record<string, string> = { website: "🌐", email: "📧", message: "📱", qr: "📷", file: "📁", phone: "📞" };

export default function HighRiskAlerts({ days }: { days: number }) {
  const q = useApi<AlertsResponse>("/analytics/high-risk", { days, limit: 5 });
  return (
    <DashboardCard title="High-risk alerts" action={<Link to="/history?threat=high_risk" className="more">View all</Link>}>
      <Async q={q} h={220}>
        {(d) => d.items.length === 0 ? (
          <p className="sub">No high or critical risk scans in the last {days} days.</p>
        ) : (
          <>
            <ul className="alerts9">
              {d.items.map((a) => (
                <li key={a.id}>
                  <Link to={`/history/${a.id}`} className={`al ${a.risk_level.toLowerCase()}`} aria-label={`${a.risk_level} risk ${a.scan_type} scan, ${a.label}, open details`}>
                    <div className="alrow">
                      <span className={`lvl ${a.risk_level.toLowerCase()}`}>{a.risk_level}</span>
                      <span>{ICON[a.scan_type] ?? "•"} {a.scan_type}</span>
                      <ThreatBadge label={a.label} />
                      <b>{Math.round(a.risk_score)}/100</b>
                    </div>
                    <div className="almeta">
                      <time dateTime={a.created_at}>{new Date(a.created_at).toLocaleString()}</time>
                      <ScanStatus status={a.status} />
                    </div>
                    {a.explanation && <p>{a.explanation}</p>}
                  </Link>
                </li>
              ))}
            </ul>
            {d.total > d.items.length && (
              <p className="sub" style={{ marginTop: 10 }}>Showing the latest {d.items.length} of {d.total} alerts. <Link to="/history?threat=high_risk" className="more">See them all in history</Link></p>
            )}
          </>
        )}
      </Async>
    </DashboardCard>
  );
}
