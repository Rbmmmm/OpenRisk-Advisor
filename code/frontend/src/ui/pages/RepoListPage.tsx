import type { RiskReportBundle } from "../../core/types";
import { useCallback, useEffect, useMemo, useState } from "react";

type RepoListRow = {
  id: string;
  platform: string;
  repo_name: string;
};

type RepoListResponse = {
  items: RepoListRow[];
};

export default function RepoListPage({ bundle }: { bundle: RiskReportBundle | null }) {
  const [repoList, setRepoList] = useState<RepoListRow[]>([]);
  const [repoListError, setRepoListError] = useState<string | null>(null);
  const [sourcesRepos, setSourcesRepos] = useState<Set<string>>(new Set());
  const [actionStatus, setActionStatus] = useState<Record<string, { add?: string }>>({});
  const [repoListQuery, setRepoListQuery] = useState("");
  const [repoListFilter, setRepoListFilter] = useState("all");
  const [qualityMap, setQualityMap] = useState<Record<string, { ok_rate: number; missing_rate: number; last_fetched_at?: string }>>({});
  const [registeredAtMap, setRegisteredAtMap] = useState<Record<string, string>>({});

  useEffect(() => {
    let alive = true;
    fetch("/api/repo-list?limit=300", { cache: "no-cache" })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<RepoListResponse>;
      })
      .then((data) => {
        if (!alive) return;
        setRepoList(Array.isArray(data.items) ? data.items : []);
      })
      .catch((err) => {
        if (!alive) return;
        setRepoListError(String(err?.message ?? err));
      });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    let alive = true;
    fetch("/api/sources/repos", { cache: "no-cache" })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<{ repos: Array<{ org: string; repo: string; enabled?: boolean; registered_at?: string }> }>;
      })
      .then((data) => {
        if (!alive) return;
        const set = new Set<string>();
        const regMap: Record<string, string> = {};
        for (const r of data.repos || []) {
          if (r.enabled === false) continue;
          if (r.org && r.repo) {
            const name = `${r.org}/${r.repo}`;
            set.add(name);
            if (r.registered_at) regMap[name] = r.registered_at;
          }
        }
        setSourcesRepos(set);
        setRegisteredAtMap(regMap);
      })
      .catch(() => {
        if (!alive) return;
        setSourcesRepos(new Set());
        setRegisteredAtMap({});
      });
    return () => {
      alive = false;
    };
  }, []);

  const items = bundle?.items ?? [];

  const mergedRepoList = useMemo(() => {
    const map = new Map<string, RepoListRow>();
    for (const row of repoList) {
      if (row.repo_name) map.set(row.repo_name, row);
    }
    for (const it of items) {
      if (!map.has(it.repo)) {
        map.set(it.repo, { id: "", platform: "github", repo_name: it.repo });
      }
    }
    return Array.from(map.values());
  }, [repoList, items]);

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

  const repoListStats = useMemo(() => {
    let hasData = 0;
    let missing = 0;
    let registered = 0;
    let unregistered = 0;
    for (const row of mergedRepoList) {
      const status = getRepoStatus(row.repo_name).status;
      if (status === "已拉取") {
        hasData += 1;
        continue;
      }
      if (status === "上游缺失数据") {
        missing += 1;
        continue;
      }
      if (sourcesRepos.has(row.repo_name)) {
        registered += 1;
      } else {
        unregistered += 1;
      }
    }
    return { loaded: mergedRepoList.length, hasData, missing, registered, unregistered };
  }, [mergedRepoList, sourcesRepos, qualityMap, registeredAtMap]);

  const filteredRepoList = useMemo(() => {
    const q = repoListQuery.trim().toLowerCase();
    return mergedRepoList.filter((row) => {
      if (q && !row.repo_name.toLowerCase().includes(q)) return false;
      const status = getRepoStatus(row.repo_name).status;
      if (repoListFilter === "hasData") return status === "已拉取";
      if (repoListFilter === "missing") return status === "上游缺失数据";
      if (repoListFilter === "registered") return status === "已登记";
      if (repoListFilter === "unregistered") return status === "未登记";
      return true;
    });
  }, [mergedRepoList, repoListQuery, repoListFilter, sourcesRepos, qualityMap, registeredAtMap]);

  function getRepoStatus(repoName: string) {
    const quality = qualityMap[repoName];
    const registeredAt = registeredAtMap[repoName];
    if (!sourcesRepos.has(repoName)) return { status: "未登记", tone: "empty" };
    if (quality?.last_fetched_at && (!registeredAt || quality.last_fetched_at >= registeredAt)) {
      if ((quality.ok_rate ?? 0) > 0) return { status: "已拉取", tone: "ok" };
      return { status: "上游缺失数据", tone: "warn" };
    }
    return { status: "已登记", tone: "mid" };
    return { status: "未登记", tone: "empty" };
  }

  function markStatus(repo: string, message: string) {
    setActionStatus((prev) => ({
      ...prev,
      [repo]: { ...prev[repo], add: message },
    }));
  }

  async function handleAdd(repoName: string) {
    try {
      const res = await fetch("/api/sources/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_name: repoName }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      markStatus(repoName, "已登记");
      setSourcesRepos((prev) => new Set(prev).add(repoName));
      loadQuality();
    } catch (err: any) {
      markStatus(repoName, `失败: ${String(err?.message ?? err)}`);
    }
  }

  return (
    <div className="panel repoListCard">
      <div className="panelHead">
        <div>
          <div className="panelTitle">仓库清单（采样 300 + 已有仓库）</div>
          <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
            从 repo_list.csv 采样并合并已入库仓库，用于登记入口。
          </div>
        </div>
        <div className="badge">
          <span className="mono" style={{ fontSize: 11 }}>
            采样 {repoList.length}/300 · 已合并 {repoListStats.loaded} · 已拉取 {repoListStats.hasData} · 缺失 {repoListStats.missing} · 已登记 {repoListStats.registered}
          </span>
        </div>
      </div>
      <div className="repoListHead">
        <input
          className="input"
          placeholder="搜索 org/repo…"
          value={repoListQuery}
          onChange={(e) => setRepoListQuery(e.target.value)}
        />
        <select className="select" value={repoListFilter} onChange={(e) => setRepoListFilter(e.target.value)}>
          <option value="all">全部</option>
          <option value="hasData">已有数据</option>
          <option value="missing">上游缺失数据</option>
          <option value="registered">已登记</option>
          <option value="unregistered">未登记</option>
        </select>
        {repoListError ? (
          <div className="muted" style={{ fontSize: 12, color: "#ff5a7a" }}>
            读取 repo_list.csv 失败：{repoListError}
          </div>
        ) : null}
      </div>
      <div className="repoListGrid">
        {filteredRepoList.slice(0, 300).map((row) => {
          const inSources = sourcesRepos.has(row.repo_name);
          const action = actionStatus[row.repo_name];
          const statusInfo = getRepoStatus(row.repo_name);
          const cls =
            statusInfo.tone === "ok"
              ? "repoTag repoTagOk"
              : statusInfo.tone === "warn"
                ? "repoTag repoTagWarn"
                : statusInfo.tone === "mid"
                  ? "repoTag repoTagMid"
                  : "repoTag repoTagEmpty";
          return (
            <div className="repoItem" key={`${row.platform}/${row.repo_name}`}>
              <div className="repoName mono">{row.repo_name}</div>
              <div className="repoMeta">
                <span className="repoPlatform">{row.platform}</span>
                <span className={cls}>{statusInfo.status}</span>
              </div>
              <div className="repoActions">
                <button className="btn btnGhost" disabled={inSources} onClick={() => handleAdd(row.repo_name)}>
                  {inSources ? "已登记" : "登记"}
                </button>
              </div>
              {action?.add ? <div className="repoStatus">登记: {action.add}</div> : null}
            </div>
          );
        })}
        {filteredRepoList.length === 0 ? (
          <div className="muted" style={{ padding: 8 }}>
            无匹配仓库
          </div>
        ) : null}
      </div>
    </div>
  );
}
