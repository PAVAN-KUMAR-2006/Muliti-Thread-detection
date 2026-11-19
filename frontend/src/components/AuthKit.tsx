import { ReactNode, useState } from "react";
import { motion } from "framer-motion";
import { AlertCircle, Check, CheckCircle2, Eye, EyeOff } from "lucide-react";
import NetworkBackground from "./NetworkBackground";
import Nav from "./Nav";

export const passwordRules: { label: string; test: (p: string) => boolean }[] = [
  { label: "10+ characters", test: (p) => p.length >= 10 },
  { label: "Uppercase letter", test: (p) => /[A-Z]/.test(p) },
  { label: "Lowercase letter", test: (p) => /[a-z]/.test(p) },
  { label: "Number", test: (p) => /\d/.test(p) },
  { label: "Symbol", test: (p) => /[^A-Za-z0-9]/.test(p) },
];
export const passwordValid = (p: string) => passwordRules.every((r) => r.test(p)) && new TextEncoder().encode(p).length <= 72;

export function Shell({ title, lead, children }: { title: string; lead: string; children: ReactNode }) {
  return (
    <>
      <NetworkBackground />
      <div className="glow" />
      <Nav />
      <main className="auth">
        <motion.section className="auth-card" initial={{ opacity: 0, y: 18, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ duration: 0.45, ease: [0.2, 0.8, 0.2, 1] }}>
          <h1>{title}</h1>
          <p className="lead">{lead}</p>
          {children}
        </motion.section>
      </main>
    </>
  );
}

export function Alert({ kind = "error", children }: { kind?: "error" | "ok"; children: ReactNode }) {
  return (
    <motion.div className={`alert ${kind === "ok" ? "ok" : ""}`} role={kind === "ok" ? "status" : "alert"} initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}>
      {kind === "ok" ? <CheckCircle2 size={18} color="var(--safe)" /> : <AlertCircle size={18} color="var(--risk)" />}
      <span>{children}</span>
    </motion.div>
  );
}

interface FieldProps {
  id: string; label: string; value: string; onChange: (v: string) => void;
  type?: string; autoComplete?: string; error?: string; password?: boolean; strength?: boolean;
}

export function Field({ id, label, value, onChange, type = "text", autoComplete, error, password, strength }: FieldProps) {
  const [show, setShow] = useState(false);
  const passed = passwordRules.filter((r) => r.test(value)).length;
  const color = passed <= 2 ? "var(--risk)" : passed <= 4 ? "var(--warn)" : "var(--safe)";
  return (
    <div>
      <label className="lbl" htmlFor={id}>{label}</label>
      <div className="inp">
        <input id={id} type={password && show ? "text" : type} value={value} autoComplete={autoComplete}
          onChange={(e) => onChange(e.target.value)} aria-invalid={!!error} aria-describedby={error ? `${id}-err` : undefined} />
        {password && (
          <button type="button" className="eye" onClick={() => setShow(!show)} aria-label={show ? "Hide password" : "Show password"} aria-pressed={show}>
            {show ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        )}
      </div>
      {error && <div id={`${id}-err`} className="err">{error}</div>}
      {strength && value.length > 0 && (
        <>
          <div className="meter" aria-hidden="true">
            {passwordRules.map((_, i) => <i key={i} style={{ background: i < passed ? color : undefined }} />)}
          </div>
          <ul className="rules" aria-label="Password requirements">
            {passwordRules.map((r) => <li key={r.label} className={r.test(value) ? "ok" : ""}><Check size={12} />{r.label}</li>)}
          </ul>
        </>
      )}
    </div>
  );
}
