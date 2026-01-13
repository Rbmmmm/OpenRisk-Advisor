#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import random
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Masked time-series modeling pretraining (Transformer encoder)")
    p.add_argument("--sources", required=True, help="Path to sources.yaml")
    p.add_argument("--model", default="configs/model.yaml", help="Path to model.yaml")
    p.add_argument("--db", default=None, help="Override sqlite db path")
    p.add_argument("--device", default="cpu", help="torch device")
    p.add_argument("--mask-ratio", type=float, default=0.15, help="Mask ratio for inputs")
    p.add_argument("--epochs", type=int, default=5, help="Pretrain epochs")
    p.add_argument("--batch-size", type=int, default=64, help="Batch size")
    p.add_argument("--lr", type=float, default=5e-4, help="Learning rate")
    p.add_argument("--max-samples", type=int, default=20000, help="Max sequences to use")
    p.add_argument("--seed", type=int, default=7, help="Random seed")
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
class Cfg:
    version: str
    window: int
    metrics: List[str]
    derived_features: List[str]
    d_model: int
    nhead: int
    num_layers: int
    dropout: float
    save_dir: Path


def parse_cfg(model_cfg: dict) -> Cfg:
    task = model_cfg.get("task") or {}
    inputs = model_cfg.get("inputs") or {}
    models = model_cfg.get("models") or {}
    t = models.get("transformer") or {}
    return Cfg(
        version=str(model_cfg.get("version", "0.0.0")),
        window=int(task.get("input_window_months", 18)),
        metrics=list(inputs.get("metrics") or []),
        derived_features=list(inputs.get("derived_features") or []),
        d_model=int(t.get("d_model", 64)),
        nhead=int(t.get("nhead", 4)),
        num_layers=int(t.get("num_layers", 2)),
        dropout=float(t.get("dropout", 0.1)),
        save_dir=REPO_ROOT / str(t.get("save_dir", "data/ml")),
    )


def metric_id_map(conn: sqlite3.Connection) -> Dict[str, int]:
    return {str(r["name"]): int(r["id"]) for r in conn.execute("SELECT id, name FROM metrics")}


def fetch_series_value(conn: sqlite3.Connection, repo_id: int, metric_id: int, month: str) -> float:
    row = conn.execute(
        """
        SELECT value
        FROM time_series
        WHERE repo_id=? AND metric_id=? AND period_type='month' AND is_raw=0 AND period=?
        """,
        (repo_id, metric_id, month),
    ).fetchone()
    if not row or row["value"] is None:
        return 0.0
    return float(row["value"])


def fetch_feature_value(conn: sqlite3.Connection, repo_id: int, metric_id: int, feature: str, month: str) -> float:
    row = conn.execute(
        """
        SELECT value
        FROM derived_features
        WHERE repo_id=? AND metric_id=? AND period_type='month' AND feature=? AND period=?
        """,
        (repo_id, metric_id, feature, month),
    ).fetchone()
    if not row or row["value"] is None:
        return 0.0
    return float(row["value"])


def main() -> None:
    args = parse_args()
    random.seed(args.seed)

    try:
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, Dataset
    except Exception as exc:  # noqa: BLE001
        print("[pretrain_transformer_masked] torch is not installed. Install with:")
        print("  pip install -r requirements-ml.txt")
        print(f"Original error: {exc}")
        raise SystemExit(1) from exc

    cfg_raw = load_yaml(Path(args.model))
    cfg = parse_cfg(cfg_raw)

    db_path = get_sqlite_path(Path(args.sources), args.db)
    conn = connect(db_path)
    try:
        metric_ids = metric_id_map(conn)

        # Use weak_labels index as a convenient pool of (repo_id, as_of_month) points.
        rows = conn.execute("SELECT repo_id, as_of_month FROM weak_labels").fetchall()
        if not rows:
            raise SystemExit("weak_labels not found; run scripts/build_weak_labels.py first")

        # subsample
        points = [(int(r["repo_id"]), str(r["as_of_month"])) for r in rows]
        random.shuffle(points)
        points = points[: max(1, int(args.max_samples))]

        d_per_metric = 1 + len(cfg.derived_features)
        d_in = len(cfg.metrics) * d_per_metric

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
                vec.append(fetch_series_value(conn, repo_id, mid, month))
                for feat in cfg.derived_features:
                    vec.append(fetch_feature_value(conn, repo_id, mid, feat, month))
            return vec

        sequences: List[List[List[float]]] = []
        for repo_id, as_of in points:
            months = month_sequence(as_of, cfg.window)
            sequences.append([build_step(repo_id, m) for m in months])

        # Standardize per feature dimension
        mean = [0.0] * d_in
        var = [0.0] * d_in
        n = 0
        for seq in sequences:
            for step in seq:
                n += 1
                for i, v in enumerate(step):
                    mean[i] += v
        mean = [m / max(1, n) for m in mean]
        for seq in sequences:
            for step in seq:
                for i, v in enumerate(step):
                    dv = v - mean[i]
                    var[i] += dv * dv
        std = [math.sqrt(v / max(1, n)) for v in var]

        def standardize(step: List[float]) -> List[float]:
            out = []
            for i, v in enumerate(step):
                s_ = std[i]
                out.append((v - mean[i]) / (s_ if s_ > 1e-12 else 1.0))
            return out

        sequences = [[standardize(step) for step in seq] for seq in sequences]

        class DS(Dataset):
            def __len__(self) -> int:
                return len(sequences)

            def __getitem__(self, idx: int):
                x = sequences[idx]
                return torch.tensor(x, dtype=torch.float32)

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

        class Encoder(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.in_proj = nn.Linear(d_in, cfg.d_model)
                self.pos = PositionalEncoding(cfg.d_model, max_len=max(256, cfg.window + 8))
                enc_layer = nn.TransformerEncoderLayer(
                    d_model=cfg.d_model, nhead=cfg.nhead, dropout=cfg.dropout, batch_first=True
                )
                self.encoder = nn.TransformerEncoder(enc_layer, num_layers=cfg.num_layers)
                self.recon = nn.Linear(cfg.d_model, d_in)

            def forward(self, x: torch.Tensor) -> torch.Tensor:
                h = self.pos(self.in_proj(x))
                h = self.encoder(h)
                return self.recon(h)

        device = torch.device(args.device)
        model = Encoder().to(device)
        opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)

        loader = DataLoader(DS(), batch_size=args.batch_size, shuffle=True)
        mask_ratio = float(args.mask_ratio)

        for epoch in range(args.epochs):
            model.train()
            total = 0.0
            n_batches = 0
            for x in loader:
                x = x.to(device)
                # mask some positions/features
                mask = (torch.rand_like(x) < mask_ratio).float()
                x_masked = x * (1.0 - mask)
                pred = model(x_masked)
                loss = ((pred - x) ** 2 * mask).sum() / mask.sum().clamp_min(1.0)
                opt.zero_grad()
                loss.backward()
                opt.step()
                total += float(loss.detach().cpu().item())
                n_batches += 1
            print(f"[pretrain_transformer_masked] epoch={epoch+1} loss={total/max(1,n_batches):.6f}")

        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        cfg.save_dir.mkdir(parents=True, exist_ok=True)
        out_path = cfg.save_dir / f"pretrain_masked_{cfg.version}_{created_at.replace(':','')}.pt"
        torch.save(
            {
                "state_dict": model.state_dict(),
                "config": cfg_raw,
                "feature_mean": mean,
                "feature_std": std,
                "step_feature_names": step_feature_names,
            },
            out_path,
        )
        print(f"[pretrain_transformer_masked] saved: {out_path}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

