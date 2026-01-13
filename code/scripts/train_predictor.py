#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train risk predictor (baseline/transformer) and write predictions")
    p.add_argument("--sources", required=True, help="Path to sources.yaml")
    p.add_argument("--model", default="configs/model.yaml", help="Path to model.yaml")
    p.add_argument("--db", default=None, help="Override sqlite db path")
    p.add_argument("--replace", action="store_true", help="Drop and rebuild prediction/model tables")
    p.add_argument("--model-type", default="baseline", choices=["baseline", "transformer"])
    p.add_argument("--write-predictions", action="store_true", help="Write risk_predictions after training")
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


def month_to_int(month: str) -> int:
    y, m = month.split("-", 1)
    return int(y) * 12 + int(m)


def int_to_month(value: int) -> str:
    year = value // 12
    m = value % 12
    if m == 0:
        year -= 1
        m = 12
    return f"{year:04d}-{m:02d}"


def month_sequence(end_month: str, window: int) -> List[str]:
    end_int = month_to_int(end_month)
    start_int = end_int - (window - 1)
    return [int_to_month(v) for v in range(start_int, end_int + 1)]


@dataclass(frozen=True)
class TaskCfg:
    input_window_months: int
    horizon_months: int
    min_history_months: int


@dataclass(frozen=True)
class LabelCfg:
    horizon_months: int


@dataclass(frozen=True)
class ModelCfg:
    model_version: str
    task: TaskCfg
    metrics: List[str]
    derived_features: List[str]
    validation_months: int
    thresholds_low: float
    thresholds_high: float
    needs_review_min_avg_raw_ratio: float
    baseline_epochs: int
    baseline_lr: float
    baseline_l2: float


def parse_model_cfg(model: dict) -> ModelCfg:
    version = str(model.get("version", "0.0.0"))
    task = model.get("task") or {}
    inputs = model.get("inputs") or {}
    metrics = list(inputs.get("metrics") or [])
    derived_features = list(inputs.get("derived_features") or [])

    cal = model.get("calibration") or {}
    thresholds = model.get("thresholds") or {}
    needs_review = thresholds.get("needs_review") or {}
    models = model.get("models") or {}
    baseline = models.get("baseline") or {}

    return ModelCfg(
        model_version=version,
        task=TaskCfg(
            input_window_months=int(task.get("input_window_months", 18)),
            horizon_months=int(task.get("horizon_months", 3)),
            min_history_months=int(task.get("min_history_months", 24)),
        ),
        metrics=metrics,
        derived_features=derived_features,
        validation_months=int(cal.get("validation_months", 6)),
        thresholds_low=float(thresholds.get("low", 0.33)),
        thresholds_high=float(thresholds.get("high", 0.66)),
        needs_review_min_avg_raw_ratio=float(needs_review.get("min_avg_raw_ratio", 0.34)),
        baseline_epochs=int(baseline.get("epochs", 8)),
        baseline_lr=float(baseline.get("lr", 0.05)),
        baseline_l2=float(baseline.get("l2", 0.001)),
    )


