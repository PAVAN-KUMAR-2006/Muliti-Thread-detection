export interface AlertItem {
  id: string; scan_type: string; label: string; risk_score: number; risk_level: string; status: string; created_at: string; explanation: string;
}
export interface AlertsResponse { total: number; items: AlertItem[] }
export interface StatusItem { status: string; count: number }
export interface ScanStatusResponse { items: StatusItem[]; total: number }
