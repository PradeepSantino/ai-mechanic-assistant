.PHONY: setup up down logs status test

setup:
	@test -f .env || cp .env.example .env
	@echo "Edit .env and set OPENAI_API_KEY, then run: make up"

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f app

status:
	docker compose ps

test:
	@curl --fail --silent --show-error http://127.0.0.1:$${APP_PORT:-7860}/ >/dev/null
	@echo "AI Mechanic Assistant demo is responding"
