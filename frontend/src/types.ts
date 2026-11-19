export type ScanType = "website" | "email" | "message" | "qr" | "phone" | "file";
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export interface ScanSummary {
  id: string; scan_type: ScanType; input_summary: string; label: string;
  risk_score: number; risk_level: RiskLevel; status: string; created_at: string;
}
export type Scan = ScanSummary;
export interface Indicator { name: string; severity: string; weight: number }
export interface Prediction { model_name: string; model_version: string; probability: number }
export interface ScanDetail extends ScanSummary {
  confidence: number | null; explanation: string; recommendation: string;
  indicators: Indicator[]; predictions: Prediction[];
}
export type ThreatDistribution = Record<string, number>;
export type RiskDistribution = Record<RiskLevel, number>;
export type ChannelDistribution = Record<ScanType, number>;
export interface ActivityPoint { date: string; count: number }
export interface DashboardOverview {
  total: number; high_risk: number; by_label: ThreatDistribution; by_level: RiskDistribution;
  by_type: ChannelDistribution; activity_days: number; activity: ActivityPoint[];
  recent: ScanSummary[]; last_scan: ScanSummary | null; state: "No data" | "Clear" | "Elevated";
}
export interface PaginatedHistory { items: ScanSummary[]; total: number; page: number; limit: number; total_pages: number }
export interface ScanResult extends ScanDetail { protective: Indicator[]; details: ScanDetails }
export interface ScanDetails {
  url?: string; host?: string; https?: boolean; features?: Record<string, number>;
  decoded?: string; is_url?: boolean; sender?: string; subject?: string;
  urls?: { url: string; phishing_probability: number | null }[];
  file?: { name: string; type: string; size: number; sha256: string };
}
export type CardKey = "total" | "safe" | "suspicious" | "threats" | "high" | "critical";
export interface AnalyticsCard { value: number; previous: number; change_pct: number | null }
export interface AnalyticsOverview {
  range: { start: string; end: string; days: number }; scanner: string | null; total_ever: number;
  comparison_available: boolean; cards: Record<CardKey, AnalyticsCard>;
}
export interface CountItems { items: { name: string; count: number }[]; total: number }
export interface ScanTrends { points: ActivityPoint[]; total: number }
export interface ThreatTrendPoint { date: string; phishing: number; spam: number; scam: number }
export interface ThreatTrends { points: ThreatTrendPoint[]; total: number; sufficient: boolean }
export interface HighRiskItem { id: string; scan_type: string; label: string; risk_score: number; risk_level: string; created_at: string; explanation: string }
export type ModelStatus = "trained" | "not_trained" | "metrics_unavailable";
export interface ModelInfo {
  key: string; name: string; scanner: string; status: ModelStatus; algorithm: string | null;
  metrics: { accuracy: number | null; precision: number | null; recall: number | null; f1: number | null; roc_auc: number | null };
  confusion_matrix: number[][] | null; test_size: number | null; train_size: number | null; feature_count: number | null;
  dataset: string | null; description: string | null; version: string | null; trained_at: string | null; seed: number | null;
  positive_class: string | null; class_names: string[] | null; metrics_file: string;
}
export interface NotificationItem { id: string; title: string; body: string; read: boolean; created_at: string }
export interface NotificationList { items: NotificationItem[]; unread_count: number }
