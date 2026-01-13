import { useMemo, useState } from "react";
import type { RiskReportBundle, RiskReportItem, SignalEvidence } from "../../core/types";
import { fmt, levelBadgeClass, needsReview, riskLevel, riskScore, sortByRiskDesc } from "../../core/utils";
import ReactECharts from "echarts-for-react";

function summarizeSignals(signals: SignalEvidence[] | undefined): string {
  if (!signals || !signals.length) return "—";
  const top = signals
    .slice(0, 3)
    .map((s) => s.signal_id)
    .join(", ");
  return top;
}

function buildForecastOption(item: RiskReportItem) {
  const forecast = (item as any).forecast ?? undefined;
  const f = forecast?.metrics;
  if (!f) return null;
  const keys = Object.keys(f);
  if (!keys.length) return null;
  const metric = keys[0];
  const series = f[metric];
  const q10: number[] = series?.q10 ?? [];
  const q50: number[] = series?.q50 ?? [];
  const q90: number[] = series?.q90 ?? [];
  const x = q50.map((_, i) => `t+${i + 1}`);
  return {
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    grid: { left: 36, right: 12, top: 16, bottom: 24 },
    xAxis: { type: "category", data: x, axisLabel: { color: "rgba(169,183,224,.62)" } },
    yAxis: {
      type: "value",
      axisLabel: { color: "rgba(169,183,224,.62)" },
      splitLine: { lineStyle: { color: "rgba(56,76,128,.18)" } },
    },
    series: [
      {
        name: "q90",
        type: "line",
        data: q90,
        lineStyle: { color: "rgba(97,213,255,.55)" },
        symbol: "none",
      },
      {
        name: "q50",
        type: "line",
        data: q50,
        lineStyle: { color: "rgba(122,162,255,.9)" },
        symbol: "none",
      },
      {
        name: "q10",
        type: "line",
        data: q10,
        lineStyle: { color: "rgba(97,213,255,.35)" },
        symbol: "none",
      },
    ],
  };
}

