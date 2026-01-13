# Risk Report
- generated_at: 2026-01-13T16:03:11Z
- as_of_month: 2025-12
- model_type: baseline
- model_version: 0.1.0
- repos: 165

## babelfish-for-postgresql/postgresql_modified_for_babelfish

- risk_score: 0.999
- risk_level: High
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.635
- missing_rate: 0.365
- main_signals:
  - PR_THROUGHPUT_DROP_3M PR 流水线吞吐下降（3个月） (activity_throughput) strength=0.30 conf=0.00
    - t0=2025-05 sustained_months=3
    - zscore_12_last=-0.73
    - percentile_rank_24m_last=0.17
  - PR_SUPPLY_DEMAND_IMBALANCE_6M PR 供需失衡（提交>接受，持续6个月） (collaboration_efficiency) strength=0.30 conf=0.00
    - t0=2025-02 sustained_months=10
    - zscore_12_last=-0.73
    - percentile_rank_24m_last=0.17
  - CODE_CHURN_DROP_3M 代码变更规模下滑（3个月） (activity_throughput) strength=0.27 conf=0.00
    - t0=2025-05 sustained_months=6
    - zscore_12_last=-0.00
    - percentile_rank_24m_last=0.71
  - INACTIVE_CONTRIB_SPIKE 不活跃贡献者上升（流失加剧） (contributors_concentration) strength=0.24 conf=0.00
    - t0=2025-05 sustained_months=8
    - zscore_12_last=1.59
    - percentile_rank_24m_last=1.00
  - ATTENTION_DROP_6M_AUX 外部关注衰减（辅助信号，6个月） (attention_engagement) strength=0.07 conf=0.00
    - t0=2025-01 sustained_months=12
    - zscore_12_last=-1.06
    - percentile_rank_24m_last=0.11

## apache/iotdb

- risk_score: 0.999
- risk_level: High
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.865
- missing_rate: 0.135
- main_signals:
  - MULTI_DIMENSION_DECLINE_CORE 多维度核心衰退（至少2/3维度共同触发） (composite) strength=1.00 conf=0.20
    - t0=2025-05 sustained_months=4
    - zscore_12_last=-1.82
    - percentile_rank_24m_last=0.04
  - BUS_FACTOR_LOW_OR_DOWN Bus Factor 过低或持续下降（单点维护风险） (contributors_concentration) strength=1.00 conf=0.00
    - t0=2025-05 sustained_months=8
    - zscore_12_last=-1.41
    - percentile_rank_24m_last=0.08
  - ACT_DROP_YOY_3M 活跃度同比持续下滑（3个月） (activity_throughput) strength=0.72 conf=0.00
    - t0=2025-05 sustained_months=3
    - zscore_12_last=-1.67
    - percentile_rank_24m_last=0.08
  - CONTRIB_SHRINK_3M 贡献者规模收缩（3个月） (contributors_concentration) strength=0.72 conf=0.00
    - t0=2025-05 sustained_months=6
    - zscore_12_last=-1.57
    - percentile_rank_24m_last=0.04
  - PR_THROUGHPUT_DROP_3M PR 流水线吞吐下降（3个月） (activity_throughput) strength=0.30 conf=0.00
    - t0=2025-05 sustained_months=7
    - zscore_12_last=-1.27
    - percentile_rank_24m_last=0.12

## eslint/eslintrc

- risk_score: 0.962
- risk_level: High
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.579
- missing_rate: 0.421
- main_signals:
  - BUS_FACTOR_LOW_OR_DOWN Bus Factor 过低或持续下降（单点维护风险） (contributors_concentration) strength=1.00 conf=0.00
    - t0=2025-04 sustained_months=9
    - zscore_12_last=-0.20
    - percentile_rank_24m_last=0.62
  - INACTIVE_CONTRIB_SPIKE 不活跃贡献者上升（流失加剧） (contributors_concentration) strength=0.24 conf=0.00
    - t0=2025-05 sustained_months=7
    - zscore_12_last=1.61
    - percentile_rank_24m_last=1.00
  - ATTENTION_DROP_6M_AUX 外部关注衰减（辅助信号，6个月） (attention_engagement) strength=0.07 conf=0.00
    - t0=2025-02 sustained_months=11
    - zscore_12_last=-0.68
    - percentile_rank_24m_last=0.35
  - ISSUE_INFLOW_DROP_3M Issue 新增下降（3个月，解释性信号） (activity_throughput) strength=0.06 conf=0.00
    - t0=2025-08 sustained_months=4
    - zscore_12_last=-0.30
    - percentile_rank_24m_last=0.88
  - DATA_SUFFICIENT_6M 数据覆盖充足（可评估，6个月） (composite) strength=0.01 conf=0.00
    - t0=2025-02 sustained_months=11
    - zscore_12_last=0.51
    - percentile_rank_24m_last=0.55

## FirelyTeam/firely-docs-firely-server

