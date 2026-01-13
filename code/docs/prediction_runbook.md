# Prediction Runbook (Risk Forecasting MVP)

This repo currently uses **SQLite as the main pipeline store** and provides an MVP risk prediction module based on:
- weak supervision labels from `signal_events`
- a baseline probabilistic model (logistic regression + Platt calibration)
- optional Temporal Transformer (requires `torch`)

## 1) Prerequisites

- You already ran ingestion + parsing + features + signals:
  - `bash scripts/run_ingestion.sh`
  - `python scripts/derive_features.py --sources configs/sources.yaml --period-type month --windows 3,6,12`
  - `python scripts/signal_engine.py --sources configs/sources.yaml --metrics configs/metrics.yaml --signals configs/signals.yaml`

## 2) Build weak labels (future-window decline events)

Writes labels into SQLite table `weak_labels`.

```bash
python scripts/build_weak_labels.py --sources configs/sources.yaml --model configs/model.yaml --replace
```

## 3) Train baseline predictor + write predictions

Writes trained model into `ml_models` and predictions into `risk_predictions`.

```bash
python scripts/train_predictor.py \
  --sources configs/sources.yaml \
  --model configs/model.yaml \
  --replace \
  --model-type baseline \
  --write-predictions
```

## 4) Train Transformer (multi-task forecast + risk)

1) Enable in `configs/model.yaml`: `models.transformer.enabled: true`
2) Install deps (requires network access): `pip install -r requirements-ml.txt`
3) Train + (optional) write predictions:

```bash
python scripts/train_transformer.py \
  --sources configs/sources.yaml \
  --model configs/model.yaml \
  --device cpu \
  --write-predictions
```

The trained model checkpoint is saved under `data/ml/` and registered in SQLite `ml_models`.

## 5) (Optional) Masked pretraining (self-supervised upgrade)

```bash
python scripts/pretrain_transformer_masked.py \
  --sources configs/sources.yaml \
  --model configs/model.yaml \
  --device cpu
```

Then set `models.transformer.pretrained_path` in `configs/model.yaml` to the saved checkpoint and retrain.

## 6) Export RiskReport snapshot (JSON + Markdown)

```bash
python scripts/build_risk_explanations.py --sources configs/sources.yaml --model configs/model.yaml --signals configs/signals.yaml --model-type baseline --replace
python scripts/export_riskreports.py --sources configs/sources.yaml --model-type baseline
python scripts/build_risk_explanations.py --sources configs/sources.yaml --model configs/model.yaml --signals configs/signals.yaml --model-type transformer --replace
python scripts/export_riskreports.py --sources configs/sources.yaml --model-type transformer
```

## 7) Offline audit explanation (Integrated Gradients)

Requires `torch` and a trained transformer checkpoint in `ml_models`.

```bash
python scripts/audit_explain_ig.py \
  --sources configs/sources.yaml \
  --repo X-lab2017/open-digger \
  --as-of-month 2025-12 \
  --device cpu
```
