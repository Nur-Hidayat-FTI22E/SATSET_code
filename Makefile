# ══════════════════════════════════════════════════════════════
#  SATSET — Makefile
#  Shortcut commands untuk menjalankan semua komponen sistem.
#
#  Usage:
#    make up       → Start all infrastructure (Docker Compose)
#    make down     → Stop all infrastructure
#    make senses   → Run cross-layer telemetry agent
#    make brain    → Run SNN inference engine
#    make hand     → Run self-healing trigger
#    make antifrag → Run antifragile STDP loop
#    make attack   → Run DDoS attack simulator
#    make train    → Train SNN model (synthetic data)
#    make train-iot23 DATA=path/to/iot23.csv
#    make install  → Install all Python dependencies
#    make status   → Show running services
#    make logs     → Tail all Docker logs
#    make clean    → Remove data volumes
# ══════════════════════════════════════════════════════════════

.PHONY: up down senses brain hand antifrag attack train train-iot23 \
        install install-senses install-brain status logs clean help

SHELL := /bin/bash
.DEFAULT_GOAL := help

# ── Dynamic Python Environment ────────────────────────────────
# Automatically detect and use Virtual Environment if it exists.
# This prevents ModuleNotFoundError even if the venv is not activated.
VENV_PY     := $(CURDIR)/venv/bin/python3
DOT_VENV_PY := $(CURDIR)/.venv/bin/python3
ENV_PY      := $(CURDIR)/env/bin/python3
PYTHON      := $(shell if [ -f "$(VENV_PY)" ]; then echo "$(VENV_PY)"; elif [ -f "$(DOT_VENV_PY)" ]; then echo "$(DOT_VENV_PY)"; elif [ -f "$(ENV_PY)" ]; then echo "$(ENV_PY)"; else echo "python3"; fi)

