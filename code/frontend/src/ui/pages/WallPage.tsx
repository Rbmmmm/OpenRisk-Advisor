import type { RiskReportBundle, RiskReportItem } from "../../core/types";
import { countByLevel, fmt, needsReview, riskLevel, riskScore, sortByRiskDesc } from "../../core/utils";
import ReactECharts from "echarts-for-react";
import { useEffect, useMemo, useState } from "react";

const SIGNAL_NAME_MAP: Record<string, string> = {
  ACT_DROP_YOY_3M: "活跃度同比下滑",
  CODE_CHURN_DROP_3M: "代码变更下降",
  PR_THROUGHPUT_DROP_3M: "PR 吞吐下降",
  PR_SUPPLY_DEMAND_IMBALANCE_6M: "PR 供需失衡",
  ISSUE_INFLOW_DROP_3M: "Issue 新增下降",
  ATTENTION_DROP_6M_AUX: "外部关注下降",
  INACTIVE_CONTRIB_SPIKE: "贡献者流失上升",
  CONTRIB_SHRINK_3M: "贡献者规模收缩",
  BUS_FACTOR_LOW_OR_DOWN: "Bus Factor 偏低",
  STABLE_NO_DECLINE_6M_INFO: "稳定无明显下滑",
  DATA_SUFFICIENT_6M: "数据覆盖充足",
};

const DIMENSION_NAME_MAP: Record<string, string> = {
  activity_throughput: "活跃度/吞吐",
  contributors_concentration: "贡献者结构",
  collaboration_efficiency: "协作效率",
  attention_engagement: "外部关注",
  openrank_reference: "OpenRank 参照",
  composite: "综合衰退",
};

function friendlySignal(id?: string) {
  if (!id) return "—";
  return SIGNAL_NAME_MAP[id] ?? id.replaceAll("_", " ");
}

function friendlyDimension(name?: string) {
  if (!name) return "—";
  return DIMENSION_NAME_MAP[name] ?? name.replaceAll("_", " ");
}

function repoStatusText(item: RiskReportItem) {
  return (item as any).note === "no_prediction_available" ? "上游缺失数据" : "已评估";
}

