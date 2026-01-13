# IoTDB Runbook (OpenRisk-Advisor)

## 1. Install & Start IoTDB

- Ensure JDK 8+ installed.
- Start ConfigNode and DataNode.

```bash
nohup ./sbin/start-confignode.sh > confignode.log 2>&1 &
nohup ./sbin/start-datanode.sh > datanode.log 2>&1 &
```

## 2. Configure client

Edit `configs/iotdb.yaml` if needed:
- host/port/user/pw
- database root
- device naming

## 3. Write data (SQLite -> IoTDB)

```bash
# raw metrics only
python scripts/sync_iotdb.py --sources configs/sources.yaml --iotdb configs/iotdb.yaml --period-type month --include-raw

# raw + features
python scripts/sync_iotdb.py --sources configs/sources.yaml --iotdb configs/iotdb.yaml --period-type month --include-raw --include-feat

# incremental (last 6 months)
python scripts/sync_iotdb.py --sources configs/sources.yaml --iotdb configs/iotdb.yaml --period-type month --include-raw --include-feat --recent-months 6
```

## 4. Export views for DataEase/SQLBot

```bash
python scripts/iotdb_export_views.py \
  --iotdb configs/iotdb.yaml \
  --root root.openrisk.github \
  --start 2024-01-01T00:00:00 \
  --end 2025-01-01T00:00:00 \
  --snapshot 2025-01-01T08:00:00 \
  --measurements raw_activity,feat_activity_yoy \
  --output-dir data/exports
```

Outputs:
- `data/exports/iotdb_long.csv`
- `data/exports/iotdb_wide.csv`

## 5. Validate via CLI

```sql
-- check database
SHOW DATABASES;

-- query one repo
SELECT raw_activity, feat_activity_yoy
FROM root.openrisk.github.X_lab2017_open_digger
WHERE time >= 2024-01-01T00:00:00
LIMIT 10;

-- aligned query across repos
SELECT feat_activity_yoy
FROM root.openrisk.github.**
WHERE time >= 2025-01-01T00:00:00 AND time < 2025-01-02T00:00:00
ALIGN BY DEVICE;
```

## 6. Notes

- Measurement naming uses `raw_` and `feat_` prefixes.
- Timestamps use period start (month/quarter/year).
- Sync logs are stored in `data/iotdb_sync_log.jsonl`.
