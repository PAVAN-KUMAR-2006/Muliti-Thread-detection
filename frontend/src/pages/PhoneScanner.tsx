import { FormEvent, Fragment, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import NetworkBackground from "../components/NetworkBackground";
import Nav from "../components/Nav";
import RiskGauge from "../components/RiskGauge";
import { ThreatBadge } from "../components/ThreatBadge";
import { IndicatorList } from "../components/IndicatorList";
import { DashboardCard } from "../components/Charts";
import { Alert } from "../components/AuthKit";
import { Async } from "../components/Async";
import { useApi } from "../hooks/useApi";
import { api, errMsg } from "../services/api";
import { validatePhoneInput } from "../phone/validate";
import { PhoneReportItem, PhoneScanResult, Region } from "../phone/types";
import "../styles/phone.css";

const CATEGORIES = ["Spam Call", "Financial Scam", "Banking Fraud", "OTP Scam", "Impersonation", "Robocall", "Telemarketing", "Other"];
const STAGES = ["Validating the number format", "Checking community reports", "Applying the risk rules", "Writing the explanation"];

function regionName(code: string) {
  try { return new Intl.DisplayNames([navigator.language || "en"], { type: "region" }).of(code) ?? code; } catch { return code; }
}

function RegionSelect({ regions, value, onChange, id }: { regions: Region[]; value: string; onChange: (v: string) => void; id: string }) {
  const sorted = useMemo(() => [...regions].map((r) => ({ ...r, name: regionName(r.region) })).sort((a, b) => a.name.localeCompare(b.name)), [regions]);
  return (
    <select id={id} aria-label="Country" value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">Number starts with +</option>
      {sorted.map((r) => <option key={r.region} value={r.region}>{r.name} ({r.dial_code})</option>)}
    </select>
  );
}

export function PhoneResult({ r, onReport }: { r: PhoneScanResult; onReport?: () => void }) {
  const d = r.details;
  const scored = r.risk_score !== null;
  const ev = d?.evidence;
  return (
    <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}>
      <section className="hero2 detail">
        {scored ? <RiskGauge score={r.risk_score as number} /> : <div className="notscored" role="img" aria-label="Not scored">Not scored: no reports to analyse</div>}
        <div>
          <h1>{r.classification.toUpperCase()}</h1>
          <p className="sub">{scored ? `Community evidence score ${Math.round(r.risk_score as number)}/100 · ${r.risk_level} risk` : "No risk score: there is no evidence to score yet."}
            {d?.evidence_level && d.evidence_level !== "none" ? ` · ${d.evidence_level} evidence` : ""}</p>
          <p><ThreatBadge label={r.label} /> <Link className="more" to={`/history/${r.id}`}>Open saved scan</Link> {onReport && <button className="btn" onClick={onReport}>Report this number</button>}</p>
        </div>
      </section>
      <div className="charts2">
        <DashboardCard title="Why this result"><p>{r.explanation}</p><p className="sub" style={{ marginTop: 10 }}>{r.recommendation}</p></DashboardCard>
        <DashboardCard title="Indicators"><IndicatorList items={r.indicators ?? []} /></DashboardCard>
      </div>
      <div className="charts2" style={{ marginTop: 14 }}>
        {d && (
          <DashboardCard title="Number details">
            <dl className="info">
              <dt>Number</dt><dd className="mono">{d.number_display}</dd>
              <dt>Normalized</dt><dd className="mono">{d.normalized}</dd>
              <dt>Country</dt><dd>{d.region ? `${regionName(d.region)} (${d.country_code})` : d.country_code}</dd>
              <dt>Type</dt><dd>{d.number_type}</dd>
              <dt>Format</dt><dd>{d.format_valid ? "Valid format (this is not a safety check)" : "Invalid"}</dd>
            </dl>
          </DashboardCard>
        )}
        {ev && (
          <DashboardCard title="Community evidence">
            <p><b>{ev.reports}</b> {ev.reports === 1 ? "report" : "reports"} from <b>{ev.reporters}</b> {ev.reporters === 1 ? "user" : "users"}
              {ev.last_report_days_ago !== null ? `, latest ${ev.last_report_days_ago} day(s) ago` : ""}</p>
            {Object.keys(ev.categories).length > 0 && <ul className="evchips" aria-label="Report categories">{Object.entries(ev.categories).map(([k, v]) => <li key={k}>{k}<b style={{ marginLeft: 8 }}>{v}</b></li>)}</ul>}
            {scored && d.score_breakdown.length > 0 && (
              <table className="bd" style={{ marginTop: 12 }}><caption className="sub" style={{ textAlign: "left" }}>Score breakdown</caption>
                <tbody>{d.score_breakdown.map((b, i) => <Fragment key={i}><tr><td>{b.rule}</td><td>+{b.points}</td></tr></Fragment>)}</tbody></table>
            )}
          </DashboardCard>
        )}
      </div>
      {d && <p className="note9e">Source: {d.intel_source}. Reports are submitted by Sentinel users and are not independently verified. Sentinel never calls or messages the number.</p>}
    </motion.div>
  );
}

