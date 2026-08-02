"""
SATSET — Brain Layer
inference_engine.py

Engine inferensi asinkron yang berjalan kontinu:
  1. Ambil data terbaru dari InfluxDB (network_stats + hpc_stats)
  2. Normalisasi → 6 fitur input SNN
  3. Jalankan SNN inference → threat_score
  4. Publish ke MQTT topic satset/brain/threat
  5. Tulis ke InfluxDB (brain_output measurement)
  6. Jika threat_score > THRESHOLD: trigger healing via MQTT

Usage:
    python inference_engine.py [--model model/snn_model.pt] [--interval 1.0]
"""

import argparse
import json
import os
import signal
import sys
import time
import warnings
from snntorch import utils
from datetime import datetime, timezone, timedelta

import torch
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient
import joblib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "senses"))
from influx_writer import InfluxWriter

from snn_model import build_model, SATSETBrain

warnings.filterwarnings("ignore", category=UserWarning)

# Load .env dari root project (bukan dari direktori brain/)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT, ".env"))

INFLUX_URL    = os.getenv("INFLUXDB_URL",    "http://localhost:8086")
INFLUX_TOKEN  = os.environ.get("INFLUXDB_TOKEN")
if not INFLUX_TOKEN:
    raise EnvironmentError("Critical: INFLUXDB_TOKEN is not set in environment. Please configure .env file.")
INFLUX_ORG    = os.getenv("INFLUXDB_ORG",    "satset-lab")
INFLUX_BUCKET = os.getenv("INFLUXDB_BUCKET", "satset")
MQTT_HOST     = os.getenv("MQTT_HOST",       "localhost")
MQTT_PORT     = int(os.getenv("MQTT_PORT",   1883))
THRESHOLD     = float(os.getenv("THREAT_THRESHOLD", 0.85))
INTERVAL      = float(os.getenv("INFERENCE_INTERVAL", 1.0))
MODEL_PATH    = os.getenv("SNN_MODEL_PATH",  os.path.join(os.path.dirname(os.path.abspath(__file__)), "model", "snn_model.pt"))

_running = True

# ── Feature normalizer ───────────────────────────────────────────────────
import numpy as np

_scaler_min = None
_scaler_max = None

_FEATURE_DEFAULTS_MAX = [500.0, 1500.0, 1000.0, 50_000.0, 50_000_000.0, 15_000.0]


def _load_scaler_stats(stats: dict):
    """Load scaler statistics from model checkpoint."""
    global _scaler_min, _scaler_max
    _scaler_min = np.array(stats["feature_min"], dtype=np.float32)
    _scaler_max = np.array(stats["feature_max"], dtype=np.float32)
    print(f"[InferenceEngine] Scaler loaded: {len(_scaler_min)} features")
    for i, name in enumerate(stats.get("feature_names", [])):
        print(f"  {name}: [{_scaler_min[i]:.2f}, {_scaler_max[i]:.2f}]")


