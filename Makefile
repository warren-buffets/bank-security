.PHONY: help up down

help:
	@echo "Commands: make up, make down, make logs"

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

ps:
	docker compose ps

migrate:
	docker compose exec -T postgres psql -U postgres -d antifraud -f /migrations/V001__init.sql

health:
	@docker compose exec -T postgres pg_isready -U postgres
	@docker compose exec -T redis redis-cli ping