function ReportForm({ regions, defaultRegion, initialNumber, onDone }: { regions: Region[]; defaultRegion: string; initialNumber: string; onDone: () => void }) {
  const [number, setNumber] = useState(initialNumber);
  const [region, setRegion] = useState(defaultRegion);
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [description, setDescription] = useState("");
  const [evidence, setEvidence] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  useEffect(() => { if (initialNumber) setNumber(initialNumber); }, [initialNumber]);

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setError(""); setOk("");
    const v = validatePhoneInput(number, region);
    if (v) return setError(v);
    if (description.trim().length < 10) return setError("Describe what happened in at least 10 characters.");
    setBusy(true);
    try {
      await api.post("/phone/reports", { number: number.trim(), region: region || undefined, category, description: description.trim(), evidence: evidence.trim() || undefined });
      setOk("Report submitted. Thank you: it helps other Sentinel users."); setDescription(""); setEvidence(""); onDone();
    } catch (err) { setError(errMsg(err)); }
    setBusy(false);
  };

  return (
    <form className="panel2 scanform" onSubmit={submit} noValidate aria-label="Report a phone number">
      <div className="phrow">
        <RegionSelect id="rep-region" regions={regions} value={region} onChange={setRegion} />
        <input aria-label="Phone number to report" inputMode="tel" autoComplete="off" placeholder="Phone number" value={number} onChange={(e) => setNumber(e.target.value)} />
      </div>
      <select aria-label="Report category" value={category} onChange={(e) => setCategory(e.target.value)}>{CATEGORIES.map((c) => <option key={c}>{c}</option>)}</select>
      <textarea aria-label="What happened" rows={4} maxLength={1000} placeholder="What happened? (10 to 1000 characters)" value={description} onChange={(e) => setDescription(e.target.value)} />
      <div className="charcount">{description.length}/1000</div>
      <input aria-label="Evidence or reference (optional)" maxLength={500} placeholder="Evidence or reference (optional). It is stored as text and never opened." value={evidence} onChange={(e) => setEvidence(e.target.value)} />
      {error && <Alert>{error}</Alert>}
      {ok && <Alert kind="ok">{ok}</Alert>}
      <div className="cta-row"><button className="btn primary" disabled={busy}>{busy ? "Submitting…" : "Submit report"}</button></div>
      <p className="sub" style={{ fontSize: 12 }}>Your identity is never shown to other users. Duplicate reports in the same category are rejected.</p>
    </form>
  );
}

