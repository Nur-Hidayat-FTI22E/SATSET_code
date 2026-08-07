"""
SATSET — Brain Layer
stdp_learner.py

Plastisitas sinaptik berbasis jejak spike untuk memperkuat bobot deteksi
(layer fc1) setiap kali sebuah serangan berhasil ditangani oleh Hand.

Semantik dua-fase (selaras dengan alur MQTT di antifragile_loop.py):
  1. update_weights(pre, post)  → dipanggil berkali-kali selama serangan
                                    berlangsung; DELTA bobot diakumulasi,
                                    belum diterapkan ke model.
  2. apply_stdp()               → dipanggil sekali saat event 'healed'
                                    terkonfirmasi; rata-rata delta yang
                                    terakumulasi diterapkan ke bobot fc1.
  3. reset_traces()             → mengosongkan akumulator untuk siklus baru.

Catatan ilmiah: aturan di bawah adalah plastisitas Hebbian berbasis LAJU
(rate-based), bukan STDP temporal murni. Penyempurnaan ke jejak temporal
(Δt pre-vs-post) direncanakan pada tahap berikutnya.
"""

import torch


class STDPLearner:
    def __init__(self, model, learning_rate: float = 0.005,
                 A_plus: float = 1.0, A_minus: float = 0.8):
        self.model = model            # nn.Linear (fc1) yang bobotnya diperkuat
        self.lr = learning_rate
        self.A_plus = A_plus
        self.A_minus = A_minus

        # ── State akumulator & penghitung ────────────────────
        self._pending = None          # akumulasi delta_w antar update
        self._pending_count = 0       # jumlah sampel yang terakumulasi
        self.total_updates = 0        # jumlah apply_stdp() yang berhasil

    # ------------------------------------------------------------------
    def update_weights(self, pre_spikes: torch.Tensor, post_spikes: torch.Tensor) -> bool:
        """
        Akumulasi delta bobot Hebbian dari jejak spike.

        Args:
            pre_spikes  : [num_steps, INPUT_SIZE]  spike input (biner)
            post_spikes : [num_steps, HIDDEN_SIZE] spike hidden (biner)
        """
        with torch.no_grad():
            pre_rate = pre_spikes.mean(dim=0).squeeze()    # [INPUT_SIZE]
            post_rate = post_spikes.mean(dim=0).squeeze()  # [HIDDEN_SIZE]

            # outer product → [HIDDEN_SIZE, INPUT_SIZE] (sesuai shape fc1.weight)
            delta_w = torch.ger(post_rate, pre_rate)

            # Potensiasi bila ko-aktivasi kuat, depresiasi bila lemah
            delta_w = torch.where(
                delta_w > 0.1,
                self.A_plus * delta_w,
                -self.A_minus * (1.0 - delta_w),
            )

        if self._pending is None:
            self._pending = delta_w.clone()
        else:
            self._pending += delta_w
        self._pending_count += 1
        return True

    # ------------------------------------------------------------------
    def apply_stdp(self) -> bool:
        """
        Terapkan rata-rata delta yang terakumulasi ke bobot fc1.
        Dipanggil saat serangan terkonfirmasi telah ditangani.
        """
        if self._pending is None or self._pending_count == 0:
            print("[STDPLearner] apply_stdp() dipanggil tanpa jejak terakumulasi — dilewati.")
            return False

        with torch.no_grad():
            avg_delta = self._pending / self._pending_count
            self.model.weight += self.lr * avg_delta
            self.model.weight.clamp_(-1.5, 1.5)

        self.total_updates += 1
        print(f"[STDPLearner] STDP diterapkan atas {self._pending_count} sampel "
              f"(update #{self.total_updates}, rata-rata Δw = {avg_delta.mean().item():+.5f})")
        return True

    # ------------------------------------------------------------------
    def reset_traces(self) -> None:
        """Kosongkan akumulator untuk memulai siklus antifragile berikutnya."""
        self._pending = None
        self._pending_count = 0
