export interface Region { region: string; dial_code: string }
export interface PhoneEvidence {
  reports: number; reporters: number; categories: Record<string, number>; reports_30d: number; reports_90d: number; last_report_days_ago: number | null;
}
export interface PhoneDetails {
  number_display: string; normalized: string; region: string | null; country_code: string; number_type: string; format_valid: boolean;
  scored: boolean; evidence_level: string; intel_source: string; external_intel: boolean; evidence: PhoneEvidence;
  score_breakdown: { rule: string; points: number }[];
}
export interface PhoneScanResult {
  id: string; scan_type: string; label: string; classification: string; risk_score: number | null; risk_level: string | null; status: string;
  created_at: string; explanation: string; recommendation: string; indicators: { name: string; severity: string; weight: number }[]; details: PhoneDetails;
}
export interface PhoneReportItem { id: string; number_display: string; category: string; description: string; evidence: string | null; created_at: string }
