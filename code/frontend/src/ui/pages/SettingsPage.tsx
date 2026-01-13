import type { DataSource } from "../../core/data";
import { fetchRiskReport, saveDataSource } from "../../core/data";
import type { RiskReportBundle } from "../../core/types";
import { useMemo, useState } from "react";

export default function SettingsPage({
  source,
  onSourceChange,
  bundle,
}: {
  source: DataSource;
  onSourceChange: (s: DataSource) => void;
  bundle: RiskReportBundle | null;
}) {
  const [url, setUrl] = useState(source.kind === "url" ? source.url : "/docs/risk_report.json");
  const [status, setStatus] = useState<string>("");

  const info = useMemo(() => {
    if (!bundle) return null;
    return {
      as_of: bundle.as_of_month ?? "—",
      model: bundle.model?.type ? `${bundle.model.type}/${bundle.model.version ?? ""}` : "unknown",
      count: bundle.items?.length ?? 0,
    };
  }, [bundle]);

  async function testUrl() {
    try {
      setStatus("测试中…");
      const data = await fetchRiskReport(url);
      setStatus(`OK: as_of=${data.as_of_month ?? "—"} items=${data.items.length}`);
    } catch (e: any) {
      setStatus(`失败: ${String(e?.message ?? e)}`);
    }
  }

  function applyUrl() {
    const ds: DataSource = { kind: "url", url };
    saveDataSource(ds);
    onSourceChange(ds);
    setStatus("已应用数据源");
  }

  function exportCurrent() {
    if (!bundle) return;
    const payload = JSON.stringify(bundle, null, 2);
    const blob = new Blob([payload], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "risk_report_export.json";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(a.href);
  }

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div className="panel">
        <div className="panelHead">
          <div>
            <div className="panelTitle">设置</div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
              配置 risk_report 数据源与导入导出。
            </div>
          </div>
          <div className="muted mono" style={{ fontSize: 12 }}>
            {info ? `as_of=${info.as_of} · model=${info.model} · items=${info.count}` : "no data"}
          </div>
        </div>
        <div style={{ padding: 14, display: "grid", gap: 12 }}>
          <div className="card">
            <div className="row">
              <div>
                <div style={{ fontWeight: 720 }}>数据源 URL</div>
                <div className="muted" style={{ marginTop: 6, fontSize: 12 }}>
                  建议默认使用 <code>/docs/risk_report.json</code>（Vite dev 或静态服务器从仓库根目录提供）。
                </div>
              </div>
              <div className="badge">{source.kind === "url" ? "url" : "file"}</div>
            </div>
            <div style={{ marginTop: 10, display: "flex", gap: 10, flexWrap: "wrap" }}>
              <input className="input" style={{ flex: 1 }} value={url} onChange={(e) => setUrl(e.target.value)} />
              <button className="btn" onClick={testUrl}>
                测试
              </button>
              <button className="btn" onClick={applyUrl}>
                应用
              </button>
              <button className="btn btnGhost" onClick={() => onSourceChange({ kind: "url", url: "/docs/risk_report.json" })}>
                重置默认
              </button>
            </div>
            {status ? (
              <div style={{ marginTop: 10, fontSize: 12, color: status.startsWith("OK") ? "rgba(68,209,158,.92)" : "rgba(255,90,122,.92)" }}>
                {status}
              </div>
            ) : null}
          </div>

          <div className="card">
            <div className="row">
              <div>
                <div style={{ fontWeight: 720 }}>导出</div>
                <div className="muted" style={{ marginTop: 6, fontSize: 12 }}>
                  将当前加载的 RiskReport 导出为 JSON（用于共享/离线查看）。
                </div>
              </div>
              <button className="btn" onClick={exportCurrent} disabled={!bundle}>
                导出当前数据
              </button>
            </div>
          </div>

          <div className="card">
            <div style={{ fontWeight: 720 }}>使用建议</div>
            <div className="muted" style={{ marginTop: 8, fontSize: 12, lineHeight: 1.6 }}>
              1) 先运行 pipeline 生成 <code>docs/risk_report.json</code><br />
              2) 前端用 <code>npm run dev</code> 启动；或 build 后用任意 HTTP 服务提供静态文件<br />
              3) 如需“展示大屏”，直接访问 <code>/wall</code>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
