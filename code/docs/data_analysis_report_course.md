# OpenRisk-Advisor 数据作品分析报告（课程论文版）

作者：任北鸣、张凌琨（华东师范大学）  
项目：OpenRisk-Advisor（开源项目衰退风险预测与治理建议系统）  
报告生成时间：2026-01-13（以仓库内落盘产物为准）

---

## 摘要

开源项目的风险并非总是“突然停止”，更常见的形态是活跃度降低、协作效率变差与贡献者流失所导致的**缓慢衰退**。本作品围绕“是否衰退、为什么衰退、如何介入”三个决策问题，构建了一套可运行、可复现、可审计的工程化系统：从 OpenDigger 指标拉取与解析出发，生成数据质量报告与衍生特征；在此基础上进行信号检测与风险预测，最终固化为结构化的 RiskReport（风险概率/等级 + 主导信号 + 数据质量 + 证据链），并通过前端页面与大屏完成展示。同时，系统提供证据约束下的 LLM 治理建议与 RAG 问答能力，支持将证据转化为可执行动作与快速解释。本文以仓库中真实落盘产物（`docs/*.json`、`data/cache`、`opendigger.db`）为依据，总结系统的数据管线、方法实现、统计结果、案例分析与局限性，并给出可复现步骤。

---

## 1. 问题背景与研究目标

### 1.1 背景

对于维护者与 OSPO 而言，风险的难点不在“看见历史”，而在：

- **提前发现**：区分短期波动与持续性恶化；
- **可解释**：说明风险来自哪些维度、从何时开始出现；
- **可行动**：给出可执行的治理动作，而不是泛泛建议。

### 1.2 研究目标（工程化表达）

本作品目标是：构建一条可运行的闭环链路，输出可审计的三类产物：

- **数据层**：可追溯的指标缓存与质量报告；
- **信号层**：可解释的结构化信号检测结果；
- **风险层**：可复核证据链的 RiskReport，并为建议系统提供事实输入。

---

## 2. 数据来源、对象范围与落地形态

### 2.1 数据来源

- 数据源：OpenDigger 静态指标 JSON（按仓库/指标文件分发）
- 时间粒度：以月度（`YYYY-MM`）为主（由缓存文件 key 体现）

### 2.2 研究对象（仓库集合）

系统以 `configs/sources.yaml` 作为“参与数据库与报告生成”的仓库集合（已登记仓库）。前端 `/repo-list` 提供候选池，`/registered` 负责登记与拉取解析。

### 2.3 数据落地（可审计产物）

本作品强调“前端只展示，真实结果必须落盘可核对”，核心产物包括：

- 原始指标缓存：`data/cache/...`
- 本地数据库：`data/sqlite/opendigger.db`
- 数据质量报告：`docs/data_quality_report.json`
- 信号报告：`docs/signal_report.json`
- 风险报告：`docs/risk_report.json`

---

## 3. 数据管线与质量评估方法

### 3.1 端到端流程（以实现为准）

流水线以“页面操作 = 终端脚本链路”的方式实现：

1. 仓库登记：候选池 `/repo-list` → 写入 `configs/sources.yaml`
2. 一键拉取解析：`/registered` → 拉取 OpenDigger 指标并解析入库
3. 生成衍生特征：`scripts/derive_features.py`
4. 生成数据质量报告：`scripts/quality_report.py` → `docs/data_quality_report.json`
5. 生成信号报告：`scripts/signal_engine.py` → `docs/signal_report.json`
6. 训练/预测模型：`scripts/train_predictor.py`（baseline/transformer）→ 写入 `risk_predictions`
7. 生成 RiskReport 证据链：`scripts/build_risk_explanations.py` + `scripts/export_riskreports.py` → `docs/risk_report.json`

### 3.2 数据质量指标

当前实现中，数据质量以“覆盖/缺失”作为核心可审计指标：

