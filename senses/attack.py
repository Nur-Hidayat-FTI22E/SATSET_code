#!/usr/bin/env python3
"""
SATSET — Attack Simulator
Mengirim sinyal attack ke MQTT untuk mengaktifkan mode serangan
"""

import json
import time
import random
import sys
import select
import paho.mqtt.client as mqtt

# Konfigurasi MQTT
MQTT_HOST = "localhost"
MQTT_PORT = 1883

# Inisialisasi MQTT
mqtt_client = mqtt.Client(client_id="satset-attack-sim")
try:
    mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    mqtt_client.loop_start()
    print(f"[AttackSim] MQTT connected to {MQTT_HOST}:{MQTT_PORT}")
except Exception as e:
    print(f"[AttackSim] ❌ MQTT connection failed: {e}")
    sys.exit(1)

print("=" * 60)
print("  SATSET — Attack Simulator")
print("=" * 60)
print("  Tekan ENTER untuk START/STOP attack")
print("  Tekan Ctrl+C untuk keluar")
print("=" * 60)

attack_running = False
tick = 0

def send_attack_status(status):
    """Kirim status attack ke MQTT"""
    payload = json.dumps({
        "attack": status,
        "type": "flood",
        "rate": 100,
        "duration": 60,
        "timestamp": time.time(),
    })
    mqtt_client.publish("satset/attack/status", payload, qos=1)
    print(f"[AttackSim] 📤 Attack status sent: {status}")

try:
    while True:
        # Cek input keyboard (tanpa blocking)
        if select.select([sys.stdin], [], [], 0.1)[0]:
            line = sys.stdin.readline()
            if line.strip() == "":
                attack_running = not attack_running
                status_text = "STARTED" if attack_running else "STOPPED"
                print(f"\n[AttackSim] 🚨 ATTACK {status_text}!")
                send_attack_status(attack_running)
                print("[AttackSim] Press ENTER again to toggle\n")
        
        if attack_running:
            tick += 1
            print(f"[AttackSim] 🔴 {tick*100} pkts sent | {tick:.1f}s elapsed")
            time.sleep(1)
        else:
            time.sleep(0.5)

except KeyboardInterrupt:
    print("\n[AttackSim] Stopped.")

mqtt_client.loop_stop()
mqtt_client.disconnect()