- risk_score: 0.962
- risk_level: High
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.583
- missing_rate: 0.417
- main_signals:
  - MULTI_DIMENSION_DECLINE_CORE 多维度核心衰退（至少2/3维度共同触发） (composite) strength=1.00 conf=0.20
    - t0=2025-05 sustained_months=4
    - zscore_12_last=-1.29
    - percentile_rank_24m_last=0.08
  - ACT_DROP_YOY_3M 活跃度同比持续下滑（3个月） (activity_throughput) strength=0.72 conf=0.00
    - t0=2025-05 sustained_months=3
    - zscore_12_last=-0.01
    - percentile_rank_24m_last=0.42
  - CONTRIB_SHRINK_3M 贡献者规模收缩（3个月） (contributors_concentration) strength=0.72 conf=0.00
    - t0=2025-05 sustained_months=6
    - zscore_12_last=0.64
    - percentile_rank_24m_last=0.67
  - PR_THROUGHPUT_DROP_3M PR 流水线吞吐下降（3个月） (activity_throughput) strength=0.30 conf=0.00
    - t0=2025-05 sustained_months=7
    - zscore_12_last=-0.23
    - percentile_rank_24m_last=0.46
  - PR_SUPPLY_DEMAND_IMBALANCE_6M PR 供需失衡（提交>接受，持续6个月） (collaboration_efficiency) strength=0.30 conf=0.00
    - t0=2025-02 sustained_months=10
    - zscore_12_last=-0.23
    - percentile_rank_24m_last=0.46

## X-lab2017/open-digger

- risk_score: 0.942
- risk_level: High
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.845
- missing_rate: 0.155
- main_signals:
  - PR_SUPPLY_DEMAND_IMBALANCE_6M PR 供需失衡（提交>接受，持续6个月） (collaboration_efficiency) strength=0.30 conf=0.00
    - t0=2025-01 sustained_months=12
    - zscore_12_last=-1.09
    - percentile_rank_24m_last=0.09
  - CODE_CHURN_DROP_3M 代码变更规模下滑（3个月） (activity_throughput) strength=0.27 conf=0.00
    - t0=2025-05 sustained_months=5
    - zscore_12_last=-0.63
    - percentile_rank_24m_last=0.30
  - INACTIVE_CONTRIB_SPIKE 不活跃贡献者上升（流失加剧） (contributors_concentration) strength=0.24 conf=0.00
    - t0=2025-05 sustained_months=3
    - zscore_12_last=1.57
    - percentile_rank_24m_last=0.96
  - ATTENTION_DROP_6M_AUX 外部关注衰减（辅助信号，6个月） (attention_engagement) strength=0.07 conf=0.00
    - t0=2025-02 sustained_months=11
    - zscore_12_last=-0.26
    - percentile_rank_24m_last=0.75
  - ISSUE_INFLOW_DROP_3M Issue 新增下降（3个月，解释性信号） (activity_throughput) strength=0.06 conf=0.00
    - t0=2025-04 sustained_months=9
    - zscore_12_last=-0.89
    - percentile_rank_24m_last=0.13

## open-telemetry/opentelemetry-js-contrib

- risk_score: 0.923
- risk_level: High
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.893
- missing_rate: 0.107
- main_signals:
  - MULTI_DIMENSION_DECLINE_CORE 多维度核心衰退（至少2/3维度共同触发） (composite) strength=1.00 conf=0.20
    - t0=2025-05 sustained_months=3
    - zscore_12_last=-1.64
    - percentile_rank_24m_last=0.04
  - BUS_FACTOR_LOW_OR_DOWN Bus Factor 过低或持续下降（单点维护风险） (contributors_concentration) strength=1.00 conf=0.00
    - t0=2025-03 sustained_months=10
    - zscore_12_last=-0.91
    - percentile_rank_24m_last=0.17
  - CONTRIB_SHRINK_3M 贡献者规模收缩（3个月） (contributors_concentration) strength=0.72 conf=0.00
    - t0=2025-05 sustained_months=6
    - zscore_12_last=-1.96
    - percentile_rank_24m_last=0.04
  - PR_THROUGHPUT_DROP_3M PR 流水线吞吐下降（3个月） (activity_throughput) strength=0.30 conf=0.00
    - t0=2025-06 sustained_months=4
    - zscore_12_last=-0.96
    - percentile_rank_24m_last=0.17
  - PR_SUPPLY_DEMAND_IMBALANCE_6M PR 供需失衡（提交>接受，持续6个月） (collaboration_efficiency) strength=0.30 conf=0.00
    - t0=2025-02 sustained_months=11
    - zscore_12_last=-1.50
    - percentile_rank_24m_last=0.04

## Ionaru/easy-markdown-editor

- risk_score: 0.904
- risk_level: High
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.540
- missing_rate: 0.460
- main_signals:
  - BUS_FACTOR_LOW_OR_DOWN Bus Factor 过低或持续下降（单点维护风险） (contributors_concentration) strength=1.00 conf=0.00
    - t0=2025-05 sustained_months=8
    - zscore_12_last=-0.82
    - percentile_rank_24m_last=0.22
  - ATTENTION_DROP_6M_AUX 外部关注衰减（辅助信号，6个月） (attention_engagement) strength=0.07 conf=0.00
    - t0=2025-03 sustained_months=10
    - zscore_12_last=-1.20
    - percentile_rank_24m_last=0.08
  - ISSUE_INFLOW_DROP_3M Issue 新增下降（3个月，解释性信号） (activity_throughput) strength=0.06 conf=0.00
    - t0=2025-04 sustained_months=7
    - zscore_12_last=-1.30
    - percentile_rank_24m_last=0.32
  - DATA_SUFFICIENT_6M 数据覆盖充足（可评估，6个月） (composite) strength=0.01 conf=0.00
    - t0=2025-02 sustained_months=7
    - zscore_12_last=-0.71
    - percentile_rank_24m_last=0.17

## sailro/EscapeFromTarkov-Trainer

