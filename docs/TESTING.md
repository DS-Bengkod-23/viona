# 🧪 Cara Menguji Project Viona

Sheet pengujian untuk arsitektur **Pipecat** (pasca-migrasi dari LiveKit Agents).
Urutan dari paling ringan (cek kode) → end-to-end (panggilan nyata).

Legenda: ✅ = expected result kalau sehat.

---

## 1. Cek kode tanpa menyalakan service (paling cepat)

| Uji | Command | ✅ Expected |
|---|---|---|
| Unit test migrasi | `cd backend && uv run pytest tests/test_pipecat_agent.py -v` | 6 passed (TTS LaTeX, RAG tool, handoff escalation, node tools) |
| Semua test | `cd backend && uv run pytest tests/ -q` | semua pass, tanpa error collection |
| Self-test pembersih LaTeX | `cd backend && uv run python app/core/text_cleaner.py` | `$\frac{1}{2}$`→"1 per 2"; `anak-anak` tetap utuh |
| Lint | `cd backend && uv run ruff check app/ main.py` | error hanya di file lama pra-migrasi (bukan file Pipecat) |
| Perakitan pipeline | `cd backend && uv run python -c "from app.agents import pipecat_worker as w; print(type(w._build_stt()).__name__, type(w._build_tts()).__name__)"` | `FasterWhisperSTTService VoxCPML2TTSService` |

---

## 2. Build & jalankan stack

| Uji | Command | ✅ Expected |
|---|---|---|
| Build image | `make build` | build sukses; Pipecat + deps ter-install |
| Nyalakan semua | `make up && make ps` | 7 service `Up`; `api` & `livekit-agent` healthy |
| Tail log agent | `docker compose logs -f livekit-agent` | `agent dispatch server ready` |

---

## 3. Health check

> **Penting:** di Docker, hanya **nginx** yang publish port ke host (`80`/`443`).
> Service `api` (8000) & `livekit-agent` (8081) **internal-only** di `viona-net` —
> jangan `curl localhost:8000/8081` dari host. Akses lewat nginx (`http://localhost/`)
> atau `docker compose exec` untuk endpoint internal.

| Service | Command | ✅ Expected |
|---|---|---|
| API health (via nginx) | `curl -f http://localhost/health` | `200`, JSON status ok |
| Token (via nginx) | `curl "http://localhost/api/token?room=test&identity=cust1"` | JSON berisi `token`, `room`, `livekit_url` (TANPA agent dispatch) |
| Agent health (internal) | `docker compose exec livekit-agent curl -sf http://localhost:8081/` | `{"status":"ok","service":"viona-agent"}` |
| Agent metrics (internal) | `docker compose exec livekit-agent curl -s http://localhost:8081/metrics` | output Prometheus (text) |
| Webhook routing (via nginx) | `curl -s -X POST http://localhost/webhooks/livekit -d '{}'` | `{"received":false}` (routing OK; signature ditolak tanpa header LiveKit) |

> Untuk dev lokal **tanpa Docker** (`uvicorn`/`python -m app.agents.server` langsung di host),
> barulah `localhost:8000` & `localhost:8081` berlaku.

---

## 4. Uji end-to-end panggilan

> **Prasyarat WAJIB:** set webhook LiveKit → POST ke `https://<host>/webhooks/livekit`
> (LiveKit Cloud dashboard / config self-host). Tanpa ini bot tidak pernah spawn.

| Uji | Langkah | ✅ Expected |
|---|---|---|
| Pantau spawn | `docker compose logs -f livekit-agent \| grep -E "caller joined\|spawning bot\|pipecat bot"` | muncul `caller joined → spawning bot` saat caller masuk |
| Panggilan dasar | Buka `http://localhost/` → mulai call → bicara Bahasa Indonesia | bot menyapa & menjawab; transkrip muncul di log |
| Fitur LaTeX (TTS) | Pancing jawaban berisi rumus (mis. "setengah tambah seperempat") | TTS membaca "satu per dua", BUKAN simbol `$`/`\frac` |
| RAG | Tanya hal yang ada di FAQ | jawaban memakai `search_faq` (cek log `rag`) |
| Escalation + SIP | Minta "sambungkan ke agen manusia" | log `escalating to human` → `sip transfer initiated` |
| Akhiri call | Tutup tab / hangup | log `participant left, ending` → `pipecat bot ended`; status sesi `ended` |

---

## 5. Toggle env mode uji ringan (CPU, tanpa GPU)

Taruh di `.env` untuk smoke test tanpa GPU (latensi/kualitas diabaikan):

```bash
VOXCPM2_DEVICE=cpu
WHISPER_MODEL_SIZE=small
WHISPER_COMPUTE_TYPE=int8
```

> Produksi: `VOXCPM2_DEVICE=cuda`, `WHISPER_MODEL_SIZE=large-v3`, `WHISPER_COMPUTE_TYPE=float16`
> (butuh GPU di container — Dockerfile saat ini `python:3.11-slim` CPU-only; perlu base CUDA + GPU reservation untuk produksi).

---

## 6. RAG / ingestion

| Uji | Command | ✅ Expected |
|---|---|---|
| Ingest FAQ | `make ingest FILE=docs/faq.pdf CATEGORY=faq` | chunk ter-upsert ke Qdrant tanpa error |
| Pull model LLM | `make pull-model MODEL=gemma4:31b-cloud` | model tersedia di Ollama |

---

## 7. Frontend

| Uji | Command | ✅ Expected |
|---|---|---|
| Dev server | `cd frontend && npm install && npm run dev` | UI call jalan di `:3000` |
| Build produksi | `npm run lint && npm run build` | lint clean, build sukses |

---

## 8. Troubleshooting cepat (grep log agent)

| Gejala | Cek | Kemungkinan sebab |
|---|---|---|
| Bot tak muncul | `grep "spawning bot"` kosong | webhook LiveKit belum diset / tak sampai ke `:8081` |
| Webhook ditolak | `grep "webhook verify failed"` | `LIVEKIT_API_KEY/SECRET` salah |
| STT diam | `grep "transcription done"` kosong | VAD / device Whisper / audio in bukan 16 kHz |
| TTS error | `grep "voxcpm synthesis failed"` | device/model VoxCPM2 (CUDA tak ada di image slim) |
| Handoff | `grep -E "escalating\|sip transfer"` | alur escalation |

---

## Catatan arsitektur (penting saat debug)

- **LiveKit server tetap dipakai** sebagai transport WebRTC + token + SIP. Yang dibuang hanya **LiveKit Agents** (orkestrasi) → diganti **Pipecat**.
- Service `livekit-agent` (container `viona-agent`, port 8081) kini berisi **server dispatch Pipecat** — nama service-nya legacy.
- Alur dispatch: caller join room → LiveKit webhook `participant_joined` → `/webhooks/livekit` → `run_bot_for_room()` spawn bot Pipecat ke room.
- ⚠️ Regresi diterima: **noise cancellation (Krisp)** & **turn-detector** hilang (turn-taking kini murni VAD).