function topSignals(items: any[]): Array<{ name: string; value: number }> {
  const m = new Map<string, number>();
  for (const it of items) {
    for (const s of it.main_signals ?? []) {
      const id = s.signal_id ?? "unknown";
      m.set(id, (m.get(id) ?? 0) + 1);
    }
  }
  return Array.from(m.entries())
    .map(([name, value]) => ({ name: friendlySignal(name), value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 10);
}

function topDimensions(items: RiskReportItem[]): Array<{ name: string; value: number }> {
  const m = new Map<string, number>();
  for (const it of items) {
    for (const s of it.main_signals ?? []) {
      const d = s.dimension ?? "unknown";
      m.set(d, (m.get(d) ?? 0) + 1);
    }
  }
  return Array.from(m.entries())
    .map(([name, value]) => ({ name: friendlyDimension(name), value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);
}

function histogram(values: number[], bins: number): { x: string[]; y: number[] } {
  const counts = new Array(bins).fill(0);
  for (const v0 of values) {
    const v = Math.max(0, Math.min(1, v0));
    const idx = Math.min(bins - 1, Math.floor(v * bins));
    counts[idx] += 1;
  }
  const x = counts.map((_, i) => `${(i / bins).toFixed(2)}-${((i + 1) / bins).toFixed(2)}`);
  return { x, y: counts };
}

function histogramClamped(values: number[], bins: number, max: number): { x: string[]; y: number[] } {
  const counts = new Array(bins).fill(0);
  const cap = Math.max(0.0001, max);
  for (const v0 of values) {
    const v = Math.max(0, Math.min(cap, v0));
    const idx = Math.min(bins - 1, Math.floor((v / cap) * bins));
    counts[idx] += 1;
  }
  const x = counts.map((_, i) => `${((i / bins) * cap).toFixed(2)}-${(((i + 1) / bins) * cap).toFixed(2)}`);
  return { x, y: counts };
}

function t0Distribution(items: RiskReportItem[]): Array<{ name: string; value: number }> {
  const m = new Map<string, number>();
  for (const it of items) {
    for (const s of it.main_signals ?? []) {
      const t0 = s.time_window?.t0 ?? s.when?.start_month;
      if (!t0) continue;
      m.set(t0, (m.get(t0) ?? 0) + 1);
    }
  }
  return Array.from(m.entries())
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => a.name.localeCompare(b.name))
    .slice(-12);
}

function metricCoverage(items: RiskReportItem[]): Array<{ name: string; value: number }> {
  const sums = new Map<string, number>();
  const counts = new Map<string, number>();
  for (const it of items) {
    const metrics = it.data_quality?.metrics ?? {};
    for (const [name, meta] of Object.entries(metrics)) {
      const cov = (meta as any)?.coverage;
      if (typeof cov !== "number" || Number.isNaN(cov)) continue;
      sums.set(name, (sums.get(name) ?? 0) + cov);
      counts.set(name, (counts.get(name) ?? 0) + 1);
    }
  }
  const out = Array.from(sums.entries()).map(([name, sum]) => ({
    name,
    value: sum / Math.max(1, counts.get(name) ?? 0),
  }));
  out.sort((a, b) => a.value - b.value);
  return out.slice(0, 10);
}

function coverageRiskScatter(items: RiskReportItem[]) {
  const pts: Array<[number, number, string]> = [];
  for (const it of items) {
    const x = Number(it.data_quality?.avg_coverage ?? NaN);
    const y = Number(riskScore(it));
    if (Number.isNaN(x) || Number.isNaN(y)) continue;
    pts.push([Math.max(0, Math.min(1, x)), Math.max(0, Math.min(1, y)), it.repo]);
  }
  return pts.slice(0, 600);
}

function levelChipClass(level: string) {
  if (level === "High") return "chip chipHigh";
  if (level === "Medium") return "chip chipMid";
  return "chip chipLow";
}

export default function WallPage({
  bundle,
  loading,
  error,
  onRefresh,
}: {
  bundle: RiskReportBundle | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}) {
  const items = bundle?.items ?? [];
  const [chartMode, setChartMode] = useState<"risk_curve" | "coverage_hist" | "missing_hist">("risk_curve");
  const [levelFilter, setLevelFilter] = useState<"All" | "High" | "Medium" | "Low">("All");
  const sorted = useMemo(() => sortByRiskDesc(items), [items]);
  const filtered = useMemo(() => {
    if (levelFilter === "All") return items;
    return items.filter((it) => String(riskLevel(it)) === levelFilter);
  }, [items, levelFilter]);
  const filteredSorted = useMemo(() => sortByRiskDesc(filtered), [filtered]);
  const counts = useMemo(() => countByLevel(items), [items]);
  const avg = useMemo(
    () => items.reduce((a, it) => a + riskScore(it), 0) / Math.max(1, items.length),
    [items]
  );
  const avgCoverage = useMemo(
    () => items.reduce((a, it) => a + (it.data_quality?.avg_coverage ?? 0), 0) / Math.max(1, items.length),
    [items]
  );
  const avgMissing = useMemo(
    () => items.reduce((a, it) => a + (it.data_quality?.missing_rate ?? 0), 0) / Math.max(1, items.length),
    [items]
  );
  const avgUncertainty = useMemo(
    () =>
      items.reduce((a, it) => a + (it.model_uncertainty?.forecast_uncertainty_ratio ?? 0), 0) /
      Math.max(1, items.length),
    [items]
  );

  const top10 = sorted.slice(0, 10);
  const topSig = topSignals(items);
  const topDim = topDimensions(items);
  const hist = histogram(items.map(riskScore), 14);
  const t0 = t0Distribution(items);
  const covScatter = coverageRiskScatter(sorted);
  const metricsCoverage = metricCoverage(items);
  const missingHist = histogram(items.map((it) => it.data_quality?.missing_rate ?? 0), 12);
  const coverageHist = histogram(items.map((it) => it.data_quality?.avg_coverage ?? 0), 12);
  const filteredMissingHist = useMemo(
    () => histogram(filtered.map((it) => it.data_quality?.missing_rate ?? 0), 12),
    [filtered]
  );
  const filteredCoverageHist = useMemo(
    () => histogram(filtered.map((it) => it.data_quality?.avg_coverage ?? 0), 12),
    [filtered]
  );
  const riskCurve = useMemo(
    () => ({
      labels: filteredSorted.map((_, idx) => String(idx + 1)),
      values: filteredSorted.map((it) => riskScore(it)),
      repos: filteredSorted.map((it) => it.repo),
    }),
    [filteredSorted]
  );
  const maxUnc = Math.min(
    Math.max(
      1,
      ...items.map((it) => (it.model_uncertainty?.forecast_uncertainty_ratio ?? 0))
    ),
    3
  );
  const uncHist = histogramClamped(
    items.map((it) => it.model_uncertainty?.forecast_uncertainty_ratio ?? 0),
    12,
    maxUnc
  );

  const [clock, setClock] = useState<string>(() => new Date().toLocaleString());
  useEffect(() => {
    const t = setInterval(() => setClock(new Date().toLocaleString()), 1000);
    return () => clearInterval(t);
  }, []);

  const spotlight = useMemo(() => {
    // Prefer the highest-risk not-review-only? Keep simple: top1.
    return sorted[0] ?? null;
  }, [sorted]);

  const spotlightSignals = useMemo(() => {
    if (!spotlight) return [];
    return (spotlight.main_signals ?? []).slice(0, 2);
  }, [spotlight]);

  const donutOpt = {
    backgroundColor: "transparent",
    series: [
      {
        type: "pie",
        radius: ["52%", "80%"],
        center: ["50%", "52%"],
        label: { show: false },
        data: [
          { value: counts.High ?? 0, name: "High", itemStyle: { color: "rgba(255,90,122,.92)" } },
          { value: counts.Medium ?? 0, name: "Medium", itemStyle: { color: "rgba(255,180,84,.92)" } },
          { value: counts.Low ?? 0, name: "Low", itemStyle: { color: "rgba(68,209,158,.92)" } },
        ],
      },
    ],
  };

  const topSignalOpt = {
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    grid: { left: 170, right: 18, top: 18, bottom: 24 },
    xAxis: {
      type: "value",
      axisLabel: { color: "rgba(169,183,224,.62)", fontFamily: "ui-monospace" },
      splitLine: { lineStyle: { color: "rgba(56,76,128,.18)" } },
    },
    yAxis: {
      type: "category",
      data: topSig.map((s) => s.name),
      axisLabel: { color: "rgba(169,183,224,.82)", fontFamily: "ui-monospace" },
      axisLine: { lineStyle: { color: "rgba(56,76,128,.25)" } },
    },
    series: [
      {
        type: "bar",
        data: topSig.map((s) => s.value),
        itemStyle: {
          color: "rgba(97,213,255,.62)",
          borderColor: "rgba(122,162,255,.35)",
          borderWidth: 1,
        },
      },
    ],
  };

  const dimOpt = {
    backgroundColor: "transparent",
    tooltip: { trigger: "item" },
    legend: {
      orient: "vertical",
      right: 8,
      top: "center",
      textStyle: { color: "rgba(169,183,224,.78)", fontFamily: "ui-monospace" },
    },
    series: [
      {
        type: "pie",
        radius: ["45%", "74%"],
        center: ["40%", "52%"],
        label: { show: false },
        data: topDim.map((d) => ({ value: d.value, name: d.name })),
        itemStyle: { borderColor: "rgba(7,10,18,.6)", borderWidth: 1 },
      },
    ],
  };

  const histOpt = {
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    grid: { left: 42, right: 14, top: 16, bottom: 44 },
    xAxis: {
      type: "category",
      data: hist.x,
      axisLabel: {
        color: "rgba(169,183,224,.62)",
        fontFamily: "ui-monospace",
        interval: 2,
        rotate: 32,
        fontSize: 10,
      },
      axisLine: { lineStyle: { color: "rgba(56,76,128,.25)" } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "rgba(169,183,224,.62)", fontFamily: "ui-monospace" },
      splitLine: { lineStyle: { color: "rgba(56,76,128,.18)" } },
    },
    series: [
      {
        type: "bar",
        data: hist.y,
        itemStyle: {
          color: "rgba(122,162,255,.62)",
          borderColor: "rgba(97,213,255,.30)",
          borderWidth: 1,
        },
      },
    ],
  };

  const t0Opt = {
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    grid: { left: 46, right: 14, top: 16, bottom: 44 },
    xAxis: {
      type: "category",
      data: t0.map((d) => d.name),
      axisLabel: {
        color: "rgba(169,183,224,.62)",
        fontFamily: "ui-monospace",
        interval: Math.max(1, Math.floor(t0.length / 6)),
        rotate: 28,
        fontSize: 10,
      },
      axisLine: { lineStyle: { color: "rgba(56,76,128,.25)" } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "rgba(169,183,224,.62)", fontFamily: "ui-monospace" },
      splitLine: { lineStyle: { color: "rgba(56,76,128,.18)" } },
    },
    series: [
      {
        type: "line",
        data: t0.map((d) => d.value),
        symbol: "none",
        lineStyle: { width: 2, color: "rgba(97,213,255,.75)" },
        areaStyle: { color: "rgba(97,213,255,.18)" },
      },
    ],
  };

  const riskCurveOpt = {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      formatter: (params: any) => {
        const p = Array.isArray(params) ? params[0] : params;
        const idx = Number(p?.dataIndex ?? 0);
        const repo = riskCurve.repos[idx] ?? "—";
        const value = Array.isArray(p?.value) ? p.value[1] : p?.value ?? 0;
        return `${repo}<br/>风险=${fmt(value, 3)}<br/>排序=${idx + 1}`;
      },
    },
    grid: { left: 46, right: 16, top: 16, bottom: 28 },
    xAxis: {
      type: "category",
      data: riskCurve.labels,
      axisLabel: {
        color: "rgba(169,183,224,.62)",
        fontFamily: "ui-monospace",
        interval: Math.max(1, Math.floor(riskCurve.labels.length / 8)),
      },
      axisLine: { lineStyle: { color: "rgba(56,76,128,.25)" } },
    },
    yAxis: {
      type: "value",
      min: 0,
      max: 1,
      axisLabel: { color: "rgba(169,183,224,.62)", fontFamily: "ui-monospace" },
      splitLine: { lineStyle: { color: "rgba(56,76,128,.18)" } },
    },
    series: [
      {
        type: "line",
        data: riskCurve.values,
        symbol: "none",
        lineStyle: { width: 2, color: "rgba(97,213,255,.75)" },
        areaStyle: { color: "rgba(97,213,255,.18)" },
      },
    ],
  };

  const covScatterOpt = {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      formatter: (p: any) => {
        const v = p.value as [number, number, string];
        return `${v[2]}<br/>覆盖率=${fmt(v[0], 2)}<br/>风险=${fmt(v[1], 2)}`;
      },
    },
    grid: { left: 42, right: 18, top: 16, bottom: 40 },
    xAxis: {
      type: "value",
      min: 0,
      max: 1,
      name: "覆盖率",
      nameTextStyle: { color: "rgba(169,183,224,.62)", fontFamily: "ui-monospace" },
      axisLabel: { color: "rgba(169,183,224,.62)", fontFamily: "ui-monospace" },
      splitLine: { lineStyle: { color: "rgba(56,76,128,.18)" } },
    },
    yAxis: {
      type: "value",
      min: 0,
      max: 1,
      name: "风险",
      nameTextStyle: { color: "rgba(169,183,224,.62)", fontFamily: "ui-monospace" },
      axisLabel: { color: "rgba(169,183,224,.62)", fontFamily: "ui-monospace" },
      splitLine: { lineStyle: { color: "rgba(56,76,128,.18)" } },
    },
    series: [
      {
        type: "scatter",
        data: covScatter.map((v) => ({ value: v })),
        symbolSize: 6,
        itemStyle: { color: "rgba(68,209,158,.68)" },
      },
    ],
  };

  const missingOpt = {
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    grid: { left: 42, right: 14, top: 16, bottom: 44 },
    xAxis: {
      type: "category",
      data: missingHist.x,
      axisLabel: {
        color: "rgba(169,183,224,.62)",
        fontFamily: "ui-monospace",
        interval: 2,
        rotate: 32,
        fontSize: 10,
      },
      axisLine: { lineStyle: { color: "rgba(56,76,128,.25)" } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "rgba(169,183,224,.62)", fontFamily: "ui-monospace" },
      splitLine: { lineStyle: { color: "rgba(56,76,128,.18)" } },
    },
    series: [
      {
        type: "bar",
        data: missingHist.y,
        itemStyle: {
          color: "rgba(255,90,122,.55)",
          borderColor: "rgba(255,90,122,.25)",
          borderWidth: 1,
        },
      },
    ],
  };

  const coverageOpt = {
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    grid: { left: 42, right: 14, top: 16, bottom: 44 },
    xAxis: {
      type: "category",
      data: coverageHist.x,
      axisLabel: {
        color: "rgba(169,183,224,.62)",
        fontFamily: "ui-monospace",
        interval: 2,
        rotate: 32,
        fontSize: 10,
      },
      axisLine: { lineStyle: { color: "rgba(56,76,128,.25)" } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "rgba(169,183,224,.62)", fontFamily: "ui-monospace" },
      splitLine: { lineStyle: { color: "rgba(56,76,128,.18)" } },
    },
    series: [
      {
        type: "bar",
        data: coverageHist.y,
        itemStyle: {
          color: "rgba(68,209,158,.55)",
          borderColor: "rgba(68,209,158,.25)",
          borderWidth: 1,
        },
      },
    ],
  };

  const filteredMissingOpt = {
    ...missingOpt,
    xAxis: { ...missingOpt.xAxis, data: filteredMissingHist.x },
    series: [{ ...missingOpt.series[0], data: filteredMissingHist.y }],
  };

  const filteredCoverageOpt = {
    ...coverageOpt,
    xAxis: { ...coverageOpt.xAxis, data: filteredCoverageHist.x },
    series: [{ ...coverageOpt.series[0], data: filteredCoverageHist.y }],
  };

  const trendOpt = useMemo(() => {
    if (chartMode === "coverage_hist") return filteredCoverageOpt;
    if (chartMode === "missing_hist") return filteredMissingOpt;
    return riskCurveOpt;
  }, [chartMode, filteredCoverageOpt, filteredMissingOpt, riskCurveOpt]);

  const uncOpt = {
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    grid: { left: 42, right: 14, top: 16, bottom: 28 },
    xAxis: {
      type: "category",
      data: uncHist.x,
      axisLabel: { color: "rgba(169,183,224,.62)", fontFamily: "ui-monospace", interval: 2 },
      axisLine: { lineStyle: { color: "rgba(56,76,128,.25)" } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "rgba(169,183,224,.62)", fontFamily: "ui-monospace" },
      splitLine: { lineStyle: { color: "rgba(56,76,128,.18)" } },
    },
    series: [
      {
        type: "bar",
        data: uncHist.y,
        itemStyle: {
          color: "rgba(97,213,255,.55)",
          borderColor: "rgba(97,213,255,.25)",
          borderWidth: 1,
        },
      },
    ],
  };

  const coverageMetricOpt = {
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    grid: { left: 170, right: 16, top: 18, bottom: 24 },
    xAxis: {
      type: "value",
      min: 0,
      max: 1,
      axisLabel: { color: "rgba(169,183,224,.62)", fontFamily: "ui-monospace" },
      splitLine: { lineStyle: { color: "rgba(56,76,128,.18)" } },
    },
    yAxis: {
      type: "category",
      data: metricsCoverage.map((d) => d.name),
      axisLabel: { color: "rgba(169,183,224,.82)", fontFamily: "ui-monospace" },
      axisLine: { lineStyle: { color: "rgba(56,76,128,.25)" } },
    },
    series: [
      {
        type: "bar",
        data: metricsCoverage.map((d) => d.value),
        itemStyle: {
          color: (p: any) => {
            const v = Number(metricsCoverage[p.dataIndex]?.value ?? 0);
            if (v < 0.5) return "rgba(255,90,122,.65)";
            if (v < 0.8) return "rgba(255,180,84,.65)";
            return "rgba(68,209,158,.65)";
          },
          borderColor: "rgba(122,162,255,.25)",
          borderWidth: 1,
        },
      },
    ],
  };

  const tickerText = useMemo(() => {
    const top = top10
      .slice(0, 10)
      .map((it) => `${it.repo} · 风险=${fmt(riskScore(it), 3)} · ${String(riskLevel(it))} · t0=${it.main_signals?.[0]?.time_window?.t0 ?? "—"}`);
    const joined = top.join("   •   ");
    return `${joined}   •   ${joined}`;
  }, [top10]);

  return (
    <div className="wall">
      <div className="wallTop">
        <div>
          <div className="wallTitle">OpenRisk-Advisor · 风险大屏</div>
          <div className="wallMeta">
            {bundle ? `统计月=${bundle.as_of_month ?? "—"} · 模型=${bundle.model?.type ?? "—"}/${bundle.model?.version ?? ""} · 仓库数=${items.length}` : "无数据"}
          </div>
          <div className="wallMeta" style={{ fontSize: 12, opacity: 0.8 }}>
            风险展示页，适合大屏轮播与汇报。
          </div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <div className="badge" title="local clock">
            <span className="mono">{clock}</span>
          </div>
          <button className="btn btnGhost" onClick={() => (document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen())}>
            全屏
          </button>
          <button className="btn" onClick={onRefresh} disabled={loading}>
            {loading ? "加载中…" : "刷新"}
          </button>
        </div>
      </div>

      <div className="wallMain">
        <div className="wallGrid">
          <div className="wallCard" style={{ gridColumn: "1", gridRow: "1" }}>
            <div className="panelTitle">全局指标</div>
            <div className="wallCardBody">
              <div style={{ marginTop: 6, display: "grid", gap: 8 }}>
                <div className="row">
                  <div className="muted">仓库数</div>
                  <div className="mono">{items.length}</div>
                </div>
                <div className="row">
                  <div className="muted">平均风险</div>
                  <div className="mono">{fmt(avg, 3)}</div>
                </div>
                <div className="row">
                  <div className="muted">需复核</div>
                  <div className="mono">{items.filter((i) => needsReview(i)).length}</div>
                </div>
                <div className="row">
                <div className="muted">平均覆盖率</div>
                <div className="mono">{fmt(avgCoverage, 3)}</div>
              </div>
              <div className="row">
                <div className="muted">平均缺失率</div>
                <div className="mono">{fmt(avgMissing * 100, 1)}%</div>
              </div>
              <div className="row">
                <div className="muted">平均不确定性</div>
                <div className="mono">{fmt(avgUncertainty, 3)}</div>
              </div>
                <div className="chipRow">
                  <span className="chip chipHigh">High {counts.High ?? 0}</span>
                  <span className="chip chipMid">Medium {counts.Medium ?? 0}</span>
                  <span className="chip chipLow">Low {counts.Low ?? 0}</span>
                </div>
              </div>
              <div style={{ marginTop: 10 }} className="ticker">
                <div className="tickerInner">{tickerText}</div>
              </div>
            </div>
          </div>

          <div className="wallCard" style={{ gridColumn: "1", gridRow: "2" }}>
            <div className="panelTitle">风险分布（等级/概率）</div>
            <div className="wallSplit wallCardBody">
              <div className="wallSplitCol">
                <ReactECharts option={donutOpt} style={{ height: "100%" }} notMerge={true} lazyUpdate={true} />
              </div>
              <div className="wallSplitCol">
                <ReactECharts option={histOpt} style={{ height: "100%" }} notMerge={true} lazyUpdate={true} />
              </div>
            </div>
          </div>

          <div className="wallCard" style={{ gridColumn: "1", gridRow: "3" }}>
            <div className="panelTitle">数据质量（缺失/覆盖）</div>
            <div className="wallSplit wallCardBody">
              <div className="wallSplitCol">
                <ReactECharts option={missingOpt} style={{ height: "100%" }} notMerge={true} lazyUpdate={true} />
              </div>
              <div className="wallSplitCol">
                <ReactECharts option={coverageOpt} style={{ height: "100%" }} notMerge={true} lazyUpdate={true} />
              </div>
            </div>
          </div>

          <div className="wallCard" style={{ gridColumn: "2", gridRow: "1" }}>
            <div className="panelTitle">态势摘要</div>
            <div className="wallKpis" style={{ marginTop: 6 }}>
              <div className="wallKpi">
                <div className="wallKpiLabel">统计月份</div>
                <div className="wallKpiValue" style={{ fontFamily: "var(--mono)", fontSize: 20 }}>
                  {bundle?.as_of_month ?? "—"}
                </div>
              </div>
              <div className="wallKpi">
                <div className="wallKpiLabel">高风险</div>
                <div className="wallKpiValue" style={{ color: "var(--bad)" }}>
                  {counts.High ?? 0}
                </div>
              </div>
              <div className="wallKpi">
                <div className="wallKpiLabel">中风险</div>
                <div className="wallKpiValue" style={{ color: "var(--warn)" }}>
                  {counts.Medium ?? 0}
                </div>
              </div>
              <div className="wallKpi">
                <div className="wallKpiLabel">低风险</div>
                <div className="wallKpiValue" style={{ color: "var(--good)" }}>
                  {counts.Low ?? 0}
                </div>
              </div>
              <div className="wallKpi">
                <div className="wallKpiLabel">需复核</div>
                <div className="wallKpiValue">{items.filter((i) => needsReview(i)).length}</div>
              </div>
              <div className="wallKpi">
                <div className="wallKpiLabel">异常起点 (t0)</div>
                <div className="wallKpiValue" style={{ fontFamily: "var(--mono)", fontSize: 20 }}>
                  {t0[t0.length - 1]?.name ?? "—"}
                </div>
              </div>
              <div className="wallKpi">
                <div className="wallKpiLabel">高频信号</div>
                <div className="wallKpiValue wallKpiSmall" style={{ fontFamily: "var(--mono)" }}>
                  {topSig[0]?.name ?? "—"}
                </div>
              </div>
              <div className="wallKpi">
                <div className="wallKpiLabel">高频维度</div>
                <div className="wallKpiValue wallKpiSmall" style={{ fontFamily: "var(--mono)" }}>
                  {topDim[0]?.name ?? "—"}
                </div>
              </div>
            </div>
          </div>

          <div className="wallCard" style={{ gridColumn: "2", gridRow: "2" }}>
            <div className="panelTitle">全仓库趋势</div>
            <div className="wallCardBody">
              <div className="row" style={{ marginBottom: 8 }}>
                <div className="muted mono" style={{ fontSize: 11 }}>
                  视图与筛选（{levelFilter === "All" ? "全部" : levelFilter} · {filtered.length} 项）
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <select
                    className="select"
                    value={chartMode}
                    onChange={(e) => setChartMode(e.target.value as "risk_curve" | "coverage_hist" | "missing_hist")}
                  >
                    <option value="risk_curve">风险排序曲线</option>
                    <option value="coverage_hist">覆盖率分布</option>
                    <option value="missing_hist">缺失率分布</option>
                  </select>
                  <select
                    className="select"
                    value={levelFilter}
                    onChange={(e) => setLevelFilter(e.target.value as "All" | "High" | "Medium" | "Low")}
                  >
                    <option value="All">全部等级</option>
                    <option value="High">高风险</option>
                    <option value="Medium">中风险</option>
                    <option value="Low">低风险</option>
                  </select>
                </div>
              </div>
              <ReactECharts option={trendOpt} style={{ height: "100%" }} notMerge={true} lazyUpdate={true} />
            </div>
          </div>

          <div className="wallCard" style={{ gridColumn: "2", gridRow: "3" }}>
            <div className="panelTitle">异常起点分布 · 覆盖率-风险</div>
            <div className="wallSplit wallCardBody">
              <div className="wallSplitCol">
                <ReactECharts option={t0Opt} style={{ height: "100%" }} notMerge={true} lazyUpdate={true} />
              </div>
              <div className="wallSplitCol">
                <ReactECharts option={covScatterOpt} style={{ height: "100%" }} notMerge={true} lazyUpdate={true} />
              </div>
            </div>
          </div>

          <div className="wallCard" style={{ gridColumn: "3", gridRow: "1" }}>
            <div className="panelTitle">重点项目</div>
            {spotlight ? (
              <>
                <div className="spotlightTitle">{spotlight.repo}</div>
                <div className="spotlightMeta">
                  风险={fmt(riskScore(spotlight), 3)} · 等级={String(riskLevel(spotlight))} · 复核={needsReview(spotlight) ? "是" : "否"}
                </div>
                <div className="muted" style={{ marginTop: 6, fontSize: 12 }}>
                  {repoStatusText(spotlight)}
                </div>
                <div className="chipRow">
                  <span className={levelChipClass(String(riskLevel(spotlight)))}>{String(riskLevel(spotlight))}</span>
                  <span className="chip">t0={spotlight.main_signals?.[0]?.time_window?.t0 ?? "—"}</span>
                  <span className="chip">信号={spotlight.main_signals?.length ?? 0}</span>
                  <span className="chip">缺失={spotlight.data_quality?.missing_rate === undefined ? "—" : fmt((spotlight.data_quality.missing_rate ?? 0) * 100, 1) + "%"}</span>
                </div>
                <div style={{ marginTop: 8, display: "grid", gap: 8 }}>
                  {spotlightSignals.map((s) => (
                    <div key={s.signal_id} className="card">
                      <div className="row">
                        <div style={{ fontWeight: 720, fontSize: 12 }}>{s.signal_name ?? friendlySignal(s.signal_id)}</div>
                        <div className="mono muted" style={{ fontSize: 11 }}>
                          {friendlyDimension(s.dimension ?? "unknown")}
                        </div>
                      </div>
                      <div className="row" style={{ marginTop: 6 }}>
                        <div className="muted mono">强度</div>
                        <div className="mono">{fmt(s.signal_strength ?? 0, 2)}</div>
                      </div>
                      <div style={{ height: 6, borderRadius: 999, overflow: "hidden", background: "rgba(56,76,128,.22)" }}>
                        <div
                          style={{
                            width: `${Math.round(Math.max(0, Math.min(1, Number(s.signal_strength ?? 0))) * 100)}%`,
                            height: "100%",
                            background: "linear-gradient(90deg, rgba(122,162,255,.95), rgba(97,213,255,.65))",
                          }}
                        />
                      </div>
                      <div className="row" style={{ marginTop: 6 }}>
                        <div className="muted mono">置信度</div>
                        <div className="mono">{fmt(s.signal_confidence ?? 0, 2)}</div>
                      </div>
                      <div style={{ height: 6, borderRadius: 999, overflow: "hidden", background: "rgba(56,76,128,.22)" }}>
                        <div
                          style={{
                            width: `${Math.round(Math.max(0, Math.min(1, Number(s.signal_confidence ?? 0))) * 100)}%`,
                            height: "100%",
                            background: "linear-gradient(90deg, rgba(68,209,158,.92), rgba(122,162,255,.55))",
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="muted" style={{ marginTop: 10 }}>
                no data
              </div>
            )}
          </div>

          <div className="wallCard" style={{ gridColumn: "3", gridRow: "2" }}>
            <div className="panelTitle">高频信号 · 维度</div>
            <div className="wallSplit wallCardBody">
              <div className="wallSplitCol">
                <ReactECharts option={topSignalOpt} style={{ height: "100%" }} notMerge={true} lazyUpdate={true} />
              </div>
              <div className="wallSplitCol">
                <ReactECharts option={dimOpt} style={{ height: "100%" }} notMerge={true} lazyUpdate={true} />
              </div>
            </div>
          </div>

          <div className="wallCard" style={{ gridColumn: "3", gridRow: "3" }}>
            <div className="panelTitle">高风险项目（Top 10）</div>
            <div className="wallCardBody">
              <table>
                <thead>
                  <tr>
                    <th>Repo</th>
                    <th>风险</th>
                    <th>等级</th>
                    <th>t0</th>
                    <th>状态</th>
                  </tr>
                </thead>
                <tbody>
                  {top10.map((it) => {
                    const lvl = String(riskLevel(it));
                    return (
                      <tr key={it.repo}>
                        <td className="mono">{it.repo}</td>
                        <td>{fmt(riskScore(it), 3)}</td>
                        <td className="mono">
                          <span className={levelChipClass(lvl)}>{lvl}</span>
                        </td>
                        <td className="mono">{it.main_signals?.[0]?.time_window?.t0 ?? "—"}</td>
                        <td className="mono muted">{repoStatusText(it)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <div className="muted mono" style={{ marginTop: 8, fontSize: 11 }}>
                {error ? `error=${error}` : "data: risk_report.json · evidence_chain"}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
