SHELL := /usr/bin/env bash
COMPOSE := docker compose

-include .env
export

LOG_DIRS := logs/client logs/captures

.PHONY: help init build up down stop restart ps verify baseline stop-baseline \
        trial logs shell clean reset

help: ## Show this help
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z_-]+:.*## / {printf "  %-14s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

init: ## Create runtime log directories
	@mkdir -p $(LOG_DIRS)

build: init ## Build the lab images
	$(COMPOSE) build

up: init ## Start the lab
	$(COMPOSE) up -d --build
	@$(COMPOSE) ps
	@printf '\nNext: make verify\n'

down: ## Stop the lab (keeps the database volume)
	$(COMPOSE) down

stop: ## Stop containers without removing them
	$(COMPOSE) stop

restart: down up ## Recreate everything

ps: ## Container status
	$(COMPOSE) ps

verify: ## Prove client -> firewall -> web, with a capture on the firewall
	@scripts/verify-path.sh

baseline: init ## Start benign traffic (TRIAL=..., DURATION=seconds)
	$(COMPOSE) exec -d client python3 -u /opt/traffic/legit_client.py \
		--label $(or $(TRIAL),baseline) \
		$(if $(DURATION),--duration $(DURATION),)
	@printf 'benign traffic running -> logs/client/legit.jsonl\n'

stop-baseline: ## Stop benign traffic
	-$(COMPOSE) exec -T client pkill -f legit_client.py

trial: ## Same as baseline, named for an experiment (TRIAL=t-000-baseline)
	@test -n "$(TRIAL)" || { echo 'usage: make trial TRIAL=t-000-baseline'; exit 1; }
	@$(MAKE) baseline TRIAL=$(TRIAL)

logs: ## Follow logs (F=firewall|web|db|client|attacker)
	$(COMPOSE) logs -f --tail=100 $(F)

shell: ## Shell in a container (S=firewall, default firewall)
	$(COMPOSE) exec $(or $(S),firewall) bash

clean: ## Remove containers, networks and the database volume
	$(COMPOSE) down -v
	rm -rf logs

reset: clean up ## Clean slate
