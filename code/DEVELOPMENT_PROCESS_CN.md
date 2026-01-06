# OpenRisk-Advisor 开发流程文档

本文档给出复赛阶段的端到端开发流程，目标是把 OpenDigger 数据转化为可复现的 RiskReport 与治理建议，并保证评审可复核、系统可运行。

## 0. 范围与目标

- 先闭环再优化：优先打通“数据 → 风险 → 证据 → 建议 → 看板”的最小闭环。
- 全流程可配置、可追溯：指标字典与信号规则配置化，产出可复现。
- 面向评审可运行：提供一键启动、演示数据与复现说明。

## 1. 仓库结构（建议）

- `docs/`
  - `architecture.md`
  - `data_dictionary.md`
  - `riskreport_schema.md`
  - `runbook.md`
- `configs/`
  - `metrics.yaml`
  - `signals.yaml`
  - `model.yaml`
  - `pipelines.yaml`
- `services/`
  - `ingestion/`
  - `feature/`
  - `risk_evidence/`
  - `advisory/`
- `data/`
  - `samples/`
  - `cache/`
- `scripts/`
  - `bootstrap.sh`
  - `sync_opendigger.sh`
  - `run_backfill.sh`
  - `generate_riskreports.sh`
- `dashboards/`
  - `dataease/`
- `sqlbot/`
- `maxkb/`
- `docker/`
- `docker-compose.yml`

## 2. 规划与需求确认

1. 确认 M1–M4 里程碑范围：M1 数据链路，M2 风险+证据，M3 建议生成，M4 工程收敛。
2. 选定首批项目池（建议 10–30 个）与平台（GitHub/Gitee）。
3. 固化指标清单与信号规则（metrics.yaml / signals.yaml）。
4. MVP 先用规则/统计模型，深度模型作为升级项。

交付物：
- `configs/metrics.yaml` 初稿
- `configs/signals.yaml` 初稿
- `docs/architecture.md` 大纲

## 3. 环境与基础设施

1. 安装运行环境：
   - Python 3.10+（采集、特征与风险服务）
   - Java 8+（IoTDB）
   - 可选 Node.js（SQLBot/前端辅助工具）
2. 推荐用 Docker Compose 启动依赖服务。
3. 约定数据与日志路径可写。

交付物：
- `docker-compose.yml`
- `docs/runbook.md`（启动、停止、端口与依赖说明）

## 4. 数据采集（OpenDigger）

1. 按静态数据根链接拉取 JSON：
   - `https://oss.open-digger.cn/{platform}/{org}/{repo}/`
2. 校验 JSON 结构并统一时间键（YYYY-MM / YYYYQX / YYYY）。
3. 保留 raw 与插值数据，记录采集时间与来源。
4. 原始文件落地至 `data/cache/`，用于复现与审计。

检查项：
- 缺失月份被标注
- 数据来源可追溯

交付物：
- `services/ingestion/` 与 CLI 脚本
- `data/samples/` 至少 3 个仓库样例

## 5. IoTDB 建模与写入

1. repo 作为 device，指标作为 measurement。
2. `raw.*` 存原始指标，`feat.*` 存衍生特征。
3. 月度指标尽量使用 aligned timeseries 提升写入与对齐效率。

检查项：
- 能对齐查询多指标
- 存储组与序列命名一致

交付物：
- `services/feature/` 写入逻辑
- `docs/data_dictionary.md`（原始与派生字段说明）

## 6. 特征生成（窗口化与同比/环比）

1. 生成滚动均值/中位数、滚动斜率、异常分数。
2. 计算 MoM / YoY 变化率，缺失值做稳健处理。
3. 记录特征版本与运行参数。

检查项：
- 特征与原始指标一致性
- 缺失率与不确定性标记生效

交付物：
- `configs/pipelines.yaml`（窗口长度、平滑策略、阈值）
- 可复现的特征生成脚本

## 7. 风险评分与证据链

1. 先实现基于 signals.yaml 的规则评分。
2. 构建 RiskReport 并落库/可查询。
3. 提取证据链：触发窗口、强度、置信度、支撑指标摘要。

检查项：
- 同输入同输出（可复现）
- 证据能驱动可视化复核

交付物：
- `services/risk_evidence/`
- `docs/riskreport_schema.md`（含 JSON 示例）

## 8. 模型升级（可选，M2 稳定后）

1. 在规则基线稳定后引入轻量 Transformer。
2. 用弱监督标签训练并滚动回测。
3. 做概率校准（Platt 或 isotonic）。

检查项：
- 指标提升或稳定性提升
- 校准曲线记录在文档

交付物：
- `configs/model.yaml`
- `docs/model_notes.md`

## 9. 建议服务（LLM + MaxKB）

1. 建立 MaxKB 治理知识库与条目索引。
2. 风险信号与知识主题映射。
3. 严格模板化输出，禁止新增未证实事实。

检查项：
- 每条建议都能追溯到知识条目
- 风险为“需复核”时输出审慎建议

交付物：
- `services/advisory/`
- `maxkb/` 知识条目

## 10. 可视化与查询

1. DataEase 看板：总览 → 诊断 → 行动三层结构。
2. 风险分布、趋势曲线、信号触发区间可视化。
3. SQLBot 提供常见查询模板。

检查项：
- 样例数据可端到端展示
- 风险与证据一致

交付物：
- `dashboards/dataease/`
- `sqlbot/` 模板

## 11. 测试与验证

- 数据质量检查：缺失、异常、时间断裂。
- 复现性验证：同样输入生成同样 RiskReport。
- 回测：滚动窗口评估误报/漏报。
- 人工抽样核验 3–5 个项目。

交付物：
- `docs/validation.md`

## 12. 打包与交付

1. 一键启动与样例数据。
2. 形成演示脚本与截图。
3. 完整 README 与部署文档。

交付物：
- `scripts/bootstrap.sh`
- `README.md`
- `docs/demo_script.md`

## 13. 里程碑清单

M1 数据链路
- [ ] 采集脚本
- [ ] IoTDB 写入
- [ ] 基础特征
- [ ] 最小看板

M2 风险与证据
- [ ] 风险基线
- [ ] RiskReport 输出
- [ ] 证据可视化

M3 建议生成
- [ ] MaxKB 知识库
- [ ] LLM 模板
- [ ] 建议输出

M4 工程收敛
- [ ] 文档 + 视频
- [ ] 可复现演示

## 14. 决策记录

建议维护 `docs/decision_log.md`，记录指标/信号/阈值的关键调整，保证可审计与回放。
