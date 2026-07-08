# Arsitektur Sistem Viona

Peta komponen & jalur data Viona — sistem voice AI customer support berbahasa Indonesia.
LiveKit dipakai **transport-only** (WebRTC + token + SIP); orkestrasi suara pakai **Pipecat**.

Dokumen ini adalah **spesifikasi arsitektur dalam bentuk instruksi teks** (daftar node +
koneksi berarah). Baca langsung, atau feed ke tool diagram/AI untuk digambar.

---

## 1. Node (komponen)

### Eksternal
| ID     | Label                | Peran |
|--------|----------------------|-------|
| Caller | Caller               | Browser WebRTC atau telepon (SIP) |
| LK     | LiveKit Cloud        | WebRTC SFU · token · SIP gateway — `viona-*.livekit.cloud` |
| Twilio | Twilio               | SIP trunk untuk eskalasi ke agen manusia |

### Docker Compose (7 service, 1 host)
| ID     | Label · port                | Publik | Peran |
|--------|-----------------------------|--------|-------|
| NGINX  | nginx · 80/443              | ✅     | Satu-satunya pintu masuk; reverse proxy + rate limit |
| FRONT  | frontend · 3000             | ❌     | Next.js 14 — VoiceAgent UI + admin dashboard |
| API    | api · 8000                  | ❌     | FastAPI (`VIONA_MODE=api`) — token, sessions, ingest, telephony, health |
| AGENT  | livekit-agent · 8081        | ❌     | FastAPI (`VIONA_MODE=agent`) — dispatch webhook, host bot Pipecat |
| BOT    | Pipecat bot                 | ❌     | Per-call, **in-process di dalam AGENT** (bukan container terpisah) |
| OLLAMA | ollama · 11434              | ❌     | LLM (cloud routing) + embedding lokal `qwen3-embedding` |
| QDRANT | qdrant · 6333               | ❌     | Vektor RAG — collection `viona_faq` |
| REDIS  | redis · 6379                | ❌     | Session store (TTL 3600s) |

### Voice pipeline (di dalam BOT)
`VAD (Silero) → STT (FasterWhisper large-v3) → LLM (Ollama) → TTS (VoxCPM2 + text_cleaner)`,
dengan cabang `LLM → RAG search → QDRANT/OLLAMA`.

---

## 2. Koneksi (edge berarah)

Format: `SUMBER → TUJUAN : label`.

### Trafik masuk (via nginx)
- `Caller → NGINX` : HTTPS / WSS
- `NGINX → FRONT` : path `/`
- `NGINX → API` : path `/api`, `/sessions`, `/telephony`
- `NGINX → AGENT` : path `/webhooks/livekit`

### Media & dispatch
- `Caller ↔ LK` : audio WebRTC / SIP (dua arah)
- `Twilio ↔ LK` : SIP (dua arah)
- `FRONT ⇢ API` : minta join token
- `API ⇢ LK` : issue LiveKit join token
- `LK → AGENT` : webhook `participant_joined` (ditandatangani, diverifikasi di AGENT)
- `AGENT → BOT` : `run_bot_for_room()` spawn bot
- `BOT ↔ LK` : bot join room (identity `viona-bot`), audio in/out
- `AGENT → Twilio` : SIP transfer saat eskalasi ke manusia

### Dependensi data
- `BOT → REDIS` : tulis transcript / state sesi
- `API → REDIS` : baca/tulis sesi
- `API → QDRANT` : ingest FAQ
- `RAG → QDRANT` : cari vektor
- `RAG → OLLAMA` : hitung embedding query
- `LLM → OLLAMA` : inferensi (model cloud via routing)

---

## 3. Alur satu panggilan (urut)

1. Caller buka UI (`NGINX /` → `FRONT`).
2. Caller `POST /api/token` (`NGINX` → `API`); `API` mint token via `LK`, balikkan ke caller.
3. Caller connect ke `LK` (WSS + audio).
4. `LK` kirim webhook `participant_joined` → `NGINX /webhooks/livekit` → `AGENT`.
5. `AGENT` verifikasi tanda tangan, panggil `run_bot_for_room()` → `BOT` join room.
6. **Loop tiap giliran bicara:** audio caller → VAD → STT → LLM (+RAG) → TTS (teks dibersihkan) → audio balik ke caller.
7. Bila perlu eskalasi: transisi ke node `escalation` → SIP transfer via `Twilio`.

---

## 4. Pengelompokan layer (untuk tata letak diagram)

- **Kolom kiri — Eksternal:** Caller, LiveKit Cloud, Twilio.
- **Kolom tengah — Edge/Presentation:** nginx, frontend.
- **Kolom tengah — Backend:** api, livekit-agent (berisi Pipecat bot + voice pipeline).
- **Kolom kanan — Data & Model:** ollama, qdrant, redis.
- Arah aliran umum: **kiri → kanan** (caller masuk kiri, data store di kanan).

---

## 5. Catatan operasional

- **Precondition webhook:** LiveKit Cloud wajib dikonfigurasi mengirim `participant_joined`
  ke `https://<host>/webhooks/livekit`. Tanpa ini `BOT` tidak pernah spawn → tidak ada
  panggilan yang bisa divalidasi end-to-end. Untuk dev: pakai tunnel (cloudflared/ngrok)
  → `http://localhost:80` (nginx).
- **nginx & rebuild:** upstream di-resolve saat startup. Jika container di-recreate,
  jalankan `docker compose restart nginx` (kalau tidak → 502).
- **LLM = cloud, embedding = lokal:** jangan pull model LLM besar ke lokal; hanya
  embedding, STT, dan TTS yang jalan lokal.
