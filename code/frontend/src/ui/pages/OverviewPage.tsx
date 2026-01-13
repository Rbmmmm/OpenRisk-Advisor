import type { RiskReportBundle, RiskReportItem } from "../../core/types";
import { countByLevel, fmt, riskLevel, riskScore, sortByRiskDesc } from "../../core/utils";
import ReactECharts from "echarts-for-react";
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";

function toHistogram(values: number[], bins: number): { x: string[]; y: number[] } {
  const clamped = values.map((v) => Math.max(0, Math.min(1, v)));
  const counts = new Array(bins).fill(0);
  for (const v of clamped) {
    const idx = Math.min(bins - 1, Math.floor(v * bins));
    counts[idx] += 1;
  }
  const x = counts.map((_, i) => {
    const a = i / bins;
    const b = (i + 1) / bins;
    return `${a.toFixed(2)}-${b.toFixed(2)}`;
  });
  return { x, y: counts };
}

function topDimensions(items: RiskReportItem[]): Array<{ name: string; value: number }> {
  const m = new Map<string, number>();
  for (const it of items) {
    const sigs = it.main_signals ?? [];
    for (const s of sigs.slice(0, 5)) {
      const d = s.dimension ?? "unknown";
      m.set(d, (m.get(d) ?? 0) + 1);
    }
  }
  return Array.from(m.entries())
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);
}