# ── Colors ────────────────────────────────────────────────────
CYAN  := \033[36m
GREEN := \033[32m
RESET := \033[0m

# ── Phase 1: Infrastructure ───────────────────────────────────

up:
	@echo -e "$(CYAN)[SATSET] Starting infrastructure...$(RESET)"
	docker compose up -d
	@echo -e "$(GREEN)"
	@echo "  ✅ Services starting..."
	@echo "  📊 Grafana        → http://localhost:3000"
	@echo "  📦 InfluxDB       → http://localhost:8086"
	@echo "  📡 MQTT Broker    → localhost:1883"
	@echo -e "$(RESET)"
	@echo "  Wait ~10s for health checks, then run: make status"

down:
	@echo -e "$(CYAN)[SATSET] Stopping infrastructure...$(RESET)"
	docker compose down

status:
	@echo -e "$(CYAN)[SATSET] Service status:$(RESET)"
	docker compose ps

logs:
	docker compose logs -f --tail=50

# ── Phase 2: Senses (Telemetry) ───────────────────────────────

senses:
	@echo -e "$(CYAN)[SATSET] Starting Telemetry Agent...$(RESET)"
	cd senses && $(PYTHON) telemetry_agent.py

senses-attack:
	@echo -e "$(CYAN)[SATSET] Starting Telemetry Agent in ATTACK mode...$(RESET)"
	cd senses && $(PYTHON) telemetry_agent.py --attack

attack:
	@echo -e "$(CYAN)[SATSET] Starting DDoS Attack Simulator (Throttled)...$(RESET)"
	cd senses && $(PYTHON) attack_simulator.py --rate 100 --duration 60

attack-fast:
	@echo -e "$(CYAN)[SATSET] Starting DDoS Attack Simulator (high rate)...$(RESET)"
	cd senses && $(PYTHON) attack_simulator.py --rate 500 --duration 30

attack-network:
	@echo -e "$(CYAN)[SATSET] Starting Network Attack...$(RESET)"
	cd senses && $(PYTHON) attack_network.py --rate 1000 --duration 30

attack-hpc:
	@echo -e "$(CYAN)[SATSET] Starting HPC Attack...$(RESET)"
	cd senses && $(PYTHON) attack_hpc.py --duration 30

attack-portscan:
	@echo -e "$(CYAN)[SATSET] Starting Port Scan Attack...$(RESET)"
	cd senses && $(PYTHON) attack_portscan.py --rate 500 --duration 30
# ── Phase 3: Brain (SNN) ──────────────────────────────────────

train:
	@echo -e "$(CYAN)[SATSET] Training SNN model (synthetic data)...$(RESET)"
	cd brain && $(PYTHON) train.py --synthetic --epochs 50

train-iot23:
	@echo -e "$(CYAN)[SATSET] Training SNN model (IoT-23 dataset)...$(RESET)"
	@if [ -z "$(DATA)" ]; then \
		echo "Usage: make train-iot23 DATA=path/to/iot23.csv"; \
		exit 1; \
	fi
	cd brain && $(PYTHON) train.py --data $(DATA) --epochs 100

brain:
	@echo -e "$(CYAN)[SATSET] Starting SNN Inference Engine...$(RESET)"
	cd brain && $(PYTHON) inference_engine.py

antifrag:
	@echo -e "$(CYAN)[SATSET] Starting Antifragile STDP Loop...$(RESET)"
	cd brain && $(PYTHON) antifragile_loop.py

# ── Phase 4: Hand (Self-Healing) ──────────────────────────────

hand:
	@echo -e "$(CYAN)[SATSET] Starting Self-Healing Trigger...$(RESET)"
	cd hand && $(PYTHON) heal_trigger.py

hand-dry:
	@echo -e "$(CYAN)[SATSET] Starting Self-Healing Trigger (dry-run)...$(RESET)"
	cd hand && $(PYTHON) heal_trigger.py --dry-run

eda:
	@echo -e "$(CYAN)[SATSET] Starting EDA Ansible Rulebook...$(RESET)"
	cd hand/ansible && ansible-rulebook \
		--rulebook rulebooks/satset_rulebook.yml \
		-i inventory.yml \
		--verbose

# ── Install dependencies ──────────────────────────────────────

install: install-senses install-brain
	@echo -e "$(GREEN)✅ All dependencies installed!$(RESET)"

install-senses:
	@echo -e "$(CYAN)[SATSET] Installing senses dependencies...$(RESET)"
	$(PYTHON) -m pip install -r senses/requirements.txt

install-brain:
	@echo -e "$(CYAN)[SATSET] Installing brain dependencies...$(RESET)"
	$(PYTHON) -m pip install -r brain/requirements.txt

# ── Full Pipeline (all in background, requires tmux) ─────────

run-all:
	@echo -e "$(CYAN)[SATSET] Starting full pipeline...$(RESET)"
	@echo "Starting in background. Use 'make logs' / 'make status' to monitor."
	$(MAKE) up
	@sleep 15
	$(PYTHON) senses/telemetry_agent.py &
	$(PYTHON) brain/inference_engine.py &
	$(PYTHON) brain/antifragile_loop.py &
	$(PYTHON) hand/heal_trigger.py &
	@echo -e "$(GREEN)✅ Full SATSET pipeline running!$(RESET)"

# ── Cleanup ───────────────────────────────────────────────────

clean:
	@echo -e "$(CYAN)[SATSET] Removing Docker volumes...$(RESET)"
	docker compose down -v
	@echo "Cleaned."

clean-models:
	rm -rf brain/model/
	@echo "Models cleaned."

# ── Help ──────────────────────────────────────────────────────

help:
	@echo ""
	@echo -e "$(CYAN)  SATSET — Spiking-based Antifragile Twin for Self-healing Edge Technology$(RESET)"
	@echo ""
	@echo "  Infrastructure:"
	@echo "    make up          Start Docker services (Mosquitto, InfluxDB, Grafana)"
	@echo "    make down        Stop Docker services"
	@echo "    make status      Show service status"
	@echo "    make logs        Tail Docker logs"
	@echo ""
	@echo "  Senses (Phase 2):"
	@echo "    make senses      Start telemetry agent"
	@echo "    make attack      Simulate DDoS attack"
	@echo ""
	@echo "  Brain (Phase 3):"
	@echo "    make train       Train SNN (synthetic data)"
	@echo "    make brain       Start inference engine"
	@echo "    make antifrag    Start antifragile STDP loop"
	@echo ""
	@echo "  Hand (Phase 4):"
	@echo "    make hand        Start self-healing trigger"
	@echo "    make hand-dry    Same but dry-run (no actual restarts)"
	@echo "    make eda         Start EDA Ansible rulebook"
	@echo ""
	@echo "  Setup:"
	@echo "    make install     Install all Python deps"
	@echo "    make clean       Remove Docker volumes"
	@echo ""
