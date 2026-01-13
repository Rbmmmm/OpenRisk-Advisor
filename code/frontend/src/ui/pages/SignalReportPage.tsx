import { useEffect, useMemo, useState } from "react";
import { fmt } from "../../core/utils";

type SignalRow = {
  repo: string;
  signal_id: string;
  signal_name: string;
  dimension: string;
  signal_strength?: number;
  signal_confidence?: number;
  when?: { start_month?: string; end_month?: string };
  time_window?: { t0?: string; t_end?: string };
  metric?: string;
};

type RepoSignals = {
  repo: string;
  signals: SignalRow[];
  count: number;
  avg_strength: number;
  avg_confidence: number;
};

export default function SignalReportPage() {
  const [rows, setRows] = useState<SignalRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [consoleLines, setConsoleLines] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  const [registeredOnly, setRegisteredOnly] = useState(true);
  const [registeredRepos, setRegisteredRepos] = useState<Set<string>>(new Set());

  function loadSignals() {
    fetch("/docs/signal_report.json", { cache: "no-cache" })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<SignalRow[]>;
      })
      .then((data) => {
        setRows(Array.isArray(data) ? data : []);
        setError(null);
      })
      .catch((err) => {
        setRows([]);
        setError(String(err?.message ?? err));
      });
  }

  useEffect(() => {
    loadSignals();
  }, []);

  useEffect(() => {
    let alive = true;
    fetch("/api/sources/repos", { cache: "no-cache" })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<{ repos?: Array<{ org: string; repo: string; enabled?: boolean }> }>;
      })
      .then((data) => {
        if (!alive) return;
        const set = new Set<string>();
        for (const r of data.repos || []) {
          if (r.enabled === false) continue;
          if (r.org && r.repo) set.add(`${r.org}/${r.repo}`);
        }
        setRegisteredRepos(set);
      })
      .catch(() => {
        if (!alive) return;
        setRegisteredRepos(new Set());
      });
    return () => {
      alive = false;
    };
  }, []);

  const grouped = useMemo(() => {
    const map = new Map<string, RepoSignals>();
    let filteredSignals = 0;
    for (const row of rows) {
      if (registeredOnly && !registeredRepos.has(row.repo)) continue;
      if (query && !row.repo.toLowerCase().includes(query.trim().toLowerCase())) continue;
      const entry = map.get(row.repo) || {
        repo: row.repo,
        signals: [],
        count: 0,
        avg_strength: 0,
        avg_confidence: 0,
      };
      entry.signals.push(row);
      entry.count += 1;
      entry.avg_strength += Number(row.signal_strength ?? 0);
      entry.avg_confidence += Number(row.signal_confidence ?? 0);
      map.set(row.repo, entry);
      filteredSignals += 1;
    }
    const repos = Array.from(map.values())
      .map((entry) => ({
        ...entry,
        avg_strength: entry.count ? entry.avg_strength / entry.count : 0,
        avg_confidence: entry.count ? entry.avg_confidence / entry.count : 0,
      }))
      .sort((a, b) => b.count - a.count);
    return { repos, filteredSignals };
  }, [rows, query, registeredOnly, registeredRepos]);

  async function handleRun() {
    if (running) return;
    setRunning(true);
    setConsoleLines((prev) => [...prev, "▶️ 开始生成信号报告…"]);
    try {
      const res = await fetch("/api/signals/run", { method: "POST" });
      const data = await res.json().catch(() => null);
      if (!res.ok || !data?.ok) {
        const msg = data?.output || `HTTP ${res.status}`;
        throw new Error(msg);
      }
      const lines = String(data.output || "").split(/\r?\n/).filter(Boolean);
      setConsoleLines((prev) => [...prev, "✅ 信号报告已生成", ...lines.slice(-120)]);
      loadSignals();
    } catch (err: any) {
      setConsoleLines((prev) => [...prev, `❌ 失败：${String(err?.message ?? err)}`]);
    } finally {
      setRunning(false);
    }
  }

  function clearConsole() {
    setConsoleLines([]);
  }

  return (
    <div className="registeredPage">
      <div className="panel registeredPanel">
        <div className="panelHead">
          <div>
            <div className="panelTitle">信号报告</div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
              生成并汇总 signal_report.json，查看各仓库信号统计。
            </div>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <input className="input" placeholder="搜索 org/repo…" value={query} onChange={(e) => setQuery(e.target.value)} />
            <button className="btn" disabled={running} onClick={handleRun}>
              {running ? "生成中…" : "生成信号报告"}
            </button>
            <button className="btn btnGhost" onClick={clearConsole}>
              清空输出
            </button>
            <label className="badge" style={{ cursor: "pointer" }}>
              <input type="checkbox" checked={registeredOnly} onChange={(e) => setRegisteredOnly(e.target.checked)} />
              仅已登记
            </label>
            <div className="badge">
              <span className="mono" style={{ fontSize: 11 }}>
                repos {grouped.repos.length} · signals {grouped.filteredSignals}
              </span>
            </div>
            {error ? (
              <div className="muted" style={{ fontSize: 12, color: "#ff5a7a" }}>
                读取 signal_report.json 失败：{error}
              </div>
            ) : null}
          </div>
        </div>
        <div className="tableWrap registeredTable">
          <table>
            <thead>
              <tr>
                <th>Repo</th>
                <th>信号数</th>
                <th>强度均值</th>
                <th>置信度均值</th>
                <th>最新信号</th>
              </tr>
            </thead>
            <tbody>
              {grouped.repos.map((entry) => {
                const latest = entry.signals[0];
                return (
                  <tr key={entry.repo}>
                    <td className="mono">{entry.repo}</td>
                    <td className="mono">{entry.count}</td>
                    <td className="mono">{fmt(entry.avg_strength, 2)}</td>
                    <td className="mono">{fmt(entry.avg_confidence, 2)}</td>
                    <td className="mono muted">{latest?.signal_name ?? latest?.signal_id ?? "—"}</td>
                  </tr>
                );
              })}
              {grouped.repos.length === 0 ? (
                <tr>
                  <td colSpan={5} className="muted">
                    暂无信号数据
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
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
