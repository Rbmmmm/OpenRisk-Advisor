import type { RiskReportBundle } from "../../core/types";
import { fmt, riskScore, sortByRiskDesc } from "../../core/utils";
import ReactECharts from "echarts-for-react";
import { useMemo, useState } from "react";

type Row = { signal_id: string; signal_name: string; dimension: string; count: number; avg_strength: number; avg_conf: number };

export default function SignalsPage({ bundle }: { bundle: RiskReportBundle | null }) {
  const [minRisk, setMinRisk] = useState(0.5);

  const rows = useMemo(() => {
    const m = new Map<string, Row>();
    const items = sortByRiskDesc(bundle?.items ?? []);
    const filtered = items.filter((it) => riskScore(it) >= minRisk);
    for (const it of filtered) {
      for (const s of it.main_signals ?? []) {
        const key = s.signal_id;
        const r = m.get(key) ?? {
          signal_id: s.signal_id,
          signal_name: s.signal_name ?? s.signal_id,
          dimension: s.dimension ?? "unknown",
          count: 0,
          avg_strength: 0,
          avg_conf: 0,
        };
        r.count += 1;
        r.avg_strength += Number(s.signal_strength ?? 0);
        r.avg_conf += Number(s.signal_confidence ?? 0);
        m.set(key, r);
      }
    }
    const out = Array.from(m.values()).map((r) => ({
      ...r,
      avg_strength: r.count ? r.avg_strength / r.count : 0,
      avg_conf: r.count ? r.avg_conf / r.count : 0,
    }));
    out.sort((a, b) => b.count - a.count);
    return out;
  }, [bundle, minRisk]);

  const dimCounts = useMemo(() => {
    const m = new Map<string, number>();
    for (const r of rows) m.set(r.dimension, (m.get(r.dimension) ?? 0) + r.count);
    const out = Array.from(m.entries()).map(([name, value]) => ({ name, value }));
    out.sort((a, b) => b.value - a.value);
    return out.slice(0, 10);
  }, [rows]);

  const opt = {
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
      data: dimCounts.map((d) => d.name),
      axisLabel: { color: "rgba(169,183,224,.82)", fontFamily: "ui-monospace" },
      axisLine: { lineStyle: { color: "rgba(56,76,128,.25)" } },
    },
    series: [
      {
        type: "bar",
        data: dimCounts.map((d) => d.value),
        itemStyle: {
          color: "rgba(97,213,255,.65)",
          borderColor: "rgba(122,162,255,.35)",
          borderWidth: 1,
        },
      },
    ],
  };

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div className="panel">
        <div className="panelHead">
          <div>
            <div className="panelTitle">信号洞察（基于 RiskReport main_signals）</div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
              汇总风险报告主信号，按风险阈值聚合。
            </div>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <div className="badge">
              <span className="muted">最小风险</span>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={minRisk}
                onChange={(e) => setMinRisk(Number(e.target.value))}
              />
              <span className="mono">{fmt(minRisk, 2)}</span>
            </div>
            <div className="muted mono" style={{ fontSize: 12 }}>
              signals={rows.length}
            </div>
          </div>
        </div>
        <div style={{ padding: 8 }}>
          <ReactECharts option={opt} style={{ height: 280 }} notMerge={true} lazyUpdate={true} />
        </div>
      </div>

      <div className="panel">
        <div className="panelHead">
          <div className="panelTitle">Top 信号（按出现次数）</div>
          <div className="muted mono" style={{ fontSize: 12 }}>
            仅统计 risk_score ≥ {fmt(minRisk, 2)} 的仓库
          </div>
        </div>
        <div className="tableWrap" style={{ maxHeight: "60vh" }}>
          <table>
            <thead>
              <tr>
                <th>signal_id</th>
                <th>dimension</th>
                <th>count</th>
                <th>avg_strength</th>
                <th>avg_conf</th>
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 200).map((r) => (
                <tr key={r.signal_id}>
                  <td className="mono">{r.signal_id}</td>
                  <td className="mono muted">{r.dimension}</td>
                  <td>{r.count}</td>
                  <td>{fmt(r.avg_strength, 2)}</td>
                  <td>{fmt(r.avg_conf, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
