"""
SATSET — Brain Layer
snn_model.py

Arsitektur Spiking Neural Network (SNN) berbasis Leaky Integrate-and-Fire (LIF).
Dibangun dengan snnTorch di atas PyTorch.

Arsitektur V3 — "Shallow but Wide":
  Input (6 fitur) → FC1(128) → LIF → Dropout → FC2(2) → LIF → Output

Perubahan dari V1/V2:
  - 128 neuron hidden (vs 64 di V1, vs 64→32 di V2)
  - 2 layer saja (menghindari vanishing spike problem)
  - Dropout 0.3 untuk mencegah overfitting
  - Default 50 timesteps (vs 25)

Input features (6):
  [0] packet_rate          — jaringan, pkt/s (ternormalisasi)
  [1] packet_size          — jaringan, bytes (ternormalisasi)
  [2] interval             — jaringan, ms (ternormalisasi)
  [3] cache_misses         — HPC (ternormalisasi)
  [4] instructions_retired — HPC (ternormalisasi)
  [5] branch_misses        — HPC (ternormalisasi)

Output:
  threat_score → float [0, 1]  (spike rate neuron output "attack")
"""

import torch
import torch.nn as nn
import snntorch as snn
from snntorch import surrogate, spikegen


class SATSETBrain(nn.Module):
    """
    V3 — Shallow-but-Wide LIF-based SNN untuk deteksi serangan DDoS pada edge AIoT.

    Menggunakan fast sigmoid sebagai surrogate gradient function
    untuk pelatihan backpropagation melalui waktu (BPTT).
    """

    INPUT_SIZE  = 6
    HIDDEN_SIZE = 128
    OUTPUT_SIZE = 2   # 0: normal, 1: attack

    def __init__(self, beta: float = 0.9, threshold: float = 1.0, num_steps: int = 16):
        """
        Args:
            beta       : konstanta peluruhan membran (decay factor LIF)
            threshold  : ambang batas potensial membran untuk spike
            num_steps  : jumlah timestep simulasi SNN (default 16 untuk V3)
        """
        super().__init__()

        self.num_steps = num_steps
        spike_grad = surrogate.fast_sigmoid(slope=25)

        # ── Layer 1: Input → Hidden ───────────────────────
        self.fc1  = nn.Linear(self.INPUT_SIZE,  self.HIDDEN_SIZE)
        self.lif1 = snn.Leaky(
            beta=beta,
            threshold=threshold,
            spike_grad=spike_grad,
            learn_beta=True,
            learn_threshold=True,
        )
        self.drop1 = nn.Dropout(0.3)

        # ── Layer 2: Hidden → Output ─────────────────────
        self.fc2  = nn.Linear(self.HIDDEN_SIZE, self.OUTPUT_SIZE)
        self.lif2 = snn.Leaky(
            beta=beta,
            threshold=threshold,
            spike_grad=spike_grad,
            learn_beta=True,
            learn_threshold=True,
        )

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass melalui num_steps timestep.

        Args:
            x : input tensor shape [batch, INPUT_SIZE]

        Returns:
            spk_out  : spike tensor shape [num_steps, batch, OUTPUT_SIZE]
            mem_out  : membrane potential [num_steps, batch, OUTPUT_SIZE]
        """
        mem1 = self.lif1.init_leaky()
        mem2 = self.lif2.init_leaky()

        spk_out_list = []
        mem_out_list = []

        for _ in range(self.num_steps):
            # Rate coding: bangkitkan spike biner stokastik berdasarkan nilai input
            spk_in = (torch.rand_like(x) < x).float()
            
            cur1 = self.fc1(spk_in)
            spk1, mem1 = self.lif1(cur1, mem1)
            spk1 = self.drop1(spk1)

            cur2 = self.fc2(spk1)
            spk2, mem2 = self.lif2(cur2, mem2)

            spk_out_list.append(spk2)
            mem_out_list.append(mem2)

        spk_out = torch.stack(spk_out_list, dim=0)   # [T, B, 2]
        mem_out = torch.stack(mem_out_list, dim=0)   # [T, B, 2]

        return spk_out, mem_out

    def threat_score(self, x: torch.Tensor) -> float:
        """
        Convenience wrapper: kembalikan threat score tunggal [0, 1].

        Args:
            x : raw feature tensor shape [1, INPUT_SIZE] atau [INPUT_SIZE]

        Returns:
            score : float, 0 = aman, 1 = serangan penuh
        """
        self.eval()
        with torch.no_grad():
            if x.dim() == 1:
                x = x.unsqueeze(0)
            spk_out, _ = self.forward(x)
            spike_rate = spk_out[:, :, 1].sum(dim=0) / self.num_steps
            return float(spike_rate.squeeze().clamp(0.0, 1.0))

    def forward_stdp(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass khusus untuk STDP. Mengubah input float menjadi rate-coded binary spikes.
        x : [batch, INPUT_SIZE] (berisi float 0.0 - 1.0)
        Return:
          spk_in   [num_steps, batch, INPUT_SIZE]  - rate-coded input spikes
          spk1     [num_steps, batch, HIDDEN_SIZE] - hidden layer spikes
          spk_out  [num_steps, batch, OUTPUT_SIZE] - output layer spikes
        """
        mem1 = self.lif1.init_leaky()
        mem2 = self.lif2.init_leaky()

        spk_in_list = []
        spk1_list = []
        spk_out_list = []

        for _ in range(self.num_steps):
            # Rate coding: bangkitkan spike biner jika random() < nilai fitur x
            spk_in = (torch.rand_like(x) < x).float()
            
            cur1 = self.fc1(spk_in)
            spk1, mem1 = self.lif1(cur1, mem1)
            spk1 = self.drop1(spk1)

            cur2 = self.fc2(spk1)
            spk2, mem2 = self.lif2(cur2, mem2)

            spk_in_list.append(spk_in)
            spk1_list.append(spk1)
            spk_out_list.append(spk2)

        return torch.stack(spk_in_list, dim=0), torch.stack(spk1_list, dim=0), torch.stack(spk_out_list, dim=0)

    def extract_traces(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Mengembalikan pre_spikes dan post_spikes (biner) sebagai FULL SEQUENCE 
        [num_steps, features] untuk keperluan temporal update_traces di STDP.
        """
        self.eval()
        with torch.no_grad():
            if x.dim() == 1:
                x = x.unsqueeze(0)
            spk_in, spk1_out, spk2_out = self.forward_stdp(x)
            
            # pre_spikes represents the sequence of binary spikes fired by the input layer
            pre_spikes = spk_in.squeeze(1)  # [num_steps, INPUT_SIZE]
            
            # post_spikes represents the sequence of binary spikes fired by the hidden layer
            post_spikes = spk1_out.squeeze(1)  # [num_steps, HIDDEN_SIZE]
            
            return pre_spikes, post_spikes
def build_model(beta: float = 0.9, threshold: float = 1.0, num_steps: int = 16) -> "SATSETBrain":
    """Factory function untuk membangun model dengan konfigurasi default."""
    return SATSETBrain(beta=beta, threshold=threshold, num_steps=num_steps)

MAX_THRESHOLDS = torch.tensor([
    2000.0,
    1500.0,
    1.0,
    20000000.0,
    150000000.0,
    1000000.0
])

def encode_telemetry_to_spikes(raw_telemetry, num_steps=50):
    raw_tensor = torch.tensor(raw_telemetry, dtype=torch.float32)

    normalized_data = raw_tensor / MAX_THRESHOLDS
    normalized_data = torch.clamp(normalized_data, 0.0, 1.0)

    spike_train = spikegen.rate(normalized_data, num_steps=num_steps)

    return spike_train

if __name__ == "__main__":
    sample_attack_data = [1147.2, 120.0, 0.0008, 15593629.0, 89023577.0, 652881.0]

    spikes_input = encode_telemetry_to_spikes(sample_attack_data, num_steps=50)

    print(f"Dimensi Spike Input: {spikes_input.shape}")
