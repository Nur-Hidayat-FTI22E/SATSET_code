#!/usr/bin/env python3
"""
SATSET — H-2 : Generator Traffic BENIGN (simulasi sensor IoT via MQTT)
=====================================================================
Mensimulasikan beberapa sensor IoT yang mem-publish telemetri ke broker MQTT
lokal pada kecepatan wajar. Jalankan di latar belakang saat capture.py merekam
skenario 'benign'.

    python3 benign.py --host 127.0.0.1 --port 1883 --sensors 5 --rate 2 --duration 120

Butuh: pip install paho-mqtt
"""
import argparse, time, random, threading, json

def sensor_loop(host, port, sid, rate, stop_at):
    import paho.mqtt.client as mqtt
    c = mqtt.Client(client_id=f"sensor-{sid}")
    try:
        c.connect(host, port, 60)
    except Exception as e:
        print(f"[benign] sensor-{sid} gagal connect: {e}"); return
    c.loop_start()
    topic = f"satset/telemetry/sensor{sid}"
    interval = 1.0 / max(rate, 0.1)
    while time.time() < stop_at:
        payload = json.dumps({
            "sensor": sid,
            "temp": round(random.uniform(25, 35), 2),
            "hum":  round(random.uniform(40, 80), 2),
            "ts":   time.time(),
        })
        c.publish(topic, payload, qos=0)
        time.sleep(interval * random.uniform(0.8, 1.2))   # jitter wajar
    c.loop_stop(); c.disconnect()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--sensors", type=int, default=5)
    ap.add_argument("--rate", type=float, default=2.0, help="pesan/detik per sensor")
    ap.add_argument("--duration", type=float, default=120)
    args = ap.parse_args()

    stop_at = time.time() + args.duration
    print(f"[benign] {args.sensors} sensor @ {args.rate} msg/s selama {args.duration}s")
    threads = [threading.Thread(target=sensor_loop,
                                args=(args.host, args.port, i, args.rate, stop_at))
               for i in range(args.sensors)]
    for t in threads: t.start()
    for t in threads: t.join()
    print("[benign] selesai")

if __name__ == "__main__":
    main()
