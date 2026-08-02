"""
SATSET — Senses Layer
telemetry_agent.py

Loop utama telemetri. Mengkoordinasikan:
  1. NetworkCollector  — statistik paket MQTT
  2. HPCSimulator      — hardware performance counters
  3. InfluxWriter      — kirim data ke InfluxDB

Setiap INTERVAL_SECONDS (default: 1 detik), satu titik data
dari setiap lapisan dikumpulkan secara sinkron dan ditulis ke InfluxDB.

Usage:
    python telemetry_agent.py [--attack]

Flags:
    --attack    Aktifkan mode simulasi serangan DDoS dari awal
"""

import argparse
import json
import signal
import time
import os

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

# Load .env dari root project
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT, ".env"))

from hpc_collector import HPCCollector
from influx_writer import InfluxWriter
from network_collector import NetworkCollector

INTERVAL  = float(os.getenv("INFERENCE_INTERVAL", 1.0))
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

# Auto-timeout: jika attack mode ON tapi packet_rate=0 selama N detik, revert ke NORMAL
ATTACK_TIMEOUT_TICKS = 10

# ── Global state ───────────────────────────────────────────
_running     = True
_hpc_sim_ref = None
_attack_start_time = 0  # timestamp saat attack mode diaktifkan


def _signal_handler(sig, frame):
    global _running
    print("\n[TelemetryAgent] Shutting down gracefully...")
    _running = False


def _on_attack_mode(client, userdata, msg):
    """Toggle HPC attack mode berdasarkan sinyal dari attack_simulator."""
    global _hpc_sim_ref, _attack_start_time
    try:
        data   = json.loads(msg.payload.decode())
        active = data.get("active", False)
        if _hpc_sim_ref is not None:
            _hpc_sim_ref.set_attack_mode(active)
            if active:
                _attack_start_time = time.time()
            status = "🔴 ATTACK MODE ON" if active else "🟢 NORMAL MODE"
            print(f"\n[TelemetryAgent] {status} (via MQTT control signal)\n")
    except Exception as e:
        print(f"[TelemetryAgent] ⚠️  attack_mode parse error: {e}")


def main():
    global _running, _hpc_sim_ref

    parser = argparse.ArgumentParser(description="SATSET Telemetry Agent")
    parser.add_argument("--attack", action="store_true", help="Start in attack simulation mode")
    args = parser.parse_args()

    # ── Init components ────────────────────────────────────
    print("=" * 55)
    print("  SATSET — Cross-Layer Telemetry Agent v1.0")
    print("=" * 55)

    writer    = InfluxWriter()
    hpc_sim   = HPCCollector(attack_mode=args.attack)
    net_col   = NetworkCollector()
    _hpc_sim_ref = hpc_sim

    net_col.start()

    def _on_connect(client, userdata, flags, rc, *args):
        if rc == 0:
            client.subscribe("satset/control/attack_mode", qos=1)
            print(f"[TelemetryAgent] 📡 Listening attack_mode on {MQTT_HOST}:{MQTT_PORT}")
        else:
            print(f"[TelemetryAgent] ⚠️  MQTT Connect failed: rc={rc}")

    # ── Subscribe ke attack_mode control signal ────────────
    ctrl_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="satset-senses-ctrl")
    ctrl_client.on_connect = _on_connect
    ctrl_client.on_message = _on_attack_mode
    try:
        ctrl_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        ctrl_client.loop_start()
    except Exception as e:
        print(f"[TelemetryAgent] ⚠️  Cannot connect or start MQTT: {e}")

    signal.signal(signal.SIGINT,  _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    if args.attack:
        print("[TelemetryAgent] ⚠️  Starting in ATTACK mode!")
    else:
        print("[TelemetryAgent] ✅ Starting in NORMAL mode.")

    print(f"[TelemetryAgent] Writing to InfluxDB every {INTERVAL}s ...\n")

    tick = 0
    zero_pkt_count = 0   # counter untuk auto-timeout attack mode

    while _running:
        start_t = time.monotonic()

        # 1. Collect Network Layer metrics
        net_stats = net_col.flush_stats(window_seconds=INTERVAL)
        real_packet_rate = net_stats["packet_rate"]

        # 2. Saat attack mode aktif, inject synthetic attack traffic
        #    karena MQTT flood loopback tidak terlihat di /proc/net/dev
        if net_stats["packet_rate"] == 0:
            net_stats["packet_rate"] = 100.0
            net_stats["packet_size"] = 500.0
            net_stats["interval"] = 0.01

        # 3. Handle Auto-timeout
        if hpc_sim.attack_mode:
            grace_elapsed = time.time() - _attack_start_time
            if grace_elapsed > 5 and real_packet_rate == 0:
                zero_pkt_count += 1
            else:
                zero_pkt_count = 0

            if zero_pkt_count >= ATTACK_TIMEOUT_TICKS:
                hpc_sim.set_attack_mode(False)
                zero_pkt_count = 0
                print(f"\n[TelemetryAgent] 🟢 NORMAL MODE (auto-timeout: no attack traffic for {ATTACK_TIMEOUT_TICKS}s)\n")
        else:
            zero_pkt_count = 0

        # 3. Collect HPC metrics
        hpc_stats = hpc_sim.read()

        # 4. Write to InfluxDB
        try:
            writer.write_network_stats(
                packet_rate=net_stats["packet_rate"],
                packet_size=net_stats["packet_size"],
                interval=net_stats["interval"],
            )
            print(f"[DEBUG] HPC: cache={hpc_stats['cache_misses']}, instr={hpc_stats['instructions_retired']}, branch={hpc_stats['branch_misses']}")
            writer.write_hpc_stats(
                cache_misses=hpc_stats["cache_misses"],
                instructions_retired=hpc_stats["instructions_retired"],
                branch_misses=hpc_stats["branch_misses"],
                cpu_usage=hpc_stats["cpu_usage"],
            )
        except Exception as e:
            print(f"[TelemetryAgent] ⚠️  Write error: {e}")

        # 5. Log to stdout
        tick += 1
        mode_tag = "🔴 ATTACK" if hpc_sim.attack_mode else "🟢 NORMAL"
        print(
            f"[{tick:04d}] {mode_tag} | "
            f"pkt_rate={net_stats['packet_rate']:.1f} pps | "
            f"cache_miss={hpc_stats['cache_misses']:,} | "
            f"cpu={hpc_stats['cpu_usage']:.1f}%"
        )

        # 6. Precise interval sleep
        elapsed = time.monotonic() - start_t
        sleep_t = max(0.0, INTERVAL - elapsed)
        time.sleep(sleep_t)

    # ── Cleanup ────────────────────────────────────────────
    ctrl_client.loop_stop()
    ctrl_client.disconnect()
    net_col.stop()
    writer.close()
    print("[TelemetryAgent] Stopped.")


if __name__ == "__main__":
    main()
