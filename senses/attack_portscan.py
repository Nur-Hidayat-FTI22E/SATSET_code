#!/usr/bin/env python3
"""
SATSET — Port Scan Attack (Network + HPC)
Fokus: n_packets tinggi + branch_misses tinggi (kedua layer)
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
    print("\n[PortScan] Stopping...")
    _running = False

def run_attack(rate=500, duration=30):
    """Port scanning — network + HPC"""
    client = mqtt.Client(client_id="satset-portscan-attack")
    try:
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
        client.loop_start()
    except Exception as e:
        print(f"[PortScan] ❌ MQTT error: {e}")
        return

    # Notify attack mode
    client.publish(
        "satset/control/attack_mode",
        json.dumps({"active": True, "type": "portscan", "rate": rate, "ts": time.time()}),
        qos=1
    )

    print("=" * 55)
    print("  SATSET — Port Scan Attack")
    print("=" * 55)
    print(f"  Target Layer : NETWORK + HPC")
    print(f"  Rate         : {rate} pkt/s")
    print(f"  Duration     : {duration}s")
    print(f"  Attacker IP  : {attacker_ip}")
    print("=" * 55)
    print("[PortScan] 🔴 ATTACK STARTED!\n")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    interval = 1.0 / rate
    start_t = time.time()
    pkt_count = 0
    ports = list(range(1, 65535))

    while _running:
        if duration > 0 and (time.time() - start_t) >= duration:
            break

        # Scan berbagai port
        port = random.choice(ports)
        payload = json.dumps({
            "attacker_ip": attacker_ip,
            "src_ip": f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
            "dst_ip": "192.168.1.100",
            "dst_port": port,
            "protocol": random.choice(["TCP", "UDP"]),
            "size": random.randint(64, 1500),
            "data": "X" * random.randint(64, 1500),
            "ts": time.time()
        })

        client.publish("satset/attack/flood", payload, qos=0)
        pkt_count += 1

        if pkt_count % 100 == 0:
            elapsed = time.time() - start_t
            print(f"[PortScan] 🔍 {pkt_count:,} ports scanned | {elapsed:.1f}s | {pkt_count/elapsed:.0f} pps")

        time.sleep(interval)

    # Clear attack mode
    client.publish(
        "satset/control/attack_mode",
        json.dumps({"active": False, "type": "portscan", "ts": time.time()}),
        qos=1
    )
    time.sleep(1)
    client.loop_stop()
    client.disconnect()

    elapsed = time.time() - start_t
    print(f"\n[PortScan] ✅ Attack finished: {pkt_count:,} packets in {elapsed:.2f}s")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--rate", type=int, default=500, help="Packets per second")
    parser.add_argument("--duration", type=int, default=30, help="Duration in seconds")
    args = parser.parse_args()
    run_attack(rate=args.rate, duration=args.duration)

if __name__ == "__main__":
    main()
