#!/usr/bin/env python3
"""
SATSET — One-Command Setup
Dengan progress bar interaktif seperti React/Go-Blueprint
"""

import os
import sys
import subprocess
import json
import shutil
import time
import platform
import threading
from pathlib import Path
from datetime import datetime

# ============================================================
# KONFIGURASI
# ============================================================

ROOT = Path(__file__).parent
VENV_PATH = ROOT / "venv"
MODEL_PATH = ROOT / "brain" / "model"
DATA_PATH = ROOT / "data"
DOCKER_PATH = ROOT / "docker"

# 🔴 GANTI DENGAN ID FILE DRIVE ANDA
DRIVE_MODEL_ID = "YOUR_MODEL_FILE_ID"
DRIVE_SCALER_ID = "YOUR_SCALER_FILE_ID"

# ============================================================
# WARNA
# ============================================================

BLUE = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BOLD = "\033[1m"
RESET = "\033[0m"
CLEAR_LINE = "\033[2K\r"

# ============================================================
# PROGRESS BAR
# ============================================================

class ProgressBar:
    """Progress bar interaktif seperti React/Go-Blueprint"""
    
    def __init__(self, total_steps=8, width=30):
        self.total_steps = total_steps
        self.width = width
        self.current_step = 0
        self.lock = threading.Lock()
        self.running = True
    
    def update(self, step, title, status="⏳"):
        """Update progress bar"""
        with self.lock:
            self.current_step = step
            progress = step / self.total_steps
            filled = int(self.width * progress)
            bar = "█" * filled + "░" * (self.width - filled)
            
            # Hitung persentase
            percent = int(progress * 100)
            
            # Tampilkan progress bar
            print(f"\r{status}  {bar}  {percent}%  {title}", end="", flush=True)
    
    def complete(self):
        """Tampilkan progress bar selesai"""
        with self.lock:
            filled = self.width
            bar = "█" * filled
            print(f"\r✅  {bar}  100%  Setup Complete! 🎉", end="", flush=True)
            print()

# ============================================================
# HEADER
# ============================================================

def print_header():
    """Tampilkan header SATSET"""
    print(f"""
{BLUE}╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   🚀  SATSET — Spiking-based Antifragile Twin                    ║
║       for Self-healing Edge Technology                            ║
║                                                                   ║
║   📦  Version: 1.0.0                                              ║
║   🖥️  Platform: {platform.system()} {platform.machine():<23} ║
║   📅  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<35} ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝{RESET}
""")

# ============================================================
# UTILITY
# ============================================================

def run_cmd(cmd, cwd=None, check=True, silent=False):
    """Jalankan command"""
    if not silent:
        print(f"  $ {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0 and check:
        print(f"{RED}  ❌ Command failed: {result.stderr}{RESET}")
        sys.exit(1)
    return result

def print_success(msg):
    print(f"\n{GREEN}  ✅ {msg}{RESET}")

def print_error(msg):
    print(f"\n{RED}  ❌ {msg}{RESET}")

def print_info(msg):
    print(f"\n{BLUE}  ℹ️  {msg}{RESET}")

def print_warning(msg):
    print(f"\n{YELLOW}  ⚠️  {msg}{RESET}")

def input_with_default(prompt, default):
    """Input dengan default value"""
    value = input(f"  {prompt} [{default}]: ").strip()
    return value if value else default

# ============================================================
# STEP 1: SYSTEM CHECK + AUTO INSTALL
# ============================================================

def step1_system_check(pbar):
    """Cek dan install paket yang kurang"""
    pbar.update(1, "System Check & Auto Install", "⏳")
    
    # Cek Python
    result = run_cmd("python3 --version", check=False, silent=True)
    if result.returncode != 0:
        run_cmd("sudo apt update && sudo apt install -y python3 python3-venv python3-pip", silent=True)
    
    # Cek pip
    result = run_cmd("pip3 --version", check=False, silent=True)
    if result.returncode != 0:
        run_cmd("sudo apt install -y python3-pip", silent=True)
    
    # Cek Docker
    result = run_cmd("docker --version", check=False, silent=True)
    if result.returncode != 0:
        run_cmd("curl -fsSL https://get.docker.com -o get-docker.sh", silent=True)
        run_cmd("sudo sh get-docker.sh", silent=True)
        run_cmd("sudo usermod -aG docker $USER", silent=True)
    
    # Cek Docker Compose
    result = run_cmd("docker compose version", check=False, silent=True)
    if result.returncode != 0:
        run_cmd("sudo apt install -y docker-compose-plugin", silent=True)
    
    pbar.update(1, "System Check & Auto Install", "✅")

# ============================================================
# STEP 2: VIRTUAL ENVIRONMENT
# ============================================================

def step2_virtual_environment(pbar):
    """Buat virtual environment"""
    pbar.update(2, "Virtual Environment", "⏳")
    
    if VENV_PATH.exists():
        response = input("\n  ⚠️  Venv already exists. Recreate? (y/n) [n]: ").strip().lower()
        if response == 'y':
            shutil.rmtree(VENV_PATH)
        else:
            pbar.update(2, "Virtual Environment (using existing)", "✅")
            return
    
    run_cmd(f"python3 -m venv {VENV_PATH}", silent=True)
    run_cmd(f"{VENV_PATH}/bin/pip install --upgrade pip", silent=True)
    
    pbar.update(2, "Virtual Environment", "✅")

# ============================================================
# STEP 3: DEPENDENCIES
# ============================================================

def step3_dependencies(pbar):
    """Install dependencies"""
    pbar.update(3, "Installing Dependencies", "⏳")
    
    requirements_file = ROOT / "requirements.txt"
    if not requirements_file.exists():
        with open(requirements_file, 'w') as f:
            f.write("""
torch>=2.0.0
numpy>=1.24.0
pandas>=2.0.0
scikit-learn>=1.3.0
snntorch>=0.7.0
paho-mqtt>=1.6.0
influxdb-client>=1.40.0
python-dotenv>=1.0.0
joblib>=1.3.0
matplotlib>=3.7.0
tqdm>=4.65.0
gdown>=5.0.0
""")
    
    run_cmd(f"{VENV_PATH}/bin/pip install --no-cache-dir -r {requirements_file}", silent=True)
    
    pbar.update(3, "Installing Dependencies", "✅")

# ============================================================
# STEP 4: ENVIRONMENT FILE
# ============================================================

def step4_environment(pbar):
    """Buat .env dengan interaksi user"""
    pbar.update(4, "Environment Configuration", "⏳")
    
    env_file = ROOT / ".env"
    
    if env_file.exists():
        response = input("\n  ⚠️  .env already exists. Recreate? (y/n) [n]: ").strip().lower()
        if response != 'y':
            pbar.update(4, "Environment Configuration (using existing)", "✅")
            return
    
    print()
    print_info("Please enter your configuration values:")
    print_warning("Press Enter to use default values\n")
    
    mqtt_host = input_with_default("MQTT Host", "localhost")
    mqtt_port = input_with_default("MQTT Port", "1883")
    influx_url = input_with_default("InfluxDB URL", "http://localhost:8086")
    influx_org = input_with_default("InfluxDB Org", "satset-lab")
    influx_bucket = input_with_default("InfluxDB Bucket", "satset")
    influx_token = input("  InfluxDB Token []: ").strip() or "your_token_here"
    threshold = input_with_default("Threat Threshold", "0.6")
    interval = input_with_default("Inference Interval (seconds)", "1.0")
    
    with open(env_file, 'w') as f:
        f.write(f"""# SATSET Environment Configuration
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# MQTT
MQTT_HOST={mqtt_host}
MQTT_PORT={mqtt_port}

# InfluxDB
INFLUXDB_URL={influx_url}
INFLUXDB_ORG={influx_org}
INFLUXDB_BUCKET={influx_bucket}
INFLUXDB_TOKEN={influx_token}

# System
THREAT_THRESHOLD={threshold}
INFERENCE_INTERVAL={interval}

# Model
SNN_MODEL_PATH=brain/model/snn_model.pt
SNN_SCALER_PATH=brain/model/snn_model_scaler.pkl
""")
    
    pbar.update(4, "Environment Configuration", "✅")

# ============================================================
# STEP 5: DOWNLOAD MODEL
# ============================================================

def step5_download_model(pbar):
    """Download model dari Google Drive"""
    pbar.update(5, "Downloading Model & Scaler", "⏳")
    
    os.makedirs(MODEL_PATH, exist_ok=True)
    
    model_file = MODEL_PATH / "snn_model.pt"
    scaler_file = MODEL_PATH / "snn_model_scaler.pkl"
    
    if not model_file.exists() and DRIVE_MODEL_ID != "YOUR_MODEL_FILE_ID":
        run_cmd(f"{VENV_PATH}/bin/gdown -O {model_file} https://drive.google.com/uc?id={DRIVE_MODEL_ID}", silent=True)
    
    if not scaler_file.exists() and DRIVE_SCALER_ID != "YOUR_SCALER_FILE_ID":
        run_cmd(f"{VENV_PATH}/bin/gdown -O {scaler_file} https://drive.google.com/uc?id={DRIVE_SCALER_ID}", silent=True)
    
    pbar.update(5, "Downloading Model & Scaler", "✅")

# ============================================================
# STEP 6: DOCKER CONTAINERS
# ============================================================

def step6_docker(pbar):
    """Start Docker containers"""
    pbar.update(6, "Starting Docker Containers", "⏳")
    
    # Baca port dari .env
    env_file = ROOT / ".env"
    mqtt_port = 1883
    influx_port = 8086
    grafana_port = 3000
    
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.startswith("MQTT_PORT="):
                    mqtt_port = int(line.strip().split("=")[1])
                elif line.startswith("INFLUXDB_URL="):
                    influx_url = line.strip().split("=")[1]
                    if ":" in influx_url:
                        influx_port = int(influx_url.split(":")[-1])
    
    docker_compose = DOCKER_PATH / "docker-compose.yml"
    if not docker_compose.exists():
        os.makedirs(DOCKER_PATH, exist_ok=True)
        with open(docker_compose, 'w') as f:
            f.write(f"""
version: '3.8'
services:
  mosquitto:
    image: eclipse-mosquitto:2.0
    container_name: satset-mosquitto
    ports:
      - "{mqtt_port}:1883"
    restart: unless-stopped
    volumes:
      - mosquitto_data:/mosquitto/data

  influxdb:
    image: influxdb:2.7
    container_name: satset-influxdb
    ports:
      - "{influx_port}:8086"
    restart: unless-stopped
    environment:
      INFLUXDB_DB: satset
      INFLUXDB_ADMIN_USER: admin
      INFLUXDB_ADMIN_PASSWORD: admin123
    volumes:
      - influxdb_data:/var/lib/influxdb2

  grafana:
    image: grafana/grafana:10.4.0
    container_name: satset-grafana
    ports:
      - "{grafana_port}:3000"
    restart: unless-stopped
    depends_on:
      - influxdb
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  mosquitto_data:
  influxdb_data:
  grafana_data:
""")
    
    run_cmd(f"docker compose -f {docker_compose} up -d", silent=True)
    
    time.sleep(5)
    
    pbar.update(6, "Starting Docker Containers", "✅")

# ============================================================
# STEP 7: VALIDASI
# ============================================================

def step7_validation(pbar):
    """Validasi koneksi"""
    pbar.update(7, "Validation & Testing", "⏳")
    
    # Baca port dari .env
    env_file = ROOT / ".env"
    mqtt_port = 1883
    influx_port = 8086
    grafana_port = 3000
    
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.startswith("MQTT_PORT="):
                    mqtt_port = int(line.strip().split("=")[1])
                elif line.startswith("INFLUXDB_URL="):
                    influx_url = line.strip().split("=")[1]
                    if ":" in influx_url:
                        influx_port = int(influx_url.split(":")[-1])
    
    # Test MQTT
    result = run_cmd(f"timeout 2 mosquitto_sub -h localhost -p {mqtt_port} -t '#' -C 1 2>/dev/null", check=False, silent=True)
    if result.returncode != 0:
        print_warning(f"MQTT may not be ready yet (port {mqtt_port})")
    
    # Test InfluxDB
    result = run_cmd(f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{influx_port}/health", check=False, silent=True)
    if result.stdout.strip() != "200":
        print_warning(f"InfluxDB may not be ready yet (port {influx_port})")
    
    # Test Grafana
    result = run_cmd(f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{grafana_port}", check=False, silent=True)
    if result.stdout.strip() not in ["200", "302"]:
        print_warning(f"Grafana may not be ready yet (port {grafana_port})")
    
    pbar.update(7, "Validation & Testing", "✅")

# ============================================================
# STEP 8: FINAL OUTPUT
# ============================================================

def step8_final():
    """Tampilkan final output"""
    # Baca port dari .env
    env_file = ROOT / ".env"
    grafana_port = 3000
    
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.startswith("INFLUXDB_URL="):
                    influx_url = line.strip().split("=")[1]
                    if ":" in influx_url:
                        influx_port = int(influx_url.split(":")[-1])
    
    print(f"""

{GREEN}╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   ✅  SATSET Setup Complete!                                      ║
║                                                                   ║
║   📊  Services:                                                   ║
║      📡 MQTT Broker     → localhost:{mqtt_port if 'mqtt_port' in dir() else 1883}      ║
║      📦 InfluxDB        → http://localhost:{influx_port if 'influx_port' in dir() else 8086}      ║
║      📊 Grafana         → http://localhost:{grafana_port}       ║
║                                                                   ║
║   🚀  Next Steps:                                                ║
║      make brain    → Start inference engine                      ║
║      make hand     → Start self-healing trigger                  ║
║      make attack   → Simulate attack                             ║
║      make up       → Start Docker containers                     ║
║      make down     → Stop Docker containers                      ║
║      make status   → Show Docker status                          ║
║      make help     → Show all commands                           ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝{RESET}
""")

# ============================================================
# MAIN
# ============================================================

def main():
    # Clear screen
    os.system('clear' if os.name == 'posix' else 'cls')
    
    # Header
    print_header()
    
    print(f"{YELLOW}📦  Setting up SATSET...{RESET}\n")
    
    # Progress bar
    pbar = ProgressBar(total_steps=8, width=30)
    
    try:
        step1_system_check(pbar)
        step2_virtual_environment(pbar)
        step3_dependencies(pbar)
        step4_environment(pbar)
        step5_download_model(pbar)
        step6_docker(pbar)
        step7_validation(pbar)
        
        # Selesai
        pbar.complete()
        
        step8_final()
        
    except KeyboardInterrupt:
        print(f"\n{RED}❌ Setup interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