- risk_score: 0.887
- risk_level: High
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.738
- missing_rate: 0.262
- main_signals:
  - BUS_FACTOR_LOW_OR_DOWN Bus Factor 过低或持续下降（单点维护风险） (contributors_concentration) strength=1.00 conf=0.00
    - t0=2025-02 sustained_months=10
    - zscore_12_last=-1.75
    - percentile_rank_24m_last=0.04
  - ACT_DROP_YOY_3M 活跃度同比持续下滑（3个月） (activity_throughput) strength=0.72 conf=0.00
    - t0=2025-05 sustained_months=3
    - zscore_12_last=-1.73
    - percentile_rank_24m_last=0.04
  - PR_THROUGHPUT_DROP_3M PR 流水线吞吐下降（3个月） (activity_throughput) strength=0.30 conf=0.00
    - t0=2025-04 sustained_months=6
    - zscore_12_last=-1.23
    - percentile_rank_24m_last=0.23
  - PR_SUPPLY_DEMAND_IMBALANCE_6M PR 供需失衡（提交>接受，持续6个月） (collaboration_efficiency) strength=0.30 conf=0.00
    - t0=2025-01 sustained_months=9
    - zscore_12_last=-1.23
    - percentile_rank_24m_last=0.23
  - INACTIVE_CONTRIB_SPIKE 不活跃贡献者上升（流失加剧） (contributors_concentration) strength=0.24 conf=0.00
    - t0=2025-05 sustained_months=8
    - zscore_12_last=1.51
    - percentile_rank_24m_last=1.00

## cta-observatory/magic-cta-pipe

- risk_score: 0.882
- risk_level: High
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.583
- missing_rate: 0.417
- main_signals:
  - BUS_FACTOR_LOW_OR_DOWN Bus Factor 过低或持续下降（单点维护风险） (contributors_concentration) strength=1.00 conf=0.00
    - t0=2025-02 sustained_months=7
    - zscore_12_last=-1.21
    - percentile_rank_24m_last=0.17
  - CONTRIB_SHRINK_3M 贡献者规模收缩（3个月） (contributors_concentration) strength=0.72 conf=0.00
    - t0=2025-05 sustained_months=5
    - zscore_12_last=-1.18
    - percentile_rank_24m_last=0.19
  - CODE_CHURN_DROP_3M 代码变更规模下滑（3个月） (activity_throughput) strength=0.27 conf=0.00
    - t0=2025-07 sustained_months=3
    - zscore_12_last=-0.65
    - percentile_rank_24m_last=0.13
  - INACTIVE_CONTRIB_SPIKE 不活跃贡献者上升（流失加剧） (contributors_concentration) strength=0.24 conf=0.00
    - t0=2025-08 sustained_months=5
    - zscore_12_last=2.71
    - percentile_rank_24m_last=1.00
  - DATA_SUFFICIENT_6M 数据覆盖充足（可评估，6个月） (composite) strength=0.01 conf=0.00
    - t0=2025-02 sustained_months=11
    - zscore_12_last=-0.98
    - percentile_rank_24m_last=0.12

## droibit/flutter_custom_tabs

- risk_score: 0.879
- risk_level: High
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.516
- missing_rate: 0.484
- main_signals:
  - BUS_FACTOR_LOW_OR_DOWN Bus Factor 过低或持续下降（单点维护风险） (contributors_concentration) strength=1.00 conf=0.00
    - t0=2025-01 sustained_months=12
    - zscore_12_last=-0.45
    - percentile_rank_24m_last=0.81
  - PR_SUPPLY_DEMAND_IMBALANCE_6M PR 供需失衡（提交>接受，持续6个月） (collaboration_efficiency) strength=0.30 conf=0.00
    - t0=2024-11 sustained_months=13
    - zscore_12_last=-0.07
    - percentile_rank_24m_last=0.57
  - INACTIVE_CONTRIB_SPIKE 不活跃贡献者上升（流失加剧） (contributors_concentration) strength=0.24 conf=0.00
    - t0=2025-09 sustained_months=4
    - zscore_12_last=1.73
    - percentile_rank_24m_last=1.00
  - ATTENTION_DROP_6M_AUX 外部关注衰减（辅助信号，6个月） (attention_engagement) strength=0.07 conf=0.00
    - t0=2025-01 sustained_months=7
    - zscore_12_last=-0.78
    - percentile_rank_24m_last=0.25
  - ISSUE_INFLOW_DROP_3M Issue 新增下降（3个月，解释性信号） (activity_throughput) strength=0.06 conf=0.00
    - t0=2025-03 sustained_months=7
    - zscore_12_last=-0.48
    - percentile_rank_24m_last=0.70

## laravel/nova-issues

- risk_score: 0.878
- risk_level: High
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.500
- missing_rate: 0.500
- main_signals:
  - BUS_FACTOR_LOW_OR_DOWN Bus Factor 过低或持续下降（单点维护风险） (contributors_concentration) strength=1.00 conf=0.00
    - t0=2025-03 sustained_months=10
    - zscore_12_last=-1.14
    - percentile_rank_24m_last=0.12
  - ACT_DROP_YOY_3M 活跃度同比持续下滑（3个月） (activity_throughput) strength=0.72 conf=0.00
    - t0=2025-05 sustained_months=3
    - zscore_12_last=-1.59
    - percentile_rank_24m_last=0.04
  - INACTIVE_CONTRIB_SPIKE 不活跃贡献者上升（流失加剧） (contributors_concentration) strength=0.24 conf=0.00
    - t0=2025-06 sustained_months=4
    - zscore_12_last=1.86
    - percentile_rank_24m_last=1.00
  - ISSUE_INFLOW_DROP_3M Issue 新增下降（3个月，解释性信号） (activity_throughput) strength=0.06 conf=0.00
    - t0=2025-05 sustained_months=8
    - zscore_12_last=-1.60
    - percentile_rank_24m_last=0.04

