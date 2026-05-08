.PHONY: up down build logs ps shell-api shell-agent ingest pull-model

# ── Docker Compose shortcuts ───────────────────────────────────────────────────
up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build --no-cache

logs:
	docker compose logs -f --tail=100

ps:
	docker compose ps

# ── Shell access ───────────────────────────────────────────────────────────────
shell-api:
	docker compose exec api bash

shell-agent:
	docker compose exec livekit-agent bash

# ── Knowledge base ingestion ───────────────────────────────────────────────────
# Usage: make ingest FILE=path/to/doc.pdf [CATEGORY=faq]
ingest:
	docker compose exec api python -m scripts.ingest $(FILE) --category $(or $(CATEGORY),faq)

# ── Ollama model pull ──────────────────────────────────────────────────────────
# Usage: make pull-model MODEL=gpt-oss:120b-cloud
pull-model:
	docker compose exec ollama ollama pull $(or $(MODEL),gpt-oss:120b-cloud)
