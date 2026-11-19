import { useState } from "react";
import { Download } from "lucide-react";
import { api, errMsg } from "../services/api";
import { Filters } from "./ScanFilters";

const FORMATS = [["csv", "CSV"], ["excel", "Excel"], ["pdf", "PDF"]] as const;
const EXT = { csv: "csv", excel: "xlsx", pdf: "pdf" } as const;

/** Exports exactly what the current filters show. The server re-applies the filters for the signed-in user. */
export default function ExportMenu({ filters, total }: { filters: Filters; total?: number }) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");

  const go = async (fmt: keyof typeof EXT) => {
    setBusy(fmt); setError("");
    try {
      const r = await api.get(`/history/export/${fmt}`, {
        responseType: "blob",
        params: {
          q: filters.q || undefined, type: filters.type || undefined, threat: filters.threat || undefined, risk: filters.risk || undefined,
          date_from: filters.from ? `${filters.from}T00:00:00` : undefined, date_to: filters.to ? `${filters.to}T23:59:59` : undefined,
        },
      });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(r.data);
      a.download = `sentinel-history-${new Date().toISOString().slice(0, 10)}.${EXT[fmt]}`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) { setError(errMsg(e)); }
    setBusy(null);
  };

  return (
    <div className="exportbar" role="group" aria-label="Export history">
      <span className="sub"><Download size={14} style={{ verticalAlign: -2 }} /> Export {total === undefined ? "" : `${total} matching scans`} (applies the filters above)</span>
      {FORMATS.map(([k, label]) => (
        <button key={k} className="btn" disabled={busy !== null || total === 0} onClick={() => go(k)}>{busy === k ? "Preparing…" : label}</button>
      ))}
      {error && <span className="err">{error}</span>}
    </div>
  );
}
