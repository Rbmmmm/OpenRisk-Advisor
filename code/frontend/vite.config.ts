import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import readline from "node:readline";
import { spawn } from "node:child_process";

function contentTypeFor(filePath: string): string {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === ".json") return "application/json; charset=utf-8";
  if (ext === ".md") return "text/markdown; charset=utf-8";
  if (ext === ".csv") return "text/csv; charset=utf-8";
  if (ext === ".txt") return "text/plain; charset=utf-8";
  return "application/octet-stream";
}

function serveRepoDocs(): Plugin {
  const here = path.dirname(fileURLToPath(import.meta.url));
  const repoRoot = path.resolve(here, "..");
  const docsRoot = path.join(repoRoot, "docs");
  const sourcesPath = path.join(repoRoot, "configs", "sources.yaml");

  function readSourcesRepos() {
    if (!fs.existsSync(sourcesPath)) return { defaults: {}, repos: [] as Array<{ org: string; repo: string; platform?: string; enabled?: boolean }> };
    const lines = fs.readFileSync(sourcesPath, "utf-8").split(/\r?\n/);
    const defaults: Record<string, string> = {};
    const repos: Array<{ org: string; repo: string; platform?: string; enabled?: boolean; registered_at?: string }> = [];
    let inDefaults = false;
    let inRepos = false;
    let cur: any = null;
    for (const raw of lines) {
      const line = raw.trimEnd();
      if (!line) continue;
      if (line.startsWith("defaults:")) {
        inDefaults = true;
        inRepos = false;
        continue;
      }
      if (line.startsWith("repos:")) {
        inDefaults = false;
        inRepos = true;
        continue;
      }
      if (inDefaults) {
        const m = line.match(/^\s*([A-Za-z0-9_]+):\s*(.+)$/);
        if (m) defaults[m[1]] = m[2];
        continue;
      }
      if (inRepos) {
        const orgMatch = line.match(/^\s*-\s*org:\s*(.+)$/);
        if (orgMatch) {
          cur = { org: orgMatch[1].trim(), repo: "" };
          repos.push(cur);
          continue;
        }
        const repoMatch = line.match(/^\s*repo:\s*(.+)$/);
        if (cur && repoMatch) {
          cur.repo = repoMatch[1].trim();
          continue;
        }
        const platformMatch = line.match(/^\s*platform:\s*(.+)$/);
        if (cur && platformMatch) {
          cur.platform = platformMatch[1].trim();
          continue;
        }
        const enabledMatch = line.match(/^\s*enabled:\s*(.+)$/);
        if (cur && enabledMatch) {
          cur.enabled = enabledMatch[1].trim() !== "false";
          continue;
        }
        const registeredMatch = line.match(/^\s*registered_at:\s*(.+)$/);
        if (cur && registeredMatch) {
          cur.registered_at = registeredMatch[1].trim();
        }
      }
    }
    return { defaults, repos };
  }

  function addRepoToSources(org: string, repo: string) {
    const { repos } = readSourcesRepos();
    const exists = repos.some((r) => r.org === org && r.repo === repo);
    if (exists) return { ok: true, message: "already_exists" };
    const registeredAt = new Date().toISOString();
    const block = `- org: ${org}\n  repo: ${repo}\n  enabled: true\n  registered_at: ${registeredAt}\n`;
    const content = fs.existsSync(sourcesPath) ? fs.readFileSync(sourcesPath, "utf-8") : "";
    const out = content.trimEnd() + "\n" + block;
    fs.writeFileSync(sourcesPath, out);
    return { ok: true, message: "added" };
  }

  function resolveRepoPlatform(org: string, repo: string, defaults: Record<string, string>, repos: Array<{ org: string; repo: string; platform?: string }>) {
    const match = repos.find((r) => r.org === org && r.repo === repo);
    return match?.platform || defaults.platform || "github";
  }

  function buildMetricSummary(filePath: string) {
    const raw = fs.readFileSync(filePath, "utf-8");
    const json = JSON.parse(raw || "{}");
    const entries = Object.entries(json).filter(([key]) => !key.endsWith("-raw"));
    const monthEntries = entries.filter(([key]) => /^\d{4}-\d{2}$/.test(key));
    const ordered = (monthEntries.length ? monthEntries : entries).sort(([a], [b]) => a.localeCompare(b));
    const series = ordered.slice(-12).map(([period, value]) => ({ period, value }));
    const latest = ordered.length ? ordered[ordered.length - 1] : null;
    return {
      latest_period: latest ? latest[0] : null,
      latest_value: latest ? latest[1] : null,
      points: ordered.length,
      series,
    };
  }

  async function readRepoListSample(limit: number) {
    const filePath = path.join(repoRoot, "repo_list.csv");
    if (!fs.existsSync(filePath)) return { items: [] as Array<{ id: string; platform: string; repo_name: string }> };
    const stream = fs.createReadStream(filePath, { encoding: "utf-8" });
    const rl = readline.createInterface({ input: stream, crlfDelay: Infinity });
    const items: Array<{ id: string; platform: string; repo_name: string }> = [];
    let headerSkipped = false;
    for await (const line of rl) {
      if (!headerSkipped) {
        headerSkipped = true;
        continue;
      }
      if (!line.trim()) continue;
      const [id, platform, repo_name] = line.split(",");
      if (id && platform && repo_name) items.push({ id, platform, repo_name });
      if (items.length >= limit) {
        rl.close();
        stream.destroy();
        break;
      }
    }
    return { items };
  }

  function registerApiRoutes(server: any) {
    server.middlewares.use("/api/sources/repos", (req: any, res: any) => {
      try {
        const { repos } = readSourcesRepos();
        res.statusCode = 200;
        res.setHeader("Content-Type", "application/json; charset=utf-8");
        res.end(JSON.stringify({ repos }));
      } catch {
        res.statusCode = 500;
        res.end("Failed to read sources.yaml");
      }
    });
    server.middlewares.use("/api/sources/add", (req: any, res: any) => {
      let body = "";
      req.on("data", (chunk: any) => (body += chunk));
      req.on("end", () => {
        try {
          const data = body ? JSON.parse(body) : {};
          const repoName = String(data.repo_name || "");
          const [org, repo] = repoName.split("/");
          if (!org || !repo) {
            res.statusCode = 400;
            res.end("invalid repo_name");
            return;
          }
          const result = addRepoToSources(org, repo);
          res.statusCode = 200;
          res.setHeader("Content-Type", "application/json; charset=utf-8");
          res.end(JSON.stringify(result));
        } catch {
          res.statusCode = 500;
          res.end("Failed to update sources.yaml");
        }
      });
    });
    server.middlewares.use("/api/raw", (req: any, res: any) => {
      try {
        const url = new URL(req.url || "", "http://localhost");
        const repoName = String(url.searchParams.get("repo") || "");
        const [org, repo] = repoName.split("/");
        if (!org || !repo) {
          res.statusCode = 400;
          res.end("invalid repo");
          return;
        }
        const { defaults, repos } = readSourcesRepos();
        const platform = resolveRepoPlatform(org, repo, defaults, repos);
        const cacheDir = defaults.cache_dir || "data/cache";
        const repoDir = path.join(repoRoot, cacheDir, platform, org, repo);
        if (!fs.existsSync(repoDir)) {
          res.statusCode = 404;
          res.setHeader("Content-Type", "application/json; charset=utf-8");
          res.end(JSON.stringify({ ok: false, error: "cache_not_found", repo: repoName }));
          return;
        }
        const files = fs.readdirSync(repoDir).filter((f) => f.endsWith(".json"));
        const metrics = files
          .map((file) => {
            const name = file.replace(/\.json$/i, "");
            try {
              const summary = buildMetricSummary(path.join(repoDir, file));
              return { name, ...summary };
            } catch {
              return { name, latest_period: null, latest_value: null, points: 0, series: [] };
            }
          })
          .sort((a, b) => a.name.localeCompare(b.name));
        res.statusCode = 200;
        res.setHeader("Content-Type", "application/json; charset=utf-8");
        res.end(JSON.stringify({ ok: true, repo: repoName, metrics }));
      } catch {
        res.statusCode = 500;
        res.end("Failed to load raw data");
      }
    });
    server.middlewares.use("/api/repo-list", async (req: any, res: any) => {
      try {
        const url = new URL(req.url || "", "http://localhost");
        const limitRaw = Number(url.searchParams.get("limit") || 300);
        const limit = Math.max(1, Math.min(1000, Number.isFinite(limitRaw) ? limitRaw : 300));
        const result = await readRepoListSample(limit);
        res.statusCode = 200;
        res.setHeader("Content-Type", "application/json; charset=utf-8");
        res.end(JSON.stringify(result));
      } catch {
        res.statusCode = 500;
        res.end("Failed to read repo_list.csv");
      }
    });
    server.middlewares.use("/api/signals/run", (req: any, res: any) => {
      try {
        const proc = spawn("python", ["scripts/signal_engine.py", "--sources", "configs/sources.yaml", "--metrics", "configs/metrics.yaml", "--signals", "configs/signals.yaml"], {
          cwd: repoRoot,
        });
        let output = "";
        proc.stdout.on("data", (d) => (output += d.toString()));
        proc.stderr.on("data", (d) => (output += d.toString()));
        proc.on("close", (code) => {
          res.statusCode = code === 0 ? 200 : 500;
          res.setHeader("Content-Type", "application/json; charset=utf-8");
          res.end(JSON.stringify({ ok: code === 0, code, output: output.slice(-8000) }));
        });
      } catch {
        res.statusCode = 500;
        res.end("Failed to run signal engine");
      }
    });
    server.middlewares.use("/api/model/status", (req: any, res: any) => {
      try {
        const proc = spawn("python", ["scripts/model_status.py", "--sources", "configs/sources.yaml", "--model", "configs/model.yaml"], {
          cwd: repoRoot,
        });
        let output = "";
        proc.stdout.on("data", (d) => (output += d.toString()));
        proc.stderr.on("data", (d) => (output += d.toString()));
        proc.on("close", (code) => {
          res.statusCode = code === 0 ? 200 : 500;
          res.setHeader("Content-Type", "application/json; charset=utf-8");
          if (code === 0) {
            res.end(output.trim());
          } else {
            res.end(JSON.stringify({ ok: false, output: output.slice(-8000) }));
          }
        });
      } catch {
        res.statusCode = 500;
        res.end("Failed to read model status");
      }
    });
    server.middlewares.use("/api/model/train", (req: any, res: any) => {
      let body = "";
      req.on("data", (chunk: any) => (body += chunk));
      req.on("end", () => {
        try {
          const data = body ? JSON.parse(body) : {};
          const modelType = String(data.model_type || "baseline");
          const args =
            modelType === "transformer"
              ? ["python", "scripts/train_transformer.py", "--sources", "configs/sources.yaml", "--model", "configs/model.yaml", "--replace", "--write-predictions"]
              : ["python", "scripts/train_predictor.py", "--sources", "configs/sources.yaml", "--model", "configs/model.yaml", "--model-type", "baseline", "--replace", "--write-predictions"];
          const proc = spawn(args[0], args.slice(1), { cwd: repoRoot });
          let output = "";
          proc.stdout.on("data", (d) => (output += d.toString()));
          proc.stderr.on("data", (d) => (output += d.toString()));
          proc.on("close", (code) => {
            res.statusCode = code === 0 ? 200 : 500;
            res.setHeader("Content-Type", "application/json; charset=utf-8");
            res.end(JSON.stringify({ ok: code === 0, code, output: output.slice(-8000) }));
          });
        } catch {
          res.statusCode = 500;
          res.end("Failed to train model");
        }
      });
    });
    server.middlewares.use("/api/model/predict", (req: any, res: any) => {
      let body = "";
      req.on("data", (chunk: any) => (body += chunk));
      req.on("end", async () => {
        try {
          const data = body ? JSON.parse(body) : {};
          const modelType = String(data.model_type || "baseline");
          const steps: Array<{ label: string; args: string[] }> = [
            {
              label: "build_risk_reports",
              args: ["python", "scripts/build_risk_explanations.py", "--sources", "configs/sources.yaml", "--model", "configs/model.yaml", "--signals", "configs/signals.yaml", "--model-type", modelType, "--replace"],
            },
            {
              label: "export_risk_reports",
              args: ["python", "scripts/export_riskreports.py", "--sources", "configs/sources.yaml", "--model-type", modelType, "--output-json", "docs/risk_report.json", "--output-md", "docs/risk_report.md"],
            },
          ];
          const runStep = (label: string, args: string[]) =>
            new Promise<{ label: string; ok: boolean; output: string }>((resolve) => {
              const proc = spawn(args[0], args.slice(1), { cwd: repoRoot });
              let output = "";
              proc.stdout.on("data", (d) => (output += d.toString()));
              proc.stderr.on("data", (d) => (output += d.toString()));
              proc.on("close", (code) => resolve({ label, ok: code === 0, output: output.trim() }));
            });
          const results = [];
          let hasFail = false;
          for (const step of steps) {
            // eslint-disable-next-line no-await-in-loop
            const result = await runStep(step.label, step.args);
            if (!result.ok) hasFail = true;
            results.push({ label: result.label, ok: result.ok, output: result.output.slice(-8000) });
          }
          res.statusCode = hasFail ? 500 : 200;
          res.setHeader("Content-Type", "application/json; charset=utf-8");
          res.end(JSON.stringify({ ok: !hasFail, steps: results }));
        } catch {
          res.statusCode = 500;
          res.end("Failed to run prediction");
        }
      });
    });
    server.middlewares.use("/api/model/predictions", (req: any, res: any) => {
      try {
        const url = new URL(req.url || "", "http://localhost");
        const modelType = String(url.searchParams.get("model_type") || "baseline");
        const proc = spawn("python", ["scripts/model_predictions.py", "--sources", "configs/sources.yaml", "--model-type", modelType], {
          cwd: repoRoot,
        });
        let output = "";
        proc.stdout.on("data", (d) => (output += d.toString()));
        proc.stderr.on("data", (d) => (output += d.toString()));
        proc.on("close", (code) => {
          res.statusCode = code === 0 ? 200 : 500;
          res.setHeader("Content-Type", "application/json; charset=utf-8");
          res.end(output.trim() || JSON.stringify({ ok: false, error: "empty_output" }));
        });
      } catch {
        res.statusCode = 500;
        res.end("Failed to load predictions");
      }
    });
    server.middlewares.use("/api/llm/advise", (req: any, res: any) => {
      let body = "";
      req.on("data", (chunk: any) => (body += chunk));
      req.on("end", async () => {
        try {
          const apiKey = "sk-4626d28a7be04c4abc04bdcb73eab025";
          if (!apiKey) {
            res.statusCode = 400;
            res.end(JSON.stringify({ ok: false, error: "missing_api_key" }));
            return;
          }
          const data = body ? JSON.parse(body) : {};
          const report = data.risk_report ?? null;
          const userFocus = String(data.user_focus || "");
          if (!report || !report.repo) {
            res.statusCode = 400;
            res.end(JSON.stringify({ ok: false, error: "invalid_risk_report" }));
            return;
          }
          const systemPrompt =
            "You are a governance action generator. Use only the provided RiskReport JSON as evidence. " +
            "Do not introduce new facts. If needs_review=true or model_uncertainty is high, state that human review is required first. " +
            "Do not output emojis.";
          const userPrompt =
            "RiskReport JSON:\\n" +
            JSON.stringify(report, null, 2) +
            "\\n\\n" +
            "User focus (optional): " +
            userFocus +
            "\\n\\n" +
            "Output format:\\n" +
            "1) 风险摘要\\n" +
            "2) 逐信号治理建议（Goal/Steps/Expected Impact/Risks）\\n" +
            "3) 优先级与30/60/90天计划\\n";
          const payload = {
            model: "qwen3-max",
            messages: [
              { role: "system", content: systemPrompt },
              { role: "user", content: userPrompt },
            ],
            temperature: 0.3,
          };
          const resp = await fetch("https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", {
            method: "POST",
            headers: {
              Authorization: `Bearer ${apiKey}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
          });
          const json = await resp.json();
          if (!resp.ok) {
            res.statusCode = 500;
            res.end(JSON.stringify({ ok: false, error: json?.error || "llm_failed" }));
            return;
          }
          const content = json?.choices?.[0]?.message?.content ?? "";
          res.statusCode = 200;
          res.setHeader("Content-Type", "application/json; charset=utf-8");
          res.end(JSON.stringify({ ok: true, content }));
        } catch (err: any) {
          res.statusCode = 500;
          res.end(JSON.stringify({ ok: false, error: String(err?.message ?? err) }));
        }
      });
    });
    server.middlewares.use("/api/llm/rag", (req: any, res: any) => {
      let body = "";
      req.on("data", (chunk: any) => (body += chunk));
      req.on("end", async () => {
        try {
          const apiKey = "sk-4626d28a7be04c4abc04bdcb73eab025";
          if (!apiKey) {
            res.statusCode = 400;
            res.end(JSON.stringify({ ok: false, error: "missing_api_key" }));
            return;
          }
          const data = body ? JSON.parse(body) : {};
          const repoName = String(data.repo || "");
          const question = String(data.question || "");
          const [org, repo] = repoName.split("/");
          if (!org || !repo || !question) {
            res.statusCode = 400;
            res.end(JSON.stringify({ ok: false, error: "invalid_payload" }));
            return;
          }

          let riskItem: any = null;
          const riskPath = path.join(repoRoot, "docs", "risk_report.json");
          if (fs.existsSync(riskPath)) {
            try {
              const rr = JSON.parse(fs.readFileSync(riskPath, "utf-8"));
              riskItem = (rr.items || []).find((it: any) => it.repo === repoName) ?? null;
            } catch {
              riskItem = null;
            }
          }

          const { defaults, repos } = readSourcesRepos();
          const platform = resolveRepoPlatform(org, repo, defaults, repos);
          const cacheDir = defaults.cache_dir || "data/cache";
          const repoDir = path.join(repoRoot, cacheDir, platform, org, repo);
          let rawSummary: any = { ok: false, metrics: [] };
          if (fs.existsSync(repoDir)) {
            const files = fs.readdirSync(repoDir).filter((f) => f.endsWith(".json"));
            const metrics = files
              .map((file) => {
                const name = file.replace(/\.json$/i, "");
                try {
                  const summary = buildMetricSummary(path.join(repoDir, file));
                  return { name, ...summary };
                } catch {
                  return { name, latest_period: null, latest_value: null, points: 0, series: [] };
                }
              })
              .sort((a, b) => b.points - a.points)
              .slice(0, 24);
            rawSummary = { ok: true, metrics };
          }

          const context = {
            repo: repoName,
            risk_report: riskItem
              ? {
                  risk_level: riskItem.risk_level,
                  risk_score: riskItem.risk_score,
                  data_quality: riskItem.data_quality,
                  main_signals: riskItem.main_signals,
                  as_of_month: riskItem.as_of_month || riskItem.as_of,
                }
              : null,
            raw_metrics: rawSummary.ok
              ? {
                  metric_count: rawSummary.metrics.length,
                  metrics: rawSummary.metrics.map((m: any) => ({
                    name: m.name,
                    latest_period: m.latest_period,
                    latest_value: m.latest_value,
                    points: m.points,
                    series_tail: m.series,
                  })),
                }
              : null,
          };

          const systemPrompt =
            "You are a repo data assistant. Answer only using the provided context JSON. " +
            "If data is missing, say it clearly. Do not invent facts. Do not output emojis.";
          const userPrompt =
            "Context JSON:\\n" +
            JSON.stringify(context, null, 2) +
            "\\n\\n" +
            "User question:\\n" +
            question +
            "\\n\\n" +
            "Answer in Chinese with clear bullet points if applicable.";

          const payload = {
            model: "qwen3-max",
            messages: [
              { role: "system", content: systemPrompt },
              { role: "user", content: userPrompt },
            ],
            temperature: 0.2,
          };
          const resp = await fetch("https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", {
            method: "POST",
            headers: {
              Authorization: `Bearer ${apiKey}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
          });
          const json = await resp.json();
          if (!resp.ok) {
            res.statusCode = 500;
            res.end(JSON.stringify({ ok: false, error: json?.error || "llm_failed" }));
            return;
          }
          const content = json?.choices?.[0]?.message?.content ?? "";
          res.statusCode = 200;
          res.setHeader("Content-Type", "application/json; charset=utf-8");
          res.end(JSON.stringify({ ok: true, content, context }));
        } catch (err: any) {
          res.statusCode = 500;
          res.end(JSON.stringify({ ok: false, error: String(err?.message ?? err) }));
        }
      });
    });
    server.middlewares.use("/api/ingest", (req: any, res: any) => {
      let body = "";
      req.on("data", (chunk: any) => (body += chunk));
      req.on("end", async () => {
        try {
          const data = body ? JSON.parse(body) : {};
          const repoName = String(data.repo_name || "");
          const [org, repo] = repoName.split("/");
          if (!org || !repo) {
            res.statusCode = 400;
            res.end("invalid repo_name");
            return;
          }
          const { defaults } = readSourcesRepos();
          const tmpDir = path.join(repoRoot, "data", "tmp");
          fs.mkdirSync(tmpDir, { recursive: true });
          const tmpPath = path.join(tmpDir, `sources_${org.replace(/\W/g, "_")}_${repo.replace(/\W/g, "_")}.yaml`);
          const defaultsBlock = [
            "version: 1",
            "defaults:",
            `  platform: ${defaults.platform || "github"}`,
            `  base_url: ${defaults.base_url || "https://oss.open-digger.cn"}`,
            `  cache_dir: ${defaults.cache_dir || "data/cache"}`,
            `  sqlite_path: ${defaults.sqlite_path || "data/sqlite/opendigger.db"}`,
            "repos:",
            `- org: ${org}`,
            `  repo: ${repo}`,
            "  enabled: true",
            "",
          ].join("\n");
          fs.writeFileSync(tmpPath, defaultsBlock);

          const steps: Array<{ label: string; args: string[]; softFail?: boolean }> = [
            {
              label: "ingest",
              args: ["python", "-m", "services.ingestion.run_ingest", "--sources", tmpPath, "--metrics", "configs/metrics.yaml"],
            },
            {
              label: "derive_features",
              args: ["python", "scripts/derive_features.py", "--sources", "configs/sources.yaml", "--period-type", "month", "--windows", "3,6,12"],
            },
            {
              label: "quality_report",
              args: ["python", "scripts/quality_report.py", "--sources", "configs/sources.yaml", "--metrics", "configs/metrics.yaml", "--json-output", "docs/data_quality_report.json"],
            },
            {
              label: "signal_engine",
              args: ["python", "scripts/signal_engine.py", "--sources", "configs/sources.yaml", "--metrics", "configs/metrics.yaml", "--signals", "configs/signals.yaml"],
            },
            {
              label: "build_risk_reports",
              args: ["python", "scripts/build_risk_explanations.py", "--sources", "configs/sources.yaml", "--model", "configs/model.yaml", "--signals", "configs/signals.yaml", "--replace"],
              softFail: true,
            },
            {
              label: "export_risk_reports",
              args: ["python", "scripts/export_riskreports.py", "--sources", "configs/sources.yaml", "--output-json", "docs/risk_report.json", "--output-md", "docs/risk_report.md"],
              softFail: true,
            },
          ];

          const runStep = (label: string, args: string[]) =>
            new Promise<{ label: string; ok: boolean; output: string }>((resolve) => {
              const proc = spawn(args[0], args.slice(1), { cwd: repoRoot });
              let output = "";
              proc.stdout.on("data", (d) => (output += d.toString()));
              proc.stderr.on("data", (d) => (output += d.toString()));
              proc.on("close", (code) => {
                resolve({ label, ok: code === 0, output: output.trim() });
              });
            });

          const results = [];
          let hasHardFail = false;
          const warnings: string[] = [];
          for (const step of steps) {
            // eslint-disable-next-line no-await-in-loop
            const result = await runStep(step.label, step.args);
            const missingPredictions = /no risk_predictions/i.test(result.output);
            const ok = result.ok || (step.softFail && missingPredictions);
            if (!ok) {
              if (step.softFail) warnings.push(step.label);
              else hasHardFail = true;
            }
            results.push({ label: result.label, ok, output: result.output.slice(-8000) });
          }

          res.statusCode = hasHardFail ? 500 : 200;
          res.setHeader("Content-Type", "application/json; charset=utf-8");
          res.end(JSON.stringify({ ok: !hasHardFail, steps: results, warnings }));
        } catch {
          res.statusCode = 500;
          res.end("Failed to start ingestion");
        }
      });
    });
  }

  function docsMiddleware(req: any, res: any, next: any) {
    try {
      const urlPath = decodeURIComponent((req.url || "/").split("?")[0]);
      const rel = urlPath.replace(/^\/+/, "");
      const candidate = path.normalize(path.join(docsRoot, rel));
      if (!candidate.startsWith(docsRoot)) {
        res.statusCode = 403;
        res.end("Forbidden");
        return;
      }
      if (!fs.existsSync(candidate) || fs.statSync(candidate).isDirectory()) {
        next();
        return;
      }
      res.statusCode = 200;
      res.setHeader("Content-Type", contentTypeFor(candidate));
      fs.createReadStream(candidate).pipe(res);
    } catch {
      next();
    }
  }

  return {
    name: "openrisk-serve-repo-docs",
    configureServer(server) {
      server.middlewares.use("/docs", docsMiddleware);
      registerApiRoutes(server);
    },
    configurePreviewServer(server) {
      server.middlewares.use("/docs", docsMiddleware);
      registerApiRoutes(server);
    },
  };
}

export default defineConfig({
  plugins: [react(), serveRepoDocs()],
  server: {
    port: 5173,
    strictPort: true,
  },
});
