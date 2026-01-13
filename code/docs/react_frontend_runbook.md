# React Frontend Runbook (Platform + Wall)

This repo includes a React-based “platform” frontend under `frontend/`:
- Console pages: Overview / Repos / Signals / Settings
- Big-screen wall: `/wall` (full-screen friendly)

It consumes existing pipeline outputs (no backend required):
- `docs/risk_report.json`

## 1) Generate data

From repo root:

```bash
python scripts/build_risk_explanations.py --sources configs/sources.yaml --model configs/model.yaml --signals configs/signals.yaml --model-type baseline --replace
python scripts/export_riskreports.py --sources configs/sources.yaml --model-type baseline
```

## 2) Install frontend deps

```bash
cd frontend
npm install
```

## 3) Run dev server

```bash
npm run dev
```

Open:
- `http://localhost:5173/`
- Big screen: `http://localhost:5173/wall`

Note: The default data URL is `/docs/risk_report.json`. The Vite dev server in `frontend/` already serves the repo `docs/` folder under `/docs/*`, so it should work out of the box. If you still can’t load it, use Settings to change the URL, or import the JSON file directly (top bar “导入 JSON”).

## 4) Build static assets

```bash
npm run build
npm run preview
```
