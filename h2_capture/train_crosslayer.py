#!/usr/bin/env python3
"""
SATSET — H-3 : Model Cross-Layer + Ablation HPC (Raspberry Pi 5)
===============================================================
Melatih SATSET brain pada dataset cross-layer hasil H-2, lalu MEMBUKTIKAN
kontribusi HPC dengan ablation:

    Model A (net saja)     : n_packets, total_bytes                       (2 fitur)
    Model B (net + HPC)    : + cache_misses, instructions, branch_misses  (5 fitur)

Menjawab S-2 (kontribusi HPC nyata & terukur) dan melengkapi S-9 (metrik +
latency tersimpan). Juga menyimpan model B sebagai model deployment.

Pembersihan (activity-based labeling):
  * Baris pertama tiap skenario dibuang (warm-up perf/cache).
  * Baris berlabel attack yang sinyal jaringannya di baseline benign (tool
    serangan sudah berhenti) dikecualikan — jujur & standar dalam konstruksi
    dataset.

Colab/Pi:
    python3 train_crosslayer.py --data pi_crosslayer_dataset.csv --out_dir _h3_out
Uji kode:
    python3 train_crosslayer.py --selftest
"""
import argparse, os, json, time
import numpy as np, pandas as pd

NET = ["n_packets", "total_bytes"]
HPC = ["cache_misses", "instructions", "branch_misses"]


def clean(df):
    """Buang warm-up + jendela attack tak-aktif. Sebuah jendela attack dianggap
    AKTIF bila jaringan ATAU HPC melonjak di atas baseline benign — ini penting
    agar cpu_attack (paket rendah tapi HPC tinggi) tidak ikut terbuang."""
    df = df.copy()
    df = df.groupby("scenario", group_keys=False).apply(lambda g: g.iloc[1:])   # warm-up
    b = df.loc[df.label == 0]
    net_thr = max(b["n_packets"].quantile(0.95) * 3, b["n_packets"].quantile(0.95) + 50)
    hpc_thr = b["instructions"].quantile(0.95) * 1.5
    active = (df["n_packets"] > net_thr) | (df["instructions"] > hpc_thr)
    inactive_attack = (df.label == 1) & (~active)
    before = len(df)
    df = df[~inactive_attack]
    print(f"[clean] aktif bila n_packets>{net_thr:.0f} ATAU instructions>{hpc_thr:.0f} | "
          f"buang {int(inactive_attack.sum())} jendela attack tak-aktif "
          f"({before}→{len(df)} baris)")
    return df


