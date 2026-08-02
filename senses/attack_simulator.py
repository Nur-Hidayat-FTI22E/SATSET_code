"""
SATSET — Senses Layer
attack_simulator.py

Mensimulasikan serangan DDoS hyper-volumetrik dengan cara:
  1. Mempublish paket MQTT burst rate tinggi ke topic satset/attack/flood
  2. Mensimulasikan HPC anomaly melalui flag di shared state (MQTT control)

Digunakan untuk:
  - Validasi deteksi SNN Brain (harus spike threat_score > 0.85)
  - Mengukur MTTR (time dari attack start ke healing selesai)

Usage:
    python attack_simulator.py [--duration 30] [--rate 500]
"""

import argparse
import json
import os
import random
import signal
import sys
import time
#import socket

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

_running = True

#attacker_ip = socket.gethostbyname(socket.gethostname())
attacker_ip = f"192.168.1.{random.randint(2, 254)}"

def _signal_handler(sig, frame):
    global _running
    print("\n[AttackSim] Stopping attack simulation...")
    _running = False


def run_attack(rate: int, duration: int):
    """
    Simulate a DDoS flood attack by publishing to MQTT at high rate.

    Args:
        rate: packets per second to publish
        duration: attack duration in seconds (0 = unlimited)
    """
    client = mqtt.Client(client_id="satset-attack-simulator")
    try:
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
        client.loop_start()
    except Exception as e:
        print(f"[AttackSim] ❌ Cannot connect to MQTT: {e}")
        print("[AttackSim] ℹ️  Make sure MQTT broker is running: make up")
        return

    # Wait for connection to establish before publishing control signals
    time.sleep(0.5)

    # Notify other SATSET components that attack is starting
    client.publish(
        "satset/control/attack_mode",
        json.dumps({"active": True, "rate": rate, "ts": time.time()}),
        qos=1,
    )

    print("=" * 55)
    print("  SATSET — DDoS Attack Simulator")
    print("=" * 55)
    print(f"  Target    : satset/attack/flood")
    print(f"  Rate      : {rate} pkt/s")
    print(f"  Duration  : {'Unlimited (Ctrl+C to stop)' if duration == 0 else f'{duration}s'}")
    print(f"  Payload   : 512–8192 bytes (random)")
    print("=" * 55)
    print("[AttackSim] 🔴 ATTACK STARTED!\n")

    signal.signal(signal.SIGINT,  _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    interval = 1.0 / rate
    start_t  = time.time()
    pkt_count = 0

    while _running:
        if duration > 0 and (time.time() - start_t) >= duration:
            print(f"\n[AttackSim] Duration reached ({duration}s). Stopping.")
            break

        # Generate flood packet with random size payload
        payload_size = random.randint(512, 8192)
        payload = json.dumps({
            "attacker_ip": attacker_ip,  # TAMBAHKAN INI
            "src_ip":    f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
            "dst_ip":    "192.168.1.100",
            "protocol":  random.choice(["UDP", "TCP", "ICMP"]),
            "size":      payload_size,
            "data":      "X" * min(payload_size, 256),
            "ts":        time.time(),
        })

        client.publish("satset/attack/flood", payload, qos=0)
        pkt_count += 1

        if pkt_count % rate == 0:
            elapsed = time.time() - start_t
            print(f"[AttackSim] 📦 {pkt_count:,} pkts sent | {elapsed:.1f}s elapsed | {pkt_count/elapsed:.0f} pps actual")

        time.sleep(interval)

    # Clear attack mode — tunggu 1 detik agar message terkirim sebelum disconnect
    client.publish(
        "satset/control/attack_mode",
        json.dumps({"active": False, "ts": time.time()}),
        qos=1,
    )
    time.sleep(1.0)   # pastikan MQTT broker menerima pesan sebelum disconnect
    client.loop_stop()
    client.disconnect()

    elapsed = time.time() - start_t
    print(f"\n[AttackSim] ✅ Attack finished: {pkt_count:,} packets in {elapsed:.2f}s ({pkt_count/elapsed:.0f} pps avg)")


def main():
    parser = argparse.ArgumentParser(description="SATSET DDoS Attack Simulator")
    parser.add_argument("--rate",     type=int, default=300,  help="Packets per second (default: 300)")
    parser.add_argument("--duration", type=int, default=60,   help="Duration in seconds, 0=unlimited (default: 60)")
    args = parser.parse_args()

    run_attack(rate=args.rate, duration=args.duration)


if __name__ == "__main__":
    main()
