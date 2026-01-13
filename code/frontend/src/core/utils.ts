import type { RiskLevel, RiskReportItem } from "./types";

export function clamp01(x: number): number {
  return Math.max(0, Math.min(1, x));
}

export function fmt(n: number | undefined | null, digits = 0): string {
  if (n === undefined || n === null || Number.isNaN(n)) return "—";
  return Number(n).toFixed(digits);
}

export function toLevel(level: string | undefined | null): RiskLevel | string {
  if (!level) return "Low";
  if (level === "Low" || level === "Medium" || level === "High") return level;
  return level;
}

export function riskScore(it: RiskReportItem): number {
  if (typeof it.risk_score === "number") return it.risk_score;
  // legacy fallback
  // @ts-expect-error
  if (it.risk && typeof it.risk.p_calibrated === "number") return it.risk.p_calibrated;
  return 0;
}

export function riskLevel(it: RiskReportItem): RiskLevel | string {
  // @ts-expect-error
  const lvl = it.risk_level ?? it.risk?.level;
  return toLevel(lvl);
}

export function needsReview(it: RiskReportItem): boolean {
  if (typeof it.needs_review === "boolean") return it.needs_review;
  // @ts-expect-error
  if (typeof it.risk?.needs_review === "boolean") return it.risk.needs_review;
  return false;
}

export function levelColor(level: RiskLevel | string): string {
  if (level === "High") return "#ff5a7a";
  if (level === "Medium") return "#ffb454";
  return "#44d19e";
}

export function levelBadgeClass(level: RiskLevel | string): string {
  if (level === "High") return "badge badgeHigh";
  if (level === "Medium") return "badge badgeMid";
  return "badge badgeLow";
}

export function sortByRiskDesc(items: RiskReportItem[]): RiskReportItem[] {
  return [...items].sort((a, b) => riskScore(b) - riskScore(a));
}

export function countByLevel(items: RiskReportItem[]): Record<string, number> {
  const out: Record<string, number> = { High: 0, Medium: 0, Low: 0 };
  for (const it of items) {
    const lvl = String(riskLevel(it));
    out[lvl] = (out[lvl] || 0) + 1;
  }
  return out;
}

