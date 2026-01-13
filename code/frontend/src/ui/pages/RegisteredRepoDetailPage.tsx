import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { fmt } from "../../core/utils";

type MetricSeriesPoint = {
  period: string;
  value: number | string | null;
};

type MetricSummary = {
  name: string;
  latest_period: string | null;
  latest_value: number | string | null;
  points: number;
  series: MetricSeriesPoint[];
};

export default function RegisteredRepoDetailPage() {
  const nav = useNavigate();
  const params = useParams();
  const org = params.org || "";
  const repo = params.repo || "";
  const repoName = org && repo ? `${org}/${repo}` : "";

  const [metrics, setMetrics] = useState<MetricSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!repoName) return;
    let alive = true;
    setLoading(true);
    setError(null);
    fetch(`/api/raw?repo=${encodeURIComponent(repoName)}`, { cache: "no-cache" })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<{ ok: boolean; metrics?: MetricSummary[]; error?: string }>;
      })
      .then((data) => {
        if (!alive) return;
        if (!data.ok) throw new Error(data.error || "加载失败");
        setMetrics(Array.isArray(data.metrics) ? data.metrics : []);
      })
      .catch((err) => {
        if (!alive) return;
        setError(String(err?.message ?? err));
      })
      .finally(() => {
        if (!alive) return;
        setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [repoName]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return metrics.filter((m) => (q ? m.name.toLowerCase().includes(q) : true));
  }, [metrics, query]);

  function formatValue(value: unknown) {
    if (typeof value === "number") return fmt(value, 2);
    if (typeof value === "string") return value;
    return "—";
  }

  return (
    <div className="panel repoDetailPanel">
      <div className="panelHead">
        <div>
          <div className="panelTitle">仓库原始数据</div>
          <div className="muted" style={{ marginTop: 4 }}>
            {repoName || "—"}
          </div>
          <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
            展示该仓库拉取的指标摘要与近 12 个周期。
          </div>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <input
            className="input"
            placeholder="搜索指标…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button className="btn btnGhost" onClick={() => nav("/registered")}>
            返回
          </button>
        </div>
      </div>
      <div className="repoDetailBody">
        {loading ? <div className="muted">加载中…</div> : null}
        {error ? <div className="muted" style={{ color: "#ff5a7a" }}>{error}</div> : null}
        {!loading && !error ? (
          <div className="metricGrid">
            {filtered.map((metric) => (
              <div className="card metricCard" key={metric.name}>
                <div className="metricHeader">
                  <div className="metricTitle">{metric.name}</div>
                  <div className="muted mono" style={{ fontSize: 11 }}>
                    {metric.points} points
                  </div>
                </div>
                <div className="metricValue">
                  <div className="metricNumber">{formatValue(metric.latest_value)}</div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    最新：{metric.latest_period || "—"}
                  </div>
                </div>
                <div className="metricSeries">
                  <table>
                    <thead>
                      <tr>
                        <th>Period</th>
                        <th>Value</th>
                      </tr>
                    </thead>
                    <tbody>
                      {metric.series.length ? (
                        metric.series.map((row) => (
                          <tr key={`${metric.name}-${row.period}`}>
                            <td className="mono">{row.period}</td>
                            <td className="mono">{formatValue(row.value)}</td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={2} className="muted">
                            暂无数据
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
            {filtered.length === 0 ? <div className="muted">无匹配指标</div> : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
