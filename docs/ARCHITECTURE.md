# Arsitektur Sistem Viona

Peta komponen & jalur data Viona — **AI learning companion suara berbahasa Indonesia**
untuk LMS (LMS demo: "Bengkel Koding"). Viona muncul sebagai **popup widget** yang
di-embed di halaman LMS: siswa bertanya (suara/teks), Viona menjawab **hanya tentang
materi di layar** (konteks di-*inject* ke prompt, bukan RAG).

LiveKit dipakai **transport-only** (WebRTC + token + webhook); orkestrasi suara pakai
**Pipecat**. Dokumen ini spesifikasi arsitektur dalam bentuk teks (node + edge berarah).

> **Pivot:** dulu agen telepon customer-service; sekarang LMS companion. Twilio/SIP,
> eskalasi-ke-manusia, dan komplain **sudah dihapus**. RAG **di-park** (Qdrant opsional).

---

## 0. Dua jalur suara (penting)

Ada **dua implementasi paralel** — ketahui mana yang disentuh:

1. **Native path (yang dipakai popup live sekarang).** STT + TTS jalan **di browser** via
   Web Speech API (`webkitSpeechRecognition` + `SpeechSynthesis`); jawaban dari
   **`POST /chat`** → Ollama dengan `lms_context`. Hook `useNativeVoiceConnection.ts`.
   **Wajib Chrome/Edge.** Tidak menyentuh LiveKit/Pipecat/Whisper/Cartesia.
2. **LiveKit/Pipecat path (pipeline server "real").** Bot Pipecat join room LiveKit dan
   jalankan `transport → VAD → STT → LLM → TTS`. Hook `useLiveKitConnection.ts`. Gated pada
   bot benar-benar di-spawn (lihat §3).

Keduanya berbagi **otak yang sama**: Ollama LLM + injeksi `lms_context`.

---

## 1. Node (komponen)

### Eksternal
| ID   | Label          | Peran |
|------|----------------|-------|
| USER | Siswa (browser)| Chrome/Edge — buka LMS, pakai popup Viona |
| LK   | LiveKit Cloud  | WebRTC SFU · token · sumber webhook — `viona-*.livekit.cloud` (hanya jalur LiveKit) |
| CART | Cartesia       | Cloud TTS (`sonic-multilingual`, suara Indonesia) — TTS **aktif** jalur LiveKit |

### Docker Compose (7 service default, 1 host)
| ID    | Label · port          | Publik | Peran |
|-------|-----------------------|--------|-------|
| NGINX | nginx · 80/443        | ✅     | Satu-satunya pintu masuk; reverse proxy + rate limit |
| WEB   | website · 8002        | ❌     | **Laravel** "LMS Dummy" (Bengkel Koding). Meng-embed popup via iframe |
| FRONT | frontend · 3000       | ❌     | **Next.js 16** (basePath `/dashboard`) — popup widget + demo + admin |
| API   | api · 8000            | ❌     | FastAPI (`VIONA_MODE=api`) — `/chat`, token, sessions, ingest, health |
| AGENT | livekit-agent · 8081  | ❌     | FastAPI (`VIONA_MODE=agent`) — webhook dispatch, host bot Pipecat |
| BOT   | Pipecat bot           | ❌     | Per-room, **in-process di AGENT** (bukan container terpisah) |
| OLLAMA| ollama · 11434        | ❌     | LLM (routing cloud `gemma4:31b-cloud`) + embedding lokal (RAG parked) |
| REDIS | redis · 6379          | ❌     | Session store (TTL 3600s) |
| QDRANT| qdrant · 6333         | ❌     | **Opsional** — vektor RAG (parked). Hanya `--profile rag` |

### Voice pipeline (di dalam BOT — jalur LiveKit)
`transport.input() → VAD (Silero) → STT (FasterWhisper large-v3) → LLM (Ollama) →
TTS (Cartesia) → transport.output()`. Single node `support`, tanpa tool; jawaban dari
`lms_context` yang di-inject ke persona prompt. (VoxCPM2 = TTS lokal **parked**, tak wired.)

---

## 2. Peta URL (via nginx :80)

| URL | → Service | Ini apa |
|-----|-----------|---------|
| **`/`** | **WEB** (Laravel) | **Landing page** LMS Bengkel Koding; popup Viona ter-embed di sini |
| `/dashboard` | FRONT | Home Next.js (demo Web-Speech standalone) |
| `/dashboard/widget` | FRONT | Konten popup widget (yang di-iframe website) |
| **`/dashboard/admin`** | FRONT | **Dashboard admin** |
| `/dashboard/demo` | FRONT | Demo standalone |
| `/api` `/chat` `/health` `/sessions` `/ingest` `/docs` | API | Backend FastAPI |
| `/webhooks/livekit` | AGENT | Terima webhook LiveKit → spawn bot |
| `/metrics` | API | Prometheus (internal-only: allow LAN, deny all) |

