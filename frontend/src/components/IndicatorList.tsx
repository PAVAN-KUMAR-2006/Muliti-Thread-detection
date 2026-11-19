import { motion } from "framer-motion";
import { Indicator } from "../types";

const TONE: Record<string, string> = { high: "var(--risk)", medium: "var(--warn)", low: "var(--safe)" };

export function IndicatorList({ items }: { items: Indicator[] }) {
  if (!items.length) return <p className="sub">No indicators were recorded for this scan.</p>;
  return (
    <ul className="ind">
      {items.map((i, k) => (
        <li key={`${i.name}-${k}`}>
          <div className="row"><span>{i.name}</span><span style={{ color: TONE[i.severity.toLowerCase()] }}>{i.severity}</span></div>
          <div className="bar"><motion.i style={{ background: TONE[i.severity.toLowerCase()] ?? "var(--cyan)" }} initial={{ width: 0 }} animate={{ width: `${Math.min(100, Math.max(4, i.weight * 100))}%` }} transition={{ duration: 0.9, delay: k * 0.06 }} /></div>
        </li>
      ))}
    </ul>
  );
}

export function ScanTimeline({ events }: { events: { title: string; detail?: string }[] }) {
  return (
    <ol className="tl">
      {events.map((e, k) => <li key={k}><b>{e.title}</b>{e.detail && <span>{e.detail}</span>}</li>)}
    </ol>
  );
}
