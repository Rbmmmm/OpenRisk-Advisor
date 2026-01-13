#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Offline audit explanation: Integrated Gradients (Transformer risk head)")
    p.add_argument("--sources", required=True, help="Path to sources.yaml")
    p.add_argument("--model", default="configs/model.yaml", help="Path to model.yaml (for feature list)")
    p.add_argument("--db", default=None, help="Override sqlite db path")
    p.add_argument("--repo", required=True, help="Repo full name, e.g. X-lab2017/open-digger")
    p.add_argument("--as-of-month", required=True, help="YYYY-MM")
    p.add_argument("--model-version", default=None, help="Model version (default: latest transformer)")
    p.add_argument("--steps", type=int, default=32, help="IG steps")
    p.add_argument("--device", default="cpu", help="torch device")
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


def metric_id_map(conn: sqlite3.Connection) -> Dict[str, int]:
    return {str(r["name"]): int(r["id"]) for r in conn.execute("SELECT id, name FROM metrics")}


def repo_id(conn: sqlite3.Connection, full_name: str) -> Optional[int]:
    row = conn.execute("SELECT id FROM repos WHERE full_name=?", (full_name,)).fetchone()
    if not row:
        return None
    return int(row["id"])


def fetch_series_value(conn: sqlite3.Connection, repo_id_: int, metric_id: int, month: str) -> float:
    row = conn.execute(
        """
        SELECT value
        FROM time_series
        WHERE repo_id=? AND metric_id=? AND period_type='month' AND is_raw=0 AND period=?
        """,
        (repo_id_, metric_id, month),
    ).fetchone()
    if not row or row["value"] is None:
        return 0.0
    return float(row["value"])


def fetch_feature_value(conn: sqlite3.Connection, repo_id_: int, metric_id: int, feature: str, month: str) -> float:
    row = conn.execute(
        """
        SELECT value
        FROM derived_features
        WHERE repo_id=? AND metric_id=? AND period_type='month' AND feature=? AND period=?
        """,
        (repo_id_, metric_id, feature, month),
    ).fetchone()
    if not row or row["value"] is None:
        return 0.0
    return float(row["value"])


