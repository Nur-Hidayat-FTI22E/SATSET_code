# heal_trigger.py - Enhanced with real firewall, rate limiting, adaptive cooldown
# VERSI STABLE — PAKAI PAHO-MQTT 1.6.1 + Callback API v1

import os
import json
import time
import subprocess
import threading
from collections import defaultdict
from datetime import datetime

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

# ============================================
# KONFIGURASI
# ============================================
THRESHOLD_CRITICAL = float(os.getenv("THRESHOLD_CRITICAL", 0.8))
THRESHOLD_HIGH = float(os.getenv("THRESHOLD_HIGH", 0.6))
THRESHOLD_MEDIUM = float(os.getenv("THRESHOLD_MEDIUM", 0.4))

BASE_COOLDOWN = float(os.getenv("BASE_COOLDOWN", 15.0))
MAX_COOLDOWN = float(os.getenv("MAX_COOLDOWN", 120.0))

RATE_LIMIT_PER_IP = int(os.getenv("RATE_LIMIT_PER_IP", 3))
BLACKLIST_DURATION = int(os.getenv("BLACKLIST_DURATION", 3600))

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
        
        self.broker_host = MQTT_HOST
        self.broker_port = MQTT_PORT
        
        self.ip_attack_history = defaultdict(list)
        self.blacklisted_ips = {}
        self.heal_timestamps = []
        self.suspicious_events = []
        
        # PAKAI VERSI 1 (tanpa CallbackAPIVersion)
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        
        self.lock = threading.Lock()
        self.running = True
        
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
            self._handle_threat(threat_score, attacker_ip, features)
        except Exception as e:
            print(f"[HealTrigger] Parse error: {e}")
    
    def _is_ip_blacklisted(self, ip):
        if ip in self.blacklisted_ips:
            if time.time() < self.blacklisted_ips[ip]:
                return True
            else:
                del self.blacklisted_ips[ip]
        return False
    
    def _block_ip(self, ip):
        if self._is_ip_blacklisted(ip):
            return
        try:
            subprocess.run(["sudo", "iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"], check=True, timeout=5)
            subprocess.run(["sudo", "iptables", "-A", "FORWARD", "-s", ip, "-j", "DROP"], check=True, timeout=5)
            self.blacklisted_ips[ip] = time.time() + BLACKLIST_DURATION
            print(f"[HealTrigger] 🔒 IP {ip} blocked for {BLACKLIST_DURATION}s")
            self._log_action(f"BLOCK_IP", ip, None)
        except Exception as e:
            print(f"[HealTrigger] ⚠️ Failed to block IP {ip}: {e}")
    
    def _check_rate_limit(self, ip):
        if not ip:
            return True
        now = time.time()
        recent = [t for t in self.ip_attack_history[ip] if now - t < 3600]
        self.ip_attack_history[ip] = recent
        if len(recent) >= RATE_LIMIT_PER_IP:
            print(f"[HealTrigger] ⚠️ IP {ip} exceeded rate limit")
            self._block_ip(ip)
            return False
        self.ip_attack_history[ip].append(now)
        return True
    
    def _adaptive_cooldown(self):
        now = time.time()
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
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "threat_score": threat_score,
            "attacker_ip": attacker_ip,
            "severity": "MEDIUM"
        }
        self.suspicious_events.append(log_entry)
        print(f"[HealTrigger] 📝 Logged suspicious activity (score={threat_score:.4f})")
    
    def _restart_mqtt(self):
        """Restart MQTT broker — tanpa disconnect manual"""
        try:
            start = time.time()
            
            # 1. Restart container (client akan reconnect otomatis)
            print("[HealTrigger] 🔄 Restarting container...")
            subprocess.run(
                ["docker", "restart", "-t", "3", "satset-mosquitto"],
                check=True, timeout=15
            )
            
            # 2. Tunggu broker siap
            print("[HealTrigger] ⏳ Waiting for broker...")
            time.sleep(3)
            
            mttr = (time.time() - start) * 1000
            print(f"[HealTrigger] ✅ Service restarted — {mttr:.0f}ms")
            return mttr
            
        except Exception as e:
            print(f"[HealTrigger] ❌ Restart failed: {e}")
            return None
    
    def _heal(self, threat_score, attacker_ip, severity):
        with self.lock:
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
            
            healed_msg = json.dumps({
                "status": "healed",
                "threat_score": threat_score,
                "mttr_ms": mttr if mttr is not None else -1,
                "heal_count": self.heal_count,
                "cooldown": self.cooldown
            })
            try:
                self.client.publish("satset/hand/healed", healed_msg)
            except:
                pass
            self._log_action("HEAL", attacker_ip, threat_score)
            mt = f"{mttr:.0f}ms" if mttr is not None else "N/A"
            print(f"[HealTrigger] ✅ Healing complete. MTTR={mt}")
            print(f"[HealTrigger] 📊 Stats: {self.heal_count} heals, cooldown={self.cooldown:.0f}s\n")
    
    def _log_action(self, action, ip, threat_score):
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
        if attacker_ip and self._is_ip_blacklisted(attacker_ip):
            print(f"[HealTrigger] 🚫 Ignoring threat from blacklisted IP: {attacker_ip}")
            return
        if not self._check_rate_limit(attacker_ip):
            return
        if threat_score >= THRESHOLD_CRITICAL:
            self._heal(threat_score, attacker_ip, "CRITICAL")
        elif threat_score >= THRESHOLD_HIGH:
            self._heal(threat_score, attacker_ip, "HIGH")
        elif threat_score >= THRESHOLD_MEDIUM:
            self._log_suspicious(threat_score, attacker_ip, features)
    
    def run(self):
        while self.running:
            try:
                self.client.connect(MQTT_HOST, MQTT_PORT)
                self.client.loop_forever()
            except KeyboardInterrupt:
                print("\n[HealTrigger] Shutting down...")
                self.running = False
                self.client.disconnect()
                break
            except Exception as e:
                print(f"[HealTrigger] ⚠️ Connection error: {e}. Reconnecting in 5s...")
                time.sleep(5)
                continue
        
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