- **覆盖率（coverage / avg_coverage）**：在固定窗口内，某指标实际拥有月度数据点的比例；
- **缺失率（missing_rate）**：`1 - avg_coverage`；
- 上游缺失（HTTP 404）将记录到质量报告中，用于区分“抓取失败”与“上游根本不存在”。

---

## 4. 信号检测：从指标到治理语义

### 4.1 信号的定位

信号用于回答“风险从哪里来”，将指标变化模式转成结构化的治理语义（例如活跃度下降、协作供需失衡、贡献者缩减等），并提供强度/置信度与触发窗口字段，便于解释与后续建议对齐。

### 4.2 落盘产物与展示

- 信号产物为事件级列表：`docs/signal_report.json`（每条记录对应 repo×signal×时间窗口）
- 前端页面：`/signals-report` 用于“一键生成信号报告 + 按仓库聚合展示”

---

## 5. 风险预测模型：baseline 训练与输出机制（以代码为准）

### 5.1 为什么采用弱监督与轻量模型

“衰退/不衰退”难以人工标注，因此系统采用弱监督标签（`weak_labels` 表）作为训练信号，并以轻量模型快速闭环交付。当前默认模型为 baseline（逻辑回归），更复杂模型可作为升级项。

### 5.2 训练数据与特征构造（`scripts/train_predictor.py`）

模型配置来自 `configs/model.yaml`：

- 窗口：输入窗口 `18` 个月，预测窗口 `3` 个月，最小历史 `24` 个月
- 输入指标：`14` 个（如 activity、contributors、issue_age、change_requests、stars 等）
- 衍生特征：`mom/yoy/trend_slope_3/trend_slope_6/roll_std_3/zscore_12/raw_ratio_win3/interp_ratio_win3`

特征构造方式（实现摘要）：

- 对每个指标与每种特征（原值 + 衍生特征），在窗口内计算四类统计：`last/mean/min/max`
- 同时计算该指标的覆盖率（coverage）
- 额外加入全局的 `raw_ratio_win3` 平均值用于复核策略（needs_review）

### 5.3 baseline 模型训练（实现摘要）

baseline 模型为 SGD 训练的逻辑回归（`logreg_sgd`），包含：

- 标准化：对特征做 mean/std 标准化
- 损失：加权 BCE（样本权重来自弱监督样本 `sample_weight`）
- 正则：L2 正则（`l2=0.001`）
- 训练轮数：`epochs=8`（见 `configs/model.yaml`）

### 5.4 概率校准与风险分级

训练后在验证集上使用 Platt Scaling（`fit_platt`）对 raw logit 做概率校准，得到 `p_calibrated`。  
风险分级阈值来自 `configs/model.yaml`：

- Low：`p < 0.33`
- Medium：`0.33 ≤ p < 0.66`
- High：`p ≥ 0.66`

预测结果写入 SQLite 表 `risk_predictions`，随后被 RiskReport 生成脚本读取并固化到 `docs/risk_report.json`。

---

## 6. RiskReport 证据链：把“分数”变成“可复核解释”

### 6.1 RiskReport 的定位

RiskReport 是系统对外“事实对象”，用于统一承载：

- 风险结论：`risk_score`、`risk_level`、`as_of_month`
- 主导信号：`main_signals[]`（t0、强度、置信度、维度）
- 数据质量：`data_quality`（覆盖/缺失与窗口信息）
- 不确定性：`model_uncertainty`（若存在）

### 6.2 前端承载

前端 `/repos` 页面展示风险列表与右侧抽屉证据链，目标是“评委能看见并复核”：

- 列表：risk_score、risk_level、as_of、signals 等
- 详情：主导信号的 t0/强度/置信度/异常度 + 数据质量关联信息

---

## 7. 实验结果与统计分析（基于仓库落盘产物）

本节统计均来自：

