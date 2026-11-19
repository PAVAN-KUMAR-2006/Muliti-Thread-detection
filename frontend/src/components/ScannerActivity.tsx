import { DashboardCard, ChannelDistribution } from "./Charts";
import { Async } from "./Async";
import { CountUp } from "./RiskGauge";
import { useApi } from "../hooks/useApi";
import { ScanStatusResponse } from "../dashboardTypes";
import type { ChannelDistribution as ChannelDistributionData, CountItems } from "../types";

export default function ScannerActivity({ days }: { days: number }) {
  const usage = useApi<CountItems>("/analytics/scanner-usage", { days });
  const labels = useApi<CountItems>("/analytics/threat-distribution", { days });
  const status = useApi<ScanStatusResponse>("/analytics/scan-status", { days });

  return (
    <DashboardCard title="Scanner activity">
      <p className="sub range9">Last {days} days, counted from your saved scans (one row per scan).</p>
      <Async q={usage} h={200}>
        {(u) => (
          <>
            <p className="big9"><CountUp to={u.total} /> <span>scans in this period</span></p>
            {u.total === 0 ? <p className="sub">No scans in this period.</p> : (
              <>
                <h3 className="sech3">By scanner</h3>
                <ChannelDistribution data={Object.fromEntries(u.items.map((i) => [i.name, i.count])) as unknown as ChannelDistributionData} />
              </>
            )}
          </>
        )}
      </Async>
      <h3 className="sech3">Classifications</h3>
      <Async q={labels} h={50}>
        {(l) => (
          <ul className="chips9" aria-label="Scans by classification">
            {l.items.map((i) => <li key={i.name}>{i.name}<b>{i.count}</b></li>)}
          </ul>
        )}
      </Async>
      <h3 className="sech3">Scan status</h3>
      <Async q={status} h={50}>
        {(s) => {
          const done = s.items.find((i) => i.status === "completed")?.count ?? 0;
          const other = s.items.filter((i) => i.status !== "completed");
          return (
            <>
              <p><b>{done}</b> completed</p>
              {other.length > 0 ? (
                <ul className="chips9" aria-label="Scans that are not completed">{other.map((i) => <li key={i.status}>{i.status}<b>{i.count}</b></li>)}</ul>
              ) : (
                <p className="sub">No failed or incomplete scans are recorded. Only finished analyses are saved, so a scan that fails before finishing does not appear here.</p>
              )}
            </>
          );
        }}
      </Async>
    </DashboardCard>
  );
}
