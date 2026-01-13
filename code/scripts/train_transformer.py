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
from typing import Dict, List, Optional, Tuple

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train Temporal Transformer (forecast + risk) and write predictions")
    p.add_argument("--sources", required=True, help="Path to sources.yaml")
    p.add_argument("--model", default="configs/model.yaml", help="Path to model.yaml")
    p.add_argument("--db", default=None, help="Override sqlite db path")
    p.add_argument("--device", default="cpu", help="torch device, e.g. cpu/cuda")
    p.add_argument("--replace", action="store_true", help="Drop and rebuild ml_models/risk_predictions entries for transformer")
    p.add_argument("--write-predictions", action="store_true", help="Write risk_predictions for transformer")
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


def sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def fit_platt(logits: List[float], ys: List[int], ws: List[float], epochs: int = 200, lr: float = 0.05) -> Tuple[float, float]:
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


def ensure_tables(conn: sqlite3.Connection) -> None:
    # Shared tables created by scripts/train_predictor.py; ensure columns exist.
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
            artifact_path TEXT NOT NULL DEFAULT '',
            extra_json TEXT NOT NULL DEFAULT '{}',
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
            explain_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            UNIQUE(repo_id, as_of_month, model_version, model_type)
        )
        """
    )
    conn.commit()

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


def fetch_series_value(conn: sqlite3.Connection, repo_id: int, metric_id: int, month: str) -> Optional[float]:
    row = conn.execute(
        """
        SELECT value
        FROM time_series
        WHERE repo_id=? AND metric_id=? AND period_type='month' AND is_raw=0 AND period=?
        """,
        (repo_id, metric_id, month),
    ).fetchone()
    if not row:
        return None
    v = row["value"]
    return float(v) if v is not None else None


def fetch_feature_value(
    conn: sqlite3.Connection, repo_id: int, metric_id: int, feature: str, month: str
) -> Optional[float]:
    row = conn.execute(
        """
        SELECT value
        FROM derived_features
        WHERE repo_id=? AND metric_id=? AND period_type='month' AND feature=? AND period=?
        """,
        (repo_id, metric_id, feature, month),
    ).fetchone()
    if not row:
        return None
    v = row["value"]
    return float(v) if v is not None else None


def fetch_top_signals(conn: sqlite3.Connection, repo_id: int, start_month: str, end_month: str, top_n: int = 5) -> List[dict]:
    rows = conn.execute(
        """
        SELECT signal_id, severity, confidence, end_month, evidence_ref
        FROM signal_events
        WHERE repo_id=? AND end_month >= ? AND end_month <= ?
        """,
        (repo_id, start_month, end_month),
    ).fetchall()
    best: Dict[str, float] = {}
    dim: Dict[str, str] = {}
    for r in rows:
        sid = str(r["signal_id"])
        sev = float(r["severity"] or 0.0)
        conf = float(r["confidence"] or 0.0)
        score = sev * (0.5 + 0.5 * conf)
        if score > best.get(sid, 0.0):
            best[sid] = score
            try:
                ev = json.loads(r["evidence_ref"]) if r["evidence_ref"] else {}
                if isinstance(ev, dict) and isinstance(ev.get("dimension"), str):
                    dim[sid] = ev["dimension"]
            except Exception:  # noqa: BLE001
                pass
    out = []
    for sid, s in sorted(best.items(), key=lambda x: x[1], reverse=True)[:top_n]:
        out.append({"signal_id": sid, "score": s, "dimension": dim.get(sid)})
    return out


@dataclass(frozen=True)
class Cfg:
    version: str
    window: int
    horizon: int
    validation_months: int
    metrics: List[str]
    derived_features: List[str]
    target_metrics: List[str]
    quantiles: List[float]
    log1p_metrics: set[str]
    low: float
    high: float
    min_avg_raw_ratio: float
    max_uncertainty_ratio: float
    d_model: int
    nhead: int
    num_layers: int
    dropout: float
    epochs: int
    batch_size: int
    lr: float
    weight_decay: float
    save_dir: Path
    pretrained_path: Optional[Path]
    transformer_enabled: bool


def parse_cfg(model_cfg: dict) -> Cfg:
    task = model_cfg.get("task") or {}
    inputs = model_cfg.get("inputs") or {}
    forecast = model_cfg.get("forecast") or {}
    cal = model_cfg.get("calibration") or {}
    thresholds = model_cfg.get("thresholds") or {}
    needs = thresholds.get("needs_review") or {}
    models = model_cfg.get("models") or {}
    t = models.get("transformer") or {}

    return Cfg(
        version=str(model_cfg.get("version", "0.0.0")),
        window=int(task.get("input_window_months", 18)),
        horizon=int(task.get("horizon_months", 3)),
        validation_months=int(cal.get("validation_months", 6)),
        metrics=list(inputs.get("metrics") or []),
        derived_features=list(inputs.get("derived_features") or []),
        target_metrics=list(forecast.get("target_metrics") or []),
        quantiles=[float(q) for q in (forecast.get("quantiles") or [0.1, 0.5, 0.9])],
        log1p_metrics=set(forecast.get("log1p_metrics") or []),
        low=float(thresholds.get("low", 0.33)),
        high=float(thresholds.get("high", 0.66)),
        min_avg_raw_ratio=float(needs.get("min_avg_raw_ratio", 0.34)),
        max_uncertainty_ratio=float(needs.get("max_forecast_uncertainty_ratio", 2.0)),
        d_model=int(t.get("d_model", 64)),
        nhead=int(t.get("nhead", 4)),
        num_layers=int(t.get("num_layers", 2)),
        dropout=float(t.get("dropout", 0.1)),
        epochs=int(t.get("epochs", 10)),
        batch_size=int(t.get("batch_size", 64)),
        lr=float(t.get("lr", 5e-4)),
        weight_decay=float(t.get("weight_decay", 0.01)),
        save_dir=REPO_ROOT / str(t.get("save_dir", "data/ml")),
        pretrained_path=Path(t["pretrained_path"]) if t.get("pretrained_path") else None,
        transformer_enabled=bool(t.get("enabled", False)),
    )


def apply_log1p(metric: str, value: float, log1p_metrics: set[str]) -> float:
    if metric in log1p_metrics and value >= 0:
        return math.log1p(value)
    return value


def compute_uncertainty_ratio(forecast: dict) -> float:
    # forecast: {"metrics": {metric: {"q10": [...], "q50": [...], "q90": [...]}}}
    eps = 1e-6
    ratios: List[float] = []
    for _m, v in (forecast.get("metrics") or {}).items():
        q10 = v.get("q10") or []
        q50 = v.get("q50") or []
        q90 = v.get("q90") or []
        for a, b, c in zip(q10, q50, q90):
            denom = abs(float(b)) + eps
            ratios.append((float(c) - float(a)) / denom)
    return sum(ratios) / len(ratios) if ratios else 0.0


def main() -> None:
    args = parse_args()
    cfg_raw = load_yaml(Path(args.model))
    cfg = parse_cfg(cfg_raw)
    if not cfg.transformer_enabled:
        print("[train_transformer] configs/model.yaml: set models.transformer.enabled=true")
        return

    try:
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, Dataset
    except Exception as exc:  # noqa: BLE001
        print("[train_transformer] torch is not installed. Install with:")
        print("  pip install -r requirements-ml.txt")
        print(f"Original error: {exc}")
        raise SystemExit(1) from exc

    sources_path = Path(args.sources)
    db_path = get_sqlite_path(sources_path, args.db)
    conn = connect(db_path)
    try:
        ensure_tables(conn)
        metric_ids = metric_id_map(conn)
        repo_map = configured_repo_ids(conn, sources_path)
        max_m = latest_month(conn)
        if not max_m:
            raise SystemExit("no month data found in time_series")
        cutoff = int_to_month(month_to_int(max_m) - (cfg.validation_months - 1))

        labels = conn.execute(
            """
            SELECT repo_id, as_of_month, risk_soft, risk_binary, sample_weight
            FROM weak_labels
            WHERE horizon_months = ?
            """,
            (cfg.horizon,),
        ).fetchall()
        if not labels:
            raise SystemExit("weak_labels not found; run scripts/build_weak_labels.py first")

        d_per_metric = 1 + len(cfg.derived_features)
        d_in = len(cfg.metrics) * d_per_metric

        # Feature names for explainability mapping (per time-step vector).
        step_feature_names: List[str] = []
        for m in cfg.metrics:
            step_feature_names.append(f"{m}.value")
            for f in cfg.derived_features:
                step_feature_names.append(f"{m}.{f}")

        def build_step(repo_id: int, month: str) -> List[float]:
            vec: List[float] = []
            for m in cfg.metrics:
                mid = metric_ids.get(m)
                if not mid:
                    vec.extend([0.0] * d_per_metric)
                    continue
                v = fetch_series_value(conn, repo_id, mid, month)
                v = apply_log1p(m, float(v or 0.0), cfg.log1p_metrics)
                vec.append(v)
                for feat in cfg.derived_features:
                    fv = fetch_feature_value(conn, repo_id, mid, feat, month)
                    vec.append(float(fv or 0.0))
            return vec

        def build_forecast_targets(repo_id: int, as_of_month: str) -> Tuple[List[float], List[int]]:
            # Return (targets, mask) where mask=1 if target present (has raw value), else 0.
            base = month_to_int(as_of_month)
            targets: List[float] = []
            mask: List[int] = []
            for m in cfg.target_metrics:
                mid = metric_ids.get(m)
                for h in range(1, cfg.horizon + 1):
                    month = int_to_month(base + h)
                    y = None
                    if mid:
                        y = fetch_series_value(conn, repo_id, mid, month)
                    if y is None:
                        yv = 0.0
                        mask.append(0)
                    else:
                        yv = apply_log1p(m, float(y), cfg.log1p_metrics)
                        mask.append(1)
                    targets.append(float(yv))
            return targets, mask

        def avg_raw_ratio(repo_id: int, as_of_month: str) -> float:
            # Average raw_ratio_win3 across available metrics at as_of_month.
            vals: List[float] = []
            for m in cfg.metrics:
                if "raw_ratio_win3" not in cfg.derived_features:
                    break
                mid = metric_ids.get(m)
                if not mid:
                    continue
                v = fetch_feature_value(conn, repo_id, mid, "raw_ratio_win3", as_of_month)
                if v is not None:
                    vals.append(float(v))
            return sum(vals) / len(vals) if vals else 0.0

        # Build samples in-memory (MVP).
        # For large-scale runs, switch to a streaming dataset.
        samples: List[dict] = []
        for r in labels:
            repo_id = int(r["repo_id"])
            if repo_id not in repo_map:
                continue
            as_of = str(r["as_of_month"])
            months = month_sequence(as_of, cfg.window)
            x = [build_step(repo_id, m) for m in months]
            y_soft = float(r["risk_soft"] or 0.0)
            y_bin = int(r["risk_binary"] or 0)
            w = float(r["sample_weight"] or 1.0)
            y_future, y_mask = build_forecast_targets(repo_id, as_of)
            samples.append(
                {
                    "repo_id": repo_id,
                    "as_of": as_of,
                    "x": x,
                    "y_soft": y_soft,
                    "y_bin": y_bin,
                    "w": w,
                    "y_future": y_future,
                    "y_mask": y_mask,
                    "avg_raw_ratio": avg_raw_ratio(repo_id, as_of),
                }
            )

        if not samples:
            raise SystemExit("no samples available (check weak_labels and sources.yaml filters)")

        train = [s for s in samples if s["as_of"] < cutoff]
        val = [s for s in samples if s["as_of"] >= cutoff]
        if not train or not val:
            raise SystemExit("need both train and validation samples; adjust calibration.validation_months")

        # Standardize per-feature using train set across all time steps.
        mean = [0.0] * d_in
        var = [0.0] * d_in
        count = 0
        for s in train:
            for step in s["x"]:
                count += 1
                for i, v in enumerate(step):
                    mean[i] += v
        mean = [m / max(1, count) for m in mean]
        for s in train:
            for step in s["x"]:
                for i, v in enumerate(step):
                    dv = v - mean[i]
                    var[i] += dv * dv
        std = [math.sqrt(v / max(1, count)) for v in var]

        def standardize(step: List[float]) -> List[float]:
            out = []
            for i, v in enumerate(step):
                s_ = std[i]
                out.append((v - mean[i]) / (s_ if s_ > 1e-12 else 1.0))
            return out

        for s in samples:
            s["x"] = [standardize(step) for step in s["x"]]

        class DS(Dataset):
            def __init__(self, items: List[dict]) -> None:
                self.items = items

            def __len__(self) -> int:
                return len(self.items)

            def __getitem__(self, idx: int):
                it = self.items[idx]
                return (
                    torch.tensor(it["x"], dtype=torch.float32),
                    torch.tensor([it["y_soft"]], dtype=torch.float32),
                    torch.tensor([it["y_bin"]], dtype=torch.float32),
                    torch.tensor([it["w"]], dtype=torch.float32),
                    torch.tensor(it["y_future"], dtype=torch.float32),
                    torch.tensor(it["y_mask"], dtype=torch.float32),
                    torch.tensor([it["avg_raw_ratio"]], dtype=torch.float32),
                    it["repo_id"],
                    it["as_of"],
                )

        quantiles = cfg.quantiles
        q10_idx = quantiles.index(0.1) if 0.1 in quantiles else 0
        q50_idx = quantiles.index(0.5) if 0.5 in quantiles else len(quantiles) // 2
        q90_idx = quantiles.index(0.9) if 0.9 in quantiles else len(quantiles) - 1

        class PositionalEncoding(nn.Module):
            def __init__(self, d_model: int, max_len: int = 256) -> None:
                super().__init__()
                pe = torch.zeros(max_len, d_model)
                position = torch.arange(0, max_len, dtype=torch.float32).unsqueeze(1)
                div_term = torch.exp(
                    torch.arange(0, d_model, 2, dtype=torch.float32) * (-math.log(10000.0) / d_model)
                )
                pe[:, 0::2] = torch.sin(position * div_term)
                pe[:, 1::2] = torch.cos(position * div_term)
                self.register_buffer("pe", pe.unsqueeze(0), persistent=False)

            def forward(self, x: torch.Tensor) -> torch.Tensor:
                # x: (B, T, D)
                t = x.size(1)
                return x + self.pe[:, :t, :]

        def pinball_loss(pred: torch.Tensor, target: torch.Tensor, q: float, mask: torch.Tensor) -> torch.Tensor:
            # pred/target: (B, N); mask: (B, N) in {0,1}
            diff = target - pred
            loss = torch.maximum(q * diff, (q - 1.0) * diff) * mask
            denom = mask.sum().clamp_min(1.0)
            return loss.sum() / denom

        class Model(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.in_proj = nn.Linear(d_in, cfg.d_model)
                self.pos = PositionalEncoding(cfg.d_model, max_len=max(256, cfg.window + 8))
                enc_layer = nn.TransformerEncoderLayer(
                    d_model=cfg.d_model, nhead=cfg.nhead, dropout=cfg.dropout, batch_first=True
                )
                self.encoder = nn.TransformerEncoder(enc_layer, num_layers=cfg.num_layers)
                self.risk_head = nn.Linear(cfg.d_model, 1)
                out_dim = len(cfg.target_metrics) * cfg.horizon * len(quantiles)
                self.forecast_head = nn.Linear(cfg.d_model, out_dim)

            def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
                # x: (B, T, d_in)
                h = self.pos(self.in_proj(x))
                h = self.encoder(h)
                h_last = h[:, -1, :]
                risk_logit = self.risk_head(h_last)  # (B,1)
                forecast = self.forecast_head(h_last)  # (B, out_dim)
                return risk_logit, forecast, h_last

        device = torch.device(args.device)
        model = Model().to(device)
        if cfg.pretrained_path and cfg.pretrained_path.exists():
            ckpt = torch.load(cfg.pretrained_path, map_location="cpu")
            state = ckpt.get("state_dict") if isinstance(ckpt, dict) else None
            if state:
                missing, unexpected = model.load_state_dict(state, strict=False)
                print(f"[train_transformer] loaded pretrained: missing={len(missing)} unexpected={len(unexpected)}")

        opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
        bce = torch.nn.BCEWithLogitsLoss(reduction="none")

        train_loader = DataLoader(DS(train), batch_size=cfg.batch_size, shuffle=True)
        val_loader = DataLoader(DS(val), batch_size=cfg.batch_size, shuffle=False)

        target_len = len(cfg.target_metrics) * cfg.horizon
        out_dim = target_len * len(quantiles)

        def reshape_forecast(out: torch.Tensor) -> torch.Tensor:
            return out.view(-1, len(quantiles), target_len)  # (B,Q,N)

        for epoch in range(cfg.epochs):
            model.train()
            loss_sum = 0.0
            n_batches = 0
            for x, y_soft, _y_bin, w, y_future, y_mask, *_rest in train_loader:
                x = x.to(device)
                y_soft = y_soft.to(device)
                w = w.to(device)
                y_future = y_future.to(device)
                y_mask = y_mask.to(device)

                opt.zero_grad()
                risk_logit, forecast, _ = model(x)
                # risk loss: BCE to soft label, weighted
                loss_risk = (bce(risk_logit, y_soft) * w).mean()

                # forecast loss: quantiles pinball on log1p targets
                f = reshape_forecast(forecast)  # (B,Q,N)
                loss_f = 0.0
                for qi, q in enumerate(quantiles):
                    pred_q = f[:, qi, :]
                    loss_f = loss_f + pinball_loss(pred_q, y_future, q, y_mask)
                loss = loss_risk + loss_f
                loss.backward()
                opt.step()
                loss_sum += float(loss.detach().cpu().item())
                n_batches += 1
            print(f"[train_transformer] epoch={epoch+1} loss={loss_sum/max(1,n_batches):.6f}")

        # Calibration on validation: fit Platt on risk logits vs binary label.
        model.eval()
        val_logits: List[float] = []
        val_y: List[int] = []
        val_w: List[float] = []
        with torch.no_grad():
            for x, _y_soft, y_bin, w, *_rest in val_loader:
                x = x.to(device)
                risk_logit, _, _ = model(x)
                for logit, yb, ww in zip(risk_logit.squeeze(1).cpu().tolist(), y_bin.squeeze(1).tolist(), w.squeeze(1).tolist()):
                    val_logits.append(float(logit))
                    val_y.append(int(yb))
                    val_w.append(float(ww))

        a, b = fit_platt(val_logits, val_y, val_w)

        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        cfg.save_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = cfg.save_dir / f"transformer_{cfg.version}_{created_at.replace(':','')}.pt"
        torch.save(
            {
                "state_dict": model.state_dict(),
                "config": cfg_raw,
                "feature_mean": mean,
                "feature_std": std,
                "step_feature_names": step_feature_names,
                "platt": {"a": a, "b": b, "cutoff": cutoff},
            },
            artifact_path,
        )
        print(f"[train_transformer] saved model: {artifact_path} platt=(a={a:.3f}, b={b:.3f}) cutoff={cutoff}")

        if args.replace:
            conn.execute("DELETE FROM ml_models WHERE model_version=? AND model_type='transformer'", (cfg.version,))
            conn.execute(
                "DELETE FROM risk_predictions WHERE model_version=? AND model_type='transformer'", (cfg.version,)
            )
            conn.commit()

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
                cfg.version,
                "transformer",
                created_at,
                json.dumps(step_feature_names, ensure_ascii=True),
                json.dumps(mean, ensure_ascii=True),
                json.dumps(std, ensure_ascii=True),
                "{}",  # no linear weights
                float(a),
                float(b),
                json.dumps(cfg.metrics, ensure_ascii=True),
                json.dumps(cfg.derived_features, ensure_ascii=True),
                json.dumps({"window": cfg.window, "horizon": cfg.horizon, "cutoff": cutoff}, ensure_ascii=True),
                str(artifact_path),
                json.dumps({"quantiles": quantiles, "target_metrics": cfg.target_metrics}, ensure_ascii=True),
            ),
        )
        conn.commit()

        if not args.write_predictions:
            return

        # Write predictions for all samples.
        rows_to_insert = []
        for s in samples:
            repo_id = int(s["repo_id"])
            as_of = str(s["as_of"])
            x = torch.tensor([s["x"]], dtype=torch.float32, device=device)
            x.requires_grad_(True)
            risk_logit, forecast_raw, _h = model(x)
            logit = float(risk_logit.squeeze(0).squeeze(0).detach().cpu().item())
            p_raw = sigmoid(logit)
            p_cal = sigmoid(a * logit + b)

            # Forecast quantiles
            f = reshape_forecast(forecast_raw).detach().cpu()[0]  # (Q,N)
            # split N by metric/horizon
            out = {"horizon_months": cfg.horizon, "metrics": {}, "quantiles": quantiles}
            for mi, m in enumerate(cfg.target_metrics):
                q10 = []
                q50 = []
                q90 = []
                for h in range(cfg.horizon):
                    idx = mi * cfg.horizon + h
                    q10.append(float(f[q10_idx, idx].item()))
                    q50.append(float(f[q50_idx, idx].item()))
                    q90.append(float(f[q90_idx, idx].item()))
                out["metrics"][m] = {"q10": q10, "q50": q50, "q90": q90}

            unc_ratio = compute_uncertainty_ratio(out)
            avg_rr = float(s.get("avg_raw_ratio") or 0.0)
            needs_review = 1 if (avg_rr < cfg.min_avg_raw_ratio or unc_ratio > cfg.max_uncertainty_ratio) else 0
            level = risk_level(p_cal, cfg.low, cfg.high)

            # Online explanation: gradient*input on last time-step, aggregated by metric.
            model.zero_grad(set_to_none=True)
            score = risk_logit.squeeze()
            score.backward()
            grad = x.grad.detach().cpu()[0, -1, :]  # (d_in,)
            inp = x.detach().cpu()[0, -1, :]
            contrib = (grad * inp).abs().tolist()
            metric_scores: Dict[str, float] = {m: 0.0 for m in cfg.metrics}
            for idx, name in enumerate(step_feature_names):
                m = name.split(".", 1)[0]
                metric_scores[m] = metric_scores.get(m, 0.0) + float(contrib[idx])
            top_metrics = [
                {"metric": m, "score": s}
                for m, s in sorted(metric_scores.items(), key=lambda x: x[1], reverse=True)[:8]
            ]

            start_lookback = month_sequence(as_of, cfg.window)[0]
            top_signals = fetch_top_signals(conn, repo_id, start_lookback, as_of, top_n=5)

            explain = {
                "method": "grad_x_input_last_token",
                "top_metrics": top_metrics,
                "top_signals_lookback": top_signals,
                "avg_raw_ratio_win3": avg_rr,
                "forecast_uncertainty_ratio": unc_ratio,
            }

            rows_to_insert.append(
                (
                    repo_id,
                    as_of,
                    cfg.version,
                    "transformer",
                    float(p_raw),
                    float(p_cal),
                    level,
                    int(needs_review),
                    json.dumps(out, ensure_ascii=True),
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
        print(f"[train_transformer] wrote risk_predictions rows={len(rows_to_insert)} model={cfg.version}/transformer")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

