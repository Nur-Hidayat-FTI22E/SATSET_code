"""
SATSET — Brain Layer data_loader.py (Multi-Dataset Version)
Menggabungkan IoT-23, CICIoT2023, dan Edge-IIoTset sesuai desain BAB III Skripsi.
Mengekstrak data ke dalam 6 fitur utama menggunakan HPC Proxy Mapping.
"""

import os
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from torch.utils.data import Dataset, DataLoader
import torch

# ── Konfigurasi Label ───────────────────────────────────────────────────────
BENIGN_LABELS = {"Benign", "-", "benign", "Normal", "0"}

class SATSETDataset(Dataset):
    """PyTorch Dataset untuk gabungan multi-dataset."""
    def __init__(self, features, labels):
        self.features = torch.tensor(features, dtype=torch.float32)
        self.labels = torch.tensor(labels, dtype=torch.long)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return self.features[idx], self.labels[idx]

# ── Modul Ekstraksi & HPC Proxy Mapping (BAB III E.2) ────────────────────────
def _extract_6_features_and_hpc_proxy(df: pd.DataFrame, source: str) -> tuple[np.ndarray, np.ndarray]:
    """
    Mengekstrak 6 fitur utama (packet_rate, packet_size, interval, 
    cache_misses, instructions_retired, branch_misses) dari masing-masing dataset.
    """
    extracted = pd.DataFrame()
    
    if source == "iot23":
        # Ekstraksi fitur dasar dari IoT-23
        extracted['packet_rate'] = df['orig_pkts'] / (df['duration'].replace(0, 0.001))
        extracted['packet_size'] = df['orig_ip_bytes'] / (df['orig_pkts'].replace(0, 1))
        extracted['interval'] = 1 / (extracted['packet_rate'].replace(0, 0.001))
        labels = np.where(df['label'].isin(BENIGN_LABELS), 0, 1)

    elif source == "ciciot2023":
        # Sesuaikan dengan nama kolom asli CICIoT2023 nantinya
        # Contoh: Flow Bytes/s, Flow Packets/s, dll
        extracted['packet_rate'] = df['Flow_Packets_s'] 
        extracted['packet_size'] = df['Flow_Bytes_s'] / (df['Flow_Packets_s'].replace(0, 1))
        extracted['interval'] = 1 / (extracted['packet_rate'].replace(0, 0.001))
        labels = np.where(df['label'].isin(BENIGN_LABELS), 0, 1)

    elif source == "edge_iiotset":
        # Sesuaikan dengan nama kolom asli Edge-IIoTset nantinya
        extracted['packet_rate'] = df['Network_pkts'] / (df['Time'].replace(0, 0.001))
        extracted['packet_size'] = df['Network_bytes'] / (df['Network_pkts'].replace(0, 1))
        extracted['interval'] = 1 / (extracted['packet_rate'].replace(0, 0.001))
        labels = np.where(df['label'].isin(BENIGN_LABELS), 0, 1)

    else:
        raise ValueError("Dataset tidak dikenali.")

    # -- HPC PROXY MAPPING (BAB III C.1 & E.2) --
    # Memetakan trafik jaringan ke simulasi Hardware Performance Counter
    extracted['cache_misses'] = extracted['packet_rate'] * 15000.0
    extracted['instructions_retired'] = extracted['packet_size'] * 50000.0
    extracted['branch_misses'] = (extracted['cache_misses'] * 0.2) + (extracted['interval'] * 100.0)

    # Bersihkan NaN atau Inf yang mungkin terjadi saat pembagian
    extracted.replace([np.inf, -np.inf], np.nan, inplace=True)
    extracted.fillna(0, inplace=True)

    return extracted.values, labels

# ── Modul Penggabungan Dataset (BAB III C.1) ─────────────────────────────────
def load_and_merge_datasets(iot23_path: str, ciciot_path: str, edgeiiot_path: str) -> tuple[np.ndarray, np.ndarray]:
    """Menggabungkan ketiga dataset, mengekstrak fitur, dan menyatukannya."""
    all_features = []
    all_labels = []

    print("[DataLoader] Memuat & Mengekstrak IoT-23...")
    df_iot = pd.read_csv(iot23_path, skiprows=7) # format Zeek
    feat_iot, lbl_iot = _extract_6_features_and_hpc_proxy(df_iot, "iot23")
    all_features.append(feat_iot)
    all_labels.append(lbl_iot)

    print("[DataLoader] Memuat & Mengekstrak CICIoT2023...")
    df_cic = pd.read_csv(ciciot_path)
    feat_cic, lbl_cic = _extract_6_features_and_hpc_proxy(df_cic, "ciciot2023")
    all_features.append(feat_cic)
    all_labels.append(lbl_cic)

    print("[DataLoader] Memuat & Mengekstrak Edge-IIoTset...")
    df_edge = pd.read_csv(edgeiiot_path)
    feat_edge, lbl_edge = _extract_6_features_and_hpc_proxy(df_edge, "edge_iiotset")
    all_features.append(feat_edge)
    all_labels.append(lbl_edge)

    # MERGE KETIGA DATASET
    print("[DataLoader] Menggabungkan (Merging) ketiga dataset menjadi satu...")
    merged_features = np.vstack(all_features)
    merged_labels = np.concatenate(all_labels)
    
    return merged_features, merged_labels

# ── Public API ─────────────────────────────────────────────────────────────
def get_dataloaders(
    iot23_path: str = None, 
    ciciot_path: str = None, 
    edgeiiot_path: str = None,
    batch_size: int = 128, 
    train_split: float = 0.8
) -> tuple[DataLoader, DataLoader, dict]:
    """ Kembalikan Dataloader untuk proses Training SNN. """
    
    # 1. Load, Extract 6 Features, and Merge
    X_raw, y = load_and_merge_datasets(iot23_path, ciciot_path, edgeiiot_path)

    # 2. Min-Max Scaling (BAB III E.1.a)
    print("[DataLoader] Melakukan Min-Max Scaling (0 - 1)...")
    scaler = MinMaxScaler(feature_range=(0, 1))
    X_norm = scaler.fit_transform(X_raw)

    # 3. Stratified Split Data (BAB III E.3)
    from sklearn.model_selection import train_test_split
    X_train, X_val, y_train, y_val = train_test_split(
        X_norm, y, train_size=train_split, stratify=y, random_state=42
    )

    train_dataset = SATSETDataset(X_train, y_train)
    val_dataset = SATSETDataset(X_val, y_val)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    scaler_stats = {
        "feature_min": scaler.data_min_.tolist(),
        "feature_max": scaler.data_max_.tolist(),
        "feature_names": ["packet_rate", "packet_size", "interval", "cache_misses", "instructions_retired", "branch_misses"]
    }

    return train_loader, val_loader, scaler_stats