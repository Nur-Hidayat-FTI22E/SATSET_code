"""
SATSET — Brain Layer
inference_engine.py (2 Model: Network + HPC + Attack Mode)
"""

import argparse
import json
import os
import signal
import sys
import time
import warnings
import random
import numpy as np
import torch
import torch.nn as nn
import paho.mqtt.client as mqtt
import joblib
from dotenv import load_dotenv
import snntorch as snn
from snntorch import surrogate

warnings.filterwarnings("ignore", category=UserWarning)

# Load environment variables
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT, ".env"))

# Konfigurasi
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
THRESHOLD = float(os.getenv("THREAT_THRESHOLD", 0.6))
INTERVAL = float(os.getenv("INFERENCE_INTERVAL", 1.0))

_running = True
attack_active = False  # ← Status attack dari Senses

# ============================================================
# MODEL NETWORK (2 fitur)
# ============================================================

class SNN_Network(nn.Module):
    def __init__(self, steps=16, input_size=2, hidden=64, output=2, beta=0.9):
        super().__init__()
        self.steps = steps
        g = surrogate.fast_sigmoid(slope=25)
        self.fc1 = nn.Linear(input_size, hidden)
        self.lif1 = snn.Leaky(beta=beta, spike_grad=g, learn_beta=True, learn_threshold=True)
        self.drop = nn.Dropout(0.3)
        self.fc2 = nn.Linear(hidden, output)
        self.lif2 = snn.Leaky(beta=beta, spike_grad=g, learn_beta=True, learn_threshold=True)

    def forward(self, x):
        m1 = self.lif1.init_leaky()
        m2 = self.lif2.init_leaky()
        out = []
        for _ in range(self.steps):
            s1, m1 = self.lif1(self.fc1(x), m1)
            s1 = self.drop(s1)
            s2, m2 = self.lif2(self.fc2(s1), m2)
            out.append(s2)
        return torch.stack(out)  # shape: [steps, batch, output]

# ============================================================
# MODEL HPC (3 fitur)
# ============================================================

class SNN_HPC(nn.Module):
    def __init__(self, steps=8, input_size=3, hidden=16, output=2, beta=0.9):
        super().__init__()
        self.steps = steps
        g = surrogate.fast_sigmoid(slope=25)
        self.fc1 = nn.Linear(input_size, hidden)
        self.lif1 = snn.Leaky(beta=beta, spike_grad=g, learn_beta=True, learn_threshold=True)
        self.drop = nn.Dropout(0.3)
        self.fc2 = nn.Linear(hidden, output)
        self.lif2 = snn.Leaky(beta=beta, spike_grad=g, learn_beta=True, learn_threshold=True)

    def forward(self, x):
        m1 = self.lif1.init_leaky()
        m2 = self.lif2.init_leaky()
        out = []
        for _ in range(self.steps):
            s1, m1 = self.lif1(self.fc1(x), m1)
            s1 = self.drop(s1)
            s2, m2 = self.lif2(self.fc2(s1), m2)
            out.append(s2)
        return torch.stack(out)  # shape: [steps, batch, output]

# ============================================================
# MQTT CALLBACK
# ============================================================

def on_connect(client, userdata, flags, rc):
    """Callback ketika MQTT terhubung"""
    if rc == 0:
        print(f"[InferenceEngine] MQTT connected to {MQTT_HOST}:{MQTT_PORT}")
        # Subscribe ke topic attack_mode dari Senses
        client.subscribe("satset/control/attack_mode")
        print("[InferenceEngine] Subscribed to satset/control/attack_mode")
    else:
        print(f"[InferenceEngine] ❌ MQTT connection failed with code {rc}")

def on_attack_message(client, userdata, msg):
    """Callback ketika menerima pesan attack dari Senses"""
    global attack_active
    try:
        data = json.loads(msg.payload)
        attack_active = data.get("active", False) or data.get("attack", False)
        status = "ON" if attack_active else "OFF"
        print(f"[InferenceEngine] 🚨 ATTACK MODE: {status}")
    except Exception as e:
        print(f"[InferenceEngine] ⚠️ Parse error: {e}")

# ============================================================
# MAIN
# ============================================================

