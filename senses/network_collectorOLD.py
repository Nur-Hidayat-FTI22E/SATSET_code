"""
SATSET — Senses Layer
network_collector.py

Subscribe ke MQTT broker dan mengumpulkan statistik paket:
- packet_rate  : jumlah paket per detik
- packet_size  : rata-rata ukuran payload (bytes)
- interval     : rata-rata interval antar paket (ms)

Topik yang di-subscribe:
- satset/network/telemetry  → data normal
- satset/attack/flood       → data simulasi serangan DDoS
"""

import json
import threading
import time
import os

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

TOPICS = [
    ("satset/network/telemetry", 0),
    ("satset/attack/flood",      0),
]


class NetworkCollector:
    """
    Thread-safe MQTT-based network statistics collector.
    Mengakumulasi paket selama 1 window, lalu flush ke caller.
    """

    def __init__(self):
        self._lock   = threading.Lock()
        self._pkts   = []          # list of (timestamp, size)
        self._connected = False

        self._client = mqtt.Client(client_id="satset-senses-collector")
        self._client.on_connect    = self._on_connect
        self._client.on_message    = self._on_message
        self._client.on_disconnect = self._on_disconnect

    # ── MQTT callbacks ────────────────────────────────────────────────────
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            client.subscribe(TOPICS)
            print(f"[NetworkCollector] Connected to MQTT broker {MQTT_HOST}:{MQTT_PORT}")
        else:
            print(f"[NetworkCollector] Connection failed — rc={rc}")

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        print(f"[NetworkCollector] Disconnected — rc={rc}")

    def _on_message(self, client, userdata, msg):
        now = time.time()
        try:
            payload = json.loads(msg.payload.decode())
            size = payload.get("size", len(msg.payload))
        except Exception:
            size = len(msg.payload)

        with self._lock:
            self._pkts.append((now, size))

    # ── Public API ────────────────────────────────────────────────────────
    def start(self):
        """Connect dan mulai loop MQTT di background thread."""
        try:
            self._client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            self._client.loop_start()
        except Exception as e:
            print(f"[NetworkCollector] Cannot connect to MQTT: {e}. Running in offline mode.")

    def stop(self):
        self._client.loop_stop()
        self._client.disconnect()

    def flush_stats(self, window_seconds: float = 1.0) -> dict:
        """
        Flush telemetry window dan kembalikan statistik.
        Thread-safe.

        Returns:
            {
                "packet_rate": float,   # pkt/s
                "packet_size": float,   # bytes rata-rata
                "interval":    float,   # ms rata-rata antar paket
            }
        """
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            window = [(t, s) for t, s in self._pkts if t >= cutoff]
            self._pkts = [p for p in self._pkts if p[0] >= cutoff]

        if not window:
            return {"packet_rate": 0.0, "packet_size": 0.0, "interval": 0.0}

        sizes     = [s for _, s in window]
        times     = [t for t, _ in window]
        rate      = len(window) / window_seconds
        avg_size  = sum(sizes) / len(sizes)

        if len(times) > 1:
            intervals = [(times[i+1] - times[i]) * 1000 for i in range(len(times)-1)]
            avg_interval = sum(intervals) / len(intervals)
        else:
            avg_interval = 0.0

        return {
            "packet_rate": round(rate, 3),
            "packet_size": round(avg_size, 2),
            "interval":    round(avg_interval, 3),
        }
