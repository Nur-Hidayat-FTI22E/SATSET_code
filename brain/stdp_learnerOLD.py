"""
SATSET — Brain Layer
stdp_learner.py

Implementasi Spike-Timing Dependent Plasticity (STDP) untuk
pembelajaran online antifragile.

STDP Rule:
  - Jika pre-synaptic spike MENDAHULUI post-synaptic spike (Δt < 0):
      → Potentiation (perkuat sinapsis): ΔW = +A_plus * exp(Δt / τ_plus)
  - Jika post-synaptic spike MENDAHULUI pre-synaptic spike (Δt > 0):
      → Depression (lemahkan sinapsis): ΔW = -A_minus * exp(-Δt / τ_minus)

Digunakan saat:
  - Serangan baru terkonfirmasi oleh Hand (healing terpicu)
  - Update bobot FC1 berdasarkan spike trace dari inference terakhir
"""

import torch
import torch.nn as nn


class STDPLearner:
    """
    Online STDP weight updater untuk layer FC1 dari SATSETBrain.

    Tidak mengganti backpropagation — ini adalah komplemen biologis
    yang dijalankan SETELAH backprop selesai, ketika serangan baru
    terkonfirmasi (antifragile feedback loop).
    """

    def __init__(
        self,
        fc_layer: nn.Linear,
        a_plus:   float = 0.02,    # LTP learning rate (diperbesar agar dominan)
        a_minus:  float = 0.012,   # LTD learning rate (diperlemah relatif thd LTP)
        tau_plus: float = 20.0,    # LTP time constant (ms)
        tau_minus: float = 20.0,   # LTD time constant (ms)
        w_min:    float = -1.0,
        w_max:    float = 1.0,
    ):
        self.layer   = fc_layer
        self.a_plus  = a_plus
        self.a_minus = a_minus
        self.tau_plus  = tau_plus
        self.tau_minus = tau_minus
        self.w_min = w_min
        self.w_max = w_max

        # Spike traces (eligibility traces)
        self._pre_trace  = torch.zeros(fc_layer.in_features)
        self._post_trace = torch.zeros(fc_layer.out_features)
        
        # Accumulated weight changes
        self._dw_plus_acc  = torch.zeros_like(fc_layer.weight)
        self._dw_minus_acc = torch.zeros_like(fc_layer.weight)
        self._update_count = 0

    def update_traces(self, pre_spikes_seq: torch.Tensor, post_spikes_seq: torch.Tensor, dt: float = 1.0):
        """
        Update exponentially decaying spike traces dan akumulasi perubahan bobot 
        secara temporal (asymmetric STDP).

        Args:
            pre_spikes_seq  : sequence spike dari input  [num_steps, in_features]
            post_spikes_seq : sequence spike dari output [num_steps, out_features]
            dt              : timestep dalam ms
        """
        decay_pre  = torch.exp(torch.tensor(-dt / self.tau_plus))
        decay_post = torch.exp(torch.tensor(-dt / self.tau_minus))

        for t in range(pre_spikes_seq.size(0)):
            pre_f  = pre_spikes_seq[t].float()
            post_f = post_spikes_seq[t].float()

            # 1. Asymmetric STDP Accumulation
            # Potentiation (LTP): pre mendahului post
            # Δw+ = A+ * pre_trace * post_spike
            self._dw_plus_acc += self.a_plus * torch.outer(post_f, self._pre_trace)

            # Depression (LTD): post mendahului pre
            # Δw- = A- * post_trace * pre_spike
            self._dw_minus_acc += self.a_minus * torch.outer(self._post_trace, pre_f)

            # 2. Add new spikes to traces and decay
            self._pre_trace  = self._pre_trace  * decay_pre  + pre_f
            self._post_trace = self._post_trace * decay_post + post_f

    def apply_stdp(self):
        """
        Aplikasikan accumulated weight changes ke layer.
        Dipanggil saat serangan terkonfirmasi (feedback dari Hand).
        """
        with torch.no_grad():
            # Net weight change
            dw = self._dw_plus_acc - self._dw_minus_acc

            # Apply and clamp
            self.layer.weight.data += dw
            self.layer.weight.data.clamp_(self.w_min, self.w_max)

            self._update_count += 1

        print(f"[STDP] Applied update #{self._update_count} | "
              f"ΔW mean={dw.abs().mean().item():.6f} | "
              f"W range=[{self.layer.weight.data.min().item():.3f}, "
              f"{self.layer.weight.data.max().item():.3f}]")

    def reset_traces(self):
        """Reset eligibility traces and accumulators."""
        self._pre_trace  = torch.zeros(self.layer.in_features)
        self._post_trace = torch.zeros(self.layer.out_features)
        self._dw_plus_acc.zero_()
        self._dw_minus_acc.zero_()

    @property
    def total_updates(self) -> int:
        return self._update_count