def main():
    global _running, attack_active

    parser = argparse.ArgumentParser(description="SATSET Inference Engine (2 Model)")
    parser.add_argument("--interval", type=float, default=INTERVAL)
    parser.add_argument("--model_network", type=str, default="model/satset_h1_model.pt")
    parser.add_argument("--scaler_network", type=str, default="model/satset_h1_scaler.pkl")
    parser.add_argument("--model_hpc", type=str, default="model/snn_model_hpc.pt")
    parser.add_argument("--scaler_hpc", type=str, default="model/snn_model_hpc_scaler.pkl")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, lambda s, f: globals().update(_running=False) or None)
    signal.signal(signal.SIGTERM, lambda s, f: globals().update(_running=False) or None)

    print("=" * 60)
    print("  SATSET — Inference Engine (2 Model + Attack Mode)")
    print("=" * 60)
    print(f"  Threshold: {THRESHOLD}")
    print(f"  Interval : {args.interval}s")
    print("=" * 60)

    device = torch.device("cpu")

    # ── Load Model Network ──
    print("\n[1] Loading Network Model...")
    model_network = SNN_Network(steps=16, input_size=2, hidden=64).to(device)
    model_network.load_state_dict(torch.load(args.model_network, map_location=device, weights_only=True))
    model_network.eval()
    scaler_network = joblib.load(args.scaler_network)
    print("   ✅ Network model loaded")

    # ── Load Model HPC ──
    print("\n[2] Loading HPC Model...")
    model_hpc = SNN_HPC(steps=8, input_size=3, hidden=16).to(device)
    model_hpc.load_state_dict(torch.load(args.model_hpc, map_location=device, weights_only=True))
    model_hpc.eval()
    scaler_hpc = joblib.load(args.scaler_hpc)
    print("   ✅ HPC model loaded")

    # ── MQTT ──
    mqtt_client = mqtt.Client(client_id="satset-brain-engine")
    mqtt_client.on_connect = on_connect
    mqtt_client.message_callback_add("satset/control/attack_mode", on_attack_message)

    try:
        mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        mqtt_client.loop_start()
    except Exception as e:
        print(f"MQTT error: {e}")

    print(f"\nRunning inference every {args.interval}s ...\n")
    tick = 0

    while _running:
        tick += 1

        # ── Data input berdasarkan status attack ──
        if attack_active:
            # MODE ATTACK: threat score tinggi
            n_packets = random.uniform(1000, 50000)
            total_bytes = random.uniform(100000, 5000000)
            cache_misses = random.uniform(1000000, 50000000)
            instructions = random.uniform(100000000, 10000000000)
            branch_misses = random.uniform(100000, 5000000)
        else:
            # MODE NORMAL: threat score rendah
            n_packets = random.uniform(10, 500)
            total_bytes = random.uniform(1000, 50000)
            cache_misses = random.uniform(1000, 50000)
            instructions = random.uniform(1000000, 100000000)
            branch_misses = random.uniform(1000, 30000)

        # ── Normalisasi Network ──
        network_data = np.array([[n_packets, total_bytes]])
        network_data = scaler_network.transform(network_data)
        network_tensor = torch.tensor(network_data, dtype=torch.float32)

        # ── Normalisasi HPC ──
        hpc_data = np.array([[cache_misses, instructions, branch_misses]])
        hpc_data = scaler_hpc.transform(hpc_data)
        hpc_tensor = torch.tensor(hpc_data, dtype=torch.float32)

        # ── Inferensi Network ──
        with torch.no_grad():
            spk_rec = model_network(network_tensor)
            spk_sum = spk_rec.sum(dim=0)
            prob = torch.softmax(spk_sum, dim=1)
            score_network = prob[0][1].item()

        # ── Inferensi HPC ──
        with torch.no_grad():
            spk_rec = model_hpc(hpc_tensor)
            spk_sum = spk_rec.sum(dim=0)
            prob = torch.softmax(spk_sum, dim=1)
            score_hpc = prob[0][1].item()

        # ── Ensemble ──
        final_score = max(score_network, score_hpc)
        is_attack = final_score >= THRESHOLD

        # ── Kirim ke MQTT ──
        payload = json.dumps({
            "threat_score": round(final_score, 4),
            "is_attack": is_attack,
            "score_network": round(score_network, 4),
            "score_hpc": round(score_hpc, 4),
            "attacker_ip": "192.168.1.100" if is_attack else None,
            "timestamp": time.time(),
        })
        try:
            mqtt_client.publish("satset/brain/threat", payload, qos=1)
        except:
            pass

        # ── Log ──
        status_icon = "🔴 ATTACK" if is_attack else "🟢 NORMAL"
        attack_status_text = "ON " if attack_active else "OFF"
        print(f"[{tick:04d}] {status_icon} | final={final_score:.4f} | net={score_network:.4f} | hpc={score_hpc:.4f} | attack_mode={attack_status_text}")

        time.sleep(args.interval)

    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    print("[InferenceEngine] Stopped.")


if __name__ == "__main__":
    main()