> **Kenapa membingungkan:** Next.js pakai **`basePath: "/dashboard"`** (`next.config.mjs`),
> jadi semua halaman frontend berprefiks `/dashboard/*`. **`/` (root) = Laravel**, bukan
> Next.js. Detail endpoint lihat `docs/ENDPOINTS.md`.

---

## 3. Koneksi (edge berarah)

Format: `SUMBER → TUJUAN : label`.

### Trafik masuk (via nginx)
- `USER → NGINX` : HTTPS
- `NGINX → WEB` : path `/` (Laravel LMS)
- `NGINX → FRONT` : path `/dashboard`
- `NGINX → API` : path `/api`, `/chat`, `/sessions`, `/ingest`, `/health`
- `NGINX → AGENT` : path `/webhooks/livekit`

### Integrasi popup (iframe + postMessage)
- `WEB → FRONT` : embed `<iframe src="/dashboard/widget">` (di `welcome.blade.php`)
- `WEB ⇢ popup` : `viona-context` (isi halaman via MutationObserver → set `lms_context`),
  `viona-quote` (teks di-highlight)
- `popup ⇢ WEB` : `viona-resize`

### Native path (jalur live)
- `popup → API` : `POST /chat` `{message, lms_context}` → jawaban + `timings_ms`
- (STT & TTS di browser — tak keluar ke server)

### LiveKit path (pipeline server)
- `FRONT ⇢ API` : `POST /api/token` (minta join token, bawa `lms_context`)
- `API ⇢ LK` : issue LiveKit join token
- `USER ↔ LK` : audio WebRTC (dua arah)
- `LK → AGENT` : webhook `participant_joined` → `/webhooks/livekit` (⚠️ `lms_context` kosong)
- `FRONT → AGENT` : `POST /dev/spawn` (alternatif, **membawa** `lms_context`)
- `AGENT → BOT` : `run_bot_for_room()` spawn bot (guard `_active_rooms`)
- `BOT ↔ LK` : bot join room (audio in 16k / out 24k)
- `BOT ↔ CART` : sintesis TTS (jalur LiveKit)

### Dependensi data
- `API → OLLAMA` / `BOT → OLLAMA` : inferensi LLM (model cloud via routing)
- `API → REDIS` / `BOT → REDIS` : sesi / transcript
- `API → QDRANT` : hanya bila RAG diaktifkan (`--profile rag`); default parked

---

## 4. Alur (urut)

### A. Native (popup live)
1. Siswa buka LMS (`NGINX /` → `WEB`); halaman meng-embed popup (`/dashboard/widget`).
2. `WEB` kirim `viona-context` (isi materi) → popup set `lms_context`.
3. Siswa bicara → **Web Speech STT di browser** → teks.
4. Popup `POST /chat` `{message, lms_context}` (`NGINX` → `API`) → Ollama → jawaban.
5. Popup ucapkan jawaban via **SpeechSynthesis di browser** + tampilkan transcript (KaTeX).

### B. LiveKit/Pipecat (pipeline server)
1. `FRONT POST /api/token` → `API` mint token via `LK`.
2. Siswa connect ke `LK` (audio WebRTC).
3. `LK` webhook `participant_joined` → `AGENT` (atau `FRONT POST /dev/spawn` bawa konteks).
4. `AGENT run_bot_for_room()` → `BOT` join room.
5. **Loop tiap giliran:** audio → VAD → STT(large-v3) → LLM(+`lms_context`) → TTS(Cartesia) → audio balik.

---

## 5. Pengelompokan layer (tata letak diagram)

- **Kiri — Eksternal:** Siswa (browser), LiveKit Cloud, Cartesia.
- **Tengah — Edge/Presentation:** nginx, website (Laravel), frontend (Next.js).
- **Tengah — Backend:** api, livekit-agent (berisi Pipecat bot + voice pipeline).
- **Kanan — Data & Model:** ollama, redis, (qdrant opsional).
- Arah umum: **kiri → kanan**.

---

## 6. Catatan operasional

- **Dua jalur, satu otak:** native (browser Web Speech + `/chat`) vs LiveKit (Pipecat bot).
  Popup live pakai native; LiveKit gated pada bot di-spawn.
- **Precondition webhook LiveKit:** LiveKit Cloud harus dikonfigurasi mengirim
  `participant_joined` ke `https://<host>/webhooks/livekit`. Untuk dev: tunnel
  (cloudflared/ngrok) → nginx :80. ⚠️ Webhook **tak membawa** `lms_context` → pakai
  `/dev/spawn` bila butuh konteks (open design question).
- **nginx & rebuild:** upstream di-resolve saat startup; setelah recreate container →
  `docker compose restart nginx` (kalau tidak → 502).
- **LLM = cloud, sisanya lokal:** jangan pull model LLM besar; hanya STT (jalur LiveKit)
  dan embedding (RAG, parked) yang lokal. TTS aktif = Cartesia (cloud).
- **Config dev-safe (CPU) default; prod opt-in GPU** — lihat `docs/ENV_PROFILES.md`.
