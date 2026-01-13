import { useEffect, useMemo, useState } from "react";
import type { RiskReportBundle, RiskReportItem } from "../../core/types";

type RawMetric = {
  name: string;
  latest_period: string | null;
  latest_value: any;
  points: number;
  series: Array<{ period: string; value: any }>;
};

type RawResponse = {
  ok: boolean;
  repo: string;
  metrics: RawMetric[];
};

type RagResponse = {
  ok: boolean;
  content?: string;
  error?: string;
};

export default function RagPage() {
  const [repos, setRepos] = useState<string[]>([]);
  const [bundle, setBundle] = useState<RiskReportBundle | null>(null);
  const [repo, setRepo] = useState("");
  const [question, setQuestion] = useState("");
  const [raw, setRaw] = useState<RawResponse | null>(null);
  const [output, setOutput] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const suggestedQuestions = [
    "这个仓库近 6 个月的活跃度趋势如何？",
    "哪些指标缺失最多，可能影响判断？",
    "当前风险等级的主要信号是什么？",
    "是否存在协作效率恶化的迹象？",
  ];

  useEffect(() => {
    fetch("/api/sources/repos", { cache: "no-cache" })
      .then((res) => res.json())
      .then((data) => {
        const list = (data?.repos ?? []).map((r: any) => `${r.org}/${r.repo}`);
        setRepos(list);
        if (list.length) setRepo(list[0]);
      })
      .catch((err) => setStatus(String(err?.message ?? err)));
  }, []);

  useEffect(() => {
    fetch("/docs/risk_report.json", { cache: "no-cache" })
      .then((res) => res.json() as Promise<RiskReportBundle>)
      .then((data) => setBundle(data))
      .catch(() => null);
  }, []);

  useEffect(() => {
    if (!repo) return;
    setRaw(null);
    fetch(`/api/raw?repo=${encodeURIComponent(repo)}`, { cache: "no-cache" })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<RawResponse>;
      })
      .then((data) => setRaw(data))
      .catch(() => setRaw(null));
  }, [repo]);

  const riskItem = useMemo<RiskReportItem | null>(() => {
    if (!bundle || !repo) return null;
    return bundle.items.find((it) => it.repo === repo) ?? null;
  }, [bundle, repo]);

  async function handleAsk() {
    if (!repo || !question.trim()) return;
    setLoading(true);
    setStatus(null);
    setOutput("");
    try {
      const res = await fetch("/api/llm/rag", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo, question }),
      });
      const data = (await res.json()) as RagResponse;
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
            <div className="panelTitle">RAG 问答</div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
              选择仓库，将该仓库的缓存数据与风险摘要提供给 Qwen 进行问答。
            </div>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <select className="select" value={repo} onChange={(e) => setRepo(e.target.value)}>
              {repos.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
            <button className="btn" disabled={!repo || !question.trim() || loading} onClick={handleAsk}>
              {loading ? "生成中…" : "提交问题"}
            </button>
          </div>
        </div>

        <div className="modelBody">
          <div className="card">
            <div className="muted">问题</div>
            <textarea
              className="input"
              style={{ marginTop: 8, minHeight: 90 }}
              placeholder="例如：这个仓库近期活跃度如何？数据缺失主要集中在哪些指标？"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />
            <div className="ragSuggestions">
              {suggestedQuestions.map((q) => (
                <button key={q} className="btn btnGhost" onClick={() => setQuestion(q)} type="button">
                  {q}
                </button>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="muted">数据指标说明（片段）</div>
            <div className="ragHintGrid">
              <div>
                <div className="ragHintTitle">activity</div>
                <div className="ragHintText">综合活跃度，常用于判断产出节奏。</div>
              </div>
              <div>
                <div className="ragHintTitle">contributors</div>
                <div className="ragHintText">活跃贡献者规模，反映人力投入。</div>
              </div>
              <div>
                <div className="ragHintTitle">issue_age</div>
                <div className="ragHintText">Issue 停留时间，代表协作效率。</div>
              </div>
              <div>
                <div className="ragHintTitle">change_requests</div>
                <div className="ragHintText">PR/CR 规模与流入量。</div>
              </div>
              <div>
                <div className="ragHintTitle">bus_factor</div>
                <div className="ragHintText">关键贡献集中度，越低风险越高。</div>
              </div>
              <div>
                <div className="ragHintTitle">openrank</div>
                <div className="ragHintText">生态综合影响力参考指标。</div>
              </div>
            </div>
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
              <div className="llmOutputBox llmOutputBoxLarge" style={{ marginTop: 8 }}>
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
