export interface Filters { q: string; type: string; threat: string; risk: string; from: string; to: string; sort: string }
export const EMPTY_FILTERS: Filters = { q: "", type: "", threat: "", risk: "", from: "", to: "", sort: "newest" };
const TYPES = ["website", "email", "message", "qr", "phone", "file"];

export default function ScanFilters({ value, onChange }: { value: Filters; onChange: (f: Filters) => void }) {
  const set = (k: keyof Filters, v: string) => onChange({ ...value, [k]: v });
  return (
    <div>
      <div className="chips" role="group" aria-label="Scan type">
        <button aria-pressed={value.type === ""} onClick={() => set("type", "")}>All</button>
        {TYPES.map((t) => <button key={t} aria-pressed={value.type === t} onClick={() => set("type", t)}>{t[0].toUpperCase() + t.slice(1)}</button>)}
      </div>
      <div className="filters">
        <input aria-label="Search scans" placeholder="Search URL, message, result or type…" value={value.q} onChange={(e) => set("q", e.target.value)} />
        <select aria-label="Threat" value={value.threat} onChange={(e) => set("threat", e.target.value)}>
          <option value="">All threats</option>
          <option value="threat">Any threat</option>
          {["safe", "suspicious", "spam", "phishing", "scam", "high_risk"].map((t) => <option key={t} value={t}>{t === "high_risk" ? "High risk" : t[0].toUpperCase() + t.slice(1)}</option>)}
        </select>
        <select aria-label="Risk level" value={value.risk} onChange={(e) => set("risk", e.target.value)}>
          <option value="">All risk levels</option>{["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((r) => <option key={r}>{r}</option>)}
        </select>
        <select aria-label="Sort" value={value.sort} onChange={(e) => set("sort", e.target.value)}>
          <option value="newest">Newest</option><option value="oldest">Oldest</option><option value="risk_desc">Highest risk</option><option value="risk_asc">Lowest risk</option>
        </select>
        <input type="date" aria-label="From date" value={value.from} onChange={(e) => set("from", e.target.value)} />
        <input type="date" aria-label="To date" value={value.to} onChange={(e) => set("to", e.target.value)} />
      </div>
    </div>
  );
}
