import { FormEvent, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Alert, Field, passwordValid, Shell } from "../components/AuthKit";
import { api, errMsg } from "../services/api";

export default function ResetPassword() {
  const token = useSearchParams()[0].get("token") ?? "";
  const nav = useNavigate();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (!passwordValid(password)) return setError("Password does not meet all requirements.");
    if (password !== confirm) return setError("Passwords do not match.");
    setBusy(true);
    try {
      const { data } = await api.post("/auth/reset-password", { token, password });
      nav("/login", { state: { notice: data.message } });
    } catch (err) { setError(errMsg(err)); setBusy(false); }
  };

  return (
    <Shell title="Choose a new password" lead="You will be signed out everywhere after changing it.">
      {!token ? (
        <><Alert>This reset link is missing its token. Request a new one.</Alert><p className="alt"><Link to="/forgot-password">Request a reset link</Link></p></>
      ) : (
        <form onSubmit={submit} noValidate>
          {error && <Alert>{error}</Alert>}
          <Field id="password" label="New password" password strength autoComplete="new-password" value={password} onChange={setPassword} />
          <Field id="confirm" label="Confirm new password" password autoComplete="new-password" value={confirm} onChange={setConfirm} />
          <button className="btn primary submit" disabled={busy}>{busy ? "Saving…" : "Update password"}</button>
        </form>
      )}
    </Shell>
  );
}