## SWIFTSIM/pipeline-configs

- risk_score: 0.852
- risk_level: High
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.365
- missing_rate: 0.635
- main_signals:
  - BUS_FACTOR_LOW_OR_DOWN Bus Factor 过低或持续下降（单点维护风险） (contributors_concentration) strength=1.00 conf=0.00
    - t0=2025-01 sustained_months=10
    - zscore_12_last=1.73
    - percentile_rank_24m_last=0.86
  - CODE_CHURN_DROP_3M 代码变更规模下滑（3个月） (activity_throughput) strength=0.27 conf=0.00
    - t0=2025-03 sustained_months=8
    - zscore_12_last=-2.57
    - percentile_rank_24m_last=0.05
  - DATA_SUFFICIENT_6M 数据覆盖充足（可评估，6个月） (composite) strength=0.01 conf=0.00
    - t0=2025-01 sustained_months=8
    - zscore_12_last=0.65
    - percentile_rank_24m_last=0.67

## JustTemmie/steam-presence

- risk_score: 0.847
- risk_level: High
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.587
- missing_rate: 0.413
- main_signals:
  - BUS_FACTOR_LOW_OR_DOWN Bus Factor 过低或持续下降（单点维护风险） (contributors_concentration) strength=1.00 conf=0.00
    - t0=2025-02 sustained_months=9
    - zscore_12_last=-0.49
    - percentile_rank_24m_last=0.39
  - ACT_DROP_YOY_3M 活跃度同比持续下滑（3个月） (activity_throughput) strength=0.72 conf=0.00
    - t0=2025-04 sustained_months=4
    - zscore_12_last=-0.67
    - percentile_rank_24m_last=0.14
  - PR_SUPPLY_DEMAND_IMBALANCE_6M PR 供需失衡（提交>接受，持续6个月） (collaboration_efficiency) strength=0.30 conf=0.00
    - t0=2024-01 sustained_months=21
    - zscore_12_last=-0.71
    - percentile_rank_24m_last=0.70
  - ATTENTION_DROP_6M_AUX 外部关注衰减（辅助信号，6个月） (attention_engagement) strength=0.07 conf=0.00
    - t0=2025-02 sustained_months=11
    - zscore_12_last=-0.62
    - percentile_rank_24m_last=0.25
  - ISSUE_INFLOW_DROP_3M Issue 新增下降（3个月，解释性信号） (activity_throughput) strength=0.06 conf=0.00
    - t0=2025-03 sustained_months=10
    - zscore_12_last=-0.22
    - percentile_rank_24m_last=0.76

## trustimaging/stride

- risk_score: 0.798
- risk_level: High
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.484
- missing_rate: 0.516
- main_signals:
  - BUS_FACTOR_LOW_OR_DOWN Bus Factor 过低或持续下降（单点维护风险） (contributors_concentration) strength=1.00 conf=0.00
    - t0=2025-02 sustained_months=11
    - zscore_12_last=-0.45
    - percentile_rank_24m_last=0.63
  - PR_SUPPLY_DEMAND_IMBALANCE_6M PR 供需失衡（提交>接受，持续6个月） (collaboration_efficiency) strength=0.30 conf=0.00
    - t0=2024-08 sustained_months=12
    - zscore_12_last=-0.56
    - percentile_rank_24m_last=0.62
  - INACTIVE_CONTRIB_SPIKE 不活跃贡献者上升（流失加剧） (contributors_concentration) strength=0.24 conf=0.00
    - t0=2025-07 sustained_months=4
    - zscore_12_last=1.18
    - percentile_rank_24m_last=1.00
  - DATA_SUFFICIENT_6M 数据覆盖充足（可评估，6个月） (composite) strength=0.01 conf=0.00
    - t0=2025-02 sustained_months=11
    - zscore_12_last=-0.08
    - percentile_rank_24m_last=0.42

## ACINQ/phoenixd

- risk_score: 0.794
- risk_level: High
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.643
- missing_rate: 0.357
- main_signals:
  - CODE_CHURN_DROP_3M 代码变更规模下滑（3个月） (activity_throughput) strength=0.27 conf=0.00
    - t0=2025-04 sustained_months=4
    - zscore_12_last=-0.32
    - percentile_rank_24m_last=0.13
  - INACTIVE_CONTRIB_SPIKE 不活跃贡献者上升（流失加剧） (contributors_concentration) strength=0.24 conf=0.00
    - t0=2025-09 sustained_months=4
    - zscore_12_last=2.24
    - percentile_rank_24m_last=1.00
  - ATTENTION_DROP_6M_AUX 外部关注衰减（辅助信号，6个月） (attention_engagement) strength=0.07 conf=0.00
    - t0=2025-03 sustained_months=10
    - zscore_12_last=-1.33
    - percentile_rank_24m_last=0.17
  - ISSUE_INFLOW_DROP_3M Issue 新增下降（3个月，解释性信号） (activity_throughput) strength=0.06 conf=0.00
    - t0=2025-05 sustained_months=4
    - zscore_12_last=-0.18
    - percentile_rank_24m_last=0.53
  - STABLE_NO_DECLINE_6M_INFO 近期未发现衰退（稳定/健康，6个月） (composite) strength=0.02 conf=0.00
    - t0=2025-02 sustained_months=6
    - zscore_12_last=-0.31
    - percentile_rank_24m_last=0.35

## JamesCJ60/Universal-x86-Tuning-Utility

