import { NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import type { DataSource } from "../core/data";
import { fetchRiskReport, loadSavedDataSource, readJsonFile, saveDataSource } from "../core/data";
import type { RiskReportBundle } from "../core/types";
import OverviewPage from "./pages/OverviewPage";
import ReposPage from "./pages/ReposPage";
import RepoListPage from "./pages/RepoListPage";
import RegisteredReposPage from "./pages/RegisteredReposPage";
import RegisteredRepoDetailPage from "./pages/RegisteredRepoDetailPage";
import SignalReportPage from "./pages/SignalReportPage";
import ModelPage from "./pages/ModelPage";
import GovernancePage from "./pages/GovernancePage";
import RagPage from "./pages/RagPage";
import SignalsPage from "./pages/SignalsPage";
import WallPage from "./pages/WallPage";
import SettingsPage from "./pages/SettingsPage";

const DEFAULT_URL = "/docs/risk_report.json";

function NavItem({
  to,
  label,
  hint,
}: {
  to: string;
  label: string;
  hint: string;
}) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) => (isActive ? "navItem navItemActive" : "navItem")}
    >
      <div>
        <div>{label}</div>
        <div className="navHint">{hint}</div>
      </div>
      <div className="navHint">↗</div>
    </NavLink>
  );
}

export default function App() {
  const nav = useNavigate();
  const loc = useLocation();
  const isWall = loc.pathname.startsWith("/wall");

  const [source, setSource] = useState<DataSource>(() => loadSavedDataSource() ?? { kind: "url", url: DEFAULT_URL });
  const [bundle, setBundle] = useState<RiskReportBundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const metaLine = useMemo(() => {
    const m = bundle?.model;
    const model = m?.type ? `${m.type}/${m.version ?? ""}` : "unknown";
    return `as_of=${bundle?.as_of_month ?? "—"} · model=${model} · items=${bundle?.items?.length ?? 0}`;
  }, [bundle]);

  async function refresh() {
    try {
      setLoading(true);
      setError(null);
      if (source.kind === "inline") {
        setBundle(source.json);
        return;
      }
      const data = await fetchRiskReport(source.url);
      setBundle(data);
      saveDataSource(source);
    } catch (e: any) {
      setError(String(e?.message ?? e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source.kind === "url" ? source.url : "inline"]);

  async function onImportFile(file: File) {
    const json = (await readJsonFile(file)) as RiskReportBundle;
    if (!json || !Array.isArray(json.items)) throw new Error("导入失败：不是有效的 risk_report.json");
    setSource({ kind: "inline", name: file.name, json });
    setBundle(json);
    setError(null);
    nav("/");
  }

  if (isWall) {
    return (
      <Routes>
        <Route path="/wall" element={<WallPage bundle={bundle} loading={loading} error={error} onRefresh={refresh} />} />
        <Route path="*" element={<WallPage bundle={bundle} loading={loading} error={error} onRefresh={refresh} />} />
      </Routes>
    );
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand" onClick={() => nav("/")} role="button" tabIndex={0}>
          <div className="brandMark" aria-hidden="true" />
          <div>
            <div className="brandTitle">OpenRisk-Advisor</div>
            <div className="brandSub">Risk Console</div>
          </div>
        </div>

        <nav className="nav">
          <NavItem to="/repo-list" label="仓库清单" hint="采样 · 状态 · 检索" />
          <NavItem to="/registered" label="已登记仓库" hint="登记 · 拉取 · 成功率" />
          <NavItem to="/signals-report" label="信号报告" hint="生成 · 仓库 · 统计" />
          <NavItem to="/models" label="模型" hint="训练 · 预测 · 状态" />
          <NavItem to="/governance" label="治理建议" hint="LLM · 证据 · 动作" />
          <NavItem to="/rag" label="RAG 问答" hint="仓库 · 数据 · 提问" />
          <NavItem to="/repos" label="项目库" hint="筛选 · 钻取 · 证据链" />
          <NavItem to="/signals" label="信号洞察" hint="Top 信号 · 维度占比" />
          <NavItem to="/" label="概览" hint="KPI · 分布 · 热点" />
          <NavItem to="/wall" label="大屏" hint="Wall · 适合展示" />
          <NavItem to="/settings" label="设置" hint="数据源 · 导入 · 导出" />
        </nav>

        <div style={{ marginTop: 14 }}>
          <div className="card">
            <div className="row">
              <div className="muted">数据源</div>
              <div className="mono" style={{ fontSize: 11 }}>
                {source.kind === "url" ? source.url : `file:${source.name}`}
              </div>
            </div>
            <div style={{ marginTop: 10, display: "flex", gap: 10 }}>
              <button className="btn" onClick={refresh} disabled={loading}>
                {loading ? "加载中…" : "刷新"}
              </button>
              <button className="btn btnGhost" onClick={() => nav("/wall")}>打开大屏</button>
            </div>
            {error ? (
              <div style={{ marginTop: 10, color: "#ff5a7a", fontSize: 12 }}>
                {error}
                <div className="muted" style={{ marginTop: 6 }}>
                  建议用 `npm run dev` 或任意 HTTP 服务访问，并确保 `docs/risk_report.json` 已生成。
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </aside>

      <div className="content">
        <header className="topbar">
          <div className="topbarLeft">
            <div className="topTitle">Risk Console</div>
            <div className="topMeta">{metaLine}</div>
          </div>
          <div className="topActions">
            <label className="btn btnGhost" style={{ display: "inline-flex", alignItems: "center", gap: 10 }}>
              导入 JSON
              <input
                type="file"
                accept="application/json"
                style={{ display: "none" }}
                onChange={async (e) => {
                  const f = e.target.files?.[0];
                  if (!f) return;
                  try {
                    await onImportFile(f);
                  } catch (err: any) {
                    setError(String(err?.message ?? err));
                  } finally {
                    e.target.value = "";
                  }
                }}
              />
            </label>
            <button className="btn" onClick={refresh} disabled={loading}>
              {loading ? "加载中…" : "刷新"}
            </button>
          </div>
        </header>

        <div className="page">
          <Routes>
            <Route path="/" element={<OverviewPage bundle={bundle} loading={loading} error={error} />} />
            <Route path="/repos" element={<ReposPage bundle={bundle} />} />
            <Route path="/repo-list" element={<RepoListPage bundle={bundle} />} />
            <Route path="/registered" element={<RegisteredReposPage bundle={bundle} />} />
            <Route path="/registered/:org/:repo" element={<RegisteredRepoDetailPage />} />
            <Route path="/signals-report" element={<SignalReportPage />} />
            <Route path="/models" element={<ModelPage />} />
            <Route path="/governance" element={<GovernancePage />} />
            <Route path="/rag" element={<RagPage />} />
            <Route path="/signals" element={<SignalsPage bundle={bundle} />} />
            <Route
              path="/settings"
              element={
                <SettingsPage
                  source={source}
                  onSourceChange={(s) => setSource(s)}
                  bundle={bundle}
                />
              }
            />
            <Route path="*" element={<OverviewPage bundle={bundle} loading={loading} error={error} />} />
          </Routes>
        </div>
      </div>
    </div>
  );
}