def _normalize_features(raw: dict) -> torch.Tensor:
    """Convert raw measurement dict to normalized [1, 6] tensor."""
    vals = np.array([
        raw.get("packet_rate", 0),
        raw.get("packet_size", 0),
        raw.get("interval", 0),
        raw.get("cache_misses", 0),
        raw.get("instructions_retired", 0),
        raw.get("branch_misses", 0),
    ], dtype=np.float32).reshape(1, -1)

    scaler_path = os.path.join(os.path.dirname(__file__), 'model', 'satset_robust_scaler.pkl')
    if os.path.exists(scaler_path):
        scaler = joblib.load(scaler_path)
        normalized = scaler.transform(vals)
    else:
        max_vals = np.array([500.0, 1500.0, 3.5, 210000.0, 267000000.0, 100000.0])
        normalized = (vals / max_vals).clip(0,1)

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

    # ── Load model ─────────────────────────────────────────
    device = torch.device("cpu")
    if os.path.exists(args.model):
        checkpoint = torch.load(args.model, map_location=device, weights_only=True)
        num_steps  = checkpoint.get("num_steps", 25)
        model = build_model(num_steps=num_steps).to(device)
        if "model_state_dict" in checkpoint:
            model.load_state_dict(checkpoint["model_state_dict"])
        else:
            model.load_state_dict(checkpoint)
        print(f"[InferenceEngine] ✅ Model loaded (epoch {checkpoint.get('epoch','?')}, "
              f"val_acc={checkpoint.get('val_acc', 0):.4f})")
        
        scaler_path = args.model.replace(".pt", "_scaler.json")
        if os.path.exists(scaler_path):
            import json as _json
            with open(scaler_path) as f:
                _load_scaler_stats(_json.load(f))
        else:
            print("[InferenceEngine] ⚠️ No scaler JSON found — using default ranges")
    else:
        print(f"[InferenceEngine] ⚠️ Model not found at {args.model}. Using untrained model.")
        model = build_model().to(device)

    model.eval()

    # ── Init clients ───────────────────────────────────────
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

        # 1. Query latest telemetry
        raw = _query_latest(influx_reader)

        # 2. Use fallback defaults if no data yet
        if not raw:
            raw = {
                "packet_rate": 0.0, "packet_size": 0.0, "interval": 1000.0,
                "cache_misses": 100, "instructions_retired": 5_000_000, "branch_misses": 200,
            }

        # 3. Extract attacker_ip from raw data (FIXED - setelah raw diisi)
        attacker_ip = raw.get("attacker_ip", None)
        
        # Fallback: jika tidak ada, gunakan simulated IP untuk testing
        if not attacker_ip:
            import random
            attacker_ip = f"192.168.1.{random.randint(2, 254)}"

        # 4. Normalize & infer
        x_raw = _normalize_features(raw)
        if not isinstance(x_raw, torch.Tensor):
            x_tensor = torch.tensor(x_raw, dtype=torch.float32)
        else:
            x_tensor = x_raw.clone().detach().float()

        x_clamped = torch.clamp(x_tensor, 0.0, 1.0)

        model.eval()
        utils.reset(model)
        #spike_train = spikegen.rate(x, num_steps=50)
        
        with torch.no_grad():
            score = model.threat_score(x_clamped)
#            spk_out_record = []
#            for step in range(50):
#                spk_out, mem_out = model(x_clamped)
#                spk_out_record.append(spk_out)

#            firing_rates = torch.stack(spk_out_record).mean(dim=0)
#            score = firing_rates.view(-1)[1].item()

        is_attack = score >= THRESHOLD

        #print(f"[DEBUG] Input ke SNN: {x_clamped.tolist()}")

        display_ip = attacker_ip if is_attack else "-"
        status_icon = "ATTACK" if is_attack else "NORMAL"
        # 5. Write to InfluxDB
        try:
            writer.write_brain_output(
                threat_score=score,
                is_attack=is_attack,
                spike_rate=score,
            )
        except Exception as e:
            print(f"[InferenceEngine] Write error: {e}")

        # 6. Publish to MQTT (FIXED - attacker_ip sekarang terdefinisi)
        payload = json.dumps({
            "threat_score": round(score, 4),
            "is_attack":    is_attack,
            "attacker_ip":  attacker_ip,  # SEKARANG SUDAH ADA
            "features":     x_clamped.tolist(),
            "timestamp":    time.time(),
        })
        try:
            mqtt_client.publish("satset/brain/threat", payload, qos=1)
        except Exception as e:
            pass

        # 7. Log
        tick += 1
        print(f"[{tick:04d}] {status_icon} | threat={score:.4f} | attacker={display_ip} | "
              f"pkt_rate={raw.get('packet_rate', 0):.1f}")

        # 8. Sleep precise interval
        elapsed = time.monotonic() - t_start
        time.sleep(max(0.0, args.interval - elapsed))

    # ── Cleanup ────────────────────────────────────────────
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    writer.close()
    influx_reader.close()
    print("[InferenceEngine] Stopped.")


if __name__ == "__main__":
    main()

