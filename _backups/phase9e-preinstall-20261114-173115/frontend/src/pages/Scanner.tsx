import { Fragment, FormEvent, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import NetworkBackground from "../components/NetworkBackground";
import Nav from "../components/Nav";
import RiskGauge from "../components/RiskGauge";
import { ThreatBadge } from "../components/ThreatBadge";
import { IndicatorList } from "../components/IndicatorList";
import { DashboardCard } from "../components/Charts";
import DownloadPdf from "../components/DownloadPdf";
import { Alert } from "../components/AuthKit";
import axios from "axios";
import QrCamera from "../components/QrCamera";
import { decodeImageFile } from "../qr/decodeFrame";
import { api, errMsg } from "../services/api";
import { ScanDetails, ScanResult } from "../types";

type Kind = "website" | "email" | "message" | "qr" | "file";
const BASE = ["Initializing security engine"];
const CFG: Record<Kind, { title: string; lead: string; icon: string; stages: string[] }> = {
  website: { title: "Website scanner", lead: "Check a link before you open it. The URL is analysed as text and is never visited.", icon: "🌐",
    stages: [...BASE, "Extracting URL features", "Analyzing domain structure", "Running phishing detection model", "Calculating risk", "Generating explanation"] },
  email: { title: "Email scanner", lead: "Paste an email, or upload a .eml or .txt file.", icon: "📧",
    stages: [...BASE, "Reading the message", "Scoring language with the email model", "Checking linked URLs", "Calculating risk", "Generating explanation"] },
  message: { title: "Message scanner", lead: "Paste an SMS, WhatsApp, Telegram or other text message.", icon: "📱",
    stages: [...BASE, "Reading the message", "Running the message spam model", "Checking linked URLs", "Calculating risk", "Generating explanation"] },
  qr: { title: "QR code scanner", lead: "Upload a QR image or use your camera. Links inside are checked by the website model.", icon: "📷",
    stages: [...BASE, "Decoding the QR code", "Extracting the embedded data", "Running phishing detection model", "Calculating risk"] },
  file: { title: "File scanner", lead: "Upload a TXT, CSV, EML, PDF or DOCX file (max 5 MB). Files are read as data and never executed.", icon: "📁",
    stages: [...BASE, "Validating the file", "Extracting text and links", "Running the text model", "Checking linked URLs", "Calculating risk"] },
};
const HUB: [Kind, string][] = [["website", "Website"], ["email", "Email"], ["message", "Message"], ["qr", "QR code"], ["file", "File"]];

const noQrFound = (e: unknown) =>
  axios.isAxiosError(e) && e.response?.status === 422 && String(e.response.data?.detail ?? "").includes("No readable QR code");

export function ScanHub() {
  return (
    <>
      <NetworkBackground /><div className="glow" /><Nav />
      <main className="wrap">
        <h1>What would you like to analyze?</h1>
        <div className="stats" style={{ marginTop: 24 }}>
          {HUB.map(([k, n]) => <Link key={k} className="stat" to={`/scan/${k}`}><strong>{CFG[k].icon}</strong><span>{n}</span></Link>)}
        </div>
      </main>
    </>
  );
}

function Drop({ accept, file, onFile, hint }: { accept: string; file: File | null; onFile: (f: File) => void; hint: string }) {
  const [over, setOver] = useState(false);
  const ref = useRef<HTMLInputElement>(null);
  return (
    <div className={`drop ${over ? "over" : ""}`} role="button" tabIndex={0} onClick={() => ref.current?.click()}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); ref.current?.click(); } }}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files[0]; if (f) onFile(f); }}>
      {file ? `${file.name} · ${(file.size / 1024).toFixed(1)} KB` : hint}
      <input ref={ref} type="file" hidden accept={accept} onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); }} />
    </div>
  );
}