def latest_transformer_version(conn: sqlite3.Connection) -> Optional[str]:
    row = conn.execute(
        "SELECT model_version FROM ml_models WHERE model_type='transformer' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    if not row:
        return None
    return str(row["model_version"])


def artifact_path(conn: sqlite3.Connection, version: str) -> Optional[str]:
    row = conn.execute(
        "SELECT artifact_path FROM ml_models WHERE model_type='transformer' AND model_version=?",
        (version,),
    ).fetchone()
    if not row or not row["artifact_path"]:
        return None
    return str(row["artifact_path"])


def main() -> None:
    args = parse_args()

    try:
        import torch
        import torch.nn as nn
    except Exception as exc:  # noqa: BLE001
        print("[audit_explain_ig] torch is not installed. Install with: pip install -r requirements-ml.txt")
        raise SystemExit(1) from exc

    model_cfg = load_yaml(Path(args.model))
    task = model_cfg.get("task") or {}
    inputs = model_cfg.get("inputs") or {}
    models = model_cfg.get("models") or {}
    tcfg = models.get("transformer") or {}
    window = int(task.get("input_window_months", 18))
    metrics: List[str] = list(inputs.get("metrics") or [])
    derived_features: List[str] = list(inputs.get("derived_features") or [])

    d_per_metric = 1 + len(derived_features)
    d_in = len(metrics) * d_per_metric

    db_path = get_sqlite_path(Path(args.sources), args.db)
    conn = connect(db_path)
    try:
        rid = repo_id(conn, args.repo)
        if rid is None:
            raise SystemExit(f"unknown repo: {args.repo}")
        metric_ids = metric_id_map(conn)

        version = args.model_version or latest_transformer_version(conn)
        if not version:
            raise SystemExit("no transformer model found in ml_models; run scripts/train_transformer.py first")
        art = artifact_path(conn, version)
        if not art:
            raise SystemExit("transformer artifact_path missing in ml_models")
    finally:
        conn.close()

    ckpt = torch.load(art, map_location="cpu")
    mean = ckpt.get("feature_mean") or [0.0] * d_in
    std = ckpt.get("feature_std") or [1.0] * d_in
    step_feature_names = ckpt.get("step_feature_names") or []
    if not step_feature_names:
        # fallback mapping
        for m in metrics:
            step_feature_names.append(f"{m}.value")
            for f in derived_features:
                step_feature_names.append(f"{m}.{f}")

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
            t = x.size(1)
            return x + self.pe[:, :t, :]

    class Model(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            d_model = int(tcfg.get("d_model", 64))
            nhead = int(tcfg.get("nhead", 4))
            num_layers = int(tcfg.get("num_layers", 2))
            dropout = float(tcfg.get("dropout", 0.1))
            self.in_proj = nn.Linear(d_in, d_model)
            self.pos = PositionalEncoding(d_model, max_len=max(256, window + 8))
            enc_layer = nn.TransformerEncoderLayer(
                d_model=d_model, nhead=nhead, dropout=dropout, batch_first=True
            )
            self.encoder = nn.TransformerEncoder(enc_layer, num_layers=num_layers)
            self.risk_head = nn.Linear(d_model, 1)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            h = self.pos(self.in_proj(x))
            h = self.encoder(h)
            return self.risk_head(h[:, -1, :]).squeeze(1)

    device = torch.device(args.device)
    model = Model().to(device)
    model.load_state_dict(ckpt["state_dict"], strict=False)
    model.eval()

    # rebuild input sequence
    conn = connect(db_path)
    try:
        rid = repo_id(conn, args.repo)
        if rid is None:
            raise SystemExit(f"unknown repo: {args.repo}")
        metric_ids = metric_id_map(conn)
        months = month_sequence(args.as_of_month, window)

        seq: List[List[float]] = []
        for month in months:
            vec: List[float] = []
            for m in metrics:
                mid = metric_ids.get(m)
                if not mid:
                    vec.extend([0.0] * d_per_metric)
                    continue
                vec.append(fetch_series_value(conn, rid, mid, month))
                for f in derived_features:
                    vec.append(fetch_feature_value(conn, rid, mid, f, month))
            # standardize
            std_vec = []
            for i, v in enumerate(vec):
                s_ = float(std[i]) if i < len(std) else 1.0
                mu = float(mean[i]) if i < len(mean) else 0.0
                std_vec.append((float(v) - mu) / (s_ if s_ > 1e-12 else 1.0))
            seq.append(std_vec)
    finally:
        conn.close()

    x = torch.tensor([seq], dtype=torch.float32, device=device)
    baseline = torch.zeros_like(x)

    steps = max(8, int(args.steps))
    attributions = torch.zeros_like(x)
    for i in range(1, steps + 1):
        alpha = float(i) / float(steps)
        xi = (baseline + alpha * (x - baseline)).detach()
        xi.requires_grad_(True)
        y = model(xi).sum()
        model.zero_grad(set_to_none=True)
        y.backward()
        attributions += xi.grad.detach()
    attributions = (x - baseline) * attributions / float(steps)  # IG

    # Summarize by metric using last token attribution.
    contrib = attributions.detach().cpu()[0, -1, :].abs().tolist()
    metric_scores: Dict[str, float] = {m: 0.0 for m in metrics}
    for idx, name in enumerate(step_feature_names[: len(contrib)]):
        metric = name.split(".", 1)[0]
        metric_scores[metric] = metric_scores.get(metric, 0.0) + float(contrib[idx])
    top_metrics = sorted(metric_scores.items(), key=lambda x: x[1], reverse=True)[:10]

    out = {
        "repo": args.repo,
        "as_of_month": args.as_of_month,
        "model_version": version,
        "method": "integrated_gradients",
        "steps": steps,
        "top_metrics": [{"metric": m, "score": s} for m, s in top_metrics],
    }
    print(json.dumps(out, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

