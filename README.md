# Viona — Indonesian Voice AI Customer Support

Viona adalah sistem layanan pelanggan berbasis suara yang dibangun di atas [LiveKit Agents](https://docs.livekit.io/agents/) dengan pipeline end-to-end yang sepenuhnya berjalan lokal (self-hosted). AI berbicara Bahasa Indonesia natural layaknya agen call center profesional.

---

## Fitur

- **Realtime voice** — latensi rendah via LiveKit WebRTC
- **STT lokal** — faster-whisper (large-v3) berjalan di GPU/CPU
- **LLM lokal** — Ollama (`gpt-oss:120b-cloud`) via OpenAI-compatible API
- **TTS** — Cartesia Sonic Multilingual (suara Indonesia)
- **VAD** — Silero VAD dengan StreamAdapter
- **RAG** — Qdrant + bge-m3 (fastembed) untuk knowledge base FAQ
- **Sesi** — Redis dengan TTL per sesi
- **Multi-agent** — CustomerSupportAgent → HumanEscalationAgent
- **Telephony** — Twilio SIP inbound/outbound
- **Web UI** — Next.js 14 dengan LiveKit React Components
- **Admin dashboard** — upload FAQ (PDF/teks), statistik sesi
- **Observability** — Prometheus metrics + structlog JSON

---

## Struktur Proyek

```
viona-api/
├── backend/                        # Python backend (clean architecture)
│   ├── app/
│   │   ├── core/                   # Config (pydantic-settings), logging (structlog)
│   │   ├── domain/                 # Entitas domain: CustomerSessionData, PersonaKey
│   │   ├── infrastructure/
│   │   │   ├── metrics/            # Prometheus counters, histograms, gauges
│   │   │   ├── rag/                # Embeddings (bge-m3), Qdrant retriever, PDF ingester
│   │   │   ├── session/            # Redis session store (async singleton)
│   │   │   └── stt/                # FasterWhisperSTT (LiveKit STT plugin)
│   │   ├── prompts/                # System prompts Bahasa Indonesia
│   │   ├── telephony/              # SIP transfer handler (Twilio)
│   │   ├── agents/
│   │   │   ├── support.py          # CustomerSupportAgent + BaseVionaAgent
│   │   │   ├── escalation.py       # HumanEscalationAgent
│   │   │   └── worker.py           # LiveKit worker entrypoint
│   │   └── api/
│   │       ├── app.py              # FastAPI app + lifespan
│   │       ├── deps.py             # FastAPI dependencies
│   │       └── routes/             # health, token, sessions, ingestion, webhooks
│   ├── scripts/
│   │   ├── ingest.py               # CLI bulk ingestion
│   │   └── start.sh                # Entrypoint (VIONA_MODE=api|agent)
│   ├── tests/
│   ├── docker/Dockerfile           # Single image, mode via VIONA_MODE env
│   └── pyproject.toml
│
├── frontend/                       # Next.js 14 frontend
│   ├── src/
│   │   ├── app/                    # page.tsx (voice call), admin/page.tsx
│   │   ├── components/             # VoiceAgent, Transcript, FAQUpload, StatsCard
│   │   └── lib/api.ts              # API client (token, session, ingest)
│   └── docker/Dockerfile
│
├── docker/
│   └── nginx/nginx.conf            # Reverse proxy (rate limiting, WebSocket)
├── docker-compose.yml              # 7 layanan: nginx, frontend, api, agent, ollama, qdrant, redis
├── Makefile                        # Shortcut commands
└── .env.example                    # Template environment variables
```

---

## Prasyarat

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose v2
- GPU NVIDIA (opsional, direkomendasikan untuk whisper & ollama)
- Akun [LiveKit Cloud](https://cloud.livekit.io) atau LiveKit self-hosted
- API key [Cartesia](https://cartesia.ai)

---

## Cara Menjalankan

### 1. Salin dan isi konfigurasi

```bash
cp .env.example .env
```

Edit `.env` dan isi nilai berikut:

```env
# Wajib
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIxxxxxxxx
LIVEKIT_API_SECRET=xxxxxxxx

CARTESIA_API_KEY=sk_xxxxxxxx

# Opsional (Twilio telephony)
TWILIO_ACCOUNT_SID=ACxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxx
TWILIO_SIP_TRUNK_SID=TKxxxxxxxx
```

### 2. Jalankan semua layanan

```bash
make up
# atau
docker compose up -d
```

### 3. Pull model Ollama

```bash
make pull-model
# atau
docker compose exec ollama ollama pull gpt-oss:120b-cloud
```

### 4. Ingest knowledge base (FAQ)

```bash
# Dari file PDF
make ingest FILE=docs/faq.pdf

# Dari file teks
make ingest FILE=docs/faq.txt CATEGORY=faq
```

### 5. Buka UI

| Layanan | URL |
|---|---|
| Web UI (voice call) | http://localhost |
| Admin dashboard | http://localhost/admin |
| API docs (dev) | http://localhost/docs |
| Prometheus metrics | http://localhost/metrics *(internal only)* |

---

## Perintah Makefile

```bash
make up            # Jalankan semua container
make down          # Hentikan semua container
make build         # Build ulang semua image
make logs          # Lihat log real-time
make ps            # Status container

make shell-api     # Shell ke container API
make shell-agent   # Shell ke container Agent

make ingest FILE=path/to/file.pdf [CATEGORY=faq]
make pull-model [MODEL=gpt-oss:120b-cloud]
```

---

## Variabel Environment

Lihat [backend/.env.example](backend/.env.example) untuk daftar lengkap. Variabel utama:

| Variabel | Default | Keterangan |
|---|---|---|
| `LIVEKIT_URL` | — | WebSocket URL LiveKit server |
| `LIVEKIT_API_KEY` | — | LiveKit API key |
| `LIVEKIT_API_SECRET` | — | LiveKit API secret |
| `CARTESIA_API_KEY` | — | Cartesia TTS API key |
| `CARTESIA_VOICE_ID` | `a167e0f3-...` | ID suara Indonesia Cartesia |
| `OLLAMA_MODEL` | `gpt-oss:120b-cloud` | Model LLM Ollama |
| `OLLAMA_BASE_URL` | `http://ollama:11434/v1` | URL Ollama (internal Docker) |
| `QDRANT_COLLECTION` | `viona_faq` | Nama koleksi Qdrant |
| `REDIS_SESSION_TTL` | `3600` | TTL sesi Redis (detik) |
| `WHISPER_MODEL_SIZE` | `large-v3` | Ukuran model faster-whisper |
| `WHISPER_DEVICE` | `auto` | `cuda` / `cpu` / `auto` |
| `ENVIRONMENT` | `production` | `production` menonaktifkan `/docs` |
| `LOG_LEVEL` | `INFO` | Level log (`DEBUG`, `INFO`, `WARNING`) |

---

## Arsitektur

```
Telepon / Browser
      │
      ▼
  [ Twilio ]          [ Next.js Frontend ]
      │ SIP                   │ WebRTC (LiveKit JS SDK)
      ▼                       ▼
  [ LiveKit Server (Cloud/Self-hosted) ]
              │
              ▼ JobContext
  ┌─────────────────────────────────────┐
  │         LiveKit Agent Worker        │
  │                                     │
  │  VAD (Silero) ──► STT (Whisper)    │
  │                        │            │
  │              LLM (Ollama) ◄── RAG  │
  │                (gpt-oss)    (Qdrant)│
  │                        │            │
  │              TTS (Cartesia)         │
  └─────────────────────────────────────┘
              │
              ▼
      [ Redis Session ]   [ Prometheus ]
```

**Flow multi-agent:**
1. `CustomerSupportAgent` menangani percakapan awal
2. Jika pelanggan perlu bantuan khusus → `escalate_to_human()` → transfer ke `HumanEscalationAgent`
3. `HumanEscalationAgent` melakukan SIP transfer ke agen manusia via Twilio

---

## Development

### Jalankan backend lokal (tanpa Docker)

```bash
cd backend
uv sync
cp .env.example .env  # isi variabel

# API server
VIONA_MODE=api uv run uvicorn app.api.app:application --reload

# Agent worker (butuh LiveKit + Redis + Qdrant berjalan)
VIONA_MODE=agent uv run python -m app.agents.worker start
```

### Jalankan frontend lokal

```bash
cd frontend
npm install
cp .env.local.example .env.local  # isi NEXT_PUBLIC_API_URL
npm run dev
```

### Jalankan tests

```bash
cd backend
uv run pytest tests/ -v
```

---

## Lisensi

MIT
