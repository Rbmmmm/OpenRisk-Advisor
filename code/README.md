# OpenRisk-Advisor

开源项目衰退风险预测与治理建议系统。该仓库包含完整数据管线、风险建模、证据链生成与可视化前端，所有核心结果以本地文件产物形式落盘，便于审计与复现。

## 下载数据库

由于建立数据库需要时间较长，github 又无法上传大文件，因此发布在了仓库的 release 里，链接为：
- https://github.com/Rbmmmm/OpenRisk-Advisor/releases/tag/v0.1.0-data
- 也可以通过指令 `wget https://github.com/Rbmmmm/OpenRisk-Advisor/releases/download/v0.1.0-data/opendigger.db
` 或 

```bash
curl -L -o opendigger.db \
  https://github.com/Rbmmmm/OpenRisk-Advisor/releases/download/v0.1.0-data/opendigger.db
``` 

下载

需要注意下载完需要把 `opendigger.db` 放在 `code/data/sqlite/` 下即 `data/sqlite/opendigger.db`。

## 视频

- 项目汇报视频：
  - https://www.bilibili.com/video/BV1RqrLBqEUC/?spm_id_from=333.1387.upload.video_card.click&vd_source=cf2b6ed11510894c412447c8949c8cc7
- 实机演示视频：
  - https://www.bilibili.com/video/BV1dirLBMEv1/?share_source=copy_web&vd_source=3615cdee37e65abb40d1c38835e67b78

---

## 项目结构

- `configs/`  
  指标、信号与模型配置（`metrics.yaml`、`signals.yaml`、`model.yaml`、`sources.yaml`）。
- `scripts/`  
  数据拉取、派生特征、信号引擎、建模预测与报告导出等脚本。
- `services/`  
  数据采集与存储相关服务逻辑。
- `docs/`  
  报告与说明文档（`data_quality_report.json`、`signal_report.json`、`risk_report.json` 等）。
- `data/`  
  本地数据库与缓存（`data/sqlite/opendigger.db`、`data/cache/...`）。
- `frontend/`  
  React 前端（包含页面与展示逻辑）。

---

## 快速运行（本地可复现）

### 1) 安装依赖

- Python 依赖：`requirements.txt`（建模/训练额外依赖见 `requirements-ml.txt`）  
- 前端依赖：`frontend/package.json`

### 2) 推荐工作流（先跑数据与报告，再跑前端）

以下命令都在仓库根目录执行（`code/`）：

```
# 0) 数据拉取与解析（不依赖 typer）
python -m services.ingestion.run_ingest \
  --sources configs/sources.yaml \
  --metrics configs/metrics.yaml

# 1) 生成派生特征
python scripts/derive_features.py \
  --sources configs/sources.yaml \
  --windows 3,6,12

# 2) 生成数据质量报告
python scripts/quality_report.py \
  --sources configs/sources.yaml \
  --metrics configs/metrics.yaml \
  --json-output docs/data_quality_report.json \
  --output docs/data_quality_report.md

# 3) 生成信号事件与信号报告
python scripts/signal_engine.py \
  --sources configs/sources.yaml \
  --metrics configs/metrics.yaml \
  --signals configs/signals.yaml

# 4) 生成弱监督标签
python scripts/build_weak_labels.py \
  --sources configs/sources.yaml \
  --model configs/model.yaml

# 5) 训练模型并写入预测
python scripts/train_predictor.py \
  --sources configs/sources.yaml \
  --model configs/model.yaml \
  --model-type baseline \
  --write-predictions

# 6) 构建 RiskReport 证据链（写入数据库）
python scripts/build_risk_explanations.py \
  --sources configs/sources.yaml \
  --model configs/model.yaml \
  --signals configs/signals.yaml \
  --model-type baseline \
  --replace

# 7) 导出 RiskReport 文件（前端直接读取）
python scripts/export_riskreports.py \
  --sources configs/sources.yaml \
  --model-type baseline \
  --output-json docs/risk_report.json \
  --output-md docs/risk_report.md
```

完成后可核对以下产物是否生成：

- `docs/data_quality_report.json`
- `docs/signal_report.json`
- `docs/risk_report.json`

### 3) 运行前端

在 `frontend/` 目录启动开发服务器：

```
npm install
npm run dev
```

前端默认读取本地 `docs/*.json` 产物，并通过 Vite dev server 提供的后端 API 执行脚本。

### 4) 建议使用的页面流程

1. `/repo-list`：从候选池登记仓库（写入 `configs/sources.yaml`）  
2. `/registered`：一键拉取解析（生成缓存 + 更新报告）  
3. `/signals-report`：生成信号报告  
4. `/models`：训练模型与生成预测  
5. `/repos`：查看 RiskReport 证据链  
6. `/governance`：生成治理建议（LLM）  
7. `/rag`：基于仓库数据的问答  
8. `/overview`、`/signals`、`/wall`：全局可视化展示

---

## 关键产物（建议核对的文件）

- 原始指标缓存：`data/cache/...`
- 数据质量报告：`docs/data_quality_report.json`
- 信号报告：`docs/signal_report.json`
- 风险报告：`docs/risk_report.json`
- SQLite 数据库：`data/sqlite/opendigger.db`

---

## 运行说明文档

- 前端运行：`docs/react_frontend_runbook.md`
- 风险预测：`docs/prediction_runbook.md`
- 可视化大屏：`docs/dashboard_runbook.md`
