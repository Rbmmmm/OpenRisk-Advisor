#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import yaml


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export RiskReport snapshot from risk_predictions")
    p.add_argument("--sources", required=True, help="Path to sources.yaml")
    p.add_argument("--db", default=None, help="Override sqlite db path")
    p.add_argument("--model-type", default="baseline", choices=["baseline", "transformer"])
    p.add_argument("--model-version", default=None, help="Override model version (default: latest for model-type)")
    p.add_argument("--as-of-month", default=None, help="Snapshot month YYYY-MM (default: latest in predictions)")
    p.add_argument("--output-json", default="docs/risk_report.json", help="JSON output path")
    p.add_argument("--output-md", default="docs/risk_report.md", help="Markdown output path")
    p.add_argument("--top-n", type=int, default=50, help="Top N risky repos in markdown")
    return p.parse_args()


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_sqlite_path(sources_path: Path, override: str | None) -> Path:
    if override:
        return Path(override)
    sources = load_yaml(sources_path)
    defaults = sources.get("defaults") or {}
    return Path(defaults.get("sqlite_path", "data/sqlite/opendigger.db"))


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def configured_repo_ids(conn: sqlite3.Connection, sources_path: Path) -> Dict[int, str]:
    sources = load_yaml(sources_path)
    enabled_names = {
        f"{r.get('org')}/{r.get('repo')}"
        for r in (sources.get("repos") or [])
        if isinstance(r, dict) and r.get("enabled", True)
    }
    rows = conn.execute("SELECT id, full_name FROM repos").fetchall()
    return {int(r["id"]): str(r["full_name"]) for r in rows if str(r["full_name"]) in enabled_names}


def latest_model_version(conn: sqlite3.Connection, model_type: str) -> Optional[str]:
    row = conn.execute(
        "SELECT model_version FROM ml_models WHERE model_type=? ORDER BY created_at DESC LIMIT 1",
        (model_type,),
    ).fetchone()
    if not row:
        return None
    return str(row["model_version"])


def latest_as_of_month(conn: sqlite3.Connection, model_type: str, model_version: str) -> Optional[str]:
    row = conn.execute(
        """
        SELECT MAX(as_of_month) AS m
        FROM risk_predictions
        WHERE model_type=? AND model_version=?
        """,
        (model_type, model_version),
    ).fetchone()
    if not row or not row["m"]:
        return None
    return str(row["m"])


