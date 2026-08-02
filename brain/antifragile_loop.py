"""
SATSET — Brain Layer
antifragile_loop.py

Integrasi STDP dengan live inference feedback.

Subscribe ke MQTT topic:
  - satset/brain/threat        → inference results dari engine
  - satset/control/attack_mode → sinyal attack aktif/nonaktif

Ketika serangan TERKONFIRMASI (healing sudah dipicu oleh Hand):
  → Subscribe satset/hand/healed
  → Panggil STDP updater untuk perkuat bobot deteksi

Ini adalah siklus Antifragility: setiap serangan yang berhasil ditangani
membuat sistem lebih pintar untuk serangan berikutnya.
"""

import json
import os
import signal
import sys
import threading
import time
import uuid

import torch
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from snn_model import build_model
from stdp_learner import STDPLearner

load_dotenv()

MQTT_HOST   = os.getenv("MQTT_HOST",      "localhost")
MQTT_PORT   = int(os.getenv("MQTT_PORT",  1883))
MODEL_PATH  = os.getenv("SNN_MODEL_PATH", "model/snn_model.pt")

_running = True
_lock    = threading.Lock()

# Shared state
_heal_count = 0


class AntifragileLoop:
    """
    Menghubungkan:
      • STDP Learner (bobot update)
      • MQTT subscriber (event dari Brain dan Hand)
      • Checkpoint saver (simpan bobot yang diperbarui)
    """

    def __init__(self):
        # Load model
        device = torch.device("cpu")
        if os.path.exists(MODEL_PATH):
            checkpoint = torch.load(MODEL_PATH, map_location=device, weights_only=True)
            num_steps  = checkpoint.get("num_steps", 25)
            self.model = build_model(num_steps=num_steps)
            # self.model.load_state_dict(checkpoint["model_state_dict"])
            if "model_state_dict" in checkpoint:
                self.model.load_state_dict(checkpoint["model_state_dict"])
            else:
                self.model.load_state_dict(checkpoint)
            print(f"[AntifragileLoop] ✅ Model loaded: val_acc={checkpoint.get('val_acc', 0):.4f}")
        else:
            print(f"[AntifragileLoop] ⚠️  Model not found, using untrained weights")
            self.model = build_model()

        self.model.eval()
        self.stdp = STDPLearner(self.model.fc1)
        self._last_threat_score = 0.0
        self._attack_confirmed  = False

        # MQTT
        self._client = mqtt.Client(client_id=f"satset-antifragile-{uuid.uuid4().hex[:8]}")
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe("satset/brain/threat", qos=1)
            client.subscribe("satset/hand/healed",  qos=1)
            client.subscribe("satset/control/attack_mode", qos=0)
            print(f"[AntifragileLoop] MQTT connected to {MQTT_HOST}:{MQTT_PORT}")
        else:
            print(f"[AntifragileLoop] MQTT connect failed rc={rc}")

    def _on_message(self, client, userdata, msg):
        topic   = msg.topic
        payload = json.loads(msg.payload.decode())

        if topic == "satset/brain/threat":
            self._last_threat_score = payload.get("threat_score", 0.0)
            features = payload.get("features", None)

            # Store traces using actual inference features
            if self._last_threat_score > 0.5 and features is not None:
                x = torch.tensor(features, dtype=torch.float32)
                pre_spikes, post_spikes = self.model.extract_traces(x)
                
                with _lock:
                    self.stdp.update_weights(pre_spikes, post_spikes)

        elif topic == "satset/hand/healed":
            # Hand confirmed a real attack was healed → apply STDP
            self._attack_confirmed = True
            print(f"\n[AntifragileLoop] 🧠 STDP triggered by confirmed healing event!")
            with _lock:
                self.stdp.apply_stdp()
                self.stdp.reset_traces()
            self._save_updated_model()

        elif topic == "satset/control/attack_mode":
            active = payload.get("active", False)
            if active:
                print("[AntifragileLoop] ⚠️  Attack mode signal received — monitoring for confirmation")

    def _save_updated_model(self):
        """Simpan model setelah STDP update."""
        global _heal_count
        _heal_count += 1
        out_path = MODEL_PATH.replace(".pt", f"_antifragile_v{_heal_count}.pt")
        torch.save({
            "epoch":      f"antifragile-{_heal_count}",
            "model_state_dict": self.model.state_dict(),
            "stdp_updates":     self.stdp.total_updates,
        }, out_path)
        print(f"[AntifragileLoop] 💾 Updated model saved: {out_path}")

    def run(self):
        global _running
        try:
            self._client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            self._client.loop_start()
        except Exception as e:
            print(f"[AntifragileLoop] ⚠️  MQTT unavailable: {e}. Running in offline mode.")

        print("[AntifragileLoop] 🔄 Antifragile loop active. Waiting for events...\n")
        while _running:
            time.sleep(0.5)

        self._client.loop_stop()
        self._client.disconnect()
        print(f"[AntifragileLoop] Stopped. Total STDP updates: {self.stdp.total_updates}")


def main():
    global _running
    signal.signal(signal.SIGINT,  lambda s, f: globals().update(_running=False))
    signal.signal(signal.SIGTERM, lambda s, f: globals().update(_running=False))

    loop = AntifragileLoop()
    loop.run()


if __name__ == "__main__":
    main()
