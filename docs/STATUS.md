# Status Project Viona — Snapshot Aktual

> Snapshot faktual dari mesin dev (repo + Docker runtime). Diperbarui: 2026-07-06.
> Sumber kebenaran untuk kondisi *saat ini*; untuk arsitektur konseptual lihat
> [`ARCHITECTURE.md`](./ARCHITECTURE.md), untuk QA lihat [`TESTING.md`](./TESTING.md).

## 1. Struktur direktori (tree singkat)

```
viona/
├── backend/
│   ├── app/
│   │   ├── agents/        # pipecat_worker.py, server.py (dispatch :8081), flows.py, tools.py
│   │   ├── api/
│   │   │   ├── routes/    # token, sessions, ingestion, chat, health
│   │   │   └── app.py     # FastAPI :8000 (VIONA_MODE=api)
│   │   ├── core/          # config.py (pydantic-settings), text_cleaner.py, logging.py
│   │   ├── domain/        # session.py (VionaSession)
│   │   ├── infrastructure/
│   │   │   ├── rag/       # retriever.py, ingestion.py, embeddings.py
│   │   │   ├── session/   # store.py (Redis)
│   │   │   ├── stt/       # faster_whisper_pipecat.py
│   │   │   ├── tts/       # voxcpml2_pipecat.py
│   │   │   └── metrics/   # prometheus.py
│   │   └── prompts/       # indonesian.py
│   ├── tests/             # test_text_cleaner.py, test_pipecat_agent.py
│   ├── pyproject.toml · uv.lock · main.py · scripts/start.sh
├── frontend/
│   └── src/
│       ├── app/           # page.tsx, demo/, admin/, layout.tsx, globals.css
│       ├── components/    # voice-assistant/ (VoiceAssistant, chat-message, math-text…),
│       │                  #   ui/ (radix), agents-ui/, popup/ (widget), + Transcript.tsx
│       ├── hooks/ · lib/  # lib/api.ts, lib/tts-text.ts (normalizeForSpeech)
├── docker/ (nginx conf, Dockerfiles) · docker-compose.yml · Makefile
└── docs/   # ARCHITECTURE.md, TESTING.md, STATUS.md · CLAUDE.md
```

## 2. Tech stack + versi

**Backend** (`pyproject.toml`, Python `>=3.11,<3.12`):
- `pipecat-ai[livekit,silero]>=1.4.0`, `pipecat-ai-flows>=1.3.0`, `livekit-api>=1.0.0`
- STT: `faster-whisper>=1.1.0` + `ctranslate2>=4.4.0`
- TTS: `voxcpm>=0.3.0` + `soundfile>=0.12.0`
- RAG: `pypdf>=5.1.0` (Qdrant & embeddings via **httpx REST**, sengaja tanpa
  `qdrant-client`/`fastembed` — tak stabil di ARM/Docker)
- `fastapi>=0.115`, `uvicorn[standard]>=0.32`, `redis[hiredis]>=5.2`,
  `pydantic>=2.10`, `structlog`, `prometheus-client`, `numpy<2.0`

**Frontend** (`package.json`) — ⚠️ **drift dari CLAUDE.md** (yang menyebut Next 14):
- **`next@16.2.6`**, **`react@19`**, `typescript@5.7.3`, `tailwindcss@4.2`
- `@livekit/components-react@2.9.21`, `livekit-client@2.19` (komponen LiveKit kini idle)
- **`katex@0.17`** + `@types/katex` (fitur LaTeX), Radix UI, `next-themes`, `lucide-react`
- `@vercel/analytics@1.6.1` masih ter-*install* tapi pemakaiannya sudah dicopot dari `layout.tsx`

## 3. Config aktual + status 3 open item

Dari `.env` (rahasia disensor):

| Var | Nilai sekarang | Catatan |
|-----|----------------|---------|
| `LIVEKIT_URL` | `wss://viona-40gxtvdc.livekit.cloud` | Cloud (transport-only) |
| `VOXCPM2_ENABLED` | **`false`** 🔴 | TTS VoxCPM2 dimatikan |
| `VOXCPM2_MODEL_NAME` | `suno/bark` | Berubah VoxCPM2 → Bark (perlu klarifikasi) |
| `VOXCPM2_DEVICE` | `cuda` | Belum difix (mesin no-GPU) |
| `WHISPER_*` | `large-v3` / `auto` / `float16` | Belum difix untuk CPU (float16 invalid di CPU) |
| `EMBEDDING_MODEL` | `bge-m3` | Berubah dari `qwen3-embedding:0.6b` |
| `OLLAMA_MODEL` | `gemma4:31b-cloud` | LLM cloud |
| `ENVIRONMENT` | `development` | `/docs` aktif |

**Status 3 open item:**
1. **Webhook LiveKit** → ❌ **belum ada progres.** Log agent: **0** bot spawn; hanya **1**
   webhook diterima seumur hidup (curl-tes yang gagal verifikasi). Bot Pipecat belum
   pernah hidup. Butuh konfigurasi webhook `participant_joined` → `/webhooks/livekit`
   (tunnel/URL publik untuk dev).
2. **Device config** → ⚠️ **sebagian ter-mitigasi.** `VOXCPM2_ENABLED=false`
   menyingkirkan risiko crash TTS-cuda, tapi Whisper masih `float16`+`large-v3`+`auto`
   di mesin tanpa GPU (`cuda: False` terkonfirmasi di container). Perlu `int8`+CPU
   atau target GPU.
3. **RAG re-ingest** → ❌ **belum.** Collection `viona_faq` **status green tapi 0 points**
   (kosong). Butuh PDF sumber + `/ingest/pdf` atau `make ingest`.

## 4. Running vs mati — Docker

**Semua 7 service UP & healthy:**

| Service | Port | Status | Fungsional |
|---------|------|--------|-----------|
| nginx | 80/443 (publik) | running | 🟢 |
| frontend | 3000 (internal) | healthy | 🟢 UI demo |
| api | 8000 (internal) | healthy | 🟢 `/chat`, token, ingest |
| livekit-agent | 8081 (internal) | healthy | 🔴 bot tak pernah spawn |
| ollama | 11434 | healthy | 🟢 LLM cloud + embedding |
| qdrant | 6333 | healthy | 🟡 hidup tapi 0 dok |
| redis | 6379 | healthy | 🟢 |

**"Mati" secara fungsional (walau container up):**
- 🔴 **Voice pipeline Pipecat** — tak pernah jalan (webhook belum dikonfigurasi).
- 🔴 **TTS VoxCPM2** — dimatikan via env.
- 🟡 **RAG** — teknis hidup tapi kosong.
- 🟢 **Jalur end-to-end yang hidup**: UI demo (`/`) via **Web Speech browser + `/chat`
  → Ollama cloud**, plus render **LaTeX (KaTeX)**. Jalur ini **tidak** menyentuh
  Pipecat/webhook/VoxCPM2. (Web Speech wajib **Chrome/Edge** — Brave/Firefox/Safari gagal.)

## 5. Catatan untuk planning

- Ada **dua jalur suara paralel**: (a) demo Web Speech (hidup, butuh Chrome),
  (b) pipeline Pipecat asli (mati, butuh webhook + GPU). Perlu keputusan fokus milestone.
- Perubahan `.env` (Bark, bge-m3, VoxCPM2 off) mengindikasikan arah TTS/embedding sedang
  digeser — perlu klarifikasi apakah final.
- Docs (CLAUDE.md) mulai **drift** dari kode (Next 14 vs 16). Perlu sinkronisasi.
