import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { Alert, Field, Shell } from "../components/AuthKit";
import { api, errMsg } from "../services/api";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(""); setMsg("");
    if (!/^\S+@\S+\.\S+$/.test(email)) return setError("Enter a valid email address.");
    setBusy(true);
    try { setMsg((await api.post("/auth/forgot-password", { email: email.trim() })).data.message); }
    catch (err) { setError(errMsg(err)); }
    setBusy(false);
  };

  return (
    <Shell title="Reset your password" lead="Enter your account email and we will send a reset link.">
      <form onSubmit={submit} noValidate>
        {msg && <Alert kind="ok">{msg}</Alert>}
        {error && <Alert>{error}</Alert>}
        <Field id="email" label="Email" type="email" autoComplete="email" value={email} onChange={setEmail} />
        <button className="btn primary submit" disabled={busy}>{busy ? "Sending…" : "Send reset link"}</button>
      </form>
      <p className="alt"><Link to="/login">Back to sign in</Link></p>
    </Shell>
  );
}