- risk_score: 0.703
- risk_level: High
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.607
- missing_rate: 0.393
- main_signals:
  - BUS_FACTOR_LOW_OR_DOWN Bus Factor 过低或持续下降（单点维护风险） (contributors_concentration) strength=1.00 conf=0.00
    - t0=2025-02 sustained_months=7
    - zscore_12_last=-1.01
    - percentile_rank_24m_last=0.12
  - ACT_DROP_YOY_3M 活跃度同比持续下滑（3个月） (activity_throughput) strength=0.72 conf=0.00
    - t0=2025-05 sustained_months=3
    - zscore_12_last=-1.31
    - percentile_rank_24m_last=0.04
  - INACTIVE_CONTRIB_SPIKE 不活跃贡献者上升（流失加剧） (contributors_concentration) strength=0.24 conf=0.00
    - t0=2025-07 sustained_months=6
    - zscore_12_last=2.23
    - percentile_rank_24m_last=1.00
  - ATTENTION_DROP_6M_AUX 外部关注衰减（辅助信号，6个月） (attention_engagement) strength=0.07 conf=0.00
    - t0=2025-03 sustained_months=10
    - zscore_12_last=-1.72
    - percentile_rank_24m_last=0.04
  - ISSUE_INFLOW_DROP_3M Issue 新增下降（3个月，解释性信号） (activity_throughput) strength=0.06 conf=0.00
    - t0=2025-05 sustained_months=8
    - zscore_12_last=-0.71
    - percentile_rank_24m_last=0.25

## conda-forge/tensorflow-feedstock

- risk_score: 0.623
- risk_level: Medium
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.552
- missing_rate: 0.448
- main_signals:
  - PR_SUPPLY_DEMAND_IMBALANCE_6M PR 供需失衡（提交>接受，持续6个月） (collaboration_efficiency) strength=0.30 conf=0.00
    - t0=2025-02 sustained_months=10
    - zscore_12_last=-0.57
    - percentile_rank_24m_last=0.43
  - CODE_CHURN_DROP_3M 代码变更规模下滑（3个月） (activity_throughput) strength=0.27 conf=0.00
    - t0=2025-06 sustained_months=4
    - zscore_12_last=-1.44
    - percentile_rank_24m_last=0.09
  - INACTIVE_CONTRIB_SPIKE 不活跃贡献者上升（流失加剧） (contributors_concentration) strength=0.24 conf=0.00
    - t0=2025-07 sustained_months=4
    - zscore_12_last=1.98
    - percentile_rank_24m_last=1.00
  - ISSUE_INFLOW_DROP_3M Issue 新增下降（3个月，解释性信号） (activity_throughput) strength=0.06 conf=0.00
    - t0=2025-05 sustained_months=7
    - zscore_12_last=-0.77
    - percentile_rank_24m_last=0.47
  - DATA_SUFFICIENT_6M 数据覆盖充足（可评估，6个月） (composite) strength=0.01 conf=0.00
    - t0=2025-02 sustained_months=11
    - zscore_12_last=-0.16
    - percentile_rank_24m_last=0.35

## bmax121/KernelPatch

- risk_score: 0.587
- risk_level: Medium
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.714
- missing_rate: 0.286
- main_signals:
  - BUS_FACTOR_LOW_OR_DOWN Bus Factor 过低或持续下降（单点维护风险） (contributors_concentration) strength=1.00 conf=0.00
    - t0=2025-02 sustained_months=11
    - zscore_12_last=-0.12
    - percentile_rank_24m_last=0.65
  - PR_SUPPLY_DEMAND_IMBALANCE_6M PR 供需失衡（提交>接受，持续6个月） (collaboration_efficiency) strength=0.30 conf=0.00
    - t0=2024-10 sustained_months=15
    - zscore_12_last=-1.07
    - percentile_rank_24m_last=0.31
  - CODE_CHURN_DROP_3M 代码变更规模下滑（3个月） (activity_throughput) strength=0.27 conf=0.00
    - t0=2025-03 sustained_months=7
    - zscore_12_last=-0.46
    - percentile_rank_24m_last=0.28
  - INACTIVE_CONTRIB_SPIKE 不活跃贡献者上升（流失加剧） (contributors_concentration) strength=0.24 conf=0.00
    - t0=2025-07 sustained_months=3
    - zscore_12_last=1.61
    - percentile_rank_24m_last=1.00
  - ATTENTION_DROP_6M_AUX 外部关注衰减（辅助信号，6个月） (attention_engagement) strength=0.07 conf=0.00
    - t0=2025-02 sustained_months=11
    - zscore_12_last=-1.22
    - percentile_rank_24m_last=0.21

## easy-graph/Easy-Graph

- risk_score: 0.574
- risk_level: Medium
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.524
- missing_rate: 0.476
- main_signals:
  - BUS_FACTOR_LOW_OR_DOWN Bus Factor 过低或持续下降（单点维护风险） (contributors_concentration) strength=1.00 conf=0.00
    - t0=2024-11 sustained_months=14
    - zscore_12_last=-0.30
    - percentile_rank_24m_last=0.94
  - PR_SUPPLY_DEMAND_IMBALANCE_6M PR 供需失衡（提交>接受，持续6个月） (collaboration_efficiency) strength=0.30 conf=0.00
    - t0=2024-06 sustained_months=18
    - zscore_12_last=0.59
    - percentile_rank_24m_last=0.83
  - INACTIVE_CONTRIB_SPIKE 不活跃贡献者上升（流失加剧） (contributors_concentration) strength=0.24 conf=0.00
    - t0=2025-10 sustained_months=3
    - zscore_12_last=2.24
    - percentile_rank_24m_last=1.00
  - ATTENTION_DROP_6M_AUX 外部关注衰减（辅助信号，6个月） (attention_engagement) strength=0.07 conf=0.00
    - t0=2025-02 sustained_months=10
    - zscore_12_last=0.52
    - percentile_rank_24m_last=0.79
  - ISSUE_INFLOW_DROP_3M Issue 新增下降（3个月，解释性信号） (activity_throughput) strength=0.06 conf=0.00
    - t0=2024-10 sustained_months=13
    - zscore_12_last=-0.45
    - percentile_rank_24m_last=0.86

