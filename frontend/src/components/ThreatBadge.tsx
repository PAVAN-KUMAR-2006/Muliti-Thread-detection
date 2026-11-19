export function ThreatBadge({ label }: { label: string }) {
  const tone = label === "Safe" ? "low" : label === "Suspicious" ? "medium" : label === "Unknown" ? "neutral" : "high";
  return <span className={`badge ${tone}`}>{label}</span>;
}

export function ScanStatus({ status }: { status: string }) {
  const tone = status === "completed" ? "low" : status === "failed" ? "high" : "medium";
  return <span className={`badge ${tone}`}>{status}</span>;
}
