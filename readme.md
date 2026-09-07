# 🚀 SATSET — Spiking-based Antifragile Twin for Self-healing Edge Technology

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/SNN-snnTorch-red.svg" alt="snnTorch">
  <img src="https://img.shields.io/badge/Edge-Raspberry%20Pi%205-green.svg" alt="Raspberry Pi 5">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/Status-Stable-brightgreen.svg" alt="Status">
</p>

Sistem deteksi anomali jaringan IoT berbasis **Spiking Neural Network (SNN)** dengan mekanisme **antifragilitas** dan **self-healing** pada perangkat edge **Raspberry Pi 5**.

---

## 📋 Daftar Isi

- [✨ Fitur](#-fitur)
- [🏗️ Arsitektur Sistem](#️-arsitektur-sistem)
- [📊 Metrik Kinerja](#-metrik-kinerja)
- [🚀 One-Command Setup](#-one-command-setup)
- [📋 Perintah Tersedia](#-perintah-tersedia)
- [📁 Struktur Proyek](#-struktur-proyek)
- [🔧 Konfigurasi](#-konfigurasi)
- [📊 Dashboard](#-dashboard)
- [📝 Penelitian Terkait](#-penelitian-terkait)
- [📄 Lisensi](#-lisensi)
- [🙏 Kontribusi](#-kontribusi)

---

## ✨ Fitur

| Fitur | Keterangan |
| :--- | :--- |
| 🧠 **Spiking Neural Network** | Deteksi anomali berbasis SNN LIF dengan efisiensi energi tinggi |
| 🛡️ **Antifragile** | Belajar dari serangan melalui STDP (*Spike-Timing Dependent Plasticity*) |
| 🔄 **Self-Healing** | Pemulihan otomatis dengan MTTR rata-rata 210 ms |
| 📡 **Cross-Layer Detection** | Gabungan fitur jaringan (Network) + Hardware Performance Counter (HPC) |
| 🖥️ **Edge Computing** | Implementasi pada Raspberry Pi 5 (ARM Cortex-A76, 2GB RAM) |
| 📊 **Real-time Monitoring** | Grafana dashboard + InfluxDB time-series database |
| 🚀 **One-Command Deploy** | Setup otomatis dengan `make setup` |

---

## 🏗️ Arsitektur Sistem

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SISTEM SATSET                                  │
└─────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────┐
│                                  INPUT                                      │
│                     IoT-23 + CICIoT2023 (Training)                          │
│              4 fitur: n_packets, total_bytes, cache_misses, instructions    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                 PROSES                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. Preprocessing: Normalisasi Min-Max + Rate Coding (T=16)                │
│  2. SNN LIF: 4 → 64 → 32 → 2                                               │
│  3. Threat Score: 0,0 – 1,0 (Threshold 0,6)                               │
│  4. Antifragile: STDP update setiap serangan                               │
│  5. Self-healing: Restart container (MTTR < 1 detik)                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                 OUTPUT                                      │
│         Threat Score + Klasifikasi (Normal/Serangan) + Self-healing        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Metrik Kinerja

| Metrik | IoT-23 (Validation) | CICIoT2023 (Cross-Dataset) |
| :--- | :---: | :---: |
| **Akurasi** | 95.96% | **94.50%** |
| **Precision** | 93.69% | **97.74%** |
| **Recall** | 99.96% | **96.21%** |
| **F1-Score** | 96.72% | **96.97%** |

### Ablation Study: Kontribusi HPC

| Pipeline | F1-Score | Improvement |
| :--- | :---: | :---: |
| Network-Only (2 fitur) | 81.86% | - |
| **Network+HPC (5 fitur)** | **99.21%** | **+17.35%** |

---

## 🚀 One-Command Setup

Clone repository dan jalankan setup otomatis:

```bash
git clone https://github.com/Nur-Hidayat-FTI22E/SATSET_code.git
cd SATSET_code
make setup
```

### Yang Terjadi Saat `make setup`

```text
⏳  ██████████████████████████████  100%  System Check & Auto Install ✅
⏳  ██████████████████████████████  100%  Virtual Environment ✅
⏳  ██████████████████████████████  100%  Installing Dependencies ✅
⏳  ██████████████████████████████  100%  Environment Configuration ✅
⏳  ██████████████████████████████  100%  Downloading Model & Scaler ✅
⏳  ██████████████████████████████  100%  Starting Docker Containers ✅
⏳  ██████████████████████████████  100%  Validation & Testing ✅
✅  ██████████████████████████████  100%  Setup Complete! 🎉
```

---

## 📋 Perintah Tersedia

| Perintah | Deskripsi |
| :--- | :--- |
| `make setup` | Setup otomatis (install dependencies, download model, start Docker) |
| `make up` | Start Docker containers (MQTT, InfluxDB, Grafana) |
| `make down` | Stop Docker containers |
| `make brain` | Start inference engine (deteksi anomali) |
| `make hand` | Start self-healing trigger |
| `make attack` | Simulasi MQTT Flood attack |
| `make attack-hpc` | Simulasi CPU attack (HPC) |
| `make attack-network` | Simulasi Network attack (DDoS) |
| `make attack-portscan` | Simulasi Port Scan attack |
| `make status` | Tampilkan status Docker containers |
| `make logs` | Tampilkan log Docker containers |
| `make clean` | Bersihkan semua file (venv, model, data) |
| `make help` | Tampilkan semua perintah |

---

## 📁 Struktur Proyek

```text
SATSET_code/
├── Makefile                    # Perintah utama
├── setup.py                    # Setup otomatis
├── requirements.txt            # Dependencies
├── .env.example                # Template environment
├── .gitignore                  # File yang tidak di-commit
├── README.md                   # Dokumentasi
│
├── brain/                      # Modul deteksi (SNN)
│   ├── inference_engine.py     # Inference engine utama
│   ├── snn_model.py            # Arsitektur SNN
│   └── model/
│       ├── snn_model.pt        # Model terlatih (2 fitur)
│       └── snn_model_scaler.pkl # Scaler
│
├── hand/                       # Modul self-healing
│   └── heal_trigger.py         # Self-healing trigger
│
├── senses/                     # Modul telemetry
│   ├── telemetry_agent.py      # Pengumpul data
│   ├── attack_simulator.py     # Simulasi MQTT Flood
│   ├── attack_hpc.py           # Simulasi CPU attack
│   ├── attack_network.py       # Simulasi Network attack
│   └── attack_portscan.py      # Simulasi Port Scan
│
└── docker/                     # Docker configuration
    └── docker-compose.yml      # Docker Compose file
```

---

## 🔧 Konfigurasi

### Environment Variables (`.env`)

| Variabel | Default | Keterangan |
| :--- | :--- | :--- |
| `MQTT_HOST` | `localhost` | MQTT broker host |
| `MQTT_PORT` | `1883` | MQTT broker port |
| `INFLUXDB_URL` | `http://localhost:8086` | InfluxDB URL |
| `INFLUXDB_ORG` | `satset-lab` | InfluxDB organization |
| `INFLUXDB_BUCKET` | `satset` | InfluxDB bucket |
| `INFLUXDB_TOKEN` | `-` | **WAJIB** InfluxDB token |
| `THREAT_THRESHOLD` | `0.6` | Threshold deteksi serangan |
| `INFERENCE_INTERVAL` | `1.0` | Interval inferensi (detik) |
| `CONTAINER_NAME` | `satset-mosquitto` | Container MQTT yang akan di-restart |
| `BASE_COOLDOWN` | `15.0` | Cooldown awal self-healing (detik) |
| `MAX_COOLDOWN` | `120.0` | Cooldown maksimal (detik) |

### Cara Konfigurasi

```bash
# Copy template
cp .env.example .env

# Edit sesuai kebutuhan
nano .env

# Isi InfluxDB token (WAJIB)
INFLUXDB_TOKEN=your_super_secret_influx_token_here
```

---

## 📊 Dashboard

| Service | URL | Default Credential |
| :--- | :--- | :--- |
| **Grafana** | `http://localhost:3000` | `admin` / `admin` |
| **InfluxDB** | `http://localhost:8086` | - |

---

## 📝 Penelitian Terkait

| Peneliti | Metode | Perbedaan dengan SATSET |
| :--- | :--- | :--- |
| Vishwanath et al. (2025) | Hybrid SNN | Tanpa implementasi edge, tanpa antifragile |
| Wang et al. (2024) | LSTM + HPC | Bukan SNN, tanpa self-healing |
| Zhukabayeva et al. (2025) | Survey literatur | Teoritis, tanpa implementasi |

**Keunggulan SATSET:**
- ✅ Implementasi pada Raspberry Pi 5 (edge nyata)
- ✅ Deteksi cross-layer (Network + HPC)
- ✅ Mekanisme antifragile (STDP)
- ✅ Self-healing otomatis (MTTR 210 ms)
- ✅ Validasi multi-dataset (IoT-23 + CICIoT2023)

---

## 📄 Lisensi

Distributed under the MIT License. See `LICENSE` for more information.

---

## 🙏 Kontribusi

Kontribusi selalu diterima! Silakan buat *issue* atau *pull request*.

Dibuat dengan ❤️ oleh **Nur Hidayat**  
*Universitas Muhammadiyah Makassar, 2026*