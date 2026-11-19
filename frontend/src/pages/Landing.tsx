import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
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
        <section className="hero">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
            <span className="pill"><b />Explainable results · every scan saved to your history</span>
            <h1>One platform. <span>Every digital threat.</span></h1>
            <p className="sub">Detect phishing, spam, scams and malicious content across websites, emails and messaging platforms using intelligent machine learning.</p>
            <div className="scanner" id="scan">
              <div className="tabs" role="tablist" aria-label="What would you like to analyze?">
                {kinds.map((x) => (
                  <button key={x.k} className="tab" role="tab" aria-selected={kind.k === x.k} onClick={() => pick(x)}>{x.label}</button>
                ))}
              </div>
              <div className="field">
                {kind.as === "input" && <input aria-label={kind.label} placeholder={kind.ph} value={value} onChange={(e) => setValue(e.target.value)} />}
                {kind.as === "area" && <textarea aria-label={kind.label} rows={3} placeholder={kind.ph} value={value} onChange={(e) => setValue(e.target.value)} />}
                {kind.as === "file" && (
                  <label className="drop">
                    {fileName || kind.ph}
                    <input type="file" hidden onChange={(e) => setFileName(e.target.files?.[0]?.name ?? "")} />
                  </label>
                )}
              </div>
            </div>
            <div className="cta-row">
              <button className="btn primary" onClick={() => nav(user ? "/dashboard" : "/register")}>Analyze threat</button>
              <a className="btn" href="#channels">Explore platform</a>
            </div>
          </motion.div>
          <motion.aside className="panel" aria-label="Analysis preview" initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.7, delay: 0.15 }}>
            <div className="gauge">
              <svg viewBox="0 0 180 180" width="190" height="190"><circle className="trk" cx="90" cy="90" r="80" /><circle className="val" cx="90" cy="90" r="80" /></svg>
              <div><strong>0</strong><small>risk score</small></div>
            </div>
            <p className="verdict" style={{ color: "var(--muted)" }}>No analysis yet</p>
            <p className="note">Create a free account to run your first scan. Scoring from the trained models arrives in a later phase.</p>
          </motion.aside>
        </section>
        <section className="ch" id="channels">
          <h2>Seven ways to check what lands in front of you.</h2>
          <div className="grid">
            {channels.map(([i, t, d]) => <div className="card" key={t}><div className="ico">{i}</div><h3>{t}</h3><p>{d}</p></div>)}
          </div>
        </section>
      </main>
      <footer>Sentinel · Phishing and spam detection across web, email and messaging</footer>
    </>
  );
}
