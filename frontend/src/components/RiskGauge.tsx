import { useEffect, useState } from "react";
import { RiskLevel } from "../types";

export const levelOf = (s: number): RiskLevel => (s > 80 ? "CRITICAL" : s > 60 ? "HIGH" : s > 30 ? "MEDIUM" : "LOW");
export const LEVEL_COLOR: Record<RiskLevel, string> = { LOW: "#34d399", MEDIUM: "#fbbf24", HIGH: "#f87171", CRITICAL: "#ef4444" };

export function CountUp({ to }: { to: number }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    let raf = 0; const t0 = performance.now();
    const step = (t: number) => { const p = Math.min(1, (t - t0) / 900); setN(Math.round(to * (1 - Math.pow(1 - p, 3)))); if (p < 1) raf = requestAnimationFrame(step); };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [to]);
  return <>{n}</>;
}

export default function RiskGauge({ score, size = 190 }: { score: number; size?: number }) {
  const [v, setV] = useState(0);
  useEffect(() => { const id = requestAnimationFrame(() => setV(score)); return () => cancelAnimationFrame(id); }, [score]);
  const level = levelOf(score);
  const color = LEVEL_COLOR[level];
  return (
    <div className="gauge" style={{ width: size, height: size }} role="img" aria-label={`Risk score ${Math.round(score)} out of 100, ${level}`}>
      <svg viewBox="0 0 180 180" width={size} height={size}>
        <circle className="trk" cx="90" cy="90" r="80" />
        <circle className="val" cx="90" cy="90" r="80" style={{ stroke: color, strokeDashoffset: 502 * (1 - v / 100), filter: `drop-shadow(0 0 8px ${color})` }} />
      </svg>
      <div><strong><CountUp to={Math.round(score)} /></strong><small>{level} risk</small></div>
    </div>
  );
}