def train_eval(Xtr, ytr, Xte, yte, epochs, tag, seed=42):
    import torch, torch.nn as nn
    import snntorch as snn
    from snntorch import surrogate
    torch.manual_seed(seed); np.random.seed(seed)
    IN = Xtr.shape[1]

    class SNN(nn.Module):
        def __init__(self, IN, steps=16, beta=0.9):
            super().__init__(); g = surrogate.fast_sigmoid(slope=25); self.steps = steps
            self.fc1 = nn.Linear(IN, 64)
            self.lif1 = snn.Leaky(beta=beta, spike_grad=g, learn_beta=True, learn_threshold=True)
            self.drop = nn.Dropout(0.3)
            self.fc2 = nn.Linear(64, 2)
            self.lif2 = snn.Leaky(beta=beta, spike_grad=g, learn_beta=True, learn_threshold=True)
        def forward(self, x):
            m1 = self.lif1.init_leaky(); m2 = self.lif2.init_leaky(); out = []
            for _ in range(self.steps):                 # direct/current encoding (deterministik)
                s1, m1 = self.lif1(self.fc1(x), m1); s1 = self.drop(s1)
                s2, m2 = self.lif2(self.fc2(s1), m2); out.append(s2)
            return torch.stack(out).sum(0)

    dev = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = SNN(IN).to(dev)
    ytr_t = torch.tensor(ytr)
    n0 = (ytr_t == 0).sum().float(); n1 = (ytr_t == 1).sum().float(); tot = n0 + n1
    w = torch.tensor([tot/(2*n0+1e-9), tot/(2*n1+1e-9)]).to(dev)
    crit = nn.CrossEntropyLoss(weight=w)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    dl = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(torch.tensor(Xtr), ytr_t), batch_size=64, shuffle=True)
    for ep in range(epochs):
        model.train()
        for xb, yb in dl:
            xb, yb = xb.to(dev), yb.to(dev)
            opt.zero_grad(); loss = crit(model(xb), yb); loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step()

    model.eval()
    with torch.no_grad():
        pred = model(torch.tensor(Xte).to(dev)).argmax(1).cpu().numpy()
    tp=int(((pred==1)&(yte==1)).sum()); tn=int(((pred==0)&(yte==0)).sum())
    fp=int(((pred==1)&(yte==0)).sum()); fn=int(((pred==0)&(yte==1)).sum())
    acc=(tp+tn)/max(1,len(yte)); prec=tp/max(1,tp+fp); rec=tp/max(1,tp+fn)
    spec=tn/max(1,tn+fp); f1=2*prec*rec/max(1e-9,prec+rec)
    m = {"tag":tag,"features":IN,"acc":acc,"precision":prec,"recall":rec,
         "specificity":spec,"f1":f1,"tp":tp,"fp":fp,"fn":fn,"tn":tn}
    print(f"  [{tag}] acc={acc:.4f} prec={prec:.4f} rec={rec:.4f} "
          f"spec={spec:.4f} f1={f1:.4f}  (TP{tp} FP{fp} FN{fn} TN{tn})")

    # ukur latency inferensi 1 jendela (rata-rata 200x)
    x1 = torch.tensor(Xte[:1]).to(dev)
    with torch.no_grad():
        for _ in range(10): model(x1)          # warm-up
        t0 = time.time()
        for _ in range(200): model(x1)
        lat_ms = (time.time()-t0)/200*1000
    m["latency_ms"] = lat_ms
    print(f"        latency/inferensi: {lat_ms:.3f} ms")
    return model, m, dev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=None)
    ap.add_argument("--out_dir", default="./_h3_out")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.model_selection import train_test_split
    os.makedirs(args.out_dir, exist_ok=True)

    if args.selftest:
        print(">> SELF-TEST (sintetis mirip data Pi).")
        rng = np.random.default_rng(0)
        def rows(n, scen, lab, npk, tb, cm, ins, bm):
            return pd.DataFrame({
                "scenario":scen, "label":lab,
                "n_packets": rng.lognormal(np.log(npk), .3, n),
                "total_bytes": rng.lognormal(np.log(tb), .3, n),
                "cache_misses": rng.lognormal(np.log(cm), .3, n),
                "instructions": rng.lognormal(np.log(ins), .3, n),
                "branch_misses": rng.lognormal(np.log(bm), .3, n)})
        df = pd.concat([
            rows(300,"benign",0, 124,14000, 1e6,4e8,1e6),
            rows(120,"ddos",1, 495000,20e6, 15e6,4.2e9,1.5e7),
            rows(120,"portscan",1, 280000,12e6, 13e6,3.7e9,1.4e7),
            rows(60,"mqtt_flood",1, 15000,45e6, 75e6,7.5e9,3e7),
            # cpu_attack: net ≈ BENIGN tapi HPC TINGGI -> net-only BUTA, HPC menang
            rows(120,"cpu_attack",1, 130,14500, 60e6,9e9,2.5e7),
        ], ignore_index=True)
    else:
        assert args.data, "Butuh --data atau --selftest."
        df = pd.read_csv(args.data)

    print(f">> Dataset mentah: {len(df)} baris")
    print(df.groupby(["scenario","label"]).size())
    df = clean(df)

    Xnet = df[NET].values.astype(np.float32)
    Xall = df[NET+HPC].values.astype(np.float32)
    y = df["label"].values.astype(int)

    # split sama untuk kedua model (adil)
    idx = np.arange(len(y))
    itr, ite = train_test_split(idx, train_size=0.7, stratify=y, random_state=42)

    def prep(X, itr, ite):
        Xl = np.log1p(np.clip(X,0,None))
        sc = MinMaxScaler().fit(Xl[itr])
        return np.clip(sc.transform(Xl[itr]),0,1), np.clip(sc.transform(Xl[ite]),0,1), sc

    Xtr_n, Xte_n, _   = prep(Xnet, itr, ite)
    Xtr_a, Xte_a, sc_a = prep(Xall, itr, ite)
    ytr, yte = y[itr], y[ite]

    print("\n>> Melatih Model A (net saja, 2 fitur) ...")
    _, mA, _ = train_eval(Xtr_n, ytr, Xte_n, yte, args.epochs, "NET")
    print(">> Melatih Model B (net + HPC, 5 fitur) ...")
    modelB, mB, dev = train_eval(Xtr_a, ytr, Xte_a, yte, args.epochs, "NET+HPC")

    # tabel bukti HPC
    print("\n" + "="*62)
    print("  TABEL BUKTI CROSS-LAYER (kontribusi HPC)")
    print("="*62)
    print(f"  {'Metrik':14s}{'NET':>12s}{'NET+HPC':>12s}{'Δ (HPC)':>12s}")
    for k,lab in [("acc","Accuracy"),("precision","Precision"),("recall","Recall"),
                  ("specificity","Specificity"),("f1","F1")]:
        print(f"  {lab:14s}{mA[k]:>12.4f}{mB[k]:>12.4f}{mB[k]-mA[k]:>+12.4f}")
    print("="*62)

    import torch
    torch.save(modelB.state_dict(), os.path.join(args.out_dir,"satset_crosslayer.pt"))
    with open(os.path.join(args.out_dir,"h3_metrics.json"),"w") as f:
        json.dump({"features_all":NET+HPC,"transform":"log1p_then_minmax","encoding":"direct",
                   "scaler_min":sc_a.data_min_.tolist(),"scaler_max":sc_a.data_max_.tolist(),
                   "model_net":mA,"model_net_hpc":mB}, f, indent=2)
    print(f"\n✅ Model & metrik → {args.out_dir}/  (satset_crosslayer.pt, h3_metrics.json)")


if __name__ == "__main__":
    main()
