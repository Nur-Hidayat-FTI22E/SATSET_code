"""
SATSET — Brain Layer
inference_engine.py
Engine inferensi yang benar-benar membaca data dari InfluxDB dan model SNN
"""

import argparse
import json
import os
import signal
import sys
import time
import warnings
from datetime import datetime, timezone, timedelta

import torch
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient
import joblib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "senses"))
from influx_writer import InfluxWriter
from snn_model import build_model

warnings.filterwarnings("ignore", category=UserWarning)

# Load .env
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT, ".env"))

INFLUX_URL    = os.getenv("INFLUXDB_URL",    "http://localhost:8086")
INFLUX_TOKEN  = os.environ.get("INFLUXDB_TOKEN")
if not INFLUX_TOKEN:
    raise EnvironmentError("Critical: INFLUXDB_TOKEN is not set in environment.")
INFLUX_ORG    = os.getenv("INFLUXDB_ORG",    "satset-lab")
INFLUX_BUCKET = os.getenv("INFLUXDB_BUCKET", "satset")
MQTT_HOST     = os.getenv("MQTT_HOST",       "localhost")
MQTT_PORT     = int(os.getenv("MQTT_PORT",   1883))
THRESHOLD     = float(os.getenv("THREAT_THRESHOLD", 0.85))
INTERVAL      = float(os.getenv("INFERENCE_INTERVAL", 1.0))
MODEL_PATH    = os.getenv("SNN_MODEL_PATH",  os.path.join(os.path.dirname(os.path.abspath(__file__)), "model", "snn_model.pt"))

_running = True
import numpy as np

def _normalize_features(raw: dict) -> torch.Tensor:
    """Convert raw measurement dict to normalized [1, 4] tensor (sesuai skripsi)."""
    vals = np.array([
        raw.get("n_packets", 0),
        raw.get("total_bytes", 0),
        raw.get("cache_misses", 0),
        raw.get("instructions", 0),
    ], dtype=np.float32).reshape(1, -1)

    scaler_path = os.path.join(os.path.dirname(__file__), 'model', 'satset_scaler.pkl')
    if os.path.exists(scaler_path):
        scaler = joblib.load(scaler_path)
        normalized = scaler.transform(vals)
    else:
        max_vals = np.array([500.0, 1500.0, 50000.0, 50000000.0])
        normalized = (vals / max_vals).clip(0, 1)

    return torch.tensor(normalized, dtype=torch.float32)

def _query_latest(influx_client: InfluxDBClient) -> dict:
    """Query field terbaru dari network_stats & hpc_stats."""
    query_api = influx_client.query_api()
    now = datetime.now(timezone.utc)
    start = (now - timedelta(seconds=30)).isoformat()
    raw = {}

    for measurement in ("network_stats", "hpc_stats"):
        flux = f"""
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: {start})
  |> filter(fn: (r) => r._measurement == "{measurement}")
  |> last()
"""
        try:
            tables = query_api.query(flux, org=INFLUX_ORG)
            for table in tables:
                for record in table.records:
                    field = record.get_field()
                    value = record.get_value()
                    if field and value is not None:
                        raw[field] = value
        except Exception as e:
            print(f"[InferenceEngine] ⚠️ Query error ({measurement}): {e}")

    return raw

def main():
    global _running

    parser = argparse.ArgumentParser(description="SATSET SNN Inference Engine")
    parser.add_argument("--model",    type=str,   default=MODEL_PATH, help="Path ke SNN model checkpoint")
    parser.add_argument("--interval", type=float, default=INTERVAL,   help="Inference interval (detik)")
    args = parser.parse_args()

    signal.signal(signal.SIGINT,  lambda s, f: globals().update(_running=False) or None)
    signal.signal(signal.SIGTERM, lambda s, f: globals().update(_running=False) or None)

    print("=" * 60)
    print("  SATSET — Neuromorphic Inference Engine v1.0")
    print("=" * 60)
    print(f"  Model     : {args.model}")
    print(f"  Interval  : {args.interval}s")
    print(f"  Threshold : {THRESHOLD}")
    print("=" * 60)

    # ── Load model ──
    device = torch.device("cpu")
    if os.path.exists(args.model):
        checkpoint = torch.load(args.model, map_location=device, weights_only=True)
        num_steps = checkpoint.get("num_steps", 25)
        model = build_model(num_steps=num_steps).to(device)
        if "model_state_dict" in checkpoint:
            model.load_state_dict(checkpoint["model_state_dict"])
        else:
            model.load_state_dict(checkpoint)
        print(f"[InferenceEngine] ✅ Model loaded (epoch {checkpoint.get('epoch','?')}, val_acc={checkpoint.get('val_acc', 0):.4f})")
    else:
        print(f"[InferenceEngine] ⚠️ Model not found at {args.model}.")
        return

    model.eval()

    # ── Init clients ──
    writer = InfluxWriter()
    mqtt_client = mqtt.Client(client_id="satset-brain-engine")
    try:
        mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        mqtt_client.loop_start()
        print(f"[InferenceEngine] MQTT connected to {MQTT_HOST}:{MQTT_PORT}")
    except Exception as e:
        print(f"[InferenceEngine] ⚠️ MQTT not available: {e}")

    influx_reader = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)

    print(f"\n[InferenceEngine] Running inference every {args.interval}s ...\n")
    tick = 0

    while _running:
        t_start = time.monotonic()

        raw = _query_latest(influx_reader)

        if not raw:
            print(f"[{tick+1:04d}] ⚠️ No data, using fallback values")
            raw = {
                "n_packets": 0.0, "total_bytes": 0.0,
                "cache_misses": 100, "instructions": 5_000_000,
            }

        x_tensor = _normalize_features(raw)
        x_clamped = torch.clamp(x_tensor, 0.0, 1.0)

        # ── Inferensi SNN (50 timestep) ──
        with torch.no_grad():
            spk_out_record = []
            for step in range(50):
                spk_out, mem_out = model(x_clamped)
                spk_out_record.append(spk_out)
            firing_rates = torch.stack(spk_out_record).mean(dim=0)
            score = firing_rates.view(-1)[1].item()

        is_attack = score >= THRESHOLD

        # ── Kirim ke MQTT ──
        payload = json.dumps({
            "threat_score": round(score, 4),
            "is_attack": is_attack,
            "timestamp": time.time(),
        })
        try:
            mqtt_client.publish("satset/brain/threat", payload, qos=1)
        except:
            pass

        # ── Log ──
        tick += 1
        status = "🔴 ATTACK" if is_attack else "🟢 NORMAL"
        print(f"[{tick:04d}] {status} | threat={score:.4f} | pkt_rate={raw.get('n_packets', 0):.1f}")

        elapsed = time.monotonic() - t_start
        time.sleep(max(0.0, args.interval - elapsed))

    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    writer.close()
    influx_reader.close()
    print("[InferenceEngine] Stopped.")

if __name__ == "__main__":
    main()
