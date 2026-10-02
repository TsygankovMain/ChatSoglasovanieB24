.PHONY: dev-front dev-python prod-python test lint status ps down logs clean

# Development
dev-front:
	@echo "Starting frontend"
	COMPOSE_PROFILES=frontend,cloudpub docker compose -f docker-compose.dev.yml --env-file .env up --build

dev-python:
	@echo "Starting dev python"
	COMPOSE_PROFILES=frontend,python,cloudpub docker compose -f docker-compose.dev.yml --env-file .env up --build

# Production (three containers behind nginx; the single-image build is the root Dockerfile)
prod-python:
	@echo "Starting prod python environment"
	docker compose --env-file .env up --build -d

# Checks
test:
	cd backends/python/api && python -m unittest discover -s tests

lint:
	cd frontend && pnpm run lint

# Utils
status:
	docker stats

ps:
	watch -n 2 docker ps

down:
	docker compose down
	docker compose -f docker-compose.dev.yml down

logs:
	docker compose -f docker-compose.dev.yml logs -f

clean:
	docker compose -f docker-compose.dev.yml down -v