- `docs/data_quality_report.json`（生成时间：`2026-01-13T14:38:49Z`）
- `docs/signal_report.json`
- `docs/risk_report.json`（as_of=`2025-12`，model=`baseline/0.1.0`）

### 7.1 数据质量概览

质量报告中统计（抓取 × 解析）：

- 覆盖组合规模：`repo_count=196`、`metric_count=31`、`combos=6076`
- 抓取状态：`ok=5097`，`http_404=979`
- 解析状态：`parsed_ok=5069`，`parse_error=1007`

缺失最严重的指标（Top 10，按 not_found_cnt）：

| metric_name | not_found_cnt |
|---|---:|
| community_openrank | 196 |
| change_requests_reviews | 74 |
| issues_closed | 71 |
| issue_resolution_duration | 70 |
| issues_new | 56 |
| issue_response_time | 55 |
| issue_age | 55 |
| stars | 40 |
| technical_fork | 35 |
| inactive_contributors | 28 |

> 解释：`http_404/not_found` 反映“上游缺失”占比高，这会直接影响模型窗口覆盖与信号置信度，是生态数据分析中必须面对的现实约束。

### 7.2 信号事件统计（`docs/signal_report.json`）

- 信号事件总数：`9478`
- 覆盖仓库数（出现过信号事件的 repo）：`144`
- 信号种类数：`13`

Top 信号（出现次数最多）：

| signal_id | cnt |
|---|---:|
| DATA_SUFFICIENT_6M | 2982 |
| PR_SUPPLY_DEMAND_IMBALANCE_6M | 1258 |
| ATTENTION_DROP_6M_AUX | 1057 |
| BUS_FACTOR_LOW_OR_DOWN | 973 |
| ISSUE_INFLOW_DROP_3M | 925 |
| INACTIVE_CONTRIB_SPIKE | 861 |

Top 仓库（信号事件最多）：

| repo | signal_events |
|---|---:|
| NixOS/nixpkgs | 536 |
| XX-net/XX-Net | 424 |
| apache/iotdb | 388 |
| mdaus/nitro | 373 |
| open-telemetry/opentelemetry-js-contrib | 320 |

### 7.3 风险预测结果统计（`docs/risk_report.json`）

- 评估月份：`2025-12`
- 模型：`baseline/0.1.0`
- 预测覆盖：`162` 个仓库

风险等级分布：

| level | count |
|---|---:|
| High | 16 |
| Medium | 8 |
| Low | 138 |

数据质量在 RiskReport 口径下的整体水平（按模型输入指标与 18 个月窗口计算）：

- 平均覆盖率：`0.194`
- 覆盖率中位数：`0.079`
- 平均缺失率：`0.806`
- 缺失率中位数：`0.921`

> 解释：由于指标上游缺失（404）与仓库历史跨度不足，导致“按固定窗口与固定指标集求均值”的覆盖率整体偏低。该结果并非系统错误，而是生态数据的真实分布特性；系统通过质量报告与证据链把该不确定性显式暴露出来。

---

## 8. 案例分析（两类典型情形）

本节从 `docs/risk_report.json` 中选取两个仓库案例：一个“高风险且数据相对充分”，一个“数据严重缺失导致结论需要谨慎”。

### 8.1 案例 A：apache/iotdb（高风险 + 数据相对充分）

- repo：`apache/iotdb`
- 风险：`risk_score=0.999`，`risk_level=High`，`as_of=2025-12`
- 数据质量：`avg_coverage≈0.865`，`missing_rate≈0.135`

主导信号（Top 5，按 RiskReport main_signals）：

1. `MULTI_DIMENSION_DECLINE_CORE`：多维度核心衰退（t0=2025-05）
2. `BUS_FACTOR_LOW_OR_DOWN`：单点维护风险（t0=2025-05）
3. `ACT_DROP_YOY_3M`：活跃度同比持续下滑（t0=2025-05）
4. `CONTRIB_SHRINK_3M`：贡献者规模收缩（t0=2025-05）
5. `PR_THROUGHPUT_DROP_3M`：PR 吞吐下降（t0=2025-05）

