import torch
import torch.nn as nn

class STDPLearner:
    def __init__(self, model, learning_rate=0.005, A_plus=1.0, A_minus=0.8):
        self.model = model
        self.lr = learning_rate
        self.A_plus = A_plus
        self.A_minus = A_minus

    def update_weights(self, pre_spikes, post_spikes):
        with torch.no_grad():
            fc1_weight = self.model.weight

            pre_rate = pre_spikes.mean(dim=0).squeeze()
            post_rate = post_spikes.mean(dim=0).squeeze()

            delta_w = torch.ger(post_rate, pre_rate)

            delta_w = torch.where(delta_w > 0.1,
                                  self.A_plus * delta_w,
                                  -self.A_minus * (1.0 - delta_w))

            fc1_weight += self.lr * delta_w

            fc1_weight.clamp_(-1.5, 1.5)

        print(f"[STDPLearner] STDP Applied! Weight variance changed by: {delta_w.mean().item():.4f}")
        return True
