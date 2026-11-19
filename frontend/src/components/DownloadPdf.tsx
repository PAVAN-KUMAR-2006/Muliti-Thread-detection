import { useState } from "react";
import { api, errMsg } from "../services/api";

export default function DownloadPdf({ id }: { id: string }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const go = async () => {
    setBusy(true); setErr("");
    try {
      const r = await api.get(`/reports/scan/${id}/pdf`, { responseType: "blob" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(r.data); a.download = `sentinel-scan-${id.slice(0, 8)}.pdf`; a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) { setErr(errMsg(e)); }
    setBusy(false);
  };
  return <><button className="btn" onClick={go} disabled={busy}>{busy ? "Preparing…" : "Download PDF"}</button>{err && <span className="err"> {err}</span>}</>;
}
