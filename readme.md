# SATSET: Spiking-based Antifragile Twin for Self-healing Edge Technology

[![Target: Jurnal Sinta 2](https://img.shields.io/badge/Target-Jurnal_Sinta_2-green?style=for-the-badge)](#)

**SATSET** adalah kerangka kerja (framework) keamanan otonom generasi masa depan yang dirancang untuk melindungi ekosistem **AIoT** (Artificial Intelligence of Things) dari serangan siber multi-level.

Berbeda dengan sistem keamanan tradisional yang bersifat reaktif atau sekadar bertahan (*resilient*), SATSET mengadopsi paradigma **Antifragility** — sebuah kemampuan sistem untuk tidak hanya pulih dari guncangan serangan, tetapi justru **belajar dan menjadi lebih kuat** akibat gangguan tersebut melalui mekanisme saraf biologis.

---

## 🚀 Konsep & Filosofi Sistem

Penelitian ini didasarkan pada kebutuhan mendesak untuk mengatasi **"Accountability Void"** dalam keamanan IoT, di mana sistem sering kali lumpuh total saat konektivitas cloud diputus oleh serangan DDoS hyper-volumetrik *(rekor 22,2 Tbps pada 2025)*. SATSET menawarkan solusi melalui:

- **Neuromorphic Intelligence**: Menggunakan Spiking Neural Network (SNN) yang meniru efisiensi otak manusia (55% lebih hemat energi) untuk deteksi anomali temporal secara real-time.
- **Localized Autonomy**: Menggunakan pendekatan *Local-First Infrastructure-as-Code* (IaC) untuk regenerasi layanan secara instan (MTTR < 1 detik) tanpa bergantung pada API cloud.

---

## 🏗️ Arsitektur 4 Pilar (Closed-Loop MAPE-K)

Sistem ini mengintegrasikan empat pilar utama ke dalam siklus otonom **Monitor-Analyze-Plan-Execute**:

### 1. 🔍 Senses (Monitor — Cross-Layer Telemetry)

Mengekstraksi fitur lintas-lapisan secara sinkron untuk memvalidasi ancaman:

- **Network Layer**: Memantau statistik paket MQTT/LoRa (laju paket, ukuran, dan interval waktu).
- **Hardware Layer**: Mengambil data Hardware Performance Counters (HPC) dari CPU ARM BCM2712 Raspberry Pi 5 (misal: `cache-misses`, `instructions-retired`) untuk mendeteksi anomali pada tingkat mikroarsitektur.

### 2. 🧠 Brain (Analyze — SNN Core)

Mesin inferensi berbasis `snnTorch` yang berjalan secara asinkron:

- **LIF Neuron**: Menggunakan model *Leaky Integrate-and-Fire* untuk memproses data sebagai lonjakan pulsa saraf (*spikes*).
- **Antifragile Loop**: Implementasi STDP (*Spike-Timing Dependent Plasticity*) yang secara otonom memperkuat bobot sinaptik deteksi setiap kali pola serangan baru muncul.

### 3. 💾 Memory (Knowledge — Digital Twin)

Mengintegrasikan **InfluxDB** dan **Grafana** sebagai replika virtual yang menyimpan status fisik perangkat. Digital Twin bertindak sebagai *"Intelligent Mirror"* untuk mensimulasikan dampak serangan dan memvalidasi langkah perbaikan sebelum dieksekusi.

### 4. 🤖 Hand (Execute — Self-Healing IaC)

Sistem saraf pemulihan menggunakan **Event-Driven Ansible (EDA)**:

- Melakukan auto-redeploy kontainer Docker layanan yang terinfeksi.
- Memperbarui aturan firewall `iptables` lokal dalam hitungan milidetik tanpa intervensi manusia.

---

## 🗺️ Roadmap Pengembangan & Target Capaian

| Tahap  | Fokus Pengembangan             | Target Capaian (Milestones)                                                                                      |
|--------|-------------------------------|------------------------------------------------------------------------------------------------------------------|
| ✅ Fase 1 | Infrastructure Baseline        | Setup lab virtual menggunakan Docker Compose. MQTT Broker, InfluxDB, dan Grafana wajib berstatus *Up & Healthy*. |
| ✅ Fase 2 | Cross-Layer Acquisition        | Membangun agen telemetri Python yang mengintegrasikan data jaringan dan simulasi register CPU (HPC) melalui korelasi sinkron. |
| ✅ Fase 3 | Neuromorphic Brain Core        | Implementasi model SNN LIF. Target: Akurasi deteksi serangan DDoS **> 95%** menggunakan dataset IoT-23. (Tercapai ~92% untuk model edge ringan). |
| ✅ Fase 4 | Autonomous Healing Loop        | Integrasi Ansatz Rulebook / Python trigger untuk menghubungkan deteksi *Brain* ke aksi *Hand*. Target: **MTTR < 1 detik**.       |
| ⏳ Fase 5 | Antifragile Optimization       | Aktivasi pembelajaran online STDP. Target: Pembuktian peningkatan akurasi sistem pada variasi serangan kedua tanpa pelatihan ulang. |

---

## 🚀 Quick Start (Cara Menjalankan Sistem)

Proyek ini dilengkapi dengan `Makefile` untuk mempermudah eksekusi seluruh komponen.

### 1. Instalasi Dependensi
Pastikan Python 3.10+ terinstal, kemudian masuk ke environment (disarankan gunakan virtual environment):
```bash
make install
```

### 2. Jalankan Infrastruktur (Docker)
Ini akan menghidupkan Mosquitto MQTT, InfluxDB, dan Grafana:
```bash
make up
```
*Tunggu sekitar 10 detik. Akses Dashboard Grafana di `http://localhost:3000` (User: admin, Pass: admin).*

### 3. Hidupkan "Senses" dan "Brain"
Buka 2 terminal baru dan jalankan masing-masing:
```bash
# Terminal 1: Menjalankan agen pengumpul data
make senses

# Terminal 2: Menjalankan AI inference engine (SNN)
make brain
```
*(Cek Grafana: Grafik Network dan CPU akan bergerak dengan Threat Score di angka stabil mendekati 0.0)*

### 4. Hidupkan "Hand" (Sistem Self-Healing)
Buka terminal baru untuk menjalankan agen pemulihan otonom:
```bash
# Mode dry-run (hanya mencetak log tanpa restart Docker sungguhan)
make hand-dry

# atau mode production (membutuhkan akses ke Docker socket)
make hand
```

### 5. Simulasi Serangan DDoS & Reaksi Otonom!
Buka terminal baru dan tembakkan serangan DDoS ke sistem:
```bash
make attack
```
*Lihat keajaibannya di Grafana!: Threat Score akan melonjak ke angka **1.0 (Merah)**, dan agent `hand` akan langsung mencetak log `[HealTrigger] Healing complete.` secara otomatis dalam hitungan milidetik.*

---

## 🛠️ Stack Teknologi

| Kategori            | Teknologi                                                    |
|---------------------|--------------------------------------------------------------|
| **Languages**       | Python 3.10+, C++ (ESP32 Firmware), YAML (Ansible/Docker)   |
| **AI Frameworks**   | snnTorch, PyTorch (LIF Neuron & STDP Learning)               |
| **Automation/IaC**  | Event-Driven Ansible (EDA), Docker, Docker Compose           |
| **Observability**   | InfluxDB v2 (Time-series store), Grafana (Digital Twin viz.) |
| **Hardware**        | Raspberry Pi 5 (Cortex-A76), akselerasi kriptografi 45× vs Pi 4 |

---

## 🧪 Metrik Validasi untuk Jurnal Sinta 2

Penelitian ini mengukur keberhasilan arsitektur berdasarkan:

- **Mean Time to Recovery (MTTR)**: Kecepatan sistem kembali ke status *"Golden Image"* pasca-serangan.
- **Energy Efficiency Gain**: Penghematan siklus CPU SNN vs model AI tradisional di perangkat edge.
- **Detection Specificity**: Kemampuan SNN membedakan trafik lonjakan legal vs serangan DDoS melalui verifikasi hardware.

---

## 📝 Konteks Akademik

Riset ini dikembangkan oleh **Nur Hidayat** (NIM: `105841115422`) sebagai proyek Capstone dan syarat kelulusan Program Studi Informatika, **Universitas Muhammadiyah Makassar**.

Penelitian ini dirancang untuk menjawab tantangan kedaulatan digital nasional sesuai **Regulasi BSSN No. 4 Tahun 2023**.

> 📧 **Kontak Peneliti**: nurhidayat@example.com