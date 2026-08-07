#!/usr/bin/env python3
"""
SATSET — H-2 : Perekam Cross-Layer Tersinkron (Raspberry Pi 5)
=============================================================
Merekam, per jendela waktu (default 1 detik), 5 fitur NYATA + label:

  Jaringan (delta /proc/net/dev pada iface):
      n_packets     = Δ(rx_packets + tx_packets)
      total_bytes   = Δ(rx_bytes   + tx_bytes)
  Hardware (perf stat -a, PMU Cortex-A76):
      cache_misses
      instructions          (instructions retired)
      branch_misses

Setiap baris = satu jendela, dengan kolom `label` (0=benign, 1=attack) dan
`scenario` (nama skenario). Ground-truth diketahui karena KAMU yang menjalankan
skenarionya.

Contoh:
    sudo python3 capture.py --iface lo --window 1.0 --duration 120 \
        --scenario benign --label 0 --out benign.csv

Catatan:
  * Butuh sudo (perf -a butuh akses PMU sistem).
  * Jika event PMU tak tersedia, nilainya ditandai NaN (jangan dipakai).
  * perf dijalankan per-jendela (sleep <window>) → sederhana & sinkron dengan
    delta counter jaringan yang dibaca tepat sebelum & sesudah jendela.
"""
import argparse, subprocess, time, os, csv, sys

PERF_EVENTS = ["cache-misses", "instructions", "branch-misses"]
# nama kolom keluaran untuk tiap event perf
PERF_COLS = {"cache-misses": "cache_misses",
             "instructions": "instructions",
             "branch-misses": "branch_misses"}


def read_net(iface: str):
    """Baca (packets, bytes) kumulatif untuk satu iface dari /proc/net/dev."""
    with open("/proc/net/dev") as f:
        for line in f:
            if ":" not in line:
                continue
            name, rest = line.split(":", 1)
            if name.strip() != iface:
                continue
            v = rest.split()
            # urutan: rx_bytes rx_packets rx_errs rx_drop rx_fifo rx_frame
            #         rx_compressed rx_multicast tx_bytes tx_packets ...
            rx_bytes, rx_pkts = int(v[0]), int(v[1])
            tx_bytes, tx_pkts = int(v[8]), int(v[9])
            return (rx_pkts + tx_pkts, rx_bytes + tx_bytes)
    raise ValueError(f"iface '{iface}' tak ditemukan di /proc/net/dev")


def parse_perf_csv(stderr_text: str):
    """Parse keluaran `perf stat -x,` (CSV). Kembalikan dict {kolom: nilai|None}."""
    out = {c: None for c in PERF_COLS.values()}
    for line in stderr_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(",")
        if len(parts) < 3:
            continue
        raw_val, _unit, event = parts[0], parts[1], parts[2]
        event = event.strip()
        if event not in PERF_COLS:
            continue
        col = PERF_COLS[event]
        if raw_val in ("<not counted>", "<not supported>", ""):
            out[col] = None
        else:
            try:
                out[col] = float(raw_val)
            except ValueError:
                out[col] = None
    return out


def perf_window(window: float):
    """Jalankan perf stat -a selama `window` detik, kembalikan dict HPC."""
    cmd = ["perf", "stat", "-a", "-x", ",",
           "-e", ",".join(PERF_EVENTS), "--", "sleep", str(window)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return parse_perf_csv(proc.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iface",    default="lo")
    ap.add_argument("--window",   type=float, default=1.0, help="durasi jendela (detik)")
    ap.add_argument("--duration", type=float, default=120, help="total durasi rekam (detik)")
    ap.add_argument("--scenario", required=True, help="nama skenario (mis. benign, ddos)")
    ap.add_argument("--label",    type=int, required=True, choices=[0, 1])
    ap.add_argument("--out",      required=True)
    args = ap.parse_args()

    header = ["ts", "scenario", "label", "n_packets", "total_bytes",
              "cache_misses", "instructions", "branch_misses"]
    new_file = not os.path.exists(args.out)
    f = open(args.out, "a", newline="")
    w = csv.writer(f)
    if new_file:
        w.writerow(header)

    n_win = int(args.duration / args.window)
    print(f"[capture] iface={args.iface} window={args.window}s "
          f"skenario={args.scenario} label={args.label} → {n_win} jendela")

    for i in range(n_win):
        p0, b0 = read_net(args.iface)
        hpc = perf_window(args.window)       # blok selama ~window detik
        p1, b1 = read_net(args.iface)
        row = [time.time(), args.scenario, args.label,
               p1 - p0, b1 - b0,
               hpc["cache_misses"], hpc["instructions"], hpc["branch_misses"]]
        w.writerow(row); f.flush()
        if (i + 1) % 10 == 0 or i == 0:
            print(f"  [{i+1:>4}/{n_win}] pkts={p1-p0:<8} bytes={b1-b0:<10} "
                  f"cache_miss={hpc['cache_misses']} instr={hpc['instructions']}")
    f.close()
    print(f"[capture] selesai → {args.out}")


if __name__ == "__main__":
    main()
