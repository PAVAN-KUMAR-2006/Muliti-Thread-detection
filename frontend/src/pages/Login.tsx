import { FormEvent, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Alert, Field, Shell } from "../components/AuthKit";
import { useAuth } from "../context/AuthContext";
import { errMsg } from "../services/api";

export default function Login() {
  const { login } = useAuth();
  const note = (useLocation().state as { notice?: string } | null)?.notice;
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (!email || !password) return setError("Enter your email and password.");
    setBusy(true);
    try { await login(email.trim(), password); } catch (err) { setError(errMsg(err)); setBusy(false); }
  };

  return (
    <Shell title="Welcome back" lead="Sign in to see your scans and security overview.">
      <form onSubmit={submit} noValidate>
        {note && <Alert kind="ok">{note}</Alert>}
        {error && <Alert>{error}</Alert>}
        <Field id="email" label="Email" type="email" autoComplete="email" value={email} onChange={setEmail} />
        <Field id="password" label="Password" password autoComplete="current-password" value={password} onChange={setPassword} />
        <div className="row-between"><Link to="/forgot-password">Forgot password?</Link></div>
        <button className="btn primary submit" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
      </form>
      <p className="alt">New to Sentinel? <Link to="/register">Create an account</Link></p>
    </Shell>
  );
}
