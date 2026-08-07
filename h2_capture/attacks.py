#!/usr/bin/env python3
"""
SATSET — H-2 : Generator SERANGAN Berlabel (semua ke localhost / lo)
====================================================================
Menyediakan beberapa skenario serangan untuk direkam sebagai label=1.
Jalankan di latar belakang saat capture.py merekam skenario terkait.

    sudo python3 attacks.py --attack ddos      --target 127.0.0.1 --port 1883 --duration 120
    sudo python3 attacks.py --attack portscan  --target 127.0.0.1 --duration 120
         python3 attacks.py --attack mqtt_flood --target 127.0.0.1 --port 1883 --duration 120

Kebutuhan:
  ddos      → hping3   (sudo apt install hping3)      + sudo (raw socket)
  portscan  → nmap     (sudo apt install nmap)        + sudo (SYN scan)
  mqtt_flood→ paho-mqtt (pip install paho-mqtt)
"""
import argparse, subprocess, time, threading, os, sys


def run_for(duration, cmd):
    """Jalankan cmd sebagai subprocess, hentikan setelah `duration` detik."""
    print(f"[attack] menjalankan: {' '.join(cmd)}  (~{duration}s)")
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(duration)
    finally:
        p.terminate()
        try: p.wait(timeout=3)
        except subprocess.TimeoutExpired: p.kill()
    print("[attack] selesai")


def ddos(target, port, duration):
    # SYN flood ke port broker MQTT (loopback). --flood = secepat mungkin.
    run_for(duration, ["hping3", "--flood", "-S", "-p", str(port), target])


def portscan(target, duration):
    # Scan berulang selama durasi (nmap satu kali cepat, diulang).
    end = time.time() + duration
    print(f"[attack] portscan {target} berulang selama {duration}s")
    while time.time() < end:
        subprocess.run(["nmap", "-sS", "-T4", "-p-", target],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("[attack] selesai")


def mqtt_flood(target, port, duration):
    # Churn koneksi (connect → burst publish → disconnect → ulang). Penanganan
    # koneksi = kerja CPU berat → sinyal HPC paling kuat. Bursty secara alami;
    # jendela tak-aktif dibersihkan di tahap training (activity-based labeling).
    import paho.mqtt.client as mqtt
    end = time.time() + duration
    print(f"[attack] mqtt_flood {target}:{port} selama {duration}s")

    def worker(wid):
        n = 0
        while time.time() < end:
            try:
                c = mqtt.Client(client_id=f"flood-{wid}-{n}"); n += 1
                c.connect(target, port, keepalive=5)
                for _ in range(100):
                    c.publish(f"satset/flood/{wid}", b"x" * 512, qos=0)
                c.disconnect()
            except Exception:
                time.sleep(0.05)                       # broker menolak → retry cepat
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(30)]
    for t in threads: t.start()
    for t in threads: t.join()
    print("[attack] selesai")


def cpu_attack(duration):
    # Simulasi MALWARE ON-DEVICE (mis. cryptominer/payload pasca-kompromi):
    # beban CPU + akses memori acak → instructions & cache_misses MELEDAK,
    # tapi traffic jaringan ~NOL. Inilah kasus di mana fitur jaringan BUTA
    # dan HPC yang menyelamatkan — bukti inti cross-layer.
    end = time.time() + duration
    print(f"[attack] cpu_attack (on-device) selama {duration}s — tanpa traffic jaringan")

    def worker():
        buf = bytearray(16 * 1024 * 1024)   # 16MB → banyak cache miss
        x = 12345
        while time.time() < end:
            for i in range(0, len(buf), 64):        # stride 64B = 1 cache line
                buf[i] = (buf[i] + 1) & 0xff
            for _ in range(200000):                 # beban aritmetika (instructions)
                x = (x * 1103515245 + 12345) & 0x7fffffff
    threads = [threading.Thread(target=worker) for _ in range(os.cpu_count() or 4)]
    for t in threads: t.start()
    for t in threads: t.join()
    print("[attack] selesai")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attack", required=True,
                    choices=["ddos", "portscan", "mqtt_flood", "cpu_attack"])
    ap.add_argument("--target", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--duration", type=float, default=120)
    args = ap.parse_args()

    if args.attack == "ddos":
        ddos(args.target, args.port, args.duration)
    elif args.attack == "portscan":
        portscan(args.target, args.duration)
    elif args.attack == "mqtt_flood":
        mqtt_flood(args.target, args.port, args.duration)
    elif args.attack == "cpu_attack":
        cpu_attack(args.duration)


if __name__ == "__main__":
    main()
