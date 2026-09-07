# 🚀 SATSET — Spiking-based Antifragile Twin for Self-healing Edge Technology

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/SNN-snnTorch-red.svg" alt="snnTorch">
  <img src="https://img.shields.io/badge/Edge-Raspberry%20Pi%205-green.svg" alt="Raspberry Pi 5">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/Status-Stable-brightgreen.svg" alt="Status">
</p>

Sistem deteksi anomali jaringan IoT berbasis **Spiking Neural Network (SNN)** dengan mekanisme **antifragilitas** dan **self-healing** yang diimplementasikan pada perangkat edge **Raspberry Pi 5**.

---

## 📋 Daftar Isi

- [✨ Fitur Utama](#-fitur-utama)
- [🏗️ Arsitektur Sistem](#️-arsitektur-sistem)
- [📊 Metrik Kinerja](#-metrik-kinerja)
- [🚀 Rapid Setup](#-rapid-setup)
- [📋 Perintah CLI (Makefile)](#-perintah-cli-makefile)
- [📁 Struktur Proyek](#-struktur-proyek)
- [🔧 Konfigurasi Sistem](#-konfigurasi-sistem)
- [📊 Dashboard & Monitoring](#-dashboard--monitoring)
- [📝 Penelitian Terkait](#-penelitian-terkait)
- [📄 Lisensi](#-lisensi)
- [🙏 Kontribusi](#-kontribusi)

---

## ✨ Fitur Utama

| Fitur | Keterangan |
| :--- | :--- |
| 🧠 **Spiking Neural Network** | Deteksi anomali berbasis SNN LIF (*Leaky Integrate-and-Fire*) dengan efisiensi energi tinggi. |
| 🛡️ **Antifragile** | Mampu belajar dan beradaptasi dari serangan melalui mekanisme STDP (*Spike-Timing Dependent Plasticity*). |
| 🔄 **Self-Healing** | Pemulihan layanan secara otomatis dengan *Mean Time to Recovery* (MTTR) rata-rata 210 ms. |
| 📡 **Cross-Layer Detection** | Integrasi fitur tingkat jaringan (*Network*) dan *Hardware Performance Counter* (HPC). |
| 🖥️ **Edge Computing** | Dioptimalkan khusus untuk deployment pada Raspberry Pi 5 (ARM Cortex-A76, 2GB RAM). |
| 📊 **Real-time Monitoring** | Visualisasi telemetri interaktif melalui Grafana dashboard dan InfluxDB time-series database. |
| 🚀 **One-Command Deploy** | Otomasi penuh untuk instalasi dependencies dan deployment dengan `make setup`. |

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
│  1. Preprocessing : Normalisasi Min-Max + Rate Coding (T=16)               │
│  2. SNN LIF Model : 4 → 64 → 32 → 2                                        │
│  3. Threat Score  : Range 0.0 – 1.0 (Threshold: 0.6)                       │
│  4. Antifragile   : STDP update secara real-time setiap serangan           │
│  5. Self-healing  : Automated Container Restart (MTTR < 1 detik)           │
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

### Evaluasi Model Pada Dataset

| Metrik | IoT-23 (Validation) | CICIoT2023 (Cross-Dataset) |
| :--- | :---: | :---: |
| **Akurasi** | 95.96% | **94.50%** |
| **Precision** | 93.69% | **97.74%** |
| **Recall** | 99.96% | **96.21%** |
| **F1-Score** | 96.72% | **96.97%** |

### Ablation Study: Kontribusi Feature HPC

| Pipeline | F1-Score | Peningkatan |
| :--- | :---: | :---: |
| Network-Only (2 Fitur) | 81.86% | — |
| **Network + HPC (5 Fitur)** | **99.21%** | **+17.35%** |

---

## 🚀 Rapid Setup

Clone repositori dan jalankan skrip instalasi otomatis:

```bash
git clone https://github.com/Nur-Hidayat-FTI22E/SATSET_code.git
cd SATSET_code
make setup
```

### Proses Eksekusi `make setup`

```text
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   🚀  SATSET — Spiking-based Antifragile Twin                    ║
║       for Self-healing Edge Technology                            ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
📦  Setting up SATSET...
  ✅  Creating virtual environment...     DONE (2s)
  ✅  Installing PyTorch (CPU for ARM64)...     DONE (45s)
  ✅  Installing dependencies...     DONE (12s)
  ✅  Running setup script...     DONE (3s)
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   ✅  Setup Complete! 🎉                                          ║
║                                                                   ║
║   📊  Services:                                                   ║
║      📡 MQTT Broker     → localhost:1883                         ║
║      📦 InfluxDB        → http://localhost:8086                  ║
║      📊 Grafana         → http://localhost:3000                  ║
║                                                                   ║
║   🚀  Next Steps:                                                ║
║      make brain    → Start inference engine                      ║
║      make hand     → Start self-healing trigger                  ║
║      make attack   → Simulate attack                             ║
║      make up       → Start Docker containers                     ║
║      make down     → Stop Docker containers                     ║
║      make status   → Show Docker status                          ║
║      make help     → Show all commands                           ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

> **Catatan:** Jika proses diinterupsi (`Ctrl + C`), terminal akan menampilkan notifikasi berikut:
> ```text
> ^C  ❌  Installing PyTorch...     INTERRUPTED (12s)
> ```

---

## 📋 Perintah CLI (Makefile)

| Perintah | Deskripsi |
| :--- | :--- |
| `make setup` | Setup otomatis (instalasi dependensi, unduh model, serta inisialisasi Docker) |
| `make up` | Menjalankan Docker containers (MQTT, InfluxDB, Grafana) |
| `make down` | Menghentikan seluruh Docker containers |
| `make brain` | Menjalankan *inference engine* SNN untuk deteksi anomali |
| `make hand` | Menjalankan modul pemicu *self-healing* |
| `make attack` | Menjalankan simulasi serangan MQTT Flood |
| `make attack-hpc` | Menjalankan simulasi serangan CPU Exhaustion (HPC) |
| `make attack-network` | Menjalankan simulasi serangan Network (DDoS) |
| `make attack-portscan` | Menjalankan simulasi serangan Port Scan |
| `make status` | Memeriksa status operasional Docker containers |
| `make logs` | Menampilkan log sistem dari Docker containers |
| `make clean` | Membersihkan lingkungan kerja (menghapus `venv`, model, dan cache data) |
| `make help` | Menampilkan panduan lengkap seluruh perintah yang tersedia |

---

## 📁 Struktur Proyek

```text
SATSET_code/
├── Makefile                    # Perintah CLI utama
├── setup.py                    # Script setup otomasi
├── requirements.txt            # Daftar dependensi Python
├── .env.example                # Template konfigurasi environment
├── .gitignore                  # Berkas pengecualian Git
├── README.md                   # Dokumentasi proyek
│
├── brain/                      # Modul SNN & Inference Engine
│   ├── inference_engine.py     # Engine inferensi utama
│   ├── snn_model.py            # Arsitektur SNN LIF
│   └── model/
│       ├── snn_model.pt        # Checkpoint model terlatih
│       └── snn_model_scaler.pkl # Scaler data
│
├── hand/                       # Modul Self-Healing Trigger
│   └── heal_trigger.py         # Eksekutor pemulihan sistem
│
├── senses/                     # Modul Telemetri & Simulasi
│   ├── telemetry_agent.py      # Kolektor data sensor dan jaringan
│   ├── attack_simulator.py     # Generator simulasi MQTT Flood
│   ├── attack_hpc.py           # Generator simulasi serangan CPU
│   ├── attack_network.py       # Generator simulasi serangan DDoS
│   └── attack_portscan.py      # Generator simulasi Port Scan
│
└── docker/                     # Konfigurasi Containerization
    └── docker-compose.yml      # Berkas orchestration Docker
```

---

## 🔧 Konfigurasi Sistem

### Environment Variables (`.env`)

| Variabel | Default | Keterangan |
| :--- | :--- | :--- |
| `MQTT_HOST` | `localhost` | Host MQTT broker |
| `MQTT_PORT` | `1883` | Port MQTT broker |
| `INFLUXDB_URL` | `http://localhost:8086` | URL server InfluxDB |
| `INFLUXDB_ORG` | `satset-lab` | Nama organisasi InfluxDB |
| `INFLUXDB_BUCKET` | `satset` | Nama bucket InfluxDB |
| `INFLUXDB_TOKEN` | `-` | Token autentikasi InfluxDB (**Wajib diisi**) |
| `THREAT_THRESHOLD` | `0.6` | Batas *threshold* deteksi serangan |
| `INFERENCE_INTERVAL` | `1.0` | Interval waktu inferensi (detik) |
| `CONTAINER_NAME` | `satset-mosquitto` | Target container MQTT yang di-restart |
| `BASE_COOLDOWN` | `15.0` | *Cooldown* awal untuk pemulihan (detik) |
| `MAX_COOLDOWN` | `120.0` | *Cooldown* maksimal pemulihan (detik) |

### Langkah Konfigurasi

```bash
# Duplicate file template environment
cp .env.example .env

# Edit variabel sesuai kebutuhan sistem Anda
nano .env

# Pastikan menyisipkan token InfluxDB yang sah
INFLUXDB_TOKEN=your_super_secret_influx_token_here
```

---

## 📊 Dashboard & Monitoring

| Layanan | URL Akses | Kredensial Default |
| :--- | :--- | :--- |
| **Grafana** | `http://localhost:3000` | `admin` / `admin` |
| **InfluxDB** | `http://localhost:8086` | Terkonfigurasi melalui `.env` |

---

## 📝 Penelitian Terkait

| Peneliti | Metode | Perbedaan Utama dengan SATSET |
| :--- | :--- | :--- |
| Vishwanath et al. (2025) | Hybrid SNN | Tidak diimplementasikan pada perangkat edge & tanpa mekanisme antifragile. |
| Wang et al. (2024) | LSTM + HPC | Bukan arsitektur berbasis SNN & tidak memiliki fitur *self-healing*. |
| Zhukabayeva et al. (2025) | Survey Literatur | Studi teoretis tanpa bentuk implementasi praktis. |

**Keunggulan SATSET:**
- ✅ Implementasi riil pada perangkat edge **Raspberry Pi 5**.
- ✅ Pendeteksian multi-layer (*Network* + *Hardware Performance Counter*).
- ✅ Kemampuan adaptasi serangan menggunakan mekanisme **Antifragile (STDP)**.
- ✅ Pemulihan mandiri secara otomatis (**Self-healing** dengan MTTR 210 ms).
- ✅ Pengujian validasi lintas dataset (**IoT-23** + **CICIoT2023**).

---

## 📄 Lisensi

Distributed under the MIT License. See `LICENSE` for more information.

---

## 🙏 Kontribusi

Kontribusi selalu terbuka! Silakan buat *issue* baru atau kirimkan *pull request*.

---

<p align="center">
  Dibuat oleh <b>C0x1n's</b><br>
  <i>Universitas Muhammadiyah Makassar, 2026</i>
</p>