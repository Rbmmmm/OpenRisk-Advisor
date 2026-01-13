import type { RiskReportBundle } from "./types";

export type DataSource =
  | { kind: "url"; url: string }
  | { kind: "inline"; name: string; json: RiskReportBundle };

const LS_KEY = "openrisk.datasource.v1";

export function loadSavedDataSource(): DataSource | null {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed?.kind === "url" && typeof parsed.url === "string") return parsed;
  } catch {
    // ignore
  }
  return null;
}

export function saveDataSource(ds: DataSource): void {
  if (ds.kind === "inline") return;
  localStorage.setItem(LS_KEY, JSON.stringify(ds));
}

export async function fetchRiskReport(url: string): Promise<RiskReportBundle> {
  const res = await fetch(url, { cache: "no-cache" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const json = await res.json();
  if (!json || !Array.isArray(json.items)) throw new Error("Invalid risk_report.json (missing items[])");
  return json as RiskReportBundle;
}

export async function readJsonFile(file: File): Promise<any> {
  const text = await file.text();
  return JSON.parse(text);
}

