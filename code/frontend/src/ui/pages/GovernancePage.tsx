import { useEffect, useMemo, useState } from "react";
import type { RiskReportBundle } from "../../core/types";

type LlmResponse = {
  ok: boolean;
  content?: string;
  error?: string;
};

export default function GovernancePage() {
  const [bundle, setBundle] = useState<RiskReportBundle | null>(null);
  const [repo, setRepo] = useState("");
  const [focus, setFocus] = useState("");
  const [output, setOutput] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetch("/docs/risk_report.json", { cache: "no-cache" })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<RiskReportBundle>;
      })
      .then((data) => {
        setBundle(data);
        if (data.items?.length) setRepo(data.items[0].repo);
      })
      .catch((err) => setStatus(String(err?.message ?? err)));
  }, []);

  const selected = useMemo(() => {
    if (!bundle || !repo) return null;
    return bundle.items.find((it) => it.repo === repo) ?? null;
  }, [bundle, repo]);

  async function handleGenerate() {
    if (!selected) return;
    setLoading(true);
    setStatus(null);
    setOutput("");
    try {
      const res = await fetch("/api/llm/advise", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          risk_report: selected,
          user_focus: focus,
        }),
      });
      const data = (await res.json()) as LlmResponse;
      if (!res.ok || !data.ok) {
        const error = data.error === "missing_api_key" ? "未配置 DASHSCOPE_API_KEY" : data.error || `HTTP ${res.status}`;
        throw new Error(error);
      }
      setOutput(data.content || "");
    } catch (err: any) {
      setStatus(String(err?.message ?? err));
    } finally {
      setLoading(false);
    }
  }

  async function handleCopy() {
    if (!output) return;
    try {
      await navigator.clipboard.writeText(output);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch (err: any) {
      setStatus(String(err?.message ?? err));
    }
  }

  function renderInline(text: string) {
    const parts: Array<JSX.Element> = [];
    const codeSplit = text.split("`");
    let key = 0;
    for (let i = 0; i < codeSplit.length; i += 1) {
      const seg = codeSplit[i];
      if (i % 2 === 1) {
        parts.push(
          <code key={`code-${key++}`} className="mdCode">
            {seg}
          </code>
        );
        continue;
      }
      const boldSplit = seg.split("**");
      for (let j = 0; j < boldSplit.length; j += 1) {
        const chunk = boldSplit[j];
        if (j % 2 === 1) {
          parts.push(
            <strong key={`bold-${key++}`} className="mdStrong">
              {chunk}
            </strong>
          );
        } else if (chunk) {
          parts.push(<span key={`txt-${key++}`}>{chunk}</span>);
        }
      }
    }
    return parts;
  }

  function renderMarkdown(text: string) {
    const lines = text.split(/\r?\n/);
    const blocks: Array<JSX.Element> = [];
    let listItems: string[] = [];
    let key = 0;

    const flushList = () => {
      if (!listItems.length) return;
      blocks.push(
        <ul className="mdList" key={`list-${key++}`}>
          {listItems.map((item) => (
            <li key={`li-${key++}`}>{renderInline(item)}</li>
          ))}
        </ul>
      );
      listItems = [];
    };

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) {
        flushList();
        continue;
      }
      if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
        listItems.push(trimmed.slice(2));
        continue;
      }
      flushList();
      if (trimmed.startsWith("### ")) {
        blocks.push(
          <h4 className="mdHeading" key={`h4-${key++}`}>
            {renderInline(trimmed.slice(4))}
          </h4>
        );
        continue;
      }
      if (trimmed.startsWith("## ")) {
        blocks.push(
          <h3 className="mdHeading" key={`h3-${key++}`}>
            {renderInline(trimmed.slice(3))}
          </h3>
        );
        continue;
      }
      if (trimmed.startsWith("# ")) {
        blocks.push(
          <h2 className="mdHeading" key={`h2-${key++}`}>
            {renderInline(trimmed.slice(2))}
          </h2>
        );
        continue;
      }
      blocks.push(
        <p className="mdParagraph" key={`p-${key++}`}>
          {renderInline(line)}
        </p>
      );
    }
    flushList();
    return blocks;
  }

  return (
    <div className="governancePage">
      <div className="panel governancePanel">
        <div className="panelHead">
          <div>
            <div className="panelTitle">LLM 治理建议</div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
              基于 RiskReport 证据生成治理动作，不读取原始时序数据。
            </div>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <select className="select" value={repo} onChange={(e) => setRepo(e.target.value)}>
              {(bundle?.items ?? []).map((it) => (
                <option key={it.repo} value={it.repo}>
                  {it.repo}
                </option>
              ))}
            </select>
            <button className="btn" disabled={!selected || loading} onClick={handleGenerate}>
              {loading ? "生成中…" : "生成建议"}
            </button>
          </div>
        </div>

        <div className="modelBody">
          <div className="card">
            <div className="muted">输入说明</div>
            <div style={{ marginTop: 8, lineHeight: 1.6 }}>
              仅使用 RiskReport JSON 作为事实来源。若需复核或不确定性较高，将先提示人工核查。
            </div>
          </div>

          <div className="card">
            <div className="muted">关注点（可选）</div>
            <textarea
              className="input"
              style={{ marginTop: 8, minHeight: 80 }}
              placeholder="例如：优先降低 triage 压力、提升响应效率"
              value={focus}
              onChange={(e) => setFocus(e.target.value)}
            />
          </div>

          <div className="card">
            <div className="row">
              <div className="muted">LLM 输出</div>
              <button className="btn btnGhost" disabled={!output} onClick={handleCopy}>
                {copied ? "已复制" : "复制 Markdown"}
              </button>
            </div>
            {status ? (
              <div style={{ marginTop: 8, color: "#ff5a7a" }}>{status}</div>
            ) : output ? (
              <div className="llmOutputBox" style={{ marginTop: 8 }}>
                {renderMarkdown(output)}
              </div>
            ) : (
              <div className="muted" style={{ marginTop: 8 }}>
                暂无输出
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
