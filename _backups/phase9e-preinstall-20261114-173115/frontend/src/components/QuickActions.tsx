import { Link } from "react-router-dom";
import { motion } from "framer-motion";

// Every destination below is an existing scanner page (route /scan/:kind in App.tsx, kind defined in pages/Scanner.tsx).
// `npm run check:actions` fails if one of them stops existing.
const ACTIONS = [
  { to: "/scan/website", icon: "🌐", title: "Scan a website", text: "Check a link for phishing" },
  { to: "/scan/email", icon: "📧", title: "Analyze an email", text: "Paste it or upload a .eml" },
  { to: "/scan/message", icon: "📱", title: "Analyze a message", text: "SMS, WhatsApp or Telegram" },
  { to: "/scan/qr", icon: "📷", title: "Scan a QR code", text: "Upload an image or use the camera" },
  { to: "/scan/file", icon: "📁", title: "Scan a file", text: "TXT, CSV, EML, PDF or DOCX" },
] as const;

export default function QuickActions() {
  return (
    <section aria-labelledby="qa-title">
      <h2 id="qa-title" className="sech">Quick actions</h2>
      <ul className="qagrid">
        {ACTIONS.map((a, i) => (
          <motion.li key={a.to} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}>
            <Link className="qa" to={a.to}>
              <span className="qaicon" aria-hidden="true">{a.icon}</span>
              <span><b>{a.title}</b><small>{a.text}</small></span>
            </Link>
          </motion.li>
        ))}
      </ul>
    </section>
  );
}
