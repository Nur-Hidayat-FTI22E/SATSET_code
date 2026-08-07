#!/usr/bin/env python3
"""
SATSET — MTTR : Ukur waktu pulih end-to-end (deteksi → layanan pulih)
====================================================================
Mengukur Mean Time To Recovery pipeline self-healing SATSET:

    t0 = threat dipublish ke satset/brain/threat  (deteksi)
    t1 = broker MQTT (satset-mosquitto) MELAYANI LAGI setelah di-restart Hand
    MTTR = t1 - t0

Catatan desain (temuan D-1): aksi healing me-restart broker — kanal yang sama
yang dipakai mengirim 'healed'. Karena itu pengukuran memakai poll port (anti
hilang pesan). Pesan 'satset/hand/healed' tetap ditangkap sebagai bonus bila
sempat terkirim.

Jalankan (broker & hand harus hidup):
    python3 measure_mttr.py --trials 10 --gap 20 --score 0.85

Prasyarat: pip install paho-mqtt ; Hand (heal_trigger.py) sedang berjalan.
"""
import argparse, json, socket, time, statistics as st

def port_up(host, port, timeout=0.3):
    try:
        s = socket.create_connection((host, port), timeout=timeout); s.close()
        return True
    except OSError:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--trials", type=int, default=10)
    ap.add_argument("--gap", type=float, default=20.0, help="jeda antar-trial (> cooldown Hand)")
    ap.add_argument("--score", type=float, default=0.85, help="threat_score (>=0.8 = CRITICAL)")
    ap.add_argument("--timeout", type=float, default=45.0, help="batas tunggu recovery per trial")
    ap.add_argument("--out", default="mttr_results.json")
    ap.add_argument("--mode", choices=["healed", "recovery"], default="healed",
                    help="healed = deteksi→pesan healed (pasca-fix D-1); "
                         "recovery = deteksi→broker melayani lagi (baseline restart)")
    args = ap.parse_args()

    import paho.mqtt.client as mqtt
    healed = []   # timestamp pesan healed (bonus, mungkin hilang saat restart)

    def on_message(c, u, msg):
        healed.append(time.time())

    sub = mqtt.Client(client_id="mttr-probe")
    sub.on_message = on_message
    sub.reconnect_delay_set(min_delay=1, max_delay=2)
    sub.connect(args.host, args.port, 60)
    sub.subscribe("satset/hand/healed")
    sub.loop_start()

    recover_ms, healed_ms, skipped = [], [], 0
    print(f"=== Ukur MTTR: {args.trials} trial, score={args.score}, gap={args.gap}s ===")

    for i in range(args.trials):
        # pastikan broker sehat sebelum mulai
        while not port_up(args.host, args.port):
            time.sleep(0.2)
        healed.clear()

        # publisher terpisah & unik tiap trial (attacker_ip pakai TEST-NET, aman)
        pub = mqtt.Client(client_id=f"mttr-pub-{i}")
        pub.connect(args.host, args.port, 60); pub.loop_start()
        payload = json.dumps({"threat_score": args.score,
                              "attacker_ip": f"198.51.100.{i+1}",   # TEST-NET-2 (aman)
                              "features": [0.9, 0.9, 0.9, 0.9, 0.9]})
        t0 = time.time()
        pub.publish("satset/brain/threat", payload, qos=1)

        if args.mode == "healed":
            # ukur deteksi → pesan healed (broker tidak di-restart pasca-fix D-1)
            t_done = None
            while time.time() - t0 < args.timeout:
                if healed:
                    t_done = healed[0]; break
                time.sleep(0.005)
            try: pub.loop_stop(); pub.disconnect()
            except Exception: pass
            if t_done is None:
                skipped += 1
                print(f"  [trial {i+1:>2}] ⏳ tak ada 'healed' (cooldown/Hand mati?) — dilewati")
                time.sleep(args.gap + 5)
                continue
            mttr = (t_done - t0) * 1000
            recover_ms.append(mttr)
            print(f"  [trial {i+1:>2}] MTTR(deteksi→healed) = {mttr:>8.2f} ms")
            time.sleep(args.gap)
            continue

        # mode == recovery: deteksi broker mati → hidup lagi (baseline restart)
        saw_down = False; t_recover = None
        while time.time() - t0 < args.timeout:
            up = port_up(args.host, args.port)
            if not up:
                saw_down = True
            elif saw_down and up:
                t_recover = time.time(); break
            time.sleep(0.05)
        try: pub.loop_stop(); pub.disconnect()
        except Exception: pass

        if t_recover is None:
            skipped += 1
            print(f"  [trial {i+1:>2}] ⏳ tidak ada restart terdeteksi (cooldown Hand?) — dilewati")
            time.sleep(args.gap + 10)
            continue

        mttr = (t_recover - t0) * 1000
        recover_ms.append(mttr)
        hstr = ""
        if healed:
            hm = (healed[0] - t0) * 1000; healed_ms.append(hm)
            hstr = f" | healed msg: {hm:.0f}ms"
        print(f"  [trial {i+1:>2}] MTTR(recovery) = {mttr:>7.0f} ms{hstr}")
        time.sleep(args.gap)

    sub.loop_stop(); sub.disconnect()

    if not recover_ms:
        print("\n⚠️ Tidak ada trial sukses. Cek: Hand berjalan? threshold? cooldown terlalu tinggi?")
        return

    def stats(x):
        return {"n": len(x), "mean_ms": st.mean(x), "median_ms": st.median(x),
                "min_ms": min(x), "max_ms": max(x),
                "std_ms": (st.stdev(x) if len(x) > 1 else 0.0)}

    R = stats(recover_ms)
    label = "deteksi → pesan healed" if args.mode == "healed" else "deteksi → layanan pulih"
    print("\n" + "="*56)
    print(f"  HASIL MTTR ({label})")
    print("="*56)
    print(f"  Trial sukses : {R['n']}  (dilewati/cooldown: {skipped})")
    print(f"  Mean         : {R['mean_ms']:.0f} ms")
    print(f"  Median       : {R['median_ms']:.0f} ms")
    print(f"  Min / Max    : {R['min_ms']:.0f} / {R['max_ms']:.0f} ms")
    print(f"  Std dev      : {R['std_ms']:.0f} ms")
    if healed_ms:
        H = stats(healed_ms)
        print(f"  [bonus] pesan healed terkirim {H['n']}/{R['n']} kali, mean {H['mean_ms']:.0f} ms")
    print("="*56)

    with open(args.out, "w") as f:
        json.dump({"recovery": R,
                   "healed": (stats(healed_ms) if healed_ms else None),
                   "raw_recovery_ms": recover_ms}, f, indent=2)
    print(f"✅ Tersimpan → {args.out}")


if __name__ == "__main__":
    main()
