# SATSET — One-Command Deploy
.PHONY: setup clean brain hand attack up down status logs help

PYTHON := python3
VENV := venv

# Warna
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m
BOLD := \033[1m

# Spinner frames
FRAMES := ⣾ ⣽ ⣻ ⢿ ⡿ ⣟ ⣯ ⣷

define spin
	@for i in {1..12}; do \
		for f in $(FRAMES); do \
			printf "\r  $$f  $1...     "; \
			sleep 0.08; \
		done \
	done
endef

define timer_start
	@START_TIME=$$(date +%s)
endef

define timer_end
	@END_TIME=$$(date +%s); \
	ELAPSED=$$((END_TIME - START_TIME)); \
	printf " (%ds)" $$ELAPSED
endef

setup:
	@echo ""
	@echo "$(BLUE)╔═══════════════════════════════════════════════════════════════════╗$(RESET)"
	@echo "$(BLUE)║                                                                   ║$(RESET)"
	@echo "$(BLUE)║   🚀  $(BOLD)SATSET$(RESET)$(BLUE) — Spiking-based Antifragile Twin                     ║$(RESET)"
	@echo "$(BLUE)║       for Self-healing Edge Technology                            ║$(RESET)"
	@echo "$(BLUE)║                                                                   ║$(RESET)"
	@echo "$(BLUE)╚═══════════════════════════════════════════════════════════════════╝$(RESET)"
	@echo ""
	@echo "$(YELLOW)📦  Setting up SATSET...$(RESET)"
	@echo ""

	@printf "  ⣾  Creating virtual environment...     "
	@$(eval START := $(shell date +%s))
	@$(PYTHON) -m venv $(VENV) 2>/dev/null
	@$(eval END := $(shell date +%s))
	@$(eval ELAPSED := $(shell echo $$(($(END) - $(START)))))
	@printf "\r  $(GREEN)✅$(RESET)  Creating virtual environment...     $(GREEN)DONE$(RESET) (%ds)\n" $(ELAPSED)
	@echo ""

	@printf "  ⣾  Installing PyTorch (CPU for ARM64)...     "
	@$(eval START := $(shell date +%s))
	@$(VENV)/bin/pip install --upgrade pip > /dev/null 2>&1
	@$(call spin,Installing PyTorch)
	@trap 'printf "\r  $(RED)❌$(RESET)  Installing PyTorch...     $(RED)INTERRUPTED$(RESET)\n"; exit 1' INT; \
	$(VENV)/bin/pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu > /dev/null 2>&1
	@$(eval END := $(shell date +%s))
	@$(eval ELAPSED := $(shell echo $$(($(END) - $(START)))))
	@printf "\r  $(GREEN)✅$(RESET)  Installing PyTorch (CPU for ARM64)...     $(GREEN)DONE$(RESET) (%ds)\n" $(ELAPSED)
	@echo ""

	@printf "  ⣾  Installing dependencies...     "
	@$(eval START := $(shell date +%s))
	@$(call spin,Installing dependencies)
	@trap 'printf "\r  $(RED)❌$(RESET)  Installing dependencies...     $(RED)INTERRUPTED$(RESET)\n"; exit 1' INT; \
	$(VENV)/bin/pip install -r requirements.txt > /dev/null 2>&1
	@$(eval END := $(shell date +%s))
	@$(eval ELAPSED := $(shell echo $$(($(END) - $(START)))))
	@printf "\r  $(GREEN)✅$(RESET)  Installing dependencies...     $(GREEN)DONE$(RESET) (%ds)\n" $(ELAPSED)
	@echo ""

	@printf "  ⣾  Running setup script...     "
	@$(eval START := $(shell date +%s))
	@$(call spin,Running setup)
	@trap 'printf "\r  $(RED)❌$(RESET)  Running setup script...     $(RED)INTERRUPTED$(RESET)\n"; exit 1' INT; \
	$(VENV)/bin/python setup.py > /dev/null 2>&1
	@$(eval END := $(shell date +%s))
	@$(eval ELAPSED := $(shell echo $$(($(END) - $(START)))))
	@printf "\r  $(GREEN)✅$(RESET)  Running setup script...     $(GREEN)DONE$(RESET) (%ds)\n" $(ELAPSED)
	@echo ""

	@echo ""
	@echo "$(GREEN)╔═══════════════════════════════════════════════════════════════════╗$(RESET)"
	@echo "$(GREEN)║                                                                   ║$(RESET)"
	@echo "$(GREEN)║   ✅  Setup Complete! 🎉                                          ║$(RESET)"
	@echo "$(GREEN)║                                                                   ║$(RESET)"
	@echo "$(GREEN)║   📊  Services:                                                   ║$(RESET)"
	@echo "$(GREEN)║      📡 MQTT Broker     → localhost:1883                         ║$(RESET)"
	@echo "$(GREEN)║      📦 InfluxDB        → http://localhost:8086                  ║$(RESET)"
	@echo "$(GREEN)║      📊 Grafana         → http://localhost:3000                  ║$(RESET)"
	@echo "$(GREEN)║                                                                   ║$(RESET)"
	@echo "$(GREEN)║   🚀  Next Steps:                                                ║$(RESET)"
	@echo "$(GREEN)║      make brain    → Start inference engine                      ║$(RESET)"
	@echo "$(GREEN)║      make hand     → Start self-healing trigger                  ║$(RESET)"
	@echo "$(GREEN)║      make attack   → Simulate attack                             ║$(RESET)"
	@echo "$(GREEN)║      make up       → Start Docker containers                     ║$(RESET)"
	@echo "$(GREEN)║      make down     → Stop Docker containers                      ║$(RESET)"
	@echo "$(GREEN)║      make status   → Show Docker status                          ║$(RESET)"
	@echo "$(GREEN)║      make help     → Show all commands                           ║$(RESET)"
	@echo "$(GREEN)║                                                                   ║$(RESET)"
	@echo "$(GREEN)╚═══════════════════════════════════════════════════════════════════╝$(RESET)"

brain:
	@echo "$(BLUE)[SATSET] Starting Inference Engine...$(RESET)"
	$(VENV)/bin/python brain/inference_engine.py

hand:
	@echo "$(BLUE)[SATSET] Starting Self-Healing Trigger...$(RESET)"
	$(VENV)/bin/python hand/heal_trigger.py

attack:
	@echo "$(BLUE)[SATSET] Starting Attack Simulator...$(RESET)"
	$(VENV)/bin/python senses/attack_simulator.py --rate 100 --duration 60

attack-hpc:
	@echo "$(BLUE)[SATSET] Starting HPC Attack...$(RESET)"
	$(VENV)/bin/python senses/attack_hpc.py --duration 30

attack-network:
	@echo "$(BLUE)[SATSET] Starting Network Attack...$(RESET)"
	$(VENV)/bin/python senses/attack_network.py --rate 1000 --duration 30

attack-portscan:
	@echo "$(BLUE)[SATSET] Starting Port Scan Attack...$(RESET)"
	$(VENV)/bin/python senses/attack_portscan.py --rate 500 --duration 30

up:
	@echo "$(BLUE)[SATSET] Starting Docker containers...$(RESET)"
	docker compose -f docker/docker-compose.yml up -d
	@echo "$(GREEN)✅ Containers started!$(RESET)"
	@echo "  📊 Grafana: http://localhost:3000"
	@echo "  📦 InfluxDB: http://localhost:8086"
	@echo "  📡 MQTT: localhost:1883"

down:
	@echo "$(BLUE)[SATSET] Stopping Docker containers...$(RESET)"
	docker compose -f docker/docker-compose.yml down

status:
	docker compose -f docker/docker-compose.yml ps

logs:
	docker compose -f docker/docker-compose.yml logs -f --tail=50

clean:
	@echo "$(RED)[SATSET] Cleaning up...$(RESET)"
	rm -rf $(VENV)
	rm -rf brain/model/*.pt
	rm -rf brain/model/*.pkl
	rm -rf data/
	@echo "$(GREEN)✅ Cleaned!$(RESET)"

help:
	@echo ""
	@echo "  $(BLUE)SATSET — Commands$(RESET)"
	@echo ""
	@echo "    $(GREEN)make setup$(RESET)     : Full setup (auto)"
	@echo "    $(GREEN)make up$(RESET)        : Start Docker containers"
	@echo "    $(GREEN)make down$(RESET)      : Stop Docker containers"
	@echo "    $(GREEN)make brain$(RESET)     : Run inference engine"
	@echo "    $(GREEN)make hand$(RESET)      : Run self-healing trigger"
	@echo "    $(GREEN)make attack$(RESET)    : Simulate MQTT Flood attack"
	@echo "    $(GREEN)make attack-hpc$(RESET)    : Simulate CPU attack"
	@echo "    $(GREEN)make attack-network$(RESET) : Simulate Network attack"
	@echo "    $(GREEN)make attack-portscan$(RESET): Simulate Port Scan"
	@echo "    $(GREEN)make status$(RESET)    : Show Docker status"
	@echo "    $(GREEN)make logs$(RESET)      : Show Docker logs"
	@echo "    $(GREEN)make clean$(RESET)     : Clean up all files"
	@echo "    $(GREEN)make help$(RESET)      : Show this help"
	@echo ""
