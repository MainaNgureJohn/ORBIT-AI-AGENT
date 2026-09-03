import type { MarketSnapshot } from "./market";

export type RiskLevel = "Low" | "Medium" | "High";

export type TechnicalMetrics = {
  trend: string;
  momentum: number;
  volatility: number;
  volume_signal: string;
  support_resistance: string;
};

export type ScoreBreakdown = {
  market: number;
  technical: number;
  on_chain: number | null;
  risk: number;
  final: number;
  missing_components: string[];
};

export type AnalysisReport = {
  asset: string;
  snapshot: MarketSnapshot;
  metrics: TechnicalMetrics;
  score: ScoreBreakdown;
  risk_level: RiskLevel;
  reasons: string[];
  limitations: string[];
  generated_at: string;
  explanation?: string | null;
};