export default function OverviewPage({
  bundle,
  loading,
  error,
}: {
  bundle: RiskReportBundle | null;
  loading: boolean;
  error: string | null;
}) {
  const items = bundle?.items ?? [];
  const nav = useNavigate();
  const counts = countByLevel(items);
  const avg = items.reduce((a, it) => a + riskScore(it), 0) / Math.max(1, items.length);
  const missingAvg =
    items.reduce((a, it) => a + (it.data_quality?.missing_rate ?? 0), 0) / Math.max(1, items.length);

  const sorted = sortByRiskDesc(items);
  const top10 = sorted.slice(0, 10);
  const hist = toHistogram(items.map(riskScore), 12);
  const dims = topDimensions(items);

  const donutOpt = {
    backgroundColor: "transparent",
    tooltip: { trigger: "item" },
    legend: {
      orient: "vertical",
      right: 8,
      top: "center",
      textStyle: { color: "rgba(169,183,224,.82)", fontFamily: "ui-monospace" },
    },
    series: [
      {
        name: "Risk Level",
        type: "pie",
        radius: ["55%", "78%"],
        center: ["38%", "52%"],
        label: { show: false },
        data: [
          { value: counts.High ?? 0, name: "High", itemStyle: { color: "rgba(255,90,122,.92)" } },
          { value: counts.Medium ?? 0, name: "Medium", itemStyle: { color: "rgba(255,180,84,.92)" } },
          { value: counts.Low ?? 0, name: "Low", itemStyle: { color: "rgba(68,209,158,.92)" } },
        ],
      },
    ],
  };

  const histOpt = {
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    grid: { left: 42, right: 14, top: 18, bottom: 28 },
    xAxis: {
      type: "category",
      data: hist.x,
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
        data: hist.y,
        itemStyle: {
          color: "rgba(122,162,255,.75)",
          borderColor: "rgba(97,213,255,.35)",
          borderWidth: 1,
        },
      },
    ],
  };

  const dimsOpt = {
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    grid: { left: 140, right: 16, top: 18, bottom: 24 },
    xAxis: {
      type: "value",
      axisLabel: { color: "rgba(169,183,224,.62)", fontFamily: "ui-monospace" },
      splitLine: { lineStyle: { color: "rgba(56,76,128,.18)" } },
    },
    yAxis: {
      type: "category",
      data: dims.map((d) => d.name),
      axisLabel: { color: "rgba(169,183,224,.82)", fontFamily: "ui-monospace" },
      axisLine: { lineStyle: { color: "rgba(56,76,128,.25)" } },
    },
    series: [
      {
        type: "bar",
        data: dims.map((d) => d.value),
        itemStyle: {
          color: "rgba(97,213,255,.65)",
          borderColor: "rgba(122,162,255,.35)",
          borderWidth: 1,
        },
      },
    ],
  };

  if (loading) {
    return (
      <div className="panel repoListCard">
        <div className="panelHead">
          <div className="panelTitle">概览</div>
        </div>
        <div style={{ padding: 14, color: "rgba(169,183,224,.82)" }}>加载中…</div>
      </div>
    );
  }
  if (error) {
    return (
      <div className="panel">
        <div className="panelHead">
          <div className="panelTitle">概览</div>
        </div>
        <div style={{ padding: 14, color: "#ff5a7a" }}>加载失败：{error}</div>
      </div>
    );
  }
  if (!bundle) {
    return (
      <div className="panel">
        <div className="panelHead">
          <div className="panelTitle">概览</div>
        </div>
        <div style={{ padding: 14, color: "rgba(169,183,224,.82)" }}>暂无数据</div>
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div className="panel">
        <div className="panelHead">
          <div>
            <div className="panelTitle">工作流导航</div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
              按“登记→抓取→信号→模型→项目库→治理建议”的顺序执行。
            </div>
          </div>
        </div>
        <div className="workflowGrid">
          {[
            { label: "已登记仓库", desc: "登记 + 拉取健康度", path: "/registered" },
            { label: "仓库清单", desc: "从清单选择并登记", path: "/repo-list" },
            { label: "信号报告", desc: "生成并汇总信号", path: "/signals-report" },
            { label: "模型", desc: "训练与预测", path: "/models" },
            { label: "项目库", desc: "预测结果与证据", path: "/repos" },
            { label: "治理建议", desc: "LLM 行动计划", path: "/governance" },
          ].map((card) => (
            <button key={card.path} className="workflowCard" onClick={() => nav(card.path)}>
              <div className="workflowTitle">{card.label}</div>
              <div className="workflowDesc">{card.desc}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="panel">
        <div className="panelHead">
          <div>
            <div className="panelTitle">全局概览</div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
              汇总 risk_report 的关键指标与分布。
            </div>
          </div>
          <div className="badge">
            <span style={{ color: "rgba(169,183,224,.62)", fontFamily: "ui-monospace" }}>
              as_of {bundle.as_of_month ?? "—"}
            </span>
          </div>
        </div>
        <div className="kpiGrid">
          <div className="kpi">
            <div className="kpiLabel">仓库数</div>
            <div className="kpiValue">{items.length}</div>
            <div className="kpiHint">risk_report.items</div>
          </div>
          <div className="kpi">
            <div className="kpiLabel">高风险</div>
            <div className="kpiValue" style={{ color: "var(--bad)" }}>
              {counts.High ?? 0}
            </div>
            <div className="kpiHint">优先介入评估</div>
          </div>
          <div className="kpi">
            <div className="kpiLabel">中风险</div>
            <div className="kpiValue" style={{ color: "var(--warn)" }}>
              {counts.Medium ?? 0}
            </div>
            <div className="kpiHint">持续观察</div>
          </div>
          <div className="kpi">
            <div className="kpiLabel">低风险</div>
            <div className="kpiValue" style={{ color: "var(--good)" }}>
              {counts.Low ?? 0}
            </div>
            <div className="kpiHint">当前未见显著衰退</div>
          </div>
          <div className="kpi">
            <div className="kpiLabel">平均风险</div>
            <div className="kpiValue">{fmt(avg, 3)}</div>
            <div className="kpiHint">校准后概率均值</div>
          </div>
        </div>
      </div>

      <div className="grid3">
        <div className="panel">
          <div className="panelHead">
            <div className="panelTitle">风险等级分布</div>
          </div>
          <div style={{ padding: 8 }}>
            <ReactECharts option={donutOpt} style={{ height: 260 }} notMerge={true} lazyUpdate={true} />
          </div>
        </div>

        <div className="panel">
          <div className="panelHead">
            <div className="panelTitle">风险直方图</div>
          </div>
          <div style={{ padding: 8 }}>
            <ReactECharts option={histOpt} style={{ height: 260 }} notMerge={true} lazyUpdate={true} />
          </div>
        </div>

        <div className="panel">
          <div className="panelHead">
            <div className="panelTitle">Top 证据维度</div>
          </div>
          <div style={{ padding: 8 }}>
            <ReactECharts option={dimsOpt} style={{ height: 260 }} notMerge={true} lazyUpdate={true} />
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panelHead">
          <div className="panelTitle">Top 风险项目</div>
          <div className="muted" style={{ fontSize: 12 }}>
            平均缺失率 {fmt(missingAvg * 100, 1)}%
          </div>
        </div>
        <div className="tableWrap">
          <table>
            <thead>
              <tr>
                <th>Repo</th>
                <th>Risk</th>
                <th>Level</th>
                <th>t0</th>
                <th>Signals</th>
              </tr>
            </thead>
            <tbody>
              {top10.map((it) => (
                <tr key={it.repo}>
                  <td className="mono">{it.repo}</td>
                  <td>{fmt(riskScore(it), 3)}</td>
                  <td>{String(riskLevel(it))}</td>
                  <td className="mono">{it.main_signals?.[0]?.time_window?.t0 ?? "—"}</td>
                  <td>{it.main_signals?.length ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