分析要点（建议写在报告里并配图）：

- 信号给出明确的 t0 与持续窗口，说明“不是单点波动”
- 覆盖率较高，支撑“结论可参考”
- 适合在前端 `/repos` 抽屉中展示证据链，并在 `/governance` 生成行动建议作为治理闭环示例

### 8.2 案例 B：dataease/DataEase（数据严重缺失 → 结论需谨慎）

- repo：`dataease/DataEase`
- 风险：`risk_score=0.000`，`risk_level=Low`，`as_of=2025-12`
- 数据质量：`avg_coverage=0.000`，`missing_rate=1.000`（模型输入指标在窗口内全部缺失）

分析要点：

- 该仓库在模型输入指标上“无数据”，因此 risk_score 低并不代表“安全”
- 系统应将此类仓库作为“数据不可用/上游缺失”的治理对象，先补齐数据再评估风险
- 在展示层应突出质量提示，避免用户把“缺数据的低风险”误读为“健康项目”

---

## 9. 讨论：结果解释与工程意义

### 9.1 为什么覆盖率整体偏低

基于产物统计，可归因于两点：

- 上游缺失：质量报告存在显著的 `http_404/not_found`（如 community_openrank 全部缺失）
- 固定窗口与固定指标集：对每个 repo 统一按 `18` 个月与 `14` 指标计算平均覆盖率，导致历史短或指标缺失时均值被显著拉低

### 9.2 系统的“可审计性”价值

本作品与常见“静态健康度面板”的差异在于：

- 结果落盘：任何展示都能在 `docs/*.json` 与 `data/cache` 中复核
- 质量显式：缺失率/覆盖率进入 RiskReport，驱动“需复核”与建议降级
- 证据链解释：RiskReport 把模型输出拆解为可读信号与触发窗口

---

## 10. 局限性与改进方向

- **数据侧**：上游指标缺失会限制模型与解释的稳定性；可引入“可用指标集自适应均值”或分层口径，减少全局均值被极端缺失拉低
- **方法侧**：弱监督标签存在噪声；需要更多回测与校准策略来控制误报/漏报
- **展示侧**：对“缺数据导致低风险”的情况，需要更强提示（例如单独状态或不参与排名）
- **知识侧**：目前 LLM 建议以证据约束为主，后续可接入更完善的知识库检索与引用追溯，提升建议一致性与可复盘性

---

## 11. 复现与运行说明（最短路径）

### 11.1 前端操作路径（推荐）

1. `/repo-list`：从候选池选择仓库并登记  
2. `/registered`：一键拉取解析（观察输出台日志）  
3. `/signals-report`：生成信号报告  
4. `/models`：训练/预测并生成报告  
5. `/repos`：查看 RiskReport 列表与证据链抽屉  
6. `/governance`：基于 RiskReport 生成治理建议（Markdown 可复制）  
7. `/rag`：基于仓库缓存指标 + 风险摘要进行问答  

### 11.2 关键产物核对（评审可直接打开）

- `docs/data_quality_report.json`
- `docs/signal_report.json`
- `docs/risk_report.json`
- `data/cache/...`（某仓库的指标 JSON）

---

## 附录 A：建议插入的图与截图位置

- 图 A1：`/repo-list`（候选池与登记状态）
- 图 A2：`/registered`（状态 + 覆盖率/缺失率 + 输出台）
- 图 A3：`/registered/:org/:repo`（单仓库指标摘要）
- 图 A4：`/signals-report`（信号生成与仓库统计）
- 图 A5：`/models`（训练/预测状态与结果表）
- 图 A6：`/repos`（RiskReport 列表 + 抽屉证据链）
- 图 A7：`/governance`（LLM 建议输出）
- 图 A8：`/rag`（问答与建议问题）
- 图 A9：`/wall`（展示大屏）

