# 数据字典（OpenDigger 数据模块）

本文档说明配置层、文件层与表层的字段含义，并说明 time_series 如何追溯到原始 JSON 文件与 URL。

## 1. 配置层

### 1.1 `configs/sources.yaml`

- `version`：配置版本号。
- `defaults.platform`：默认平台（`github` / `gitee`）。
- `defaults.base_url`：OpenDigger 静态数据根地址（默认 `https://oss.open-digger.cn`）。
- `defaults.cache_dir`：本地缓存目录（原始 JSON 落地）。
- `defaults.sqlite_path`：SQLite 数据库路径。
- `repos[]`：仓库列表。
  - `org`：组织名。
  - `repo`：仓库名。
  - `platform`：可选，覆盖默认平台。
  - `enabled`：可选，是否启用该仓库。

示例：

```yaml
version: 1

defaults:
  platform: github
  base_url: https://oss.open-digger.cn
  cache_dir: data/cache
  sqlite_path: data/sqlite/opendigger.db

repos:
  - org: X-lab2017
    repo: open-digger
```

### 1.2 `configs/metrics.yaml`

- `version`：配置版本号。
- `metrics[]`：指标定义列表。
  - `name`：指标名称（内部使用，列名）。
  - `file`：OpenDigger 指标文件名（如 `openrank.json`）。
  - `level`：指标级别（当前为 `repo`）。
  - `description`：可选说明。
- `granularity`：可选，允许粒度（如 `month/quarter/year`）。
- `keep_raw`：可选，是否保留 `-raw` 数据。
 - `missing_policy`：可选，缺失策略（如 `keep`）。
 - `efficiency`：效率指标降级配置。
  - `primary_metric`：首选效率指标（如 `issue_age`）。
  - `fallback_metric`：降级指标（如 `issues_closed`）。

### 1.3 `configs/signals.yaml`

- `signal_id`：信号唯一标识。
- `schema`：全局约定（粒度、缺失策略、置信度规则）。
- `scoring`：严重度分级与默认权重。
- `windows`：窗口定义（如 `win3`/`win6`）。
- `dimensions`：维度与指标集合说明。
- `signals[]`：信号规则。
  - `id` / `name` / `dimension` / `severity` / `weight` / `enabled`
  - `require_quarter_alignment`：是否要求季度趋势同向
  - `require_year_alignment`：是否要求年度趋势同向
  - `requires`：依赖的指标与派生特征
  - `conditions`：阈值条件（支持 `all`/`any`/`feature_ref`）
  - `consistency`：一致性要求（`k_of_n` 或 `once_in_window`）
  - `confidence`：raw/插值比例对应的置信策略
  - `min_coverage`：窗口覆盖率门槛
  - `explain`：解释模板与证据字段

示例：

```yaml
version: 1

defaults:
  granularity: [month, quarter, year]
  keep_raw: true
  missing_policy: keep

efficiency:
  primary_metric: issue_age
  fallback_metric: issues_closed

metrics:
  - name: openrank
    file: openrank.json
    level: repo
```

## 2. 文件层（缓存与追溯）

### 2.1 URL 模板

OpenDigger 静态数据访问格式：

```
https://oss.open-digger.cn/{platform}/{org}/{repo}/{metric_file}
```

示例：

```
https://oss.open-digger.cn/github/X-lab2017/open-digger/openrank.json
```

### 2.2 本地缓存路径规则

缓存目录结构与 URL 路径一致：

```
{cache_dir}/{platform}/{org}/{repo}/{metric_file}
```

示例：

```
data/cache/github/X-lab2017/open-digger/openrank.json
```

### 2.3 追溯字段

每次抓取都会记录：
- `path`：本地缓存路径（`raw_files.path`）
- `url`：抓取 URL（`raw_files.url`）
- `fetched_at`：抓取时间（`raw_files.fetched_at`）
- `status`：抓取状态（`raw_files.status`）
- `file_hash`：文件 SHA256（`raw_files.file_hash`）

这些字段可用于核验数据来源与一致性。

## 3. 表层（SQLite 结构与字段）

### 3.1 `repos`

- `id`：主键
- `platform`：平台
- `org`：组织名
- `repo`：仓库名
- `full_name`：唯一标识（`org/repo`）

### 3.2 `metrics`

- `id`：主键
- `name`：指标名（内部列名）
- `file`：指标文件名（唯一）
- `level`：指标级别
- `description`：说明

### 3.3 `raw_files`

每次抓取产生一条记录（允许多次）。

- `id`：主键
- `repo_id`：外键 → `repos.id`
- `metric_id`：外键 → `metrics.id`
- `path`：本地缓存路径
- `url`：抓取 URL
- `fetched_at`：抓取时间
- `status`：抓取状态（`ok` / `http_xxx` / `network_error` / `error`）
- `error`：错误信息
- `file_hash`：文件 SHA256
- `http_status`：HTTP 状态码（如 200/404）
- `final_url`：最终 URL（含重定向）
- `response_size`：响应大小（bytes）
- `error_type`：错误类型（`http_error` / `timeout` / `connection` / `unknown`）
- `retry_count`：重试次数