export default function PhoneScanner() {
  const [tab, setTab] = useState<"scan" | "report" | "mine">("scan");
  const regionsQ = useApi<Region[]>("/phone/regions");
  const mine = useApi<PhoneReportItem[]>("/phone/reports", { limit: 20 });
  const [region, setRegion] = useState("");
  const [number, setNumber] = useState("");
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState(0);
  const [error, setError] = useState("");
  const [result, setResult] = useState<PhoneScanResult | null>(null);

  useEffect(() => {
    if (region || !regionsQ.data) return;
    const guess = (navigator.language.split("-")[1] ?? "").toUpperCase();
    setRegion(regionsQ.data.some((r) => r.region === guess) ? guess : regionsQ.data.some((r) => r.region === "IN") ? "IN" : "");
  }, [regionsQ.data, region]);
  useEffect(() => {
    if (!busy) { setStage(0); return; }
    const t = setInterval(() => setStage((s) => Math.min(s + 1, STAGES.length - 1)), 600);
    return () => clearInterval(t);
  }, [busy]);

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setError(""); setResult(null);
    const v = validatePhoneInput(number, region);
    if (v) return setError(v);
    setBusy(true);
    try { setResult((await api.post<PhoneScanResult>("/phone/scan", { number: number.trim(), region: region || undefined })).data); }
    catch (err) { setError(errMsg(err)); }
    setBusy(false);
  };
  const clear = () => { setNumber(""); setResult(null); setError(""); };

  return (
    <>
      <NetworkBackground /><div className="glow" /><Nav />
      <main className="wrap">
        <Link to="/scan" className="more">← All scanners</Link>
        <h1>📞 Phone number checker</h1>
        <p className="sub">Check a number against reports from Sentinel users, or report a suspicious one. Sentinel never calls or messages the number, and a valid format is not proof that a number is safe.</p>
        <div className="seg phtabs" role="group" aria-label="Phone tools">
          <button aria-pressed={tab === "scan"} onClick={() => setTab("scan")}>Check a number</button>
          <button aria-pressed={tab === "report"} onClick={() => setTab("report")}>Report a number</button>
          <button aria-pressed={tab === "mine"} onClick={() => setTab("mine")}>My reports</button>
        </div>

        {regionsQ.error && !regionsQ.data ? <Alert>Could not load the country list. {errMsg(regionsQ.error)}</Alert> : null}

        {tab === "scan" && (
          <>
            <form className="panel2 scanform" onSubmit={submit} noValidate aria-label="Check a phone number">
              <div className="phrow">
                <RegionSelect id="scan-region" regions={regionsQ.data ?? []} value={region} onChange={setRegion} />
                <input aria-label="Phone number" inputMode="tel" autoComplete="off" placeholder="e.g. 98765 43210 or +1 650 253 0000" value={number} onChange={(e) => setNumber(e.target.value)} />
              </div>
              <div className="cta-row">
                <button className="btn primary" disabled={busy || !regionsQ.data}>{busy ? "Checking…" : "Check number"}</button>
                <button type="button" className="btn" onClick={clear} disabled={busy}>Clear</button>
              </div>
            </form>
            {error && <Alert>{error}</Alert>}
            {busy && <ul className="stages" aria-live="polite">{STAGES.map((s, i) => <li key={s} className={i < stage ? "done" : i === stage ? "now" : ""}>{i < stage ? "✓" : i === stage ? "●" : "○"} {s}</li>)}</ul>}
            {result && <PhoneResult r={result} onReport={() => { setTab("report"); }} />}
          </>
        )}

        {tab === "report" && (
          <ReportForm regions={regionsQ.data ?? []} defaultRegion={region} initialNumber={result?.details.normalized ?? number} onDone={mine.reload} />
        )}

        {tab === "mine" && (
          <DashboardCard title="Reports you submitted">
            <Async q={mine} h={120}>
              {(items) => items.length === 0 ? <p className="sub">You have not reported any numbers yet.</p> : (
                <ul className="myrep">{items.map((r) => (
                  <li key={r.id}><b>{r.category}</b> · <span className="mono">{r.number_display}</span>
                    <small>{new Date(r.created_at).toLocaleString()}</small><p>{r.description}</p>{r.evidence && <small>Reference: {r.evidence}</small>}</li>))}</ul>
              )}
            </Async>
          </DashboardCard>
        )}
      </main>
    </>
  );
}
