import time
from scapy.all import AsyncSniffer

class NetworkCollector:
    def __init__(self, interface="lo", port=1883):
        self.interface = interface
        self.port = port
        self.packet_count = 0
        self.total_size = 0
        self.last_collect_time = time.time()

        self.sniffer = AsyncSniffer(iface=self.interface, filter=f"tcp port {self.port}", prn=self.process_packet)
        
    def start(self):
        self.sniffer.start()

    def process_packet(self, packet):
        self.packet_count += 1
        self.total_size += len(packet)

    def flush_stats(self, window_seconds=1.0):
        now = time.time()
        elapsed = now - self.last_collect_time
        if elapsed <= 0: elapsed = window_seconds

        rate = self.packet_count / elapsed
        avg_size = self.total_size / self.packet_count if self.packet_count > 0 else 0
        inter_arrival = 1.0 / rate if rate > 0 else 0

        data = {
            "packet_rate": float(rate),
            "packet_size": float(avg_size),
            "interval": float(inter_arrival)
        }

        self.packet_count = 0
        self.total_size = 0
        self.last_collect_time = now

        return data

    def stop(self):
        self.sniffer.stop()
