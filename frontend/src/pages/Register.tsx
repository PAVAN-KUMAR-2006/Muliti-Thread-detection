import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { Alert, Field, passwordValid, Shell } from "../components/AuthKit";
import { useAuth } from "../context/AuthContext";
import { errMsg } from "../services/api";

export default function Register() {
  const { register } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const v: Record<string, string> = {};
    if (name.trim().length < 2) v.name = "Enter your name.";
    if (!/^\S+@\S+\.\S+$/.test(email)) v.email = "Enter a valid email address.";
    if (!passwordValid(password)) v.password = "Password does not meet all requirements.";
    if (confirm !== password) v.confirm = "Passwords do not match.";
    setErrors(v);
    if (Object.keys(v).length) return;
    setBusy(true);
    try { await register(name.trim(), email.trim(), password); } catch (err) { setError(errMsg(err)); setBusy(false); }
  };

  return (
    <Shell title="Create your account" lead="Your scan history stays private to your account.">
      <form onSubmit={submit} noValidate>
        {error && <Alert>{error}</Alert>}
        <Field id="name" label="Full name" autoComplete="name" value={name} onChange={setName} error={errors.name} />
        <Field id="email" label="Email" type="email" autoComplete="email" value={email} onChange={setEmail} error={errors.email} />
        <Field id="password" label="Password" password strength autoComplete="new-password" value={password} onChange={setPassword} error={errors.password} />
        <Field id="confirm" label="Confirm password" password autoComplete="new-password" value={confirm} onChange={setConfirm} error={errors.confirm} />
        <button className="btn primary submit" disabled={busy}>{busy ? "Creating account…" : "Create account"}</button>
      </form>
      <p className="alt">Already have an account? <Link to="/login">Sign in</Link></p>
    </Shell>
  );
}
