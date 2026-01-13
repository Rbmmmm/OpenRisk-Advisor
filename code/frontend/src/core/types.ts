export type RiskLevel = "Low" | "Medium" | "High";

export type RiskReportBundle = {
  generated_at?: string;
  as_of_month?: string;
  model?: { type?: string; version?: string };
  count?: number;
  items: RiskReportItem[];
};

export type RiskReportItem = {
  repo: string;
  as_of_month: string;
  risk_score: number;
  risk_level: RiskLevel | string;
  needs_review: boolean;
  model?: { type?: string; version?: string };
  data_quality?: {
    missing_rate?: number;
    avg_coverage?: number;
    avg_raw_ratio_win3?: number;
    metrics?: Record<string, { coverage?: number; raw_ratio_win3_mean?: number }>;
  };
  model_uncertainty?: {
    forecast_uncertainty_ratio?: number;
  };
  evidence_chain?: {
    lookback_months?: number;
    top_signal_dimensions?: string[];
    top_signal_dimensions_count?: number;
  };
  main_signals?: SignalEvidence[];
  aux_explain?: any;
  explain?: any;
};

export type SignalEvidence = {
  signal_id: string;
  signal_name?: string;
  dimension?: string;
  signal_strength?: number;
  signal_confidence?: number;
  when?: {
    start_month?: string;
    end_month?: string;
    duration_months?: number;
  };
  time_window?: {
    t0?: string;
    t_end?: string;
    sustained_months?: number;
  };
  is_abnormal?: {
    zscore_12_last?: number | null;
    percentile_rank_24m_last?: number | null;
  };
  governance_meaning?: string;
  supporting_metrics?: any;
  evidence_refs?: any;
  visual_evidence?: any;
  thresholds?: any;
};
