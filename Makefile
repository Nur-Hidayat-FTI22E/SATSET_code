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

setup:
	@echo ""
	@echo "$(BLUE)╔═══════════════════════════════════════════════════════════════════╗$(RESET)"
	@echo "$(BLUE)║                                                                   ║$(RESET)"
	@echo "$(BLUE)║   🚀  SATSET — Spiking-based Antifragile Twin                    ║$(RESET)"
	@echo "$(BLUE)║       for Self-healing Edge Technology                            ║$(RESET)"
	@echo "$(BLUE)║                                                                   ║$(RESET)"
	@echo "$(BLUE)╚═══════════════════════════════════════════════════════════════════╝$(RESET)"
	@echo ""
	@echo "$(YELLOW)📦  Setting up SATSET...$(RESET)"
	@echo ""
	@$(VENV)/bin/python setup.py

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
