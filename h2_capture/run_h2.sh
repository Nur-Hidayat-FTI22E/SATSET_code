#!/usr/bin/env bash
# SATSET — H-2 : Orkestrasi perekaman cross-layer di Raspberry Pi 5
# Menghasilkan satu dataset berlabel: pi_crosslayer_dataset.csv
# (baris = jendela 1 detik; kolom = 2 fitur jaringan + 3 HPC nyata + label)
#
# Jalankan:  sudo bash run_h2.sh
set -e

IFACE="${IFACE:-lo}"
WINDOW="${WINDOW:-1.0}"
BENIGN_DUR="${BENIGN_DUR:-300}"     # detik traffic benign
ATTACK_DUR="${ATTACK_DUR:-120}"     # detik per serangan
HOST="127.0.0.1"; PORT="${PORT:-1883}"
OUT="${OUT:-pi_crosslayer_dataset.csv}"
PY="${PY:-python3}"

echo "=== SATSET H-2 capture → $OUT ==="
echo "iface=$IFACE window=${WINDOW}s benign=${BENIGN_DUR}s attack=${ATTACK_DUR}s/skenario"

# 0) Pastikan broker MQTT hidup di :$PORT (sesuaikan bila pakai docker satset-mosquitto)
if ! (echo > /dev/tcp/$HOST/$PORT) 2>/dev/null; then
  echo "[warn] Broker MQTT di $HOST:$PORT tidak merespons."
  echo "       Jalankan dulu, mis:  docker start satset-mosquitto   (atau)  mosquitto -d"
  read -p "Lanjut tanpa broker? benign/mqtt_flood butuh broker. [y/N] " a
  [ "$a" = "y" ] || exit 1
fi

rm -f "$OUT"   # mulai dataset baru

# 1) BENIGN
echo; echo ">>> [1/4] BENIGN"
$PY benign.py --host $HOST --port $PORT --sensors 5 --rate 2 --duration $BENIGN_DUR &
BG=$!
$PY capture.py --iface $IFACE --window $WINDOW --duration $BENIGN_DUR \
    --scenario benign --label 0 --out "$OUT"
kill $BG 2>/dev/null || true; wait $BG 2>/dev/null || true

# 2) DDoS (hping3, butuh sudo)
echo; echo ">>> [2/4] DDoS (SYN flood)"
$PY attacks.py --attack ddos --target $HOST --port $PORT --duration $ATTACK_DUR &
BG=$!
$PY capture.py --iface $IFACE --window $WINDOW --duration $ATTACK_DUR \
    --scenario ddos --label 1 --out "$OUT"
kill $BG 2>/dev/null || true; wait $BG 2>/dev/null || true

# 3) PORT SCAN (nmap, butuh sudo)
echo; echo ">>> [3/4] PORT SCAN"
$PY attacks.py --attack portscan --target $HOST --duration $ATTACK_DUR &
BG=$!
$PY capture.py --iface $IFACE --window $WINDOW --duration $ATTACK_DUR \
    --scenario portscan --label 1 --out "$OUT"
kill $BG 2>/dev/null || true; wait $BG 2>/dev/null || true

# 4) MQTT FLOOD
echo; echo ">>> [4/5] MQTT FLOOD"
$PY attacks.py --attack mqtt_flood --target $HOST --port $PORT --duration $ATTACK_DUR &
BG=$!
$PY capture.py --iface $IFACE --window $WINDOW --duration $ATTACK_DUR \
    --scenario mqtt_flood --label 1 --out "$OUT"
kill $BG 2>/dev/null || true; wait $BG 2>/dev/null || true

# 5) CPU ATTACK (malware on-device: HPC tinggi, jaringan ~nol → bukti cross-layer)
echo; echo ">>> [5/5] CPU ATTACK (on-device)"
$PY attacks.py --attack cpu_attack --duration $ATTACK_DUR &
BG=$!
$PY capture.py --iface $IFACE --window $WINDOW --duration $ATTACK_DUR \
    --scenario cpu_attack --label 1 --out "$OUT"
kill $BG 2>/dev/null || true; wait $BG 2>/dev/null || true

echo; echo "=== SELESAI → $OUT ==="
$PY - <<PYEOF
import pandas as pd
df = pd.read_csv("$OUT")
print("Total jendela:", len(df))
print(df.groupby(["scenario","label"]).size())
print("\nMissing HPC (NaN) per kolom:")
print(df[["cache_misses","instructions","branch_misses"]].isna().sum())
PYEOF
