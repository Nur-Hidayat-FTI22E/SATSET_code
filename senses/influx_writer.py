"""
SATSET — Senses Layer
influx_writer.py

Wrapper untuk InfluxDB v2 client.
Menyediakan fungsi write_metric() yang digunakan oleh telemetry_agent.
"""

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

load_dotenv()

INFLUX_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUX_TOKEN = os.environ.get("INFLUXDB_TOKEN")
if not INFLUX_TOKEN:
    raise EnvironmentError("Critical: INFLUXDB_TOKEN is not set in environment. Please configure .env file.")
INFLUX_ORG = os.getenv("INFLUXDB_ORG", "satset-lab")
INFLUX_BUCKET = os.getenv("INFLUXDB_BUCKET", "satset")


class InfluxWriter:
    """Thread-safe InfluxDB v2 writer with synchronous write API."""

    def __init__(self):
        self._client = InfluxDBClient(
            url=INFLUX_URL,
            token=INFLUX_TOKEN,
            org=INFLUX_ORG,
        )
        self._write_api = self._client.write_api(write_options=SYNCHRONOUS)
        print(f"[InfluxWriter] Connected to {INFLUX_URL} | org={INFLUX_ORG} | bucket={INFLUX_BUCKET}")

    def write_network_stats(self, packet_rate: float, packet_size: float, interval: float, source: str = "mqtt"):
        """Write network telemetry data point."""
        point = (
            Point("network_stats")
            .tag("source", source)
            .field("packet_rate", float(packet_rate))
            .field("packet_size", float(packet_size))
            .field("interval", float(interval))
            .time(datetime.now(timezone.utc), WritePrecision.NS)
        )
        self._write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)

    def write_hpc_stats(self, cache_misses: int, instructions_retired: int, branch_misses: int, cpu_usage: float):
        """Write hardware performance counter data point."""
        point = (
            Point("hpc_stats")
            .tag("platform", "rpi5-psutil")
            .field("cache_misses", int(cache_misses))
            .field("instructions_retired", int(instructions_retired))
            .field("branch_misses", int(branch_misses))
            .field("cpu_usage", float(cpu_usage))
            .time(datetime.now(timezone.utc), WritePrecision.NS)
        )
        self._write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)

    def write_brain_output(self, threat_score: float, is_attack: bool, spike_rate: float):
        """Write SNN Brain inference result."""
        point = (
            Point("brain_output")
            .tag("model", "snn-lif-v1")
            .field("threat_score", float(threat_score))
            .field("is_attack", int(is_attack))
            .field("spike_rate", float(spike_rate))
            .time(datetime.now(timezone.utc), WritePrecision.NS)
        )
        self._write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)

    def write_healing_event(self, action: str, trigger_score: float, target_service: str):
        """Write self-healing event for audit log."""
        point = (
            Point("healing_events")
            .tag("action", action)
            .tag("target", target_service)
            .field("trigger_score", float(trigger_score))
            .field("event", 1)
            .time(datetime.now(timezone.utc), WritePrecision.NS)
        )
        self._write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)

    def close(self):
        self._client.close()
