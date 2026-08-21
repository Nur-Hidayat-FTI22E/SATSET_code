# heal_trigger.py - Enhanced with real firewall, rate limiting, adaptive cooldown

import os
import json
import time
import signal
import subprocess
import threading
from collections import defaultdict
from datetime import datetime

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

# ============================================
# KONFIGURASI ENHANCED
# ============================================
THRESHOLD_CRITICAL = float(os.getenv("THRESHOLD_CRITICAL", 0.8))
THRESHOLD_HIGH = float(os.getenv("THRESHOLD_HIGH", 0.6))
THRESHOLD_MEDIUM = float(os.getenv("THRESHOLD_MEDIUM", 0.4))

BASE_COOLDOWN = float(os.getenv("BASE_COOLDOWN", 15.0))
MAX_COOLDOWN = float(os.getenv("MAX_COOLDOWN", 120.0))  # Maks 2 menit

RATE_LIMIT_PER_IP = int(os.getenv("RATE_LIMIT_PER_IP", 3))  # Maks 3x per jam per IP
BLACKLIST_DURATION = int(os.getenv("BLACKLIST_DURATION", 3600))  # 1 jam

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

# ============================================
# HEAL TRIGGER ENHANCED
# ============================================

class HealTriggerEnhanced:
    def __init__(self):
        self.last_heal_time = 0
        self.heal_count = 0
        self.cooldown = BASE_COOLDOWN
        
        # Rate limiting per IP
        self.ip_attack_history = defaultdict(list)  # {ip: [timestamps]}
        self.blacklisted_ips = {}  # {ip: until_timestamp}
        
        # Healing history untuk adaptive cooldown
        self.heal_timestamps = []
        
        # Severity logging
        self.suspicious_events = []  # Untuk early warning
        
        # MQTT
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        
        # Threading lock
        self.lock = threading.Lock()
        
        print("="*55)
        print("  SATSET — Self-Healing Trigger v2.0 (Enhanced)")
        print("="*55)
        print(f"  Critical threshold : {THRESHOLD_CRITICAL}")
        print(f"  High threshold     : {THRESHOLD_HIGH}")
        print(f"  Medium threshold   : {THRESHOLD_MEDIUM}")
        print(f"  Base cooldown      : {BASE_COOLDOWN}s")
        print(f"  Rate limit per IP  : {RATE_LIMIT_PER_IP}x/hour")
        print("="*55)
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe("satset/brain/threat")
            print("[HealTrigger] MQTT connected, listening on satset/brain/threat")
        else:
            print(f"[HealTrigger] MQTT connect failed: rc={rc}")
    
    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            threat_score = payload.get("threat_score", 0.0)
            attacker_ip = payload.get("attacker_ip", None)
            features = payload.get("features", [])
            
            # Proses dengan severity level
            self._handle_threat(threat_score, attacker_ip, features)
            
        except Exception as e:
            print(f"[HealTrigger] Parse error: {e}")
    
    def _is_ip_blacklisted(self, ip):
        """Cek apakah IP sedang diblacklist"""
        if ip in self.blacklisted_ips:
            if time.time() < self.blacklisted_ips[ip]:
                return True
            else:
                del self.blacklisted_ips[ip]
        return False
    
    def _block_ip(self, ip):
        """Firewall REAL - blokir IP menggunakan iptables"""
        if self._is_ip_blacklisted(ip):
            return
        
        try:
            # Blokir incoming
            subprocess.run([
                "sudo", "iptables", "-A", "INPUT",
                "-s", ip, "-j", "DROP"
            ], check=True, timeout=5)
            
            # Blokir forward
            subprocess.run([
                "sudo", "iptables", "-A", "FORWARD",
                "-s", ip, "-j", "DROP"
            ], check=True, timeout=5)
            
            self.blacklisted_ips[ip] = time.time() + BLACKLIST_DURATION
            print(f"[HealTrigger] 🔒 IP {ip} blocked for {BLACKLIST_DURATION}s")
            
            # Log ke file
            self._log_action(f"BLOCK_IP", ip, None)
            
        except subprocess.TimeoutExpired:
            print(f"[HealTrigger] ⚠️ Timeout blocking IP {ip}")
        except Exception as e:
            print(f"[HealTrigger] ⚠️ Failed to block IP {ip}: {e}")
    
    def _check_rate_limit(self, ip):
        """Rate limiting per IP"""
        if not ip:
            return True  # No IP, allow
        
        now = time.time()
        # Hanya hitung dalam 1 jam terakhir
        recent = [t for t in self.ip_attack_history[ip] if now - t < 3600]
        self.ip_attack_history[ip] = recent
        
        if len(recent) >= RATE_LIMIT_PER_IP:
            # Terlalu banyak attack dari IP yang sama → blacklist
            print(f"[HealTrigger] ⚠️ IP {ip} exceeded rate limit ({len(recent)}x/hour)")
            self._block_ip(ip)
            return False
        
        self.ip_attack_history[ip].append(now)
        return True
    
    def _adaptive_cooldown(self):
        """Exponential backoff - cooldown makin panjang jika sering healing"""
        now = time.time()
        # Hitung healing dalam 1 jam terakhir
        recent = [t for t in self.heal_timestamps if now - t < 3600]
        self.heal_timestamps = recent
        
        heal_count = len(recent)
        
        if heal_count > 10:
            self.cooldown = min(MAX_COOLDOWN, BASE_COOLDOWN * 4)
        elif heal_count > 5:
            self.cooldown = min(MAX_COOLDOWN, BASE_COOLDOWN * 2)
        else:
            self.cooldown = BASE_COOLDOWN
        
        return self.cooldown
    
    def _log_suspicious(self, threat_score, attacker_ip, features):
        """Log serangan medium (0.4-0.6) untuk early warning"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "threat_score": threat_score,
            "attacker_ip": attacker_ip,
            "severity": "MEDIUM",
            "features": features[:3] if features else []  # Simpan sebagian
        }
        
        self.suspicious_events.append(log_entry)
        
        # Simpan ke file
        with open("suspicious_log.json", "a") as f:
            json.dump(log_entry, f)
            f.write("\n")
        
        print(f"[HealTrigger] 📝 Logged suspicious activity (score={threat_score:.4f})")
    
    def _restart_mqtt(self):
        """Restart MQTT broker"""
        try:
            start = time.time()
            self.client.disconnect()
            time.sleep(0.5)

            subprocess.run(
                ["docker", "restart", "-t", "3", "satset-mosquitto"],
                check=True, timeout=15
            )

            time.sleep(1)
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            self.client.subscribe("satset/brain/threat")

            mttr = (time.time() - start) * 1000
            print(f"[HealTrigger] ✅ Service restarted & reconnected — {mttr:.0f}ms")
            return mttr
        except Exception as e:
            print(f"[HealTrigger] ❌ Restart failed: {e}")
            try:
                self.client.connect(self.broker_host, self>broker_port, 60)
                self.client.loop_start()
                self.client.subscribe("satset/brain/threat")
            except: pass
            return None
      
    def _heal(self, threat_score, attacker_ip, severity):
        """Eksekusi healing berdasarkan severity level"""
        with self.lock:
            # Update cooldown adaptive
            self._adaptive_cooldown()
            
            now = time.time()
            if now - self.last_heal_time < self.cooldown:
                print(f"[HealTrigger] ⏳ Cooldown active ({self.cooldown:.0f}s). Skipping.")
                return
            
            self.last_heal_time = now
            self.heal_timestamps.append(now)
            self.heal_count += 1
            
            print(f"\n[HealTrigger] 🚨 {severity} THREAT! score={threat_score:.4f}")
            
            mttr = self._restart_mqtt()

            # 4. Publish healed status
            healed_msg = json.dumps({
                "status": "healed",
                "threat_score": threat_score,
                "mttr_ms": mttr if mttr is not None else -1,
                "heal_count": self.heal_count,
                "cooldown": self.cooldown
            })
            try:
                self.client.publish("satset/hand/healed", healed_msg)
            except Exception:
                pass
            self._log_action("HEAL", attacker_ip, threat_score)
            mt = f"{mttr:.0f}ms" if mttr is not None else "N/A"
            print(f"[HealTrigger] ✅ Healing complete. MTTR={mt}")
            print(f"[HealTrigger] 📊 Stats: {self.heal_count} heals, cooldown={self.cooldown:.0f}s\n")
    
    def _apply_rate_limit(self, ip):
        """Apply rate limiting (bukan blokir total) untuk critical threat"""
        if not ip:
            return
        try:
            subprocess.run([
                "sudo", "iptables", "-A", "INPUT",
                "-s", ip,
                "-m", "limit", "--limit", "10/second",
                "-j", "ACCEPT"
            ], check=True, timeout=5)
            print(f"[HealTrigger] ⚡ Rate limit applied to {ip} (10 pps)")
        except Exception as e:
            print(f"[HealTrigger] ⚠️ Rate limit failed: {e}")
    
    def _log_action(self, action, ip, threat_score):
        """Log semua aksi healing ke file"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "ip": ip,
            "threat_score": threat_score,
            "heal_count": self.heal_count,
            "cooldown": self.cooldown
        }
        with open("heal_log.json", "a") as f:
            json.dump(log_entry, f)
            f.write("\n")
    
    def _handle_threat(self, threat_score, attacker_ip, features):
        """Handle threat dengan multi-level severity"""
        
        # Cek blacklist
        if attacker_ip and self._is_ip_blacklisted(attacker_ip):
            print(f"[HealTrigger] 🚫 Ignoring threat from blacklisted IP: {attacker_ip}")
            return
        
        # Rate limiting per IP
        if not self._check_rate_limit(attacker_ip):
            return
        
        # Multi-level threshold
        if threat_score >= THRESHOLD_CRITICAL:
            # Critical: Langsung healing
            self._heal(threat_score, attacker_ip, "CRITICAL")
            
        elif threat_score >= THRESHOLD_HIGH:
            # High: Healing dengan rate limiting
            self._heal(threat_score, attacker_ip, "HIGH")
            
        elif threat_score >= THRESHOLD_MEDIUM:
            # Medium: Log saja, tidak healing
            self._log_suspicious(threat_score, attacker_ip, features)
            
        else:
            # Low: Abaikan
            pass
    
    def run(self):
        try:
            self.client.connect(MQTT_HOST, MQTT_PORT)
            self.client.loop_forever()
        except KeyboardInterrupt:
            print("\n[HealTrigger] Shutting down...")
            self.client.disconnect()
            
            # Summary
            print(f"\n📊 Healing Summary:")
            print(f"   Total heals: {self.heal_count}")
            print(f"   Blacklisted IPs: {len(self.blacklisted_ips)}")
            print(f"   Suspicious events: {len(self.suspicious_events)}")

# ============================================
# MAIN
# ============================================

def main():
    trigger = HealTriggerEnhanced()
    trigger.run()

if __name__ == "__main__":
    main()