## XX-net/XX-Net

- risk_score: 0.556
- risk_level: Medium
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.560
- missing_rate: 0.440
- main_signals:
  - ACT_DROP_YOY_3M 活跃度同比持续下滑（3个月） (activity_throughput) strength=0.72 conf=0.00
    - t0=2025-05 sustained_months=3
    - zscore_12_last=-0.76
    - percentile_rank_24m_last=0.17
  - ATTENTION_DROP_6M_AUX 外部关注衰减（辅助信号，6个月） (attention_engagement) strength=0.07 conf=0.00
    - t0=2025-02 sustained_months=11
    - zscore_12_last=-1.04
    - percentile_rank_24m_last=0.08
  - ISSUE_INFLOW_DROP_3M Issue 新增下降（3个月，解释性信号） (activity_throughput) strength=0.06 conf=0.00
    - t0=2025-04 sustained_months=9
    - zscore_12_last=-1.37
    - percentile_rank_24m_last=0.04
  - DATA_SUFFICIENT_6M 数据覆盖充足（可评估，6个月） (composite) strength=0.01 conf=0.00
    - t0=2025-02 sustained_months=8
    - zscore_12_last=-0.76
    - percentile_rank_24m_last=0.17

## CarlosMontano2005/BEST_PLAYER_2024

- risk_score: 0.468
- risk_level: Medium
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.143
- missing_rate: 0.857

## coroo/nova-chartjs

- risk_score: 0.389
- risk_level: Medium
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.325
- missing_rate: 0.675
- main_signals:
  - BUS_FACTOR_LOW_OR_DOWN Bus Factor 过低或持续下降（单点维护风险） (contributors_concentration) strength=1.00 conf=0.00
    - t0=2025-01 sustained_months=8
    - zscore_12_last=-0.30
    - percentile_rank_24m_last=0.74
  - CODE_CHURN_DROP_3M 代码变更规模下滑（3个月） (activity_throughput) strength=0.27 conf=0.00
    - t0=2024-04 sustained_months=17
    - zscore_12_last=0.24
    - percentile_rank_24m_last=0.25
  - ATTENTION_DROP_6M_AUX 外部关注衰减（辅助信号，6个月） (attention_engagement) strength=0.07 conf=0.00
    - t0=2025-02 sustained_months=10
    - zscore_12_last=-0.91
    - percentile_rank_24m_last=0.25

## GreenUniversityComputerClub/gucc

- risk_score: 0.365
- risk_level: Medium
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.234
- missing_rate: 0.766
- main_signals:
  - PR_SUPPLY_DEMAND_IMBALANCE_6M PR 供需失衡（提交>接受，持续6个月） (collaboration_efficiency) strength=0.30 conf=0.00
    - t0=2025-03 sustained_months=8
    - zscore_12_last=-0.25
    - percentile_rank_24m_last=0.50
  - DATA_SUFFICIENT_6M 数据覆盖充足（可评估，6个月） (composite) strength=0.01 conf=0.00
    - t0=2025-03 sustained_months=10
    - zscore_12_last=-0.93
    - percentile_rank_24m_last=0.40

## falcosecurity/cncf-green-review-testing

- risk_score: 0.349
- risk_level: Medium
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.286
- missing_rate: 0.714
- main_signals:
  - INACTIVE_CONTRIB_SPIKE 不活跃贡献者上升（流失加剧） (contributors_concentration) strength=0.24 conf=0.00
    - t0=2025-08 sustained_months=3
    - zscore_12_last=1.46
    - percentile_rank_24m_last=1.00

## mdaus/nitro

- risk_score: 0.312
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.294
- missing_rate: 0.706
- main_signals:
  - BUS_FACTOR_LOW_OR_DOWN Bus Factor 过低或持续下降（单点维护风险） (contributors_concentration) strength=1.00 conf=0.00
    - t0=2024-10 sustained_months=15
    - zscore_12_last=-0.30
    - percentile_rank_24m_last=1.00
  - ISSUE_INFLOW_DROP_3M Issue 新增下降（3个月，解释性信号） (activity_throughput) strength=0.06 conf=0.00
    - t0=2024-10 sustained_months=15
    - zscore_12_last=-0.58
    - percentile_rank_24m_last=0.75
  - DATA_SUFFICIENT_6M 数据覆盖充足（可评估，6个月） (composite) strength=0.01 conf=0.00
    - t0=2024-10 sustained_months=14
    - zscore_12_last=-1.31
    - percentile_rank_24m_last=0.07

## return42/searxng

- risk_score: 0.299
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.298
- missing_rate: 0.702
- main_signals:
  - BUS_FACTOR_LOW_OR_DOWN Bus Factor 过低或持续下降（单点维护风险） (contributors_concentration) strength=1.00 conf=0.00
    - t0=2024-12 sustained_months=9
    - percentile_rank_24m_last=1.00

## jenkinsci/spotinst-plugin

