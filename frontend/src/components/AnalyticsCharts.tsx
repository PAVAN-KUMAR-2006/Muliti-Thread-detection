import { Area, AreaChart, Bar, BarChart, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ActivityPoint, ThreatTrendPoint } from "../types";

const tip = { background: "var(--bg2)", border: "1px solid var(--line)", borderRadius: 10, color: "var(--text)" };
const tick = { fill: "#8c9bbd", fontSize: 11 };
const CHANNEL_COLOR: Record<string, string> = { website: "#4cc9f0", email: "#8b7cff", message: "#34d399", qr: "#fbbf24", file: "#fb923c", phone: "#94a3b8" };
const cap = (s: string) => s[0].toUpperCase() + s.slice(1);

export function ScannerUsageChart({ items }: { items: { name: string; count: number }[] }) {
  const rows = items.map((i) => ({ ...i, label: cap(i.name) }));
  return (
    <ResponsiveContainer width="100%" height={Math.max(180, rows.length * 44)}>
      <BarChart data={rows} layout="vertical" margin={{ left: 0, right: 24 }}>
        <XAxis type="number" allowDecimals={false} tick={tick} axisLine={false} tickLine={false} />
        <YAxis type="category" dataKey="label" width={72} tick={tick} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={tip} cursor={{ fill: "rgba(140,170,230,.08)" }} formatter={(v: number) => [v, "Scans"]} />
        <Bar dataKey="count" radius={[0, 8, 8, 0]} animationDuration={900}>{rows.map((r) => <Cell key={r.name} fill={CHANNEL_COLOR[r.name] ?? "#4cc9f0"} />)}</Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

const axisDate = (d: string) => d.slice(5);

export function ScanTrendChart({ points }: { points: ActivityPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={points}>
        <defs><linearGradient id="an-act" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#4cc9f0" stopOpacity={0.45} /><stop offset="100%" stopColor="#8b7cff" stopOpacity={0} /></linearGradient></defs>
        <XAxis dataKey="date" tick={tick} tickFormatter={axisDate} interval="preserveStartEnd" minTickGap={24} axisLine={false} tickLine={false} />
        <YAxis allowDecimals={false} width={28} tick={tick} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={tip} />
        <Area type="monotone" dataKey="count" name="Scans" stroke="#4cc9f0" strokeWidth={2} fill="url(#an-act)" animationDuration={900} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function ThreatTrendChart({ points }: { points: ThreatTrendPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={points}>
        <XAxis dataKey="date" tick={tick} tickFormatter={axisDate} interval="preserveStartEnd" minTickGap={24} axisLine={false} tickLine={false} />
        <YAxis allowDecimals={false} width={28} tick={tick} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={tip} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Area type="monotone" dataKey="phishing" name="Phishing" stroke="#f87171" fill="#f87171" fillOpacity={0.15} strokeWidth={2} animationDuration={900} />
        <Area type="monotone" dataKey="spam" name="Spam" stroke="#8b7cff" fill="#8b7cff" fillOpacity={0.15} strokeWidth={2} animationDuration={900} />
        <Area type="monotone" dataKey="scam" name="Scam" stroke="#fb923c" fill="#fb923c" fillOpacity={0.15} strokeWidth={2} animationDuration={900} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
