import os
import json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient

load_dotenv(".env")
INFLUX_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUX_TOKEN = os.environ.get("INFLUXDB_TOKEN")
INFLUX_ORG = os.getenv("INFLUXDB_ORG", "satset-lab")
INFLUX_BUCKET = os.getenv("INFLUXDB_BUCKET", "satset")

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
query_api = client.query_api()
now = datetime.now(timezone.utc)
start = (now - timedelta(seconds=60)).isoformat()
raw = {}

for measurement in ("network_stats", "hpc_stats"):
    flux = f"""
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: {start})
  |> filter(fn: (r) => r._measurement == "{measurement}")
  |> last()
"""
    tables = query_api.query(flux, org=INFLUX_ORG)
    for table in tables:
        for record in table.records:
            field = record.get_field()
            value = record.get_value()
            if field and value is not None:
                raw[field] = value

print(json.dumps(raw, indent=2))
