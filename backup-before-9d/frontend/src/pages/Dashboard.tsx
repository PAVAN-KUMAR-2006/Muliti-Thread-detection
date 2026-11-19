import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import NetworkBackground from "../components/NetworkBackground";
import Nav from "../components/Nav";
import { CountUp } from "../components/RiskGauge";
import { ActivityChart, ChannelDistribution, DashboardCard, RISK_COLORS, ThreatDistribution } from "../components/Charts";
import { ScanTable } from "../components/ScanTable";
import { EmptyState, ErrorState, Skeleton } from "../components/States";
import { useAuth } from "../context/AuthContext";
import { useApi } from "../hooks/useApi";
import { errMsg } from "../services/api";
import { DashboardOverview } from "../types";

const STATE_TEXT: Record<DashboardOverview["state"], string> = {
  "No data": "Your security workspace is ready",
  Clear: "No high-risk results in the last 7 days",
  Elevated: "High-risk results were found in the last 7 days",
};

export default function Dashboard() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [days, setDays] = useState<7 | 30 | 90>(30);
  const { data, error, loading, reload } = useApi<DashboardOverview>("/dashboard/overview", { days });
  const h = new Date().getHours();
  const greet = h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";

  const cards: [string, number, string][] = data ? [
    ["Total scans", data.total, ""], ["Safe", data.by_label.Safe ?? 0, "safe"], ["Suspicious", data.by_label.Suspicious ?? 0, "suspicious"],
    ["Phishing", data.by_label.Phishing ?? 0, "phishing"], ["Spam", data.by_label.Spam ?? 0, "spam"], ["High risk", data.high_risk, "high_risk"],
  ] : [];

  return (
    <>
      <NetworkBackground /><div className="glow" /><Nav />
      <main className="wrap">
        <h1>{greet}, {user?.name.split(" ")[0]}</h1>
        <p className="sub">Your security overview</p>

        {!!error && !data && <ErrorState message={errMsg(error)} onRetry={reload} />}
        {!data && !error && <div className="stats">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} />)}</div>}

        {data && (
          <>
            <section className="hero2" aria-label="Security status">
              <div className="orb" data-s={data.state} aria-hidden="true" />
              <div>
                <h2>{data.state === "No data" ? "No scans yet" : data.state === "Clear" ? "All clear" : "Attention needed"}</h2>
                <p className="sub">{STATE_TEXT[data.state]}</p>
                <p className="last">
                  {data.last_scan ? <>Last scan: {data.last_scan.scan_type} · {data.last_scan.label} · {new Date(data.last_scan.created_at).toLocaleString()}</> : "Last scan: none yet"}
                </p>
              </div>
            </section>

            <div className="stats">
              {cards.map(([label, n, f], i) => (
                <motion.div key={label} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
                  <Link className="stat" to={f ? `/history?threat=${f}` : "/history"}>
                    <strong><CountUp to={n} /></strong><span>{label}</span>
                  </Link>
                </motion.div>
              ))}
            </div>

            {data.total === 0 ? (
              <EmptyState title="Your security workspace is ready" text="No scans have been analyzed yet.">
                <button className="btn primary" onClick={() => nav("/scan/website")}>Scan a website</button>
                <button className="btn" onClick={() => nav("/scan/message")}>Analyze a message</button>
              </EmptyState>
            ) : (
              <>
                <div className="charts3">
                  <DashboardCard title="Risk overview"><ThreatDistribution data={data.by_level} colors={RISK_COLORS} /></DashboardCard>
                  <DashboardCard title="Threat results"><ThreatDistribution data={data.by_label} /></DashboardCard>
                  <DashboardCard title="Detection by channel"><ChannelDistribution data={data.by_type} /></DashboardCard>
                </div>
                <div style={{ marginTop: 14, opacity: loading ? 0.6 : 1, transition: "opacity .2s" }}>
                  <ActivityChart data={data.activity} days={days} onDays={setDays} />
                </div>
                <DashboardCard title="Recent scans" action={<Link to="/history" className="more">View all</Link>}>
                  <ScanTable items={data.recent} />
                </DashboardCard>
              </>
            )}
          </>
        )}
      </main>
    </>
  );
}
