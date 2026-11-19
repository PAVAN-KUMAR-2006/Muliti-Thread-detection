import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Activity, ArrowUpRight, BarChart3, LockKeyhole, ScanLine, ShieldCheck } from "lucide-react";
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
  { id: 1, label: "Thread 01", state: "Monitoring", detail: "Live activity monitoring and suspicious behaviour signals." },
  { id: 2, label: "Thread 02", state: "Protected", detail: "Process activity checks with security-focused event tracking." },
  { id: 3, label: "Thread 03", state: "Analyzing", detail: "Anomaly review and thread-level activity inspection." },
];

function CosmicSecurityVisual() {
  const [active, setActive] = useState(0);

  return (
    <div className="cosmic-visual" aria-label="Interactive moon and cybersecurity shield visualization">
      <div className="cosmic-stars stars-a" />
      <div className="cosmic-stars stars-b" />
      <div className="particle-stream stream-one" />
      <div className="particle-stream stream-two" />

      <svg className="cosmic-orbit orbit-back" viewBox="0 0 700 430" aria-hidden="true">
        <ellipse cx="350" cy="215" rx="300" ry="104" />
        <ellipse cx="350" cy="215" rx="270" ry="145" transform="rotate(-23 350 215)" />
      </svg>

      <motion.div
        className="cosmic-object"
        drag
        dragConstraints={{ left: -42, right: 42, top: -34, bottom: 34 }}
        dragElastic={0.18}
        whileHover={{ scale: 1.025 }}
        whileTap={{ scale: 0.97 }}
        aria-label="Touch and drag the moon and shield"
      >
        <div className="moon-halo" />
        <div className="moon">
          <div className="moon-craters" />
        </div>
        <div className="shield-3d">
          <div className="shield-back" />
          <svg viewBox="0 0 180 210" role="img" aria-label="Cybersecurity shield">
            <defs>
              <linearGradient id="shieldMetal" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stopColor="#f3fbff" />
                <stop offset=".35" stopColor="#6edfff" />
                <stop offset=".72" stopColor="#2875b8" />
                <stop offset="1" stopColor="#142b55" />
              </linearGradient>
              <linearGradient id="shieldInner" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stopColor="#102b4d" />
                <stop offset="1" stopColor="#050b18" />
              </linearGradient>
              <filter id="shieldGlow">
                <feGaussianBlur stdDeviation="5" result="blur" />
                <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
            </defs>
            <path d="M90 8 157 34v58c0 48-27 83-67 108C50 175 23 140 23 92V34L90 8Z" fill="url(#shieldMetal)" stroke="#c9f5ff" strokeWidth="3" filter="url(#shieldGlow)" />
            <path d="M90 25 141 45v46c0 37-19 65-51 85-32-20-51-48-51-85V45l51-20Z" fill="url(#shieldInner)" stroke="#67dfff" strokeWidth="2" />
            <path d="m61 103 19 19 40-44" fill="none" stroke="#b9f7ff" strokeWidth="10" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx="90" cy="90" r="62" fill="none" stroke="#45cfff" strokeOpacity=".35" strokeWidth="1.5" />
          </svg>
          <div className="shield-lock"><LockKeyhole size={22} /></div>
        </div>
      </motion.div>

      <svg className="cosmic-orbit orbit-front" viewBox="0 0 700 430" aria-hidden="true">
        <ellipse cx="350" cy="215" rx="300" ry="104" />
      </svg>

      <div className="cosmic-label label-top"><span className="cosmic-live-dot" />SECURE CORE · ACTIVE</div>
      <div className="cosmic-label label-bottom">MULTI-THREAD SIGNAL FIELD</div>

      <div className="cosmic-thread-points">
        {threads.map((thread, index) => (
          <button
            type="button"
            key={thread.id}
            className={`cosmic-thread thread-point-${index + 1} ${active === thread.id ? "active" : ""}`}
            onClick={() => setActive(active === thread.id ? 0 : thread.id)}
            aria-pressed={active === thread.id}
          >
            <span className="thread-point-dot" />
            <span>{thread.label}</span>
          </button>
        ))}
      </div>

      {active > 0 && (
        <motion.div
          className="cosmic-thread-detail"
          key={active}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <b>{threads[active - 1].state}</b>
          <span>{threads[active - 1].detail}</span>
        </motion.div>
      )}
      <div className="cosmic-touch-hint">↔ Drag to explore · Tap a thread</div>
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
        <section className="reference-hero" id="top">
          <div className="reference-hero-card">
            <motion.div
              className="reference-copy"
              initial={{ opacity: 0, x: -24 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.7 }}
            >
              <span className="reference-kicker"><i /> INTELLIGENT THREAD SECURITY</span>
              <h1>Multi-Thread<br /><span>Detection.</span></h1>
              <p>Discover suspicious thread activity with intelligent monitoring. Explore connected signals, inspect activity and keep your system secure.</p>
              <div className="reference-actions">
                <button className="reference-primary" onClick={() => nav(user ? "/scan" : "/register")}><ScanLine size={17} />Start scanning</button>
                <button className="reference-secondary" onClick={() => nav(user ? "/analytics" : "/login")}><BarChart3 size={17} />View reports</button>
              </div>
              <div className="reference-caption"><ShieldCheck size={15} /> Interactive security visualization</div>
            </motion.div>
            <motion.div
              className="reference-art"
              initial={{ opacity: 0, scale: .92 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: .9, delay: .12 }}
            >
              <CosmicSecurityVisual />
            </motion.div>
          </div>
        </section>

        <section className="scanner-section" id="scan">
          <div className="scanner-intro">
            <span className="reference-kicker"><i /> THREAT INSPECTION</span>
            <h2>Inspect a digital channel.</h2>
            <p>Choose the type of content you want to check before opening or interacting with it.</p>
          </div>
          <div className="scanner">
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
        </section>

        <section className="ch" id="channels">
          <h2>One platform to inspect every digital channel.</h2>
          <p className="channels-intro">Explore the different inputs supported by the threat analysis platform.</p>
          <div className="grid">
            {channels.map(([i, t, d]) => <div className="card" key={t}><div className="ico">{i}</div><h3>{t}</h3><p>{d}</p></div>)}
          </div>
        </section>
      </main>
      <footer>Multi-Thread Detection · Intelligent thread activity monitoring</footer>
    </>
  );
}
