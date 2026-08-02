"""
SATSET — Brain Layer
train.py

Script training SNN menggunakan BPTT (Backpropagation Through Time).

Usage:
    python train.py [options]

Options:
    --epochs    Jumlah epoch (default: 50)
    --batch     Batch size (default: 128)
    --lr        Learning rate (default: 5e-4)
    --steps     SNN timesteps (default: 16)
    --synthetic Gunakan synthetic data (default jika IoT-23 tidak ada)
    --data      Path ke IoT-23 CSV file
    --output    Path output model (default: model/snn_model.pt)
"""

import argparse
import os
import sys
import time

import torch
import torch.nn as nn
from tqdm import tqdm

from snn_model import build_model
from data_loader import get_dataloaders

os.makedirs("model", exist_ok=True)


def train_epoch(model, loader, optimizer, criterion, device) -> tuple[float, float]:
    model.train()
    total_loss, correct, total = 0.0, 0, 0

    for X_batch, y_batch in loader:
        X_batch = X_batch.to(device)
        y_batch = y_batch.to(device)

        optimizer.zero_grad()

        # Forward pass: spike output [T, B, 2]
        spk_out, mem_out = model(X_batch)

        # Sum spikes across time → [B, 2] — voting dari semua timestep
        spk_sum = spk_out.sum(dim=0)

        loss = criterion(spk_sum, y_batch)
        loss.backward()

        # Gradient clipping untuk stabilitas SNN
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        total_loss += loss.item() * len(y_batch)
        preds = spk_sum.argmax(dim=1)
        correct += (preds == y_batch).sum().item()
        total += len(y_batch)

    return total_loss / total, correct / total


@torch.no_grad()
def eval_epoch(model, loader, criterion, device) -> tuple[float, float]:
    model.eval()
    total_loss, correct, total = 0.0, 0, 0

    for X_batch, y_batch in loader:
        X_batch = X_batch.to(device)
        y_batch = y_batch.to(device)

        spk_out, _ = model(X_batch)
        spk_sum = spk_out.sum(dim=0)

        loss = criterion(spk_sum, y_batch)
        total_loss += loss.item() * len(y_batch)
        preds = spk_sum.argmax(dim=1)
        correct += (preds == y_batch).sum().item()
        total += len(y_batch)

    return total_loss / total, correct / total


def main():
    parser = argparse.ArgumentParser(description="SATSET SNN Training")
    parser.add_argument("--epochs",    type=int,   default=50,                  help="Training epochs")
    parser.add_argument("--batch",     type=int,   default=128,                 help="Batch size")
    parser.add_argument("--lr",        type=float, default=1e-3,                help="Learning rate")
    parser.add_argument("--steps",     type=int,   default=16,                  help="SNN timesteps")
    parser.add_argument("--synthetic", action="store_true",                     help="Use synthetic data")
    parser.add_argument("--data",      type=str,   default=None,                help="IoT-23 CSV path")
    parser.add_argument("--output",    type=str,   default="model/snn_model.pt",help="Model output path")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("=" * 60)
    print("  SATSET — Neuromorphic Brain Training")
    print("=" * 60)
    print(f"  Device    : {device}")
    print(f"  Epochs    : {args.epochs}")
    print(f"  Batch     : {args.batch}")
    print(f"  LR        : {args.lr}")
    print(f"  SNN Steps : {args.steps}")
    print("=" * 60)

    # ── Data ────────────────────────────────────────────────
    train_loader, val_loader, scaler_stats = get_dataloaders(
        csv_path=args.data,
        synthetic=args.synthetic,
        batch_size=args.batch,
    )

    # ── Model ────────────────────────────────────────────────
    model = build_model(num_steps=args.steps).to(device)
    print(f"\n[Train] Model parameters: {sum(p.numel() for p in model.parameters()):,}")

    # ── Class-weighted loss (mengatasi imbalanced dataset) ────
    # Hitung bobot dari distribusi label di training set
    all_labels = torch.cat([y for _, y in train_loader])
    n_normal = (all_labels == 0).sum().float()
    n_attack = (all_labels == 1).sum().float()
    total = n_normal + n_attack
    # Inverse frequency: kelas minoritas mendapat bobot lebih besar
    w_normal = total / (2.0 * n_normal)
    w_attack = total / (2.0 * n_attack)
    class_weights = torch.tensor([w_normal, w_attack]).to(device)
    print(f"[Train] Class weights: normal={w_normal:.3f}, attack={w_attack:.3f}")

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, betas=(0.9, 0.999))
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=1e-5)
    criterion = nn.CrossEntropyLoss(weight=class_weights)

    # ── Training loop ────────────────────────────────────────
    best_val_acc = 0.0
    start = time.time()

    print(f"\n{'Epoch':>6} {'Train Loss':>12} {'Train Acc':>10} {'Val Loss':>10} {'Val Acc':>10}")
    print("-" * 55)

    for epoch in range(1, args.epochs + 1):
        tr_loss, tr_acc = train_epoch(model, train_loader, optimizer, criterion, device)
        vl_loss, vl_acc = eval_epoch(model, val_loader, criterion, device)
        scheduler.step()

        marker = " ✓" if vl_acc > best_val_acc else ""
        print(f"{epoch:>6} {tr_loss:>12.4f} {tr_acc:>10.4f} {vl_loss:>10.4f} {vl_acc:>10.4f}{marker}")

        if vl_acc > best_val_acc:
            best_val_acc = vl_acc
            torch.save({
                "epoch":     epoch,
                "model_state_dict": model.state_dict(),
                "val_acc":   vl_acc,
                "num_steps": args.steps,
            }, args.output)
            # Save scaler stats as a separate JSON file
            if scaler_stats is not None:
                import json
                scaler_path = args.output.replace(".pt", "_scaler.json")
                with open(scaler_path, "w") as f:
                    json.dump(scaler_stats, f, indent=2)
                print(f"  Scaler saved to {scaler_path}")

    elapsed = time.time() - start
    print("-" * 55)
    print(f"\n✅ Training complete in {elapsed:.1f}s")
    print(f"   Best val accuracy : {best_val_acc:.4f} ({best_val_acc*100:.2f}%)")
    print(f"   Model saved to    : {args.output}")

    if best_val_acc >= 0.95:
        print("   🎉 Target accuracy >95% ACHIEVED!")
    else:
        print(f"   ⚠️  Target >95% not yet reached. Try --epochs {args.epochs + 50}")


if __name__ == "__main__":
    main()