### 3.4 `raw_json`

每次解析产生一条记录。

- `id`：主键
- `repo_id`：外键 → `repos.id`
- `metric_id`：外键 → `metrics.id`
- `json_text`：原始 JSON 文本（规范化输出）
- `json_hash`：JSON 哈希（内容级追溯）
- `parsed_at`：解析时间
- `parse_status`：解析状态（`time_series` / `no_time_keys` / `invalid_json` / `non_dict`）
- `time_keys_count`：时间键数量

### 3.5 `time_series`

时间序列主表（用于后续模型/特征）。

- `id`：主键
- `repo_id`：外键 → `repos.id`
- `metric_id`：外键 → `metrics.id`
- `period`：时间键（`YYYY-MM` / `YYYYQX` / `YYYY`）
- `period_type`：时间粒度（`month` / `quarter` / `year`）
- `value`：数值
- `is_raw`：是否 raw 数据（1 为 `YYYY-MM-raw`）
- `source_key`：原始 JSON 中的键名

唯一约束：

```
(repo_id, metric_id, period, period_type, is_raw)
```

### 3.6 `time_series_object`

用于保存“非单值时序”的结构化值（如 detail/分布类指标）。

- `id`：主键
- `repo_id`：外键 → `repos.id`
- `metric_id`：外键 → `metrics.id`
- `period`：时间键（`YYYY-MM` / `YYYYQX` / `YYYY`）
- `period_type`：时间粒度（`month` / `quarter` / `year`）
- `json_value`：原始值 JSON 文本
- `is_raw`：是否 raw 数据（1 为 `YYYY-MM-raw`）
- `source_key`：原始 JSON 中的键名

唯一约束：

```
(repo_id, metric_id, period, period_type, is_raw)
```

### 3.7 `derived_features`

派生特征表（不依赖 IoTDB，先落 SQLite）。\n
- `id`：主键\n
- `repo_id`：外键 → `repos.id`\n
- `metric_id`：外键 → `metrics.id`\n
- `period`：时间键\n
- `period_type`：粒度\n
- `feature`：特征名（如 `mom_pct` / `yoy_pct` / `roll_mean_3`）\n
- `value`：特征值\n

常用特征命名（当前实现）：\n
- `value` / `mom` / `yoy`\n
- `roll_mean_{k}` / `roll_std_{k}` / `trend_slope_{k}` / `zscore_{k}`\n
- `raw_ratio_win{k}` / `interp_ratio_win{k}`\n
- 对象型指标子字段前缀：`avg_` / `p95_`（例如 `p95_yoy`）\n

唯一约束：

```
(repo_id, metric_id, period, period_type, feature)
```

### 3.8 `signal_events`

信号判定输出表（由 signal_engine 生成）。\n
- `id`：主键\n
- `repo_id`：外键 → `repos.id`\n
- `signal_id`：信号标识\n
- `metric_id`：触发指标\n
- `start_month`：触发起始月份\n
- `end_month`：触发结束月份\n
- `confidence`：置信度（raw 比例）\n
- `severity`：严重度\n
- `evidence_ref`：证据 JSON（指标/月份/阈值/是否降级）\n

## 4. IoTDB 侧映射（时序存储）

- **device**：`root.openrisk.{platform}.{org}_{repo}`\n
- **raw measurements**：`raw_{metric_name}`（来自 `time_series`）\n
- **feat measurements**：`feat_{metric_name}_{feature}`（来自 `derived_features`）\n
- **timestamp**：月/季/年首日毫秒时间戳\n
- **meta measurements**：`meta_{field}`（从 `sources.yaml` 的 `meta` 写入，TEXT 类型）\n
- **sync log**：`data/iotdb_sync_log.jsonl` 记录每次同步的参数与写入量\n

## 4. 追溯链路说明（time_series → 原始文件）

一个 `time_series` 点的追溯路径：

1. 用 `time_series.repo_id` 与 `time_series.metric_id` 关联到 `repos` 与 `metrics`，得到 `platform/org/repo` 与 `metric_file`。
2. 通过 `raw_files` 中同一 `repo_id` + `metric_id` 的最新记录，获取原始 `url` 与 `path`。
3. 若需核验内容一致性，可使用 `raw_files.file_hash` 与缓存文件进行对比。
4. 若 `time_series` 为空，可从 `time_series_object` 读取结构化值，并用 `raw_json.json_hash` 与 `raw_json.json_text` 追溯解析输入。

因此，每个时间序列点都能从 SQLite 追溯回原始 JSON 文件与 URL，实现完整的可审计闭环。
