#!/usr/bin/env python3
"""
SATSET — HPC Attack Simulator (CPU Intensive)
Fokus: Meningkatkan instructions, cache_misses (HPC Layer)
"""

import json
import os
import random
import signal
import sys
import time
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

_running = True
attacker_ip = f"192.168.1.{random.randint(2, 254)}"

def signal_handler(sig, frame):
    global _running
    print("\n[CPUAttack] Stopping...")
    _running = False

def run_attack(duration=30):
    """CPU intensive attack — meningkatkan instructions, cache_misses"""
    client = mqtt.Client(client_id="satset-hpc-attack")
    try:
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
        client.loop_start()
    except Exception as e:
        print(f"[CPUAttack] ❌ MQTT error: {e}")
        return

    # Notify attack mode
    client.publish(
        "satset/control/attack_mode",
        json.dumps({"active": True, "type": "cpu_attack", "ts": time.time()}),
        qos=1
    )

    print("=" * 55)
    print("  SATSET — HPC Attack (CPU Intensive)")
    print("=" * 55)
    print(f"  Target Layer : HPC")
    print(f"  Duration     : {duration}s")
    print(f"  Attacker IP  : {attacker_ip}")
    print("=" * 55)
    print("[CPUAttack] 🔴 ATTACK STARTED!\n")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    start_t = time.time()
    pkt_count = 0

    while _running:
        if duration > 0 and (time.time() - start_t) >= duration:
            break

        # Paket kecil (seperti normal) — network signature sama dengan benign
        # Tapi CPU load tinggi untuk meningkatkan HPC metrics
        for _ in range(1000):
            _ = [i**2 for i in range(1000)]  # Simulasi CPU load

        payload = json.dumps({
            "attacker_ip": attacker_ip,
            "src_ip": f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
            "dst_ip": "192.168.1.100",
            "protocol": "TCP",
            "size": random.randint(44, 100),
            "data": "X" * random.randint(44, 100),
            "ts": time.time()
        })

        client.publish("satset/attack/flood", payload, qos=0)
        pkt_count += 1

        if pkt_count % 10 == 0:
            elapsed = time.time() - start_t
            print(f"[CPUAttack] 🖥️ {pkt_count} pkts | {elapsed:.1f}s | CPU load: HIGH")

        time.sleep(0.1)

    # Clear attack mode
    client.publish(
        "satset/control/attack_mode",
        json.dumps({"active": False, "type": "cpu_attack", "ts": time.time()}),
        qos=1
    )
    time.sleep(1)
    client.loop_stop()
    client.disconnect()

    elapsed = time.time() - start_t
    print(f"\n[CPUAttack] ✅ Attack finished: {pkt_count} packets in {elapsed:.2f}s")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=30, help="Duration in seconds")
    args = parser.parse_args()
    run_attack(duration=args.duration)

if __name__ == "__main__":
    main()