export function ResultView({ r }: { r: ScanResult }) {
  const d: ScanDetails = r.details ?? {};
  const notUrl = d.is_url === false;
  return (
    <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}>
      <section className="hero2 detail">
        <RiskGauge score={r.risk_score} />
        <div>
          <h1>{notUrl ? "NOT A URL" : r.label === "Safe" ? "NO THREAT DETECTED" : `${r.label.toUpperCase()} DETECTED`}</h1>
          <p className="sub">Risk score {Math.round(r.risk_score)}/100 · {r.confidence == null ? "No model was run" : `Model confidence ${Math.round(r.confidence * 100)}%`}</p>
          <p><ThreatBadge label={r.label} /> <Link className="more" to={`/history/${r.id}`}>Open saved scan</Link> <DownloadPdf id={r.id} /></p>
        </div>
      </section>
      <div className="charts2">
        <DashboardCard title="Why this result"><p>{r.explanation}</p><p className="sub" style={{ marginTop: 10 }}>{r.recommendation}</p></DashboardCard>
        <DashboardCard title="Factors raising risk"><IndicatorList items={r.indicators} /></DashboardCard>
      </div>
      <div className="charts2" style={{ marginTop: 14 }}>
        {(d.url || d.decoded || d.file || d.sender) && (
          <DashboardCard title="Details">
            <dl className="info">
              {d.decoded && <><dt>Decoded</dt><dd className="mono">{d.decoded}</dd></>}
              {d.url && <><dt>URL</dt><dd className="mono">{d.url}</dd><dt>Domain</dt><dd>{d.host}</dd><dt>HTTPS</dt><dd>{d.https ? "Yes" : "No"}</dd></>}
              {d.file && <><dt>File</dt><dd>{d.file.name}</dd><dt>Type · size</dt><dd>{d.file.type} · {(d.file.size / 1024).toFixed(1)} KB</dd><dt>SHA-256</dt><dd className="mono">{d.file.sha256}</dd></>}
              {d.sender && <><dt>Sender</dt><dd>{d.sender}</dd></>}
              {d.subject && <><dt>Subject</dt><dd>{d.subject}</dd></>}
              <dt>Status</dt><dd>{r.status}</dd>
            </dl>
          </DashboardCard>
        )}
        {d.urls && d.urls.length > 0 && (
          <DashboardCard title="Detected URLs"><ul className="ind">{d.urls.map((u) => (
            <li key={u.url}><div className="row"><span className="mono">{u.url.slice(0, 70)}</span><span>{u.phishing_probability == null ? "not scored" : `${Math.round(u.phishing_probability * 100)}%`}</span></div></li>))}</ul></DashboardCard>
        )}
        {d.features && <DashboardCard title="URL characteristics"><dl className="info">{Object.entries(d.features).map(([k, v]) => <Fragment key={k}><dt>{k}</dt><dd>{v}</dd></Fragment>)}</dl></DashboardCard>}
        {r.protective.length > 0 && <DashboardCard title="Factors lowering risk"><IndicatorList items={r.protective} /></DashboardCard>}
      </div>
    </motion.div>
  );
}

