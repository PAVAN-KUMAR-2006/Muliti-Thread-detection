import { ReactNode } from "react";
import { motion } from "framer-motion";
import { Area, AreaChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import type { ActivityPoint, ChannelDistribution as ChannelDistributionData } from "../types";
import { LEVEL_COLOR } from "./RiskGauge";

export const LABEL_COLOR: Record<string, string> = { Safe: "#34d399", Suspicious: "#fbbf24", Phishing: "#f87171", Spam: "#8b7cff", Scam: "#fb923c" };
const tip = { background: "var(--bg2)", border: "1px solid var(--line)", borderRadius: 10, color: "var(--text)" };

export function DashboardCard({ title, children, action }: { title: string; children: ReactNode; action?: ReactNode }) {
  return (
    <motion.section className="panel2" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}>
      <div className="phead"><h3>{title}</h3>{action}</div>
      {children}
    </motion.section>
  );
}

/** Donut used for both the threat-label distribution and the risk-level distribution. */
export function ThreatDistribution({ data, colors = LABEL_COLOR }: { data: Record<string, number>; colors?: Record<string, string> }) {
  const rows = Object.entries(data).map(([name, value]) => ({ name, value }));
  if (rows.every((r) => r.value === 0)) return <p className="sub">Nothing to chart yet.</p>;
  return (
    <>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart><Pie data={rows.filter((r) => r.value > 0)} dataKey="value" nameKey="name" innerRadius={52} outerRadius={80} paddingAngle={3} stroke="none">
          {rows.filter((r) => r.value > 0).map((r) => <Cell key={r.name} fill={colors[r.name] ?? "#4cc9f0"} />)}</Pie><Tooltip contentStyle={tip} /></PieChart>
      </ResponsiveContainer>
      <ul className="legend">{rows.map((r) => <li key={r.name}><i style={{ background: colors[r.name] }} />{r.name} <b>{r.value}</b></li>)}</ul>
    </>
  );
}
export const RISK_COLORS = LEVEL_COLOR;

export function ActivityChart({ data, days, onDays }: { data: ActivityPoint[]; days: number; onDays: (d: 7 | 30 | 90) => void }) {
  return (
    <DashboardCard title="Scan activity" action={
      <div className="seg" role="group" aria-label="Time range">
        {([7, 30, 90] as const).map((d) => <button key={d} aria-pressed={days === d} onClick={() => onDays(d)}>{d}d</button>)}
      </div>}>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={data}>
          <defs><linearGradient id="act" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#4cc9f0" stopOpacity={0.45} /><stop offset="100%" stopColor="#8b7cff" stopOpacity={0} /></linearGradient></defs>
          <XAxis dataKey="date" tick={{ fill: "#8c9bbd", fontSize: 11 }} tickFormatter={(d: string) => d.slice(5)} interval="preserveStartEnd" axisLine={false} tickLine={false} />
          <Tooltip contentStyle={tip} />
          <Area type="monotone" dataKey="count" name="Scans" stroke="#4cc9f0" strokeWidth={2} fill="url(#act)" />
        </AreaChart>
      </ResponsiveContainer>
    </DashboardCard>
  );
}

const NAMES: Record<string, string> = { website: "Website", email: "Email", message: "Message", qr: "QR", phone: "Phone", file: "File" };

export function ChannelDistribution({ data }: { data: ChannelDistributionData }) {
  const max = Math.max(1, ...Object.values(data));
  return (
    <ul className="chan">
      {Object.entries(data).map(([k, v], i) => (
        <li key={k}>
          <span>{NAMES[k] ?? k}</span>
          <div className="bar"><motion.i initial={{ width: 0 }} animate={{ width: `${(v / max) * 100}%` }} transition={{ duration: 0.9, delay: i * 0.05 }} style={{ background: "linear-gradient(90deg,var(--cyan),var(--violet))" }} /></div>
          <b>{v}</b>
        </li>
      ))}
    </ul>
  );
}
