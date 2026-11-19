export type Level = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export interface ScanSummary { id: string; scan_type: string; input_summary: string; label: string; risk_score: number; risk_level: Level; status: string; created_at: string }
export interface Indicator { name: string; severity: string; weight: number }
export interface ScanDetail extends ScanSummary { confidence: number | null; explanation: string | null; recommendation: string | null; indicators: Indicator[]; predictions: { model: string; version: string; probability: number }[] }
export interface ActivityPoint { date: string; count: number }
export interface DashboardOverview { total: number; high_risk: number; by_label: Record<string, number>; by_level: Record<Level, number>; by_type: Record<string, number>; activity: ActivityPoint[]; recent: ScanSummary[]; last_scan: ScanSummary | null }
export interface PaginatedHistory { items: ScanSummary[]; total: number; page: number; limit: number; pages: number }
