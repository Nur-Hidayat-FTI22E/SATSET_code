#!/usr/bin/env python3
"""
Simulasi untuk presentasi sidang
Mengirim threat score bervariasi ke MQTT tanpa perlu InfluxDB
"""

import json
import random
import time
import paho.mqtt.client as mqtt

# Konfigurasi MQTT
MQTT_HOST = "localhost"
MQTT_PORT = 1883
THRESHOLD = 0.85

# Inisialisasi MQTT
mqtt_client = mqtt.Client(client_id="satset-simulator")
mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
mqtt_client.loop_start()

print("=" * 60)
print("  SATSET — Simulator untuk Presentasi")
print("=" * 60)
print(f"  Threshold: {THRESHOLD}")
print("  Mengirim threat score ke MQTT setiap 2 detik...")
print("=" * 60)

tick = 0
try:
    while True:
        tick += 1
        
        # Simulasi threat score bervariasi
        # Mode: normal (0.2-0.5) lalu attack (0.9-1.0) lalu normal lagi
        if tick % 5 == 0:  # Setiap 5 detik jadi attack
            score = random.uniform(0.90, 0.98)
            is_attack = True
            attacker_ip = f"192.168.1.{random.randint(2, 254)}"
        else:
            score = random.uniform(0.1, 0.5)
            is_attack = False
            attacker_ip = None
        
        # Kirim ke MQTT
        payload = json.dumps({
            "threat_score": round(score, 4),
            "is_attack": is_attack,
            "attacker_ip": attacker_ip,
            "timestamp": time.time(),
        })
        mqtt_client.publish("satset/brain/threat", payload, qos=1)
        
        # Log
        status = "🔴 ATTACK" if is_attack else "🟢 NORMAL"
        print(f"[{tick:04d}] {status} | threat={score:.4f} | attacker={attacker_ip if is_attack else '-'}")
        
        time.sleep(2)
        
except KeyboardInterrupt:
    print("\n[Simulator] Stopped.")

mqtt_client.loop_stop()
mqtt_client.disconnect()
