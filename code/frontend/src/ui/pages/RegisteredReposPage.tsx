import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { RiskReportBundle } from "../../core/types";
import { fmt } from "../../core/utils";

type SourcesRepo = {
  org: string;
  repo: string;
  platform?: string;
  enabled?: boolean;
  registered_at?: string;
};

type StatusTone = "ok" | "warn" | "mid" | "empty";

export default function RegisteredReposPage({ bundle: _bundle }: { bundle: RiskReportBundle | null }) {
  const [sources, setSources] = useState<SourcesRepo[]>([]);
  const [sourcesError, setSourcesError] = useState<string | null>(null);
  const [actionStatus, setActionStatus] = useState<Record<string, { ingest?: string }>>({});
  const [query, setQuery] = useState("");
  const [bulkRunning, setBulkRunning] = useState(false);
  const [consoleLines, setConsoleLines] = useState<string[]>([]);
  const [qualityMap, setQualityMap] = useState<Record<string, { ok_rate: number; missing_rate: number; last_fetched_at?: string }>>({});
  const nav = useNavigate();
  const registeredAtMap = useMemo(() => {
    const map: Record<string, string> = {};
    for (const r of sources) {
      if (!r.org || !r.repo || !r.registered_at) continue;
      map[`${r.org}/${r.repo}`] = r.registered_at;
    }
    return map;
  }, [sources]);

  useEffect(() => {
    let alive = true;
    fetch("/api/sources/repos", { cache: "no-cache" })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<{ repos: SourcesRepo[] }>;
      })
      .then((data) => {
        if (!alive) return;
        setSources(Array.isArray(data.repos) ? data.repos.filter((r) => r.enabled !== false) : []);
      })
      .catch((err) => {
        if (!alive) return;
        setSourcesError(String(err?.message ?? err));
      });
    return () => {
      alive = false;
    };
  }, []);

  const loadQuality = useCallback(() => {
    let alive = true;
    const applyRows = (rows: Array<{ repo: string; ok_rate: number; not_found_rate: number; network_fail_rate: number; last_fetched_at?: string }>) => {
      const map: Record<string, { ok_rate: number; missing_rate: number; last_fetched_at?: string }> = {};
      for (const row of rows || []) {
        const missing = (row.not_found_rate ?? 0) + (row.network_fail_rate ?? 0);
        map[row.repo] = { ok_rate: row.ok_rate ?? 0, missing_rate: missing, last_fetched_at: row.last_fetched_at };
      }
      setQualityMap(map);
    };

    const parseMarkdown = (text: string) => {
      const lines = text.split(/\r?\n/);
      const startIdx = lines.findIndex((line) => line.trim() === "## 每个仓库抓取健康度");
      if (startIdx < 0) return [];
      const tableLines: string[] = [];
      for (let i = startIdx + 1; i < lines.length; i += 1) {
        const line = lines[i];
        if (line.startsWith("## ")) break;
        if (line.trim().startsWith("|")) tableLines.push(line);
      }
      if (tableLines.length < 3) return [];
      const dataLines = tableLines.slice(2);
      return dataLines
        .map((line) => line.split("|").map((cell) => cell.trim()).filter(Boolean))
        .filter((cells) => cells.length >= 7)
        .map((cells) => {
          const okRate = parseFloat(cells[4].replace("%", "")) / 100;
          const notFoundRate = parseFloat(cells[5].replace("%", "")) / 100;
          const netRate = parseFloat(cells[6].replace("%", "")) / 100;
          return {
            repo: cells[0],
            ok_rate: Number.isFinite(okRate) ? okRate : 0,
            not_found_rate: Number.isFinite(notFoundRate) ? notFoundRate : 0,
            network_fail_rate: Number.isFinite(netRate) ? netRate : 0,
            last_fetched_at: "1970-01-01T00:00:00Z",
          };
        });
    };

    fetch("/docs/data_quality_report.json", { cache: "no-cache" })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<{ fetch_health?: Array<{ repo: string; ok_rate: number; not_found_rate: number; network_fail_rate: number; last_fetched_at?: string }> }>;
      })
      .then((data) => {
        if (!alive) return;
        if (Array.isArray(data.fetch_health) && data.fetch_health.length) {
          applyRows(data.fetch_health);
        } else {
          setQualityMap({});
        }
      })
      .catch(() => {
        fetch("/docs/data_quality_report.md", { cache: "no-cache" })
          .then((res) => {
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return res.text();
          })
          .then((text) => {
            if (!alive) return;
            const rows = parseMarkdown(text);
            applyRows(rows);
          })
          .catch(() => {
            if (!alive) return;
            setQualityMap({});
          });
      });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => loadQuality(), [loadQuality]);


  const registeredRepos = useMemo(() => {
    return sources
      .map((r) => ({
        repo: `${r.org}/${r.repo}`,
        platform: r.platform ?? "github",
      }))
      .filter((r) => (query ? r.repo.toLowerCase().includes(query.trim().toLowerCase()) : true));
  }, [sources, query]);

  function getRepoStatus(repoName: string): { status: string; tone: StatusTone } {
    const action = actionStatus[repoName];
    if (action?.ingest === "拉取完成") return { status: "已拉取", tone: "ok" };
    const quality = qualityMap[repoName];
    if (quality?.last_fetched_at) {
      const registeredAt = registeredAtMap[repoName];
      if (!registeredAt || quality.last_fetched_at >= registeredAt) {
        if ((quality.ok_rate ?? 0) > 0) return { status: "已拉取", tone: "ok" };
        return { status: "上游缺失数据", tone: "warn" };
      }
    }
    return { status: "仅已登记", tone: "mid" };
  }

  async function handleIngest(repoName: string) {
    try {
      const res = await fetch("/api/ingest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_name: repoName }),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok || !data?.ok) {
        const msg = data?.steps?.map((s: any) => s.output).filter(Boolean).join("\n") || `HTTP ${res.status}`;
        throw new Error(msg);
      }
      setActionStatus((prev) => ({ ...prev, [repoName]: { ingest: "拉取完成" } }));
      setConsoleLines((prev) => [...prev, `✅ ${repoName} 拉取完成`]);
      if (Array.isArray(data.steps)) {
        const lines = data.steps.map((s: any) => `${s.ok ? "✅" : "⚠️"} ${s.label}`);
        setConsoleLines((prev) => [...prev, ...lines]);
      }
      loadQuality();
    } catch (err: any) {
      const msg = String(err?.message ?? err);
      const lines = msg.split(/\r?\n/).filter(Boolean);
      setActionStatus((prev) => ({ ...prev, [repoName]: { ingest: "失败（见输出台）" } }));
      setConsoleLines((prev) => [
        ...prev,
        `❌ ${repoName} 失败：`,
        ...lines.slice(0, 200),
        ...(lines.length > 200 ? [`…（已省略 ${lines.length - 200} 行）`] : []),
      ]);
    }
  }

  async function handleBulkIngest() {
    if (bulkRunning) return;
    const targets = registeredRepos.filter((row) => getRepoStatus(row.repo).status === "仅已登记");
    if (!targets.length) {
      setConsoleLines((prev) => [...prev, "ℹ️ 没有可拉取的仓库"]);
      return;
    }
    setBulkRunning(true);
    setConsoleLines((prev) => [...prev, `▶️ 开始批量拉取：${targets.length} 个仓库`]);
    for (const row of targets) {
      // eslint-disable-next-line no-await-in-loop
      await handleIngest(row.repo);
    }
    setConsoleLines((prev) => [...prev, "✅ 批量拉取完成"]);
    setBulkRunning(false);
    loadQuality();
  }

  function clearConsole() {
    setConsoleLines([]);
  }

  const stats = useMemo(() => {
    let ingested = 0;
    let missing = 0;
    let registeredOnly = 0;
    for (const row of registeredRepos) {
      const status = getRepoStatus(row.repo).status;
      if (status === "已拉取") ingested += 1;
      else if (status === "上游缺失数据") missing += 1;
      else registeredOnly += 1;
    }
    return { ingested, missing, registeredOnly, total: registeredRepos.length };
  }, [registeredRepos, actionStatus, qualityMap, registeredAtMap]);

  return (
    <div className="registeredPage">
      <div className="panel registeredPanel">
        <div className="panelHead">
          <div>
            <div className="panelTitle">已登记仓库</div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
              仅展示已登记仓库的抓取健康度与拉取操作。
            </div>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <input className="input" placeholder="搜索 org/repo…" value={query} onChange={(e) => setQuery(e.target.value)} />
            <button className="btn" disabled={bulkRunning} onClick={handleBulkIngest}>
              {bulkRunning ? "批量拉取中…" : "一键拉取未拉取仓库"}
            </button>
            <button className="btn btnGhost" onClick={clearConsole}>
              清空输出
            </button>
            <div className="badge">
              <span className="mono" style={{ fontSize: 11 }}>
                已拉取 {stats.ingested} · 缺失 {stats.missing} · 仅登记 {stats.registeredOnly} · 总数 {stats.total}
              </span>
            </div>
            {sourcesError ? (
              <div className="muted" style={{ fontSize: 12, color: "#ff5a7a" }}>
                读取 sources.yaml 失败：{sourcesError}
              </div>
            ) : null}
          </div>
        </div>
        <div className="tableWrap registeredTable">
          <table>
            <thead>
              <tr>
                <th>Repo</th>
                <th>状态</th>
                <th>成功率</th>
                <th>缺失率</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {registeredRepos.map((row) => {
                const statusInfo = getRepoStatus(row.repo);
                const quality = qualityMap[row.repo];
                const registeredAt = registeredAtMap[row.repo];
                const fetchedAt = quality?.last_fetched_at;
                const hasQuality =
                  statusInfo.status === "已拉取" ||
                  (statusInfo.status === "上游缺失数据" && fetchedAt && (!registeredAt || fetchedAt >= registeredAt));
                const coverage = hasQuality ? quality?.ok_rate : undefined;
                const missing = hasQuality ? quality?.missing_rate : undefined;
                const action = actionStatus[row.repo];
                const canIngest = statusInfo.status === "仅已登记";
                const cls =
                  statusInfo.tone === "ok"
                    ? "repoTag repoTagOk"
                    : statusInfo.tone === "warn"
                      ? "repoTag repoTagWarn"
                      : statusInfo.tone === "mid"
                        ? "repoTag repoTagMid"
                        : "repoTag repoTagEmpty";
                return (
                  <tr
                    key={row.repo}
                    onClick={() => {
                      const [org, repo] = row.repo.split("/", 2);
                      if (!org || !repo) return;
                      nav(`/registered/${org}/${repo}`);
                    }}
                  >
                    <td className="mono">{row.repo}</td>
                    <td>
                      <span className={cls}>{statusInfo.status}</span>
                    </td>
                    <td className="mono">{coverage === undefined ? "—" : fmt(coverage * 100, 1) + "%"}</td>
                    <td className="mono">{missing === undefined ? "—" : fmt(missing * 100, 1) + "%"}</td>
                    <td>
                      <button
                        className="btn"
                        disabled={!canIngest}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleIngest(row.repo);
                        }}
                      >
                        {canIngest ? "拉取解析" : "已拉取"}
                      </button>
                      {action?.ingest ? (
                        <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>
                          {action.ingest}
                        </div>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
              {registeredRepos.length === 0 ? (
                <tr>
                  <td colSpan={5} className="muted">
                    暂无登记仓库
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