- risk_score: 0.252
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.226
- missing_rate: 0.774
- main_signals:
  - INACTIVE_CONTRIB_SPIKE 不活跃贡献者上升（流失加剧） (contributors_concentration) strength=0.24 conf=0.00
    - t0=2025-05 sustained_months=6
    - zscore_12_last=1.41
    - percentile_rank_24m_last=1.00

## teamtype/teamtype

- risk_score: 0.229
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.540
- missing_rate: 0.460
- main_signals:
  - ISSUE_INFLOW_DROP_3M Issue 新增下降（3个月，解释性信号） (activity_throughput) strength=0.06 conf=0.00
    - t0=2025-09 sustained_months=4
    - zscore_12_last=-0.64
    - percentile_rank_24m_last=0.27

## conda-forge/webtest-feedstock

- risk_score: 0.179
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.171
- missing_rate: 0.829
- main_signals:
  - PR_SUPPLY_DEMAND_IMBALANCE_6M PR 供需失衡（提交>接受，持续6个月） (collaboration_efficiency) strength=0.30 conf=0.00
    - t0=2020-04 sustained_months=67
    - zscore_12_last=-0.41
    - percentile_rank_24m_last=0.75
  - DATA_SUFFICIENT_6M 数据覆盖充足（可评估，6个月） (composite) strength=0.01 conf=0.00
    - t0=2024-11 sustained_months=12
    - zscore_12_last=-0.73
    - percentile_rank_24m_last=0.50

## schibsted/account-sdk-android-web

- risk_score: 0.168
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.317
- missing_rate: 0.683
- main_signals:
  - BUS_FACTOR_LOW_OR_DOWN Bus Factor 过低或持续下降（单点维护风险） (contributors_concentration) strength=1.00 conf=0.00
    - t0=2024-10 sustained_months=14
    - zscore_12_last=-0.55
    - percentile_rank_24m_last=0.80
  - CODE_CHURN_DROP_3M 代码变更规模下滑（3个月） (activity_throughput) strength=0.27 conf=0.00
    - t0=2025-02 sustained_months=8
    - zscore_12_last=-0.57
    - percentile_rank_24m_last=0.42
  - DATA_SUFFICIENT_6M 数据覆盖充足（可评估，6个月） (composite) strength=0.01 conf=0.00
    - t0=2024-10 sustained_months=14
    - zscore_12_last=-1.11
    - percentile_rank_24m_last=0.07

## atomiks/tippyjs-react

- risk_score: 0.109
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.266
- missing_rate: 0.734
- main_signals:
  - ATTENTION_DROP_6M_AUX 外部关注衰减（辅助信号，6个月） (attention_engagement) strength=0.07 conf=0.00
    - t0=2025-02 sustained_months=11
    - zscore_12_last=-0.87
    - percentile_rank_24m_last=0.12

## GoogleCloudPlatform/gke-poc-toolkit

- risk_score: 0.107
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.198
- missing_rate: 0.802
- main_signals:
  - CODE_CHURN_DROP_3M 代码变更规模下滑（3个月） (activity_throughput) strength=0.27 conf=0.00
    - t0=2025-03 sustained_months=5
    - zscore_12_last=-0.17
    - percentile_rank_24m_last=0.40
  - ATTENTION_DROP_6M_AUX 外部关注衰减（辅助信号，6个月） (attention_engagement) strength=0.07 conf=0.00
    - t0=2024-04 sustained_months=18
    - zscore_12_last=-0.85
    - percentile_rank_24m_last=0.50
  - DATA_SUFFICIENT_6M 数据覆盖充足（可评估，6个月） (composite) strength=0.01 conf=0.00
    - t0=2024-04 sustained_months=17
    - zscore_12_last=-0.33
    - percentile_rank_24m_last=0.67

## aternosorg/modbot

- risk_score: 0.101
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.306
- missing_rate: 0.694
- main_signals:
  - BUS_FACTOR_LOW_OR_DOWN Bus Factor 过低或持续下降（单点维护风险） (contributors_concentration) strength=1.00 conf=0.00
    - t0=2024-07 sustained_months=13
    - zscore_12_last=-0.53
    - percentile_rank_24m_last=0.67
  - ATTENTION_DROP_6M_AUX 外部关注衰减（辅助信号，6个月） (attention_engagement) strength=0.07 conf=0.00
    - t0=2025-02 sustained_months=10
    - zscore_12_last=-1.70
    - percentile_rank_24m_last=0.24
  - DATA_SUFFICIENT_6M 数据覆盖充足（可评估，6个月） (composite) strength=0.01 conf=0.00
    - t0=2024-06 sustained_months=14
    - zscore_12_last=-0.76
    - percentile_rank_24m_last=0.29

## gudaoxuri/dew

- risk_score: 0.095
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.175
- missing_rate: 0.825

## Topshelf/Topshelf

- risk_score: 0.094
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.190
- missing_rate: 0.810
- main_signals:
  - ATTENTION_DROP_6M_AUX 外部关注衰减（辅助信号，6个月） (attention_engagement) strength=0.07 conf=0.00
    - t0=2025-02 sustained_months=10
    - zscore_12_last=-0.92
    - percentile_rank_24m_last=0.22

## puppetlabs/install-puppet

- risk_score: 0.093
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.163
- missing_rate: 0.837
- main_signals:
  - INACTIVE_CONTRIB_SPIKE 不活跃贡献者上升（流失加剧） (contributors_concentration) strength=0.24 conf=0.00
    - t0=2025-06 sustained_months=5
    - zscore_12_last=1.31
    - percentile_rank_24m_last=1.00

## coding-blocks/hackerblocks.projectx

