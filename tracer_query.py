import os, json, subprocess, re
from scapy.all import sniff
#from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

load_dotenv(".env")
INFLUX_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUX_TOKEN = os.environ.get("INFLUXDB_TOKEN")
client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org="satset-lab")
write_api = client.write_api(write_options=SYNCHRONOUS)

def get_real_hpc() :
    cmd = ["perf", "stat", "-e", "cache-misses,instructions-retired", "-a", "sleep", "1"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    hpc_data = {"cache-misses": 0, "instructions-retired": 0}

    for line in result.stderr.splitlines() :
        if "cache-misses" in line:
            match = re.search(r"([\d\,]+)\s+cache-misses", line)
            if match:
                hpc_data["cache-misses"] = int(match.group(1).replace(",", ""))
        elif "instructions-retired" in line:
            match = re.search(r"([\d\,]+)\s+instructions-retired", line)
            if match:
                hpc_data["instructions-retired"] = int(match.group(1).replace(",", ""))

    return hpc_data

# --- Traffic
paket_count = 0
total_size = 0

def process_packet(packet):
    global paket_count, total_size
    paket_count += 1
    total_size += len(paket)

def get_real_network_stats():
    global paket_count, total_size
    paket_count = 0
    total_size = 0

    sniff(iface="eth0", filter="tcp port 1883", prn=process_packet, timeout=1)

    network_data = {
        "packet_rate": paket_count,
        "packet_size": total_size / paket_count if paket_count > 0 else 0,
        "inter_arrival_time": 1.0 / paket_count if paket_count > 0 else 0
    }
    return network_data

# --- syncrhonation
print("Memulai Agen Senses (Get Real-Data)...")
try:
    while True:
        hpc_stats = get_real_hpc()
        hpc_stats = get_real_network_stats()

        point_hpc = Point("hpc_stats") \
            .field("cache-misses", float(hpc_stats["cache-misses"])) \
            .field("instructions-retired", float(hpc_stats["instructions-retired"]))

        point_net = Point("network_stats") \
            .field("packet_rate", float(net_stats["packet_rate"])) \
            .field("packet_size", float(net_stats["packet_size"])) \
            .field("inter_arrival_time", float(net_stats["inter_arrival_time"]))

        write_api.write(bucket="satset", org="satset-lab", record=[point_hpc, point_net])

        print(f"Data tersimpan - HPC: {hpc_stats} | Network: {net_stats}")

except KeyboardInterrupt:
    print("\n Agen Senses dihentikan")
