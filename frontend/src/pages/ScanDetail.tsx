import axios from "axios";
import { Link, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import NetworkBackground from "../components/NetworkBackground";
import Nav from "../components/Nav";
import RiskGauge from "../components/RiskGauge";
import { ScanStatus, ThreatBadge } from "../components/ThreatBadge";
import { IndicatorList, ScanTimeline } from "../components/IndicatorList";
import { DashboardCard } from "../components/Charts";
import DownloadPdf from "../components/DownloadPdf";
import { ErrorState, Skeleton } from "../components/States";
import { useApi } from "../hooks/useApi";
import { errMsg } from "../services/api";
import { ScanDetail as Detail } from "../types";

export default function ScanDetail() {
  const { id } = useParams();
  const { data: s, error, reload } = useApi<Detail>(`/history/${id}`);
  const notFound = axios.isAxiosError(error) && (error.response?.status === 404 || error.response?.status === 422);

  const headline = s ? (s.label === "Safe" ? "NO THREAT DETECTED" : `${s.label.toUpperCase()} DETECTED`) : "";
  const events = s ? [
    { title: "Scan recorded", detail: new Date(s.created_at).toLocaleString() },
    ...s.predictions.map((p) => ({ title: `${p.model_name} v${p.model_version}`, detail: `Probability ${(p.probability * 100).toFixed(1)}%` })),
    { title: `Status: ${s.status}` },
  ] : [];

  return (
    <>
      <NetworkBackground /><div className="glow" /><Nav />
      <main className="wrap">
        <Link to="/history" className="more">← Back to history</Link>
        {!!error && !s && (notFound ? <ErrorState message="This scan does not exist or is not in your account." /> : <ErrorState message={errMsg(error)} onRetry={reload} />)}
        {!s && !error && <><Skeleton h={220} /><br /><Skeleton h={160} /></>}
        {s && (
          <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}>
            <section className="hero2 detail">
              <RiskGauge score={s.risk_score} />
              <div>
                <h1>{headline}</h1>
                <p className="sub">Risk score {Math.round(s.risk_score)}/100 · Confidence {s.confidence == null ? "not available" : `${Math.round(s.confidence * 100)}%`}</p>
                <p><ThreatBadge label={s.label} /> <ScanStatus status={s.status} /> <DownloadPdf id={s.id} /></p>
              </div>
            </section>
            <div className="charts2">
              <DashboardCard title="Scan information">
                <dl className="info">
                  <dt>Scan ID</dt><dd>{s.id}</dd>
                  <dt>Type</dt><dd>{s.scan_type}</dd>
                  <dt>Date</dt><dd>{new Date(s.created_at).toLocaleString()}</dd>
                  <dt>Classification</dt><dd>{s.label}</dd>
                  <dt>Processing</dt><dd>{s.status}</dd>
                  <dt>Input</dt><dd className="mono">{s.input_summary}</dd>
                </dl>
              </DashboardCard>
              <DashboardCard title="Detected indicators"><IndicatorList items={s.indicators} /></DashboardCard>
            </div>
            <div className="charts2" style={{ marginTop: 14 }}>
              <DashboardCard title="Explanation and recommended action">
                <p>{s.explanation || "No explanation was recorded for this scan."}</p>
                <p className="sub" style={{ marginTop: 10 }}>{s.recommendation || "No recommendation was recorded for this scan."}</p>
              </DashboardCard>
              <DashboardCard title="Timeline"><ScanTimeline events={events} /></DashboardCard>
            </div>
          </motion.div>
        )}
      </main>
    </>
  );
}
