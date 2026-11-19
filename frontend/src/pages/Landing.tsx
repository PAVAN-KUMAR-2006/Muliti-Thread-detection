import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Activity, ArrowUpRight, LockKeyhole, ShieldCheck, ScanLine, BarChart3 } from "lucide-react";
import NetworkBackground from "../components/NetworkBackground";
import Nav from "../components/Nav";
import { useAuth } from "../context/AuthContext";

const kinds = [
  { k: "url", label: "🌐 Website", ph: "https://example.com", as: "input" },
  { k: "email", label: "📧 Email", ph: "Paste the email, including subject and sender…", as: "area" },
  { k: "msg", label: "📱 Message", ph: "Paste an SMS, WhatsApp or Telegram message…", as: "area" },
  { k: "qr", label: "📷 QR code", ph: "Drop a QR image or choose a file", as: "file" },
  { k: "phone", label: "📞 Phone", ph: "+91 98765 43210", as: "input" },
  { k: "file", label: "📁 File", ph: "PDF · DOCX · TXT · EML · CSV — drop or choose", as: "file" },
] as const;

const channels = [
  ["🌐", "Websites", "URL structure, domain traits and redirects scored by a trained model."],
  ["📧", "Email", "Sender, subject, body and links checked for urgency and impersonation."],
  ["💬", "Messages", "Paste SMS, WhatsApp or Telegram text to spot scam language."],
  ["📷", "QR codes", "Decode the link inside a code before you open it."],
  ["📞", "Phone numbers", "Community reports and past scans, not guesses from digits alone."],
  ["📁", "Files", "PDF, DOCX, TXT, CSV and EML read as text. Never executed."],
];

const threads = [
  { id: 1, label: "Thread #01", state: "Monitoring", color: "cyan", detail: "Live activity monitoring and suspicious behaviour signals." },
  { id: 2, label: "Thread #02", state: "Protected", color: "blue", detail: "Process activity checks with security-focused event tracking." },
  { id: 3, label: "Thread #03", state: "Analyzing", color: "violet", detail: "Anomaly review and thread-level activity inspection." },
  { id: 4, label: "Thread #04", state: "Connected", color: "cyan", detail: "Connected thread activity displayed in the visual monitor." },
];

function ThreadVisual() {
  const [active, setActive] = useState(0);
  return (
    <div className="thread-visual" aria-label="Interactive multi-thread security illustration">
      <div className="visual-orbit orbit-one" /><div className="visual-orbit orbit-two" />
      <motion.div
        className="core-platform"
        drag
        dragConstraints={{ left: -34, right: 34, top: -28, bottom: 28 }}
        dragElastic={0.16}
        whileHover={{ scale: 1.035 }}
        whileTap={{ scale: 0.97 }}
        aria-label="Drag the security shield to explore"
      >
        <div className="core-glow" />
        <div className="core-shield"><ShieldCheck size={82} strokeWidth={1.5} /></div>
        <div className="core-lock"><LockKeyhole size={27} /></div>
        <span className="core-caption">SECURE CORE</span>
      </motion.div>
      {threads.map((thread, index) => (
        <motion.button
          type="button"
          key={thread.id}
          className={`thread-node node-${index + 1} ${thread.color} ${active === index + 1 ? "selected" : ""}`}
          onClick={() => setActive(active === index + 1 ? 0 : index + 1)}
          whileHover={{ y: -5, scale: 1.04 }}
          whileTap={{ scale: 0.96 }}
          aria-pressed={active === index + 1}
        >
          <span className="node-top"><i />{thread.label}</span>
          <svg viewBox="0 0 150 32" aria-hidden="true"><path d={index % 2 === 0 ? "M2 18 C12 18 12 7 23 17 S36 27 45 13 S57 8 65 19 S77 27 86 12 S98 8 108 18 S125 23 148 10" : "M2 22 C15 22 15 11 27 16 S40 27 51 15 S66 8 76 19 S91 26 101 13 S116 8 128 18 S140 17 148 12"} /></svg>
          <small>{thread.state}</small>
        </motion.button>
      ))}
      <div className="visual-hint"><span className="hint-pulse" />Drag the shield · Tap a thread</div>
      {active > 0 && (
        <motion.div className="thread-detail" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} key={active}>
          <b>{threads[active - 1].label}</b><span>{threads[active - 1].detail}</span>
        </motion.div>
      )}
      <div className="visual-scanline" />
    </div>
  );
}