def main() -> None:
    args = parse_args()
    sources_path = Path(args.sources)
    db_path = get_sqlite_path(sources_path, args.db)
    conn = connect(db_path)
    try:
        repo_map = configured_repo_ids(conn, sources_path)
        model_version = args.model_version or latest_model_version(conn, args.model_type)
        if not model_version:
            raise SystemExit("no ml_models found; run training first")
        as_of = args.as_of_month or latest_as_of_month(conn, args.model_type, model_version)
        if not as_of:
            raise SystemExit("no risk_predictions found; run training with --write-predictions")

        # Prefer structured reports when available (built by scripts/build_risk_explanations.py).
        has_reports = (
            conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='risk_reports'"
            ).fetchone()
            is not None
        )
        report_rows = []
        if has_reports:
            report_rows = conn.execute(
                """
                SELECT repo_id, report_json, created_at
                FROM risk_reports
                WHERE model_type=? AND model_version=? AND as_of_month=?
                """,
                (args.model_type, model_version, as_of),
            ).fetchall()

        if report_rows:
            rows = report_rows
            mode = "risk_reports"
        else:
            rows = conn.execute(
                """
                SELECT repo_id, as_of_month, p_calibrated, p_raw, risk_level, needs_review, forecast_json, explain_json, created_at
                FROM risk_predictions
                WHERE model_type=? AND model_version=? AND as_of_month=?
                """,
                (args.model_type, model_version, as_of),
            ).fetchall()
            mode = "risk_predictions"

        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        items: List[dict] = []
        for r in rows:
            rid = int(r["repo_id"])
            if rid not in repo_map:
                continue
            if mode == "risk_reports":
                try:
                    report = json.loads(r["report_json"]) if r["report_json"] else {}
                except Exception:  # noqa: BLE001
                    report = {}
                # ensure repo name is consistent with sources selection
                if isinstance(report, dict):
                    report["repo"] = repo_map[rid]
                items.append(report)
                continue

            # fallback: legacy export from risk_predictions
            try:
                forecast = json.loads(r["forecast_json"]) if r["forecast_json"] else {}
            except Exception:  # noqa: BLE001
                forecast = {}
            try:
                explain = json.loads(r["explain_json"]) if r["explain_json"] else {}
            except Exception:  # noqa: BLE001
                explain = {}
            items.append(
                {
                    "repo": repo_map[rid],
                    "as_of_month": str(r["as_of_month"]),
                    "risk_score": float(r["p_calibrated"]),
                    "risk_level": str(r["risk_level"]),
                    "needs_review": bool(int(r["needs_review"])),
                    "forecast": forecast,
                    "explain": explain,
                    "model": {"type": args.model_type, "version": model_version},
                    "created_at": str(r["created_at"]),
                }
            )

        out = {
            "generated_at": created_at,
            "as_of_month": as_of,
            "model": {"type": args.model_type, "version": model_version},
            "count": len(items),
            "items": sorted(
                items,
                key=lambda x: float(x.get("risk_score") or (x.get("risk") or {}).get("p_calibrated") or 0.0),
                reverse=True,
            ),
        }

        out_json = Path(args.output_json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(out, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

        out_md = Path(args.output_md)
        out_md.parent.mkdir(parents=True, exist_ok=True)
        lines: List[str] = []
        lines.append("# Risk Report\n")
        lines.append(f"- generated_at: {created_at}\n")
        lines.append(f"- as_of_month: {as_of}\n")
        lines.append(f"- model_type: {args.model_type}\n")
        lines.append(f"- model_version: {model_version}\n")
        lines.append(f"- repos: {len(items)}\n\n")

        top = out["items"][: max(1, int(args.top_n))]
        for it in top:
            lines.append(f"## {it.get('repo')}\n\n")
            lines.append(f"- risk_score: {float(it.get('risk_score') or 0.0):.3f}\n")
            lines.append(f"- risk_level: {it.get('risk_level')}\n")
            lines.append(f"- needs_review: {it.get('needs_review')}\n")
            if it.get("model_uncertainty"):
                mu = it["model_uncertainty"]
                if isinstance(mu, dict) and "forecast_uncertainty_ratio" in mu:
                    lines.append(f"- forecast_uncertainty_ratio: {float(mu['forecast_uncertainty_ratio']):.3f}\n")
            if it.get("data_quality"):
                dq = it["data_quality"]
                if isinstance(dq, dict):
                    if "avg_raw_ratio_win3" in dq:
                        lines.append(f"- avg_raw_ratio_win3: {float(dq['avg_raw_ratio_win3']):.3f}\n")
                    if "avg_coverage" in dq:
                        lines.append(f"- avg_coverage: {float(dq['avg_coverage']):.3f}\n")
                    if "missing_rate" in dq:
                        lines.append(f"- missing_rate: {float(dq['missing_rate']):.3f}\n")

            # Prefer main_signals evidence chain when present.
            ms = it.get("main_signals")
            if isinstance(ms, list) and ms:
                lines.append("- main_signals:\n")
                for s in ms[:5]:
                    lines.append(
                        f"  - {s.get('signal_id')} {s.get('signal_name')} ({s.get('dimension')}) "
                        f"strength={float(s.get('signal_strength') or 0.0):.2f} "
                        f"conf={float(s.get('signal_confidence') or 0.0):.2f}\n"
                    )
                    tw = s.get("time_window") if isinstance(s, dict) else None
                    if isinstance(tw, dict) and tw.get("t0"):
                        lines.append(
                            f"    - t0={tw.get('t0')} sustained_months={tw.get('sustained_months')}\n"
                        )
                    ab = s.get("is_abnormal") if isinstance(s, dict) else None
                    if isinstance(ab, dict):
                        if ab.get("zscore_12_last") is not None:
                            lines.append(f"    - zscore_12_last={float(ab['zscore_12_last']):.2f}\n")
                        if ab.get("percentile_rank_24m_last") is not None:
                            lines.append(
                                f"    - percentile_rank_24m_last={float(ab['percentile_rank_24m_last']):.2f}\n"
                            )
            else:
                explain = it.get("explain") or {}
                if explain.get("top_signals_lookback"):
                    lines.append("- top_signals_lookback:\n")
                    for s in explain["top_signals_lookback"]:
                        lines.append(
                            f"  - {s.get('signal_id')} ({s.get('dimension')}) score={s.get('score'):.1f}\n"
                        )
                if explain.get("top_metrics"):
                    lines.append("- top_metrics:\n")
                    for m in explain["top_metrics"]:
                        lines.append(f"  - {m.get('metric')}: {m.get('score'):.3f}\n")
            lines.append("\n")

        out_md.write_text("".join(lines), encoding="utf-8")
        print(f"[export_riskreports] wrote: {out_json} and {out_md}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
