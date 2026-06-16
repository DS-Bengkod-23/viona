.PHONY: up down build build-frontend rebuild-frontend logs ps shell-api shell-agent ingest pull-model pull-model-test pull-embedding

# ── Docker Compose shortcuts ───────────────────────────────────────────────────
up:
	docker compose up -d

down:
	docker compose down

# Build semua service (pakai cache jika tidak ada perubahan)
build:
	docker compose build

# Build semua service TANPA cache — paling lambat tapi paling bersih
build-no-cache:
	docker compose build --no-cache

# ── Frontend rebuild ───────────────────────────────────────────────────────────
# Rebuild frontend dengan invalidate cache paksa (gunakan ini jika frontend tidak update)
rebuild-frontend:
	docker compose build --build-arg CACHE_BUST=$$(date +%s) frontend

# Rebuild frontend lalu restart container-nya saja
redeploy-frontend:
	docker compose build --build-arg CACHE_BUST=$$(date +%s) frontend
	docker compose up -d --no-deps frontend

logs:
	docker compose logs -f --tail=100

# Log khusus per service
logs-agent:
	docker compose logs -f --tail=100 livekit-agent

logs-api:
	docker compose logs -f --tail=100 api

logs-frontend:
	docker compose logs -f --tail=100 frontend

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
# Pull model ringan untuk testing
pull-model-test:
	docker compose exec ollama ollama pull llama3.2:3b

# Pull model produksi (default: qwen3.5-cloud)
# Usage: make pull-model [MODEL=qwen3.5-cloud]
pull-model:
	docker compose exec ollama ollama pull $(or $(MODEL),qwen3.5-cloud)

# Pull embedding model (qwen3-embedding:0.6b)
pull-embedding:
	docker compose exec ollama ollama pull qwen3-embedding:0.6b

# Pull semua model yang dibutuhkan (LLM + embedding) sekaligus
pull-all:
	docker compose exec ollama ollama pull $(or $(MODEL),qwen3.5-cloud)
	docker compose exec ollama ollama pull qwen3-embedding:0.6b

# Lihat model Ollama yang sudah terinstall
list-models:
	docker compose exec ollama ollama list