export default function Landing() {
  const [kind, setKind] = useState<(typeof kinds)[number]>(kinds[0]);
  const [value, setValue] = useState("");
  const [fileName, setFileName] = useState("");
  const { user } = useAuth();
  const nav = useNavigate();
  const pick = (k: (typeof kinds)[number]) => { setKind(k); setValue(""); setFileName(""); };

  return (
    <>
      <NetworkBackground />
      <div className="glow" />
      <Nav landing />
      <main>
        <section className="hero hero-sentinel">
          <motion.div className="hero-copy" initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.65 }}>
            <span className="pill"><b />Advanced Thread Analysis · Real-Time Detection</span>
            <h1>Multi-Thread <span>Detection.</span></h1>
            <p className="sub">Detect and analyze multi-thread based activities, identify suspicious threads and help keep your system secure.</p>
            <div className="hero-actions">
              <button className="btn primary hero-action" onClick={() => nav(user ? "/scan" : "/register")}><ScanLine size={18} />Start Scan</button>
              <button className="btn hero-action secondary-action" onClick={() => nav(user ? "/analytics" : "/login")}><ChartNoAxesCombined size={18} />View Reports</button>
            </div>
            <div className="scanner" id="scan">
              <div className="scanner-heading"><Activity size={17} /><span>Choose what you want to inspect</span></div>
              <div className="tabs" role="tablist" aria-label="What would you like to analyze?">
                {kinds.map((x) => (
                  <button key={x.k} className="tab" role="tab" aria-selected={kind.k === x.k} onClick={() => pick(x)}>{x.label}</button>
                ))}
              </div>
              <div className="field">
                {kind.as === "input" && <input aria-label={kind.label} placeholder={kind.ph} value={value} onChange={(e) => setValue(e.target.value)} />}
                {kind.as === "area" && <textarea aria-label={kind.label} rows={3} placeholder={kind.ph} value={value} onChange={(e) => setValue(e.target.value)} />}
                {kind.as === "file" && (
                  <label className="drop">{fileName || kind.ph}
                    <input type="file" hidden onChange={(e) => setFileName(e.target.files?.[0]?.name ?? "")} />
                  </label>
                )}
              </div>
              <button className="scanner-submit" onClick={() => nav(user ? "/scan" : "/register")}>Continue to secure scan <ArrowUpRight size={16} /></button>
            </div>
          </motion.div>
          <motion.div className="visual-wrap" initial={{ opacity: 0, scale: 0.92 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.8, delay: 0.12 }}>
            <div className="visual-label"><span>LIVE SYSTEM OVERVIEW</span><span className="live-dot">● LIVE</span></div>
            <ThreadVisual />
            <div className="visual-foot"><span><i /> Multi-thread monitor</span><span>Interactive preview</span></div>
          </motion.div>
        </section>
        <section className="ch" id="channels">
          <h2>One platform to inspect every digital channel.</h2>
          <p className="channels-intro">Explore the different inputs supported by the Sentinel threat analysis platform.</p>
          <div className="grid">
            {channels.map(([i, t, d]) => <div className="card" key={t}><div className="ico">{i}</div><h3>{t}</h3><p>{d}</p></div>)}
          </div>
        </section>
      </main>
      <footer>Multi-Thread Detection · Intelligent thread activity monitoring</footer>
    </>
  );
}