export default function Scanner() {
  const kind = useParams().kind as Kind;
  const cfg = CFG[kind];
  const [url, setUrl] = useState(""); const [subject, setSubject] = useState(""); const [body, setBody] = useState("");
  const [platform, setPlatform] = useState("sms"); const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false); const [stage, setStage] = useState(0); const [prog, setProg] = useState<number | null>(null);
  const [error, setError] = useState(""); const [result, setResult] = useState<ScanResult | null>(null);
  const [cam, setCam] = useState(false); const [preview, setPreview] = useState("");

  useEffect(() => {
    if (!busy || !cfg) { setStage(0); return; }
    const t = setInterval(() => setStage((s) => Math.min(s + 1, cfg.stages.length - 1)), 700);
    return () => clearInterval(t);
  }, [busy, cfg]);
  useEffect(() => { setResult(null); setError(""); setFile(null); setCam(false); }, [kind]);
  useEffect(() => {
    if (kind !== "qr" || !file) { setPreview(""); return; }
    const u = URL.createObjectURL(file); setPreview(u);
    return () => URL.revokeObjectURL(u);
  }, [file, kind]);

  const run = async (fn: () => Promise<ScanResult>) => {
    setError(""); setResult(null); setBusy(true); setProg(null);
    try { setResult(await fn()); } catch (e) { setError(errMsg(e)); }
    setBusy(false); setProg(null);
  };
  const upload = (path: string, f: File) => () => {
    const fd = new FormData(); fd.append("file", f);
    return api.post<ScanResult>(path, fd, { onUploadProgress: (e) => setProg(e.total ? Math.round((e.loaded / e.total) * 100) : null) }).then((r) => r.data);
  };


  if (!cfg) return <><Nav /><main className="dash"><h1>Scanner not found</h1><Link to="/scan" className="more">Back to scanners</Link></main></>;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (kind === "website") {
      try { const u = new URL(url.includes("://") ? url : `http://${url}`); if (!u.hostname.includes(".") || /\s/.test(url.trim())) throw 0; }
      catch { return setError("Enter a valid URL, for example https://example.com."); }
      return run(() => api.post<ScanResult>("/scan/website", { url: url.trim() }).then((r) => r.data));
    }
    if (kind === "qr" || kind === "file") {
      if (!file) return setError(kind === "qr" ? "Choose a QR image first." : "Choose a file first.");
      if (kind === "qr") {
        return run(async () => {
          try { return await upload("/scan/qr", file)(); }
          catch (e) {
            if (!noQrFound(e)) throw e;
            const text = await decodeImageFile(file).catch(() => null); // independent decoder, runs in the browser
            if (!text) throw e;
            return (await api.post<ScanResult>("/scan/qr-text", { content: text })).data;
          }
        });
      }
      return run(upload("/scan/file", file));
    }
    if (kind === "email" && file) return run(upload("/scan/email-upload", file));
    if (body.trim().length < 3) return setError("Enter the text to analyze.");
    run(() => api.post<ScanResult>(`/scan/${kind}`, kind === "email" ? { subject, body } : { text: body, platform }).then((r) => r.data));
  };
  const clear = () => { setUrl(""); setSubject(""); setBody(""); setFile(null); setResult(null); setError(""); };

  return (
    <>
      <NetworkBackground /><div className="glow" /><Nav />
      <main className="wrap">
        <Link to="/scan" className="more">← All scanners</Link>
        <h1>{cfg.icon} {cfg.title}</h1>
        <p className="sub">{cfg.lead}</p>
        <form className="panel2 scanform" onSubmit={submit} noValidate>
          {kind === "website" && <input aria-label="URL to scan" placeholder="https://example.com" value={url} onChange={(e) => setUrl(e.target.value)} />}
          {kind === "email" && <input aria-label="Email subject" placeholder="Subject" value={subject} onChange={(e) => setSubject(e.target.value)} />}
          {(kind === "email" || kind === "message") && <textarea aria-label="Text to scan" rows={7} placeholder={kind === "email" ? "Paste the email body…" : "Paste the message…"} value={body} onChange={(e) => setBody(e.target.value)} />}
          {kind === "message" && <select aria-label="Platform" value={platform} onChange={(e) => setPlatform(e.target.value)}>{["sms", "whatsapp", "telegram", "instagram", "other"].map((p) => <option key={p}>{p}</option>)}</select>}
          {kind === "email" && <Drop accept=".eml,.txt" file={file} onFile={setFile} hint="…or drop a .eml / .txt file here (it replaces the pasted text)" />}
          {kind === "qr" && <Drop accept="image/png,image/jpeg,image/webp" file={file} onFile={setFile} hint="Drop a QR image here, or click to choose (PNG, JPEG, WEBP)" />}
          {kind === "file" && <Drop accept=".txt,.csv,.eml,.pdf,.docx" file={file} onFile={setFile} hint="Drop a file here, or click to choose (TXT · CSV · EML · PDF · DOCX)" />}
          {preview && <img className="preview" src={preview} alt="QR preview" />}
          {cam && <QrCamera onClose={() => setCam(false)} onDecoded={(text) => { setCam(false); run(() => api.post<ScanResult>("/scan/qr-text", { content: text }).then((r) => r.data)); }} />}
          <div className="cta-row">
            <button className="btn primary" disabled={busy}>{busy ? "Scanning…" : "Scan now"}</button>
            <button type="button" className="btn" onClick={clear} disabled={busy}>Clear</button>
            {kind === "website" && <button type="button" className="btn" onClick={() => setUrl("http://secure-login.account-verify.example-bank.com.xyz/update?id=1")}>Use example URL</button>}
            {kind === "qr" && <button type="button" className="btn" onClick={() => setCam(!cam)} disabled={busy}>{cam ? "Stop camera" : "Use camera"}</button>}
          </div>
        </form>
        {error && <Alert>{error}</Alert>}
        {busy && prog !== null && prog < 100 && <div className="bar" aria-label={`Upload ${prog}%`}><i style={{ width: `${prog}%`, background: "var(--cyan)" }} /></div>}
        {busy && (
          <ul className="stages" aria-live="polite">
            {cfg.stages.map((s, i) => <li key={s} className={i < stage ? "done" : i === stage ? "now" : ""}>{i < stage ? "✓" : i === stage ? "●" : "○"} {s}</li>)}
          </ul>
        )}
        {result && <ResultView r={result} />}
      </main>
    </>
  );
}
