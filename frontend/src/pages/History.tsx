import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import NetworkBackground from "../components/NetworkBackground";
import Nav from "../components/Nav";
import ExportMenu from "../components/ExportMenu";
import ScanFilters, { EMPTY_FILTERS, Filters } from "../components/ScanFilters";
import { ScanTable } from "../components/ScanTable";
import { EmptyState, ErrorState, Skeleton } from "../components/States";
import { useApi } from "../hooks/useApi";
import { errMsg } from "../services/api";
import { PaginatedHistory } from "../types";

const LIMIT = 10;

export default function History() {
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const [filters, setFilters] = useState<Filters>({ ...EMPTY_FILTERS, threat: sp.get("threat") ?? "" });
  const [q, setQ] = useState(filters.q);
  const [page, setPage] = useState(1);

  useEffect(() => { const t = setTimeout(() => q !== filters.q && setFilters((f) => ({ ...f, q })), 300); return () => clearTimeout(t); }, [q, filters.q]);
  const change = (f: Filters) => { setPage(1); if (f.q !== filters.q) setQ(f.q); setFilters(f); };

  const { data, error, loading, reload } = useApi<PaginatedHistory>("/history", {
    page, limit: LIMIT, q: filters.q || undefined, type: filters.type || undefined, threat: filters.threat || undefined,
    risk: filters.risk || undefined, sort: filters.sort,
    date_from: filters.from ? `${filters.from}T00:00:00` : undefined, date_to: filters.to ? `${filters.to}T23:59:59` : undefined,
  });
  const filtered = Object.entries(filters).some(([k, v]) => k !== "sort" && v);

  return (
    <>
      <NetworkBackground /><div className="glow" /><Nav />
      <main className="wrap">
        <h1>Scan history</h1>
        <p className="sub">Only scans from your account are shown.</p>
        <ScanFilters value={{ ...filters, q }} onChange={(f) => { setQ(f.q); change({ ...f, q: filters.q }); }} />
        <ExportMenu filters={filters} total={data?.total} />
        {!!error && !data && <ErrorState message={errMsg(error)} onRetry={reload} />}
        {!data && !error && <><Skeleton h={56} /><br /><Skeleton h={56} /><br /><Skeleton h={56} /></>}
        {data && data.total === 0 && (
          <EmptyState title={filtered ? "No scans match these filters" : "No scans yet"} text={filtered ? "Try removing a filter or searching for something else." : "Run your first security analysis to start building your threat history."}>
            {filtered ? <button className="btn" onClick={() => { setQ(""); change(EMPTY_FILTERS); }}>Clear filters</button> : <button className="btn primary" onClick={() => nav("/scan")}>Start a scan</button>}
          </EmptyState>
        )}
        {data && data.total > 0 && (
          <div style={{ opacity: loading ? 0.6 : 1, transition: "opacity .2s" }}>
            <ScanTable items={data.items} />
            <div className="pager">
              <span>{data.total} scans</span>
              <button className="btn" disabled={data.page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
              <span>Page {data.page} of {data.total_pages}</span>
              <button className="btn" disabled={data.page >= data.total_pages} onClick={() => setPage(page + 1)}>Next</button>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
