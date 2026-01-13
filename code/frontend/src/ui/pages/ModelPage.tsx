import { useEffect, useMemo, useState } from "react";
import { fmt } from "../../core/utils";

type ModelStatus = {
  db: string;
  config: any;
  models: Record<
    string,
    {
      latest: null | {
        model_type: string;
        model_version: string;
        created_at: string;
        train_samples?: number;
        val_samples?: number;
        artifact_path?: string;
        extra_json?: Record<string, any>;
      };
      predictions: { count: number; latest_month: string | null };
    }
  >;
};

export default function ModelPage() {
  const [status, setStatus] = useState<ModelStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [consoleLines, setConsoleLines] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  const [modelType, setModelType] = useState("baseline");
  const [predictionsList, setPredictionsList] = useState<Array<any>>([]);
  const [predError, setPredError] = useState<string | null>(null);
  const [predQuery, setPredQuery] = useState("");

  const fetchStatus = () => {
    fetch("/api/model/status", { cache: "no-cache" })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<ModelStatus>;
      })
      .then((data) => {
        setStatus(data);
        setError(null);
      })
      .catch((err) => {
        setStatus(null);
        setError(String(err?.message ?? err));
      });
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchPredictions = () => {
    fetch(`/api/model/predictions?model_type=${encodeURIComponent(modelType)}`, { cache: "no-cache" })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<{ ok: boolean; items?: any[]; error?: string }>;
      })
      .then((data) => {
        if (!data.ok) throw new Error(data.error || "无预测数据");
        setPredictionsList(Array.isArray(data.items) ? data.items : []);
        setPredError(null);
      })
      .catch((err) => {
        setPredictionsList([]);
        setPredError(String(err?.message ?? err));
      });
  };

  useEffect(() => {
    fetchPredictions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modelType]);

  async function runTrain() {
    if (running) return;
    setRunning(true);
    setConsoleLines((prev) => [...prev, `▶️ 开始训练模型：${modelType}`]);
    try {
      const res = await fetch("/api/model/train", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_type: modelType }),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok || !data?.ok) throw new Error(data?.output || `HTTP ${res.status}`);
      const lines = String(data.output || "").split(/\r?\n/).filter(Boolean);
      setConsoleLines((prev) => [...prev, "✅ 训练完成", ...lines.slice(-120)]);
      fetchStatus();
      fetchPredictions();
    } catch (err: any) {
      setConsoleLines((prev) => [...prev, `❌ 训练失败：${String(err?.message ?? err)}`]);
    } finally {
      setRunning(false);
    }
  }

  async function runPredict() {
    if (running) return;
    setRunning(true);
    setConsoleLines((prev) => [...prev, `▶️ 开始生成预测报告：${modelType}`]);
    try {
      const res = await fetch("/api/model/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_type: modelType }),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok || !data?.ok) {
        const msg = data?.steps?.map((s: any) => s.output).filter(Boolean).join("\n") || `HTTP ${res.status}`;
        throw new Error(msg);
      }
      setConsoleLines((prev) => [...prev, "✅ 预测报告已生成", ...data.steps.map((s: any) => `${s.ok ? "✅" : "⚠️"} ${s.label}`)]);
      fetchStatus();
      fetchPredictions();
    } catch (err: any) {
      setConsoleLines((prev) => [...prev, `❌ 预测失败：${String(err?.message ?? err)}`]);
    } finally {
      setRunning(false);
    }
  }

  function clearConsole() {
    setConsoleLines([]);
  }

  const configSummary = useMemo(() => {
    const cfg = status?.config ?? {};
    return {
      version: cfg.version ?? "—",
      input_window: cfg.task?.input_window_months ?? "—",
      horizon: cfg.task?.horizon_months ?? "—",
      thresholds: cfg.thresholds ?? {},
    };
  }, [status]);

  const latestModel = status?.models?.[modelType]?.latest;
  const predStats = status?.models?.[modelType]?.predictions;

  const filteredPreds = useMemo(() => {
    const q = predQuery.trim().toLowerCase();
    return predictionsList.filter((p) => (q ? String(p.repo).toLowerCase().includes(q) : true));
  }, [predictionsList, predQuery]);

  return (
    <div className="registeredPage">
      <div className="panel registeredPanel">
        <div className="panelHead">
          <div>
            <div className="panelTitle">模型中心</div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
              训练模型并生成预测快照，查看每个仓库的预测结果。
            </div>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <select className="select" value={modelType} onChange={(e) => setModelType(e.target.value)}>
              <option value="baseline">baseline</option>
              <option value="transformer">transformer</option>
            </select>
            <button className="btn" disabled={running} onClick={runTrain}>
              {running ? "执行中…" : "新训练模型"}
            </button>
            <button className="btn btnGhost" disabled={running} onClick={runPredict}>
              预测 / 生成报告
            </button>
            <button className="btn btnGhost" onClick={clearConsole}>
              清空输出
            </button>
            {error ? (
              <div className="muted" style={{ fontSize: 12, color: "#ff5a7a" }}>
                读取模型状态失败：{error}
              </div>
            ) : null}
          </div>
        </div>

        <div className="modelBody">
          <div className="grid3">
            <div className="card">
              <div className="muted">模型版本</div>
              <div style={{ marginTop: 8, fontWeight: 780, fontSize: 22 }}>{configSummary.version}</div>
              <div className="muted" style={{ fontSize: 12 }}>
                输入窗口 {configSummary.input_window} 月 · 预测窗口 {configSummary.horizon} 月
              </div>
            </div>
            <div className="card">
              <div className="muted">最新模型</div>
              <div style={{ marginTop: 8, fontWeight: 720, fontSize: 16 }}>
                {latestModel ? `${latestModel.model_type}/${latestModel.model_version}` : "未训练"}
              </div>
              <div className="muted" style={{ fontSize: 12 }}>
                {latestModel?.created_at ?? "—"}
              </div>
            </div>
            <div className="card">
              <div className="muted">预测覆盖</div>
              <div style={{ marginTop: 8, fontWeight: 780, fontSize: 22 }}>
                {predStats?.count ?? 0}
              </div>
              <div className="muted" style={{ fontSize: 12 }}>
                最新月份 {predStats?.latest_month ?? "—"}
              </div>
            </div>
          </div>

          <div className="tableWrap registeredTable">
            <table>
              <thead>
                <tr>
                  <th>阈值</th>
                  <th>low</th>
                  <th>high</th>
                  <th>needs_review</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>risk_thresholds</td>
                  <td className="mono">{fmt(configSummary.thresholds?.low, 2)}</td>
                  <td className="mono">{fmt(configSummary.thresholds?.high, 2)}</td>
                  <td className="mono">
                    raw≥{fmt(configSummary.thresholds?.needs_review?.min_avg_raw_ratio, 2)} · uncert≤
                    {fmt(configSummary.thresholds?.needs_review?.max_forecast_uncertainty_ratio, 2)}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="panelSubhead">
            <div className="row">
              <div className="muted">模型预测（最新 as_of 月）</div>
              <input
                className="input"
                placeholder="搜索 org/repo…"
                value={predQuery}
                onChange={(e) => setPredQuery(e.target.value)}
                style={{ maxWidth: 240 }}
              />
            </div>
            {predError ? (
              <div className="muted" style={{ fontSize: 12, color: "#ff5a7a" }}>
                读取预测失败：{predError}
              </div>
            ) : null}
          </div>
          <div className="tableWrap registeredTable">
            <table>
              <thead>
                <tr>
                  <th>Repo</th>
                  <th>风险分</th>
                  <th>风险等级</th>
                  <th>需复核</th>
                  <th>as_of</th>
                </tr>
              </thead>
              <tbody>
                {filteredPreds.map((row) => (
                  <tr key={`${row.repo}-${row.as_of_month}`}>
                    <td className="mono">{row.repo}</td>
                    <td className="mono">{fmt(row.p_calibrated, 3)}</td>
                    <td>{row.risk_level ?? "—"}</td>
                    <td>{row.needs_review ? "Yes" : "No"}</td>
                    <td className="mono">{row.as_of_month ?? "—"}</td>
                  </tr>
                ))}
                {filteredPreds.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="muted">
                      暂无预测数据
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="panel consolePanel">
        <div className="panelHead">
          <div className="panelTitle">输出台</div>
          <div className="badge">
            <span className="mono" style={{ fontSize: 11 }}>
              {consoleLines.length} 条
            </span>
          </div>
        </div>
        <div className="consoleBox registeredConsoleBox">
          {consoleLines.length ? (
            consoleLines.map((line, idx) => (
              <div key={`${line}-${idx}`} className="mono">
                {line}
              </div>
            ))
          ) : (
            <div className="muted">暂无输出</div>
          )}
        </div>
      </div>
    </div>
  );
}