function SignalCard({ s }: { s: SignalEvidence }) {
  const strength = Number(s.signal_strength ?? 0);
  const conf = Number(s.signal_confidence ?? 0);
  return (
    <div className="card" style={{ marginTop: 10 }}>
      <div className="row">
        <div style={{ fontWeight: 720, fontSize: 13 }}>{s.signal_name ?? s.signal_id}</div>
        <div className="mono muted" style={{ fontSize: 11 }}>
          {s.dimension ?? "unknown"}
        </div>
      </div>
      <div className="muted" style={{ marginTop: 6, fontSize: 12, lineHeight: 1.45 }}>
        {s.governance_meaning ?? ""}
      </div>
      <div style={{ marginTop: 10, display: "grid", gap: 8 }}>
        <div className="row">
          <div className="muted mono">t0</div>
          <div className="mono">{s.time_window?.t0 ?? s.when?.start_month ?? "—"}</div>
        </div>
        <div className="row">
          <div className="muted mono">strength</div>
          <div className="mono">{fmt(strength, 2)}</div>
        </div>
        <div style={{ height: 6, borderRadius: 999, overflow: "hidden", background: "rgba(56,76,128,.22)" }}>
          <div
            style={{
              width: `${Math.round(Math.max(0, Math.min(1, strength)) * 100)}%`,
              height: "100%",
              background: "linear-gradient(90deg, rgba(122,162,255,.95), rgba(97,213,255,.65))",
            }}
          />
        </div>
        <div className="row">
          <div className="muted mono">confidence</div>
          <div className="mono">{fmt(conf, 2)}</div>
        </div>
        <div style={{ height: 6, borderRadius: 999, overflow: "hidden", background: "rgba(56,76,128,.22)" }}>
          <div
            style={{
              width: `${Math.round(Math.max(0, Math.min(1, conf)) * 100)}%`,
              height: "100%",
              background: "linear-gradient(90deg, rgba(68,209,158,.95), rgba(122,162,255,.55))",
            }}
          />
        </div>
        <div className="row">
          <div className="muted mono">abnormal</div>
          <div className="mono">
            z12={s.is_abnormal?.zscore_12_last === null || s.is_abnormal?.zscore_12_last === undefined ? "—" : fmt(s.is_abnormal.zscore_12_last, 2)}
            {" · "}
            p24={s.is_abnormal?.percentile_rank_24m_last === null || s.is_abnormal?.percentile_rank_24m_last === undefined ? "—" : fmt(s.is_abnormal.percentile_rank_24m_last, 2)}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ReposPage({ bundle }: { bundle: RiskReportBundle | null }) {
  const [query, setQuery] = useState("");
  const [level, setLevel] = useState<string>("all");
  const [reviewOnly, setReviewOnly] = useState(false);
  const [selected, setSelected] = useState<RiskReportItem | null>(null);

  const items = useMemo(() => sortByRiskDesc(bundle?.items ?? []), [bundle]);
	  const filtered = useMemo(() => {
	    const q = query.trim().toLowerCase();
	    return items.filter((it) => {
	      if (q && !it.repo.toLowerCase().includes(q)) return false;
	      if (reviewOnly && !needsReview(it)) return false;
	      const lvl = String(riskLevel(it));
	      if (level !== "all" && lvl !== level) return false;
	      return true;
	    });
	  }, [items, query, reviewOnly, level]);

  const drawerOpen = Boolean(selected);
  const opt = selected ? buildForecastOption(selected) : null;

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div className="panel">
        <div className="panelHead">
          <div>
            <div className="panelTitle">项目库</div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
              基于 risk_report.json 的预测结果与证据链检索页。
            </div>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <input className="input" placeholder="搜索 org/repo…" value={query} onChange={(e) => setQuery(e.target.value)} />
            <select className="select" value={level} onChange={(e) => setLevel(e.target.value)}>
              <option value="all">全部等级</option>
              <option value="High">高风险</option>
              <option value="Medium">中风险</option>
              <option value="Low">低风险</option>
            </select>
            <label className="badge" style={{ cursor: "pointer" }}>
              <input type="checkbox" checked={reviewOnly} onChange={(e) => setReviewOnly(e.target.checked)} />
              仅需复核
            </label>
            <div className="muted mono" style={{ fontSize: 12 }}>
              {filtered.length} / {items.length}
            </div>
          </div>
        </div>
        <div className="tableWrap" style={{ maxHeight: "62vh" }}>
          <table>
            <thead>
              <tr>
                <th>Repo</th>
                <th>Risk</th>
                <th>Level</th>
                <th>Review</th>
                <th>t0</th>
                <th>Signals</th>
              </tr>
            </thead>
            <tbody>
              {filtered.slice(0, 300).map((it) => (
                <tr key={it.repo} onClick={() => setSelected(it)}>
                  <td className="mono">{it.repo}</td>
                  <td>{fmt(riskScore(it), 3)}</td>
                  <td>
                    <span className={levelBadgeClass(riskLevel(it))}>{String(riskLevel(it))}</span>
                  </td>
                  <td>{needsReview(it) ? "Yes" : "No"}</td>
                  <td className="mono">{it.main_signals?.[0]?.time_window?.t0 ?? "—"}</td>
                  <td className="mono muted">{summarizeSignals(it.main_signals)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className={drawerOpen ? "drawer drawerOpen" : "drawer"}>
        {selected ? (
          <>
            <div className="drawerHead">
              <div>
                <div className="drawerTitle">{selected.repo}</div>
                <div className="drawerSub">
                  risk={fmt(riskScore(selected), 3)} · level={String(riskLevel(selected))} · as_of={selected.as_of_month}
                </div>
              </div>
              <button className="btn btnGhost" onClick={() => setSelected(null)}>
                关闭
              </button>
            </div>
            <div className="drawerBody">
              <div className="grid3">
                <div className="card">
                  <div className="muted">缺失率</div>
                  <div style={{ marginTop: 8, fontWeight: 780, fontSize: 22 }}>
                    {selected.data_quality?.missing_rate === undefined ? "—" : fmt((selected.data_quality.missing_rate ?? 0) * 100, 1) + "%"}
                  </div>
                </div>
                <div className="card">
                  <div className="muted">interp_ratio</div>
                  <div style={{ marginTop: 8, fontWeight: 780, fontSize: 22 }}>
                    {selected.data_quality?.avg_raw_ratio_win3 === undefined
                      ? "—"
                      : fmt(1 - (selected.data_quality.avg_raw_ratio_win3 ?? 0), 3)}
                  </div>
                </div>
                <div className="card">
                  <div className="muted">uncertainty</div>
                  <div style={{ marginTop: 8, fontWeight: 780, fontSize: 22 }}>
                    {(selected as any).forecast?.metrics
                      ? fmt(selected.model_uncertainty?.forecast_uncertainty_ratio ?? 0, 3)
                      : "—"}
                  </div>
                </div>
              </div>

              <div className="card" style={{ marginTop: 12 }}>
                <div className="row">
                  <div className="muted">预测区间（示例）</div>
                  <div className="mono muted" style={{ fontSize: 11 }}>
                    q10/q50/q90
                  </div>
                </div>
                <div style={{ marginTop: 10 }}>
                  {opt ? (
                    <ReactECharts option={opt} style={{ height: 220 }} notMerge={true} lazyUpdate={true} />
                  ) : (
                    <div className="muted" style={{ padding: 8 }}>
                      无 forecast_json（baseline 或未生成）。
                    </div>
                  )}
                </div>
              </div>

              <div style={{ marginTop: 12 }}>
                <div className="muted">主导信号（证据链）</div>
                {(selected.main_signals ?? []).slice(0, 5).map((s) => (
                  <SignalCard key={s.signal_id} s={s} />
                ))}
              </div>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