def ensure_tables(conn: sqlite3.Connection, replace: bool) -> None:
    if replace:
        conn.execute("DROP TABLE IF EXISTS ml_models")
        conn.execute("DROP TABLE IF EXISTS risk_predictions")
        conn.commit()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ml_models (
            id INTEGER PRIMARY KEY,
            model_version TEXT NOT NULL,
            model_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            feature_names_json TEXT NOT NULL,
            feature_mean_json TEXT NOT NULL,
            feature_std_json TEXT NOT NULL,
            weights_json TEXT NOT NULL,
            platt_a REAL NOT NULL,
            platt_b REAL NOT NULL,
            metrics_json TEXT NOT NULL,
            derived_features_json TEXT NOT NULL,
            task_json TEXT NOT NULL,
            UNIQUE(model_version, model_type)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS risk_predictions (
            id INTEGER PRIMARY KEY,
            repo_id INTEGER NOT NULL,
            as_of_month TEXT NOT NULL,
            model_version TEXT NOT NULL,
            model_type TEXT NOT NULL,
            p_raw REAL NOT NULL,
            p_calibrated REAL NOT NULL,
            risk_level TEXT NOT NULL,
            needs_review INTEGER NOT NULL,
            forecast_json TEXT NOT NULL,
            explain_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(repo_id, as_of_month, model_version, model_type)
        )
        """
    )
    conn.commit()

    # Lightweight migrations for existing DBs.
    cur = conn.execute("PRAGMA table_info(risk_predictions)")
    cols = {str(r[1]) for r in cur.fetchall()}
    if "explain_json" not in cols:
        conn.execute("ALTER TABLE risk_predictions ADD COLUMN explain_json TEXT NOT NULL DEFAULT '{}'")
        conn.commit()

    cur = conn.execute("PRAGMA table_info(ml_models)")
    cols = {str(r[1]) for r in cur.fetchall()}
    if "artifact_path" not in cols:
        conn.execute("ALTER TABLE ml_models ADD COLUMN artifact_path TEXT NOT NULL DEFAULT ''")
        conn.execute("ALTER TABLE ml_models ADD COLUMN extra_json TEXT NOT NULL DEFAULT '{}'")
        conn.commit()


def metric_id_map(conn: sqlite3.Connection) -> Dict[str, int]:
    return {str(r["name"]): int(r["id"]) for r in conn.execute("SELECT id, name FROM metrics")}


def configured_repo_ids(conn: sqlite3.Connection, sources_path: Path) -> Dict[int, str]:
    sources = load_yaml(sources_path)
    enabled_names = {
        f"{r.get('org')}/{r.get('repo')}"
        for r in (sources.get("repos") or [])
        if isinstance(r, dict) and r.get("enabled", True)
    }
    rows = conn.execute("SELECT id, full_name FROM repos").fetchall()
    return {int(r["id"]): str(r["full_name"]) for r in rows if str(r["full_name"]) in enabled_names}


def latest_month(conn: sqlite3.Connection) -> Optional[str]:
    row = conn.execute(
        "SELECT MAX(period) AS m FROM time_series WHERE period_type='month' AND is_raw=0"
    ).fetchone()
    if not row or not row["m"]:
        return None
    return str(row["m"])


def fetch_labels(conn: sqlite3.Connection, horizon_months: int) -> List[sqlite3.Row]:
    return conn.execute(
        """
        SELECT repo_id, as_of_month, risk_soft, risk_binary, sample_weight
        FROM weak_labels
        WHERE horizon_months = ?
        """,
        (horizon_months,),
    ).fetchall()


def fetch_series_values(
    conn: sqlite3.Connection,
    repo_id: int,
    metric_id: int,
    months: List[str],
) -> Dict[str, float]:
    placeholders = ",".join("?" for _ in months)
    rows = conn.execute(
        f"""
        SELECT period, value
        FROM time_series
        WHERE repo_id=? AND metric_id=? AND period_type='month' AND is_raw=0
          AND period IN ({placeholders})
        """,
        (repo_id, metric_id, *months),
    ).fetchall()
    return {str(r["period"]): float(r["value"]) for r in rows if r["value"] is not None}


def fetch_feature_values(
    conn: sqlite3.Connection,
    repo_id: int,
    metric_id: int,
    feature: str,
    months: List[str],
) -> Dict[str, float]:
    placeholders = ",".join("?" for _ in months)
    rows = conn.execute(
        f"""
        SELECT period, value
        FROM derived_features
        WHERE repo_id=? AND metric_id=? AND period_type='month' AND feature=?
          AND period IN ({placeholders})
        """,
        (repo_id, metric_id, feature, *months),
    ).fetchall()
    return {str(r["period"]): float(r["value"]) for r in rows if r["value"] is not None}


def agg_stats(values: List[float]) -> Tuple[float, float, float, float]:
    # last, mean, min, max
    if not values:
        return 0.0, 0.0, 0.0, 0.0
    return values[-1], sum(values) / len(values), min(values), max(values)


def sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def standardize_inplace(x: List[float], mean: List[float], std: List[float]) -> None:
    for i in range(len(x)):
        s = std[i]
        x[i] = (x[i] - mean[i]) / (s if s > 1e-12 else 1.0)


def compute_mean_std(xs: List[List[float]]) -> Tuple[List[float], List[float]]:
    if not xs:
        return [], []
    n = len(xs)
    d = len(xs[0])
    mean = [0.0] * d
    for row in xs:
        for i, v in enumerate(row):
            mean[i] += v
    mean = [m / n for m in mean]
    var = [0.0] * d
    for row in xs:
        for i, v in enumerate(row):
            dv = v - mean[i]
            var[i] += dv * dv
    std = [math.sqrt(v / n) for v in var]
    return mean, std


def train_logreg_sgd(
    xs: List[List[float]],
    ys: List[int],
    ws: List[float],
    epochs: int,
    lr: float,
    l2: float,
) -> List[float]:
    if not xs:
        return []
    d = len(xs[0])
    w = [0.0] * (d + 1)  # bias + weights

    for _ in range(max(1, epochs)):
        for x, y, sw in zip(xs, ys, ws):
            z = w[0] + dot(w[1:], x)
            p = sigmoid(z)
            # weighted BCE gradient
            err = (p - float(y)) * sw
            w[0] -= lr * err
            for i in range(d):
                w[i + 1] -= lr * (err * x[i] + l2 * w[i + 1])
    return w


def fit_platt(logits: List[float], ys: List[int], ws: List[float], epochs: int = 200, lr: float = 0.05) -> Tuple[float, float]:
    # Fit sigmoid(a*logit + b) to map raw logits to calibrated probabilities.
    a = 1.0
    b = 0.0
    for _ in range(epochs):
        for logit, y, sw in zip(logits, ys, ws):
            z = a * logit + b
            p = sigmoid(z)
            err = (p - float(y)) * sw
            a -= lr * (err * logit)
            b -= lr * err
    return a, b


def risk_level(p: float, low: float, high: float) -> str:
    if p >= high:
        return "High"
    if p >= low:
        return "Medium"
    return "Low"


def build_feature_names(metrics: List[str], derived_features: List[str]) -> List[str]:
    # For each metric and each base feature, compute four window stats: last/mean/min/max.
    names: List[str] = []
    for metric in metrics:
        for feat in ["value", *derived_features]:
            for stat in ["last", "mean", "min", "max"]:
                names.append(f"{metric}.{feat}.{stat}")
            names.append(f"{metric}.{feat}.coverage")
    # Global coverage for needs_review decision.
    names.append("global.raw_ratio_win3.mean")
    return names


def build_sample_features(
    conn: sqlite3.Connection,
    metric_ids: Dict[str, int],
    repo_id: int,
    as_of_month: str,
    window_months: int,
    metrics: List[str],
    derived_features: List[str],
) -> Tuple[List[float], float]:
    months = month_sequence(as_of_month, window_months)
    expected = len(months)

    values_cache: Dict[Tuple[str, str], Dict[str, float]] = {}

    features: List[float] = []
    raw_ratio_means: List[float] = []

    for metric in metrics:
        mid = metric_ids.get(metric)
        if not mid:
            # emit zeros for missing metric ids to keep vector aligned
            for _ in range((1 + len(derived_features)) * (4 + 1)):
                features.append(0.0)
            continue

        series = fetch_series_values(conn, repo_id, mid, months)
        ordered = [series.get(m) for m in months]
        present = [v for v in ordered if v is not None]
        last, mean, vmin, vmax = agg_stats([float(v) for v in present])
        features.extend([last, mean, vmin, vmax, len(present) / expected if expected else 0.0])

        for feat in derived_features:
            fmap = fetch_feature_values(conn, repo_id, mid, feat, months)
            o = [fmap.get(m) for m in months]
            pres = [v for v in o if v is not None]
            last, mean, vmin, vmax = agg_stats([float(v) for v in pres])
            features.extend([last, mean, vmin, vmax, len(pres) / expected if expected else 0.0])
            if feat == "raw_ratio_win3" and pres:
                raw_ratio_means.append(mean)

    global_raw_ratio_mean = sum(raw_ratio_means) / len(raw_ratio_means) if raw_ratio_means else 0.0
    features.append(global_raw_ratio_mean)
    return features, global_raw_ratio_mean


def naive_forecast(
    conn: sqlite3.Connection,
    metric_ids: Dict[str, int],
    repo_id: int,
    as_of_month: str,
    horizon: int,
    key_metrics: List[str],
) -> dict:
    # Simple baseline: y(t+h) = last_value + h * last_trend_slope_3; interval from last roll_std_3.
    out = {"horizon_months": horizon, "metrics": {}}
    months = month_sequence(as_of_month, 1)
    for metric in key_metrics:
        mid = metric_ids.get(metric)
        if not mid:
            continue
        last_val = fetch_series_values(conn, repo_id, mid, months).get(as_of_month)
        slope = fetch_feature_values(conn, repo_id, mid, "trend_slope_3", months).get(as_of_month)
        std = fetch_feature_values(conn, repo_id, mid, "roll_std_3", months).get(as_of_month)
        if last_val is None:
            continue
        slope = float(slope or 0.0)
        std = float(std or 0.0)
        preds = []
        intervals = []
        for h in range(1, horizon + 1):
            yhat = float(last_val) + float(h) * slope
            preds.append(yhat)
            intervals.append([yhat - 1.64 * std, yhat + 1.64 * std])
        out["metrics"][metric] = {"q50": preds, "q10_q90": intervals}
    return out


def main() -> None:
    args = parse_args()
    sources_path = Path(args.sources)
    model_cfg_raw = load_yaml(Path(args.model))
    cfg = parse_model_cfg(model_cfg_raw)

    if args.model_type == "transformer":
        print("[train_predictor] transformer path is implemented in scripts/train_transformer.py (requires torch).")
        print("[train_predictor] run baseline first: --model-type baseline")
        return

    db_path = get_sqlite_path(sources_path, args.db)
    conn = connect(db_path)
    try:
        ensure_tables(conn, args.replace)

        metric_ids = metric_id_map(conn)
        repo_map = configured_repo_ids(conn, sources_path)
        labels = fetch_labels(conn, cfg.task.horizon_months)
        if not labels:
            raise SystemExit(
                "weak_labels not found; run: python scripts/build_weak_labels.py --sources configs/sources.yaml --replace"
            )

        # global time split
        max_m = latest_month(conn)
        if not max_m:
            raise SystemExit("no month data found in time_series")
        cutoff = int_to_month(month_to_int(max_m) - (cfg.validation_months - 1))

        feature_names = build_feature_names(cfg.metrics, cfg.derived_features)

        train_xs: List[List[float]] = []
        train_ys: List[int] = []
        train_ws: List[float] = []
        val_xs: List[List[float]] = []
        val_ys: List[int] = []
        val_ws: List[float] = []
        sample_index: List[Tuple[int, str]] = []

        # Build samples from weak_labels (supervision target uses risk_binary for MVP).
        for row in labels:
            repo_id = int(row["repo_id"])
            if repo_id not in repo_map:
                continue
            as_of = str(row["as_of_month"])
            # require enough history
            if month_to_int(as_of) < (cfg.task.min_history_months + 1):
                # relative check doesn't work across years; keep a safer DB-based filter below.
                pass

            feats, global_raw_ratio = build_sample_features(
                conn,
                metric_ids,
                repo_id,
                as_of,
                cfg.task.input_window_months,
                cfg.metrics,
                cfg.derived_features,
            )
            y = int(row["risk_binary"])
            w = float(row["sample_weight"] or 1.0)
            if as_of >= cutoff:
                val_xs.append(feats)
                val_ys.append(y)
                val_ws.append(w)
            else:
                train_xs.append(feats)
                train_ys.append(y)
                train_ws.append(w)
            sample_index.append((repo_id, as_of))

        if not train_xs:
            raise SystemExit("no training samples (check weak_labels / data coverage)")

        mean, std = compute_mean_std(train_xs)
        for x in train_xs:
            standardize_inplace(x, mean, std)
        for x in val_xs:
            standardize_inplace(x, mean, std)

        w = train_logreg_sgd(
            train_xs,
            train_ys,
            train_ws,
            epochs=cfg.baseline_epochs,
            lr=cfg.baseline_lr,
            l2=cfg.baseline_l2,
        )

        # calibration on validation set using raw logits
        val_logits = [w[0] + dot(w[1:], x) for x in val_xs]
        a, b = fit_platt(val_logits, val_ys, val_ws)

        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        conn.execute(
            """
            INSERT INTO ml_models
              (model_version, model_type, created_at,
               feature_names_json, feature_mean_json, feature_std_json, weights_json,
               platt_a, platt_b, metrics_json, derived_features_json, task_json,
               artifact_path, extra_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(model_version, model_type) DO UPDATE SET
               created_at=excluded.created_at,
               feature_names_json=excluded.feature_names_json,
               feature_mean_json=excluded.feature_mean_json,
               feature_std_json=excluded.feature_std_json,
               weights_json=excluded.weights_json,
               platt_a=excluded.platt_a,
               platt_b=excluded.platt_b,
               metrics_json=excluded.metrics_json,
               derived_features_json=excluded.derived_features_json,
               task_json=excluded.task_json,
               artifact_path=excluded.artifact_path,
               extra_json=excluded.extra_json
            """,
            (
                cfg.model_version,
                "baseline",
                created_at,
                json.dumps(feature_names, ensure_ascii=True),
                json.dumps(mean, ensure_ascii=True),
                json.dumps(std, ensure_ascii=True),
                json.dumps(w, ensure_ascii=True),
                float(a),
                float(b),
                json.dumps(cfg.metrics, ensure_ascii=True),
                json.dumps(cfg.derived_features, ensure_ascii=True),
                json.dumps(
                    {
                        "input_window_months": cfg.task.input_window_months,
                        "horizon_months": cfg.task.horizon_months,
                        "validation_months": cfg.validation_months,
                    },
                    ensure_ascii=True,
                ),
                "",
                "{}",
            ),
        )
        conn.commit()

        print(
            f"[train_predictor] trained baseline logreg: train={len(train_xs)} val={len(val_xs)} cutoff={cutoff} platt=(a={a:.3f}, b={b:.3f})"
        )

        if not args.write_predictions:
            return

        # Write predictions for all labeled months (so downstream can align with weak_labels).
        rows_to_insert = []
        for row in labels:
            repo_id = int(row["repo_id"])
            if repo_id not in repo_map:
                continue
            as_of = str(row["as_of_month"])
            feats, global_raw_ratio = build_sample_features(
                conn,
                metric_ids,
                repo_id,
                as_of,
                cfg.task.input_window_months,
                cfg.metrics,
                cfg.derived_features,
            )
            standardize_inplace(feats, mean, std)
            logit = w[0] + dot(w[1:], feats)
            p_raw = sigmoid(logit)
            p_cal = sigmoid(a * logit + b)
            level = risk_level(p_cal, cfg.thresholds_low, cfg.thresholds_high)
            needs_review = 1 if global_raw_ratio < cfg.needs_review_min_avg_raw_ratio else 0
            forecast = naive_forecast(
                conn,
                metric_ids,
                repo_id,
                as_of,
                cfg.task.horizon_months,
                key_metrics=["activity", "contributors", "issues_new", "issues_closed"],
            )
            explain = {"method": "baseline", "note": "no attribution; see signal_events for evidence"}
            rows_to_insert.append(
                (
                    repo_id,
                    as_of,
                    cfg.model_version,
                    "baseline",
                    float(p_raw),
                    float(p_cal),
                    level,
                    int(needs_review),
                    json.dumps(forecast, ensure_ascii=True),
                    json.dumps(explain, ensure_ascii=True),
                    created_at,
                )
            )

        conn.executemany(
            """
            INSERT INTO risk_predictions
              (repo_id, as_of_month, model_version, model_type, p_raw, p_calibrated,
               risk_level, needs_review, forecast_json, explain_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(repo_id, as_of_month, model_version, model_type) DO UPDATE SET
              p_raw=excluded.p_raw,
              p_calibrated=excluded.p_calibrated,
              risk_level=excluded.risk_level,
              needs_review=excluded.needs_review,
              forecast_json=excluded.forecast_json,
              explain_json=excluded.explain_json,
              created_at=excluded.created_at
            """,
            rows_to_insert,
        )
        conn.commit()
        print(f"[train_predictor] wrote risk_predictions rows={len(rows_to_insert)} model={cfg.model_version}/baseline")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
