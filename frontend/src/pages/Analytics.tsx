import { ReactNode, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import NetworkBackground from "../components/NetworkBackground";
import Nav from "../components/Nav";
import { CountUp } from "../components/RiskGauge";
import { DashboardCard, RISK_COLORS, ThreatDistribution } from "../components/Charts";
import { ScannerUsageChart, ScanTrendChart, ThreatTrendChart } from "../components/AnalyticsCharts";
import { ScanTable } from "../components/ScanTable";
import { ThreatBadge } from "../components/ThreatBadge";
import { EmptyState, ErrorState, Skeleton } from "../components/States";
import { useApi } from "../hooks/useApi";
import { errMsg } from "../services/api";
import { AnalyticsCard, AnalyticsOverview, CardKey, CountItems, HighRiskItem, PaginatedHistory, ScanTrends, ThreatTrends } from "../types";

const iso = (d: Date) => d.toISOString().slice(0, 10);
const SCANNERS = ["website", "email", "message", "qr", "file"];
const CARDS: [CardKey, string, boolean][] = [["total", "Total scans", false], ["safe", "Safe", false], ["suspicious", "Suspicious", true],
  ["threats", "Threats detected", true], ["high", "High risk", true], ["critical", "Critical risk", true]];

interface Q<T> { data: T | null; error: unknown; reload: () => void }

/** Per-section loading skeleton, error state with retry, and content. */
function Async<T>({ q, h = 220, children }: { q: Q<T>; h?: number; children: (d: T) => ReactNode }) {
  if (q.error && !q.data) return <ErrorState message={errMsg(q.error)} onRetry={q.reload} />;
  if (!q.data) return <Skeleton h={h} />;
  return <>{children(q.data)}</>;
}

function Delta({ c, bad, days, available }: { c: AnalyticsCard; bad: boolean; days: number; available: boolean }) {
  if (c.change_pct === null) return <small className="delta flat">{available ? "No change data (none in the previous period)" : "No earlier data to compare"}</small>;
  const tone = c.change_pct === 0 || !bad ? "flat" : c.change_pct > 0 ? "up" : "down";
  return <small className={`delta ${tone}`}>{c.change_pct > 0 ? "▲" : c.change_pct < 0 ? "▼" : "•"} {Math.abs(c.change_pct)}% vs previous {days} days</small>;
}

export default function Analytics() {
  const nav = useNavigate();
  const [mode, setMode] = useState<7 | 30 | 90 | "custom">(30);
  const [from, setFrom] = useState(iso(new Date(Date.now() - 29 * 864e5)));
  const [to, setTo] = useState(iso(new Date()));
  const [scanner, setScanner] = useState("");

  const p: Record<string, unknown> = mode === "custom" ? { date_from: from, date_to: to } : { days: mode };
  if (scanner) p.scanner = scanner;

  const ov = useApi<AnalyticsOverview>("/analytics/overview", p);
  const usage = useApi<CountItems>("/analytics/scanner-usage", p);
  const threats = useApi<CountItems>("/analytics/threat-distribution", p);
  const risk = useApi<CountItems>("/analytics/risk-distribution", p);
  const trend = useApi<ScanTrends>("/analytics/scan-trends", p);
  const tt = useApi<ThreatTrends>("/analytics/threat-trends", p);
  const hr = useApi<{ items: HighRiskItem[] }>("/analytics/high-risk", p);
  const recent = useApi<PaginatedHistory>("/history", { limit: 6, type: scanner || undefined });
  const asRecord = (d: CountItems) => Object.fromEntries(d.items.map((i) => [i.name, i.count]));
  const rangeError = !!ov.error && !ov.data;

  return (
    <>
      <NetworkBackground /><div className="glow" /><Nav />
      <main className="wrap">
        <h1>Analytics</h1>
        <p className="sub">Your scan data, calculated live from the database.</p>

        <div className="filterbar" role="group" aria-label="Analytics filters">
          <div className="seg">
            {([7, 30, 90] as const).map((d) => <button key={d} aria-pressed={mode === d} onClick={() => setMode(d)}>{d} days</button>)}
            <button aria-pressed={mode === "custom"} onClick={() => setMode("custom")}>Custom</button>
          </div>
          {mode === "custom" && (
            <div className="daterange">
              <input type="date" aria-label="From date" value={from} max={to} onChange={(e) => setFrom(e.target.value)} />
              <span>to</span>
              <input type="date" aria-label="To date" value={to} min={from} max={iso(new Date())} onChange={(e) => setTo(e.target.value)} />
            </div>
          )}
          <select aria-label="Scanner" value={scanner} onChange={(e) => setScanner(e.target.value)}>
            <option value="">All scanners</option>{SCANNERS.map((s) => <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>)}
          </select>
        </div>

        {rangeError && <ErrorState message={errMsg(ov.error)} onRetry={ov.reload} />}
        {!ov.data && !ov.error && <div className="stats">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} />)}</div>}

        {ov.data && ov.data.total_ever === 0 && (
          <EmptyState title="No scan data yet" text="Analytics appear here once you have run a security scan.">
            <button className="btn primary" onClick={() => nav("/scan")}>Run your first security scan</button>
          </EmptyState>
        )}

        {ov.data && ov.data.total_ever > 0 && (
          <>
            <p className="sub range">{ov.data.range.start} to {ov.data.range.end} ({ov.data.range.days} days){ov.data.scanner ? ` · ${ov.data.scanner} scans only` : ""}</p>
            <div className="stats">
              {CARDS.map(([k, label, bad], i) => (
                <motion.div key={k} className="stat" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
                  <strong><CountUp to={ov.data!.cards[k].value} /></strong><span>{label}</span>
                  <Delta c={ov.data!.cards[k]} bad={bad} days={ov.data!.range.days} available={ov.data!.comparison_available} />
                </motion.div>
              ))}
            </div>

            <div className="charts3">
              <DashboardCard title="Threat distribution"><Async q={threats} h={260}>{(d) => d.total === 0 ? <p className="sub">No scans in this period.</p> : <ThreatDistribution data={asRecord(d)} />}</Async></DashboardCard>
              <DashboardCard title="Risk distribution"><Async q={risk} h={260}>{(d) => d.total === 0 ? <p className="sub">No scans in this period.</p> : <ThreatDistribution data={asRecord(d)} colors={RISK_COLORS} />}</Async></DashboardCard>
              <DashboardCard title="Scanner usage"><Async q={usage} h={260}>{(d) => d.total === 0 ? <p className="sub">No scans in this period.</p> : <ScannerUsageChart items={d.items} />}</Async></DashboardCard>
            </div>

            <DashboardCard title="Scan activity"><Async q={trend}>{(d) => d.total === 0 ? <p className="sub">No scans in this period.</p> : <ScanTrendChart points={d.points} />}</Async></DashboardCard>
            <DashboardCard title="Threat trends (phishing, spam, scam)">
              <Async q={tt}>{(d) => d.total === 0 ? <p className="sub">No threats detected in this period.</p>
                : !d.sufficient ? <p className="sub">Not enough data for a trend yet: detections are needed on at least two different days. {d.total} found so far.</p>
                : <ThreatTrendChart points={d.points} />}</Async>
            </DashboardCard>

            <div className="charts2">
              <DashboardCard title="High-risk activity">
                <Async q={hr} h={160}>{(d) => d.items.length === 0 ? <p className="sub">No high or critical risk scans in this period.</p> : (
                  <ul className="alerts">{d.items.map((s) => (
                    <li key={s.id}><Link to={`/history/${s.id}`}>
                      <div className="row"><span>{s.scan_type} · <ThreatBadge label={s.label} /></span><b>{Math.round(s.risk_score)}/100</b></div>
                      <small>{new Date(s.created_at).toLocaleString()}</small>
                      {s.explanation && <p>{s.explanation}</p>}
                    </Link></li>))}</ul>)}</Async>
              </DashboardCard>
              <DashboardCard title="Recent scans" action={<Link to="/history" className="more">View all history</Link>}>
                <Async q={recent} h={160}>{(d) => d.items.length === 0 ? <p className="sub">No scans yet.</p> : <ScanTable items={d.items} />}</Async>
              </DashboardCard>
            </div>
          </>
        )}
      </main>
    </>
  );
}