- risk_score: 0.072
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.202
- missing_rate: 0.798
- main_signals:
  - BUS_FACTOR_LOW_OR_DOWN Bus Factor 过低或持续下降（单点维护风险） (contributors_concentration) strength=1.00 conf=0.00
    - t0=2024-04 sustained_months=19
    - zscore_12_last=-0.30
    - percentile_rank_24m_last=1.00
  - DATA_SUFFICIENT_6M 数据覆盖充足（可评估，6个月） (composite) strength=0.01 conf=0.00
    - t0=2024-04 sustained_months=19
    - zscore_12_last=-2.07
    - percentile_rank_24m_last=0.11

## Cerebellum-Network/grant-program

- risk_score: 0.054
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.139
- missing_rate: 0.861
- main_signals:
  - DATA_SUFFICIENT_6M 数据覆盖充足（可评估，6个月） (composite) strength=0.01 conf=0.00
    - t0=2025-04 sustained_months=9
    - zscore_12_last=-0.68
    - percentile_rank_24m_last=0.50

## conda-forge/aenum-feedstock

- risk_score: 0.053
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.091
- missing_rate: 0.909

## rizafahmi/awesome-speakers-id

- risk_score: 0.052
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.087
- missing_rate: 0.913

## IU3Labs/ToP_2025

- risk_score: 0.046
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.175
- missing_rate: 0.825
- main_signals:
  - DATA_SUFFICIENT_6M 数据覆盖充足（可评估，6个月） (composite) strength=0.01 conf=0.00
    - t0=2025-04 sustained_months=7
    - zscore_12_last=-1.49
    - percentile_rank_24m_last=0.25

## muhandojeon/Why-Do-We-Work

- risk_score: 0.041
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.095
- missing_rate: 0.905

## grafana/otel-operator-demo

- risk_score: 0.038
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.087
- missing_rate: 0.913

## umrover/mrover-workspace

- risk_score: 0.027
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.071
- missing_rate: 0.929

## TeCOS-NIT-Trichy/first-issue-demo

- risk_score: 0.027
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.071
- missing_rate: 0.929

## tomasbedrich/home-assistant-hikconnect

- risk_score: 0.027
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.298
- missing_rate: 0.702
- main_signals:
  - BUS_FACTOR_LOW_OR_DOWN Bus Factor 过低或持续下降（单点维护风险） (contributors_concentration) strength=1.00 conf=0.00
    - t0=2024-07 sustained_months=13
    - zscore_12_last=-1.04
    - percentile_rank_24m_last=0.41
  - ACT_DROP_YOY_3M 活跃度同比持续下滑（3个月） (activity_throughput) strength=0.72 conf=0.00
    - t0=2024-12 sustained_months=8
    - zscore_12_last=-0.66
    - percentile_rank_24m_last=0.35
  - ATTENTION_DROP_6M_AUX 外部关注衰减（辅助信号，6个月） (attention_engagement) strength=0.07 conf=0.00
    - t0=2025-03 sustained_months=8
    - zscore_12_last=-0.77
    - percentile_rank_24m_last=0.50
  - DATA_SUFFICIENT_6M 数据覆盖充足（可评估，6个月） (composite) strength=0.01 conf=0.00
    - t0=2024-07 sustained_months=14
    - zscore_12_last=-0.66
    - percentile_rank_24m_last=0.35

## taikoxyz/taiko-client

- risk_score: 0.024
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.123
- missing_rate: 0.877

## welfoz/Machi_Koro

- risk_score: 0.024
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.091
- missing_rate: 0.909

## StatisticsGreenland/pxmake

- risk_score: 0.023
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.496
- missing_rate: 0.504
- main_signals:
  - BUS_FACTOR_LOW_OR_DOWN Bus Factor 过低或持续下降（单点维护风险） (contributors_concentration) strength=1.00 conf=0.00
    - t0=2025-02 sustained_months=11
    - zscore_12_last=2.47
    - percentile_rank_24m_last=1.00
  - ISSUE_INFLOW_DROP_3M Issue 新增下降（3个月，解释性信号） (activity_throughput) strength=0.06 conf=0.00
    - t0=2025-04 sustained_months=9
    - zscore_12_last=-0.77
    - percentile_rank_24m_last=0.38
  - DATA_SUFFICIENT_6M 数据覆盖充足（可评估，6个月） (composite) strength=0.01 conf=0.00
    - t0=2025-02 sustained_months=11
    - zscore_12_last=-0.29
    - percentile_rank_24m_last=0.50

## AgoraIO/Basic-Video-Call

- risk_score: 0.022
- risk_level: Low
- needs_review: True
- forecast_uncertainty_ratio: 0.000
- avg_raw_ratio_win3: 0.000
- avg_coverage: 0.286
- missing_rate: 0.714
- main_signals:
  - BUS_FACTOR_LOW_OR_DOWN Bus Factor 过低或持续下降（单点维护风险） (contributors_concentration) strength=1.00 conf=0.00
    - t0=2023-12 sustained_months=24
    - zscore_12_last=-0.42
    - percentile_rank_24m_last=1.00
  - ATTENTION_DROP_6M_AUX 外部关注衰减（辅助信号，6个月） (attention_engagement) strength=0.07 conf=0.00
    - t0=2025-04 sustained_months=9
    - zscore_12_last=-0.98
    - percentile_rank_24m_last=0.23
  - ISSUE_INFLOW_DROP_3M Issue 新增下降（3个月，解释性信号） (activity_throughput) strength=0.06 conf=0.00
    - t0=2024-10 sustained_months=12
    - zscore_12_last=-0.53
    - percentile_rank_24m_last=1.00

