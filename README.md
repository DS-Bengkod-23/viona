# Viona — Indonesian Voice AI Customer Support & Voice Assistant

Viona adalah sistem asisten suara interaktif berbahasa Indonesia yang dirancang untuk kebutuhan call center dan asisten virtual. Viona mendukung **dua mode operasional utama**:
1. **Mode Offline (Client-Side)**: Berjalan murni di browser menggunakan Web Speech API (tanpa membutuhkan server AI eksternal, sangat cepat dan enteng untuk pengujian UI).
2. **Mode Online (Server-Side)**: Terhubung ke LiveKit Server dengan pipeline end-to-end (STT Whisper, LLM Ollama, dan TTS Cartesia) untuk produksi dan akurasi tinggi.

---

## 📋 Prasyarat & Persiapan

Sebelum menjalankan aplikasi, pastikan Anda telah menyiapkan komponen berikut:

1. **Docker & Docker Compose** (Wajib jika ingin menjalankan mode online).
2. **Node.js v18 atau v20** dan **npm/pnpm** (Wajib untuk menjalankan frontend).
3. **API Key Cartesia** (Untuk suara TTS Bahasa Indonesia yang natural).
4. **LiveKit Cloud Credentials** (Atau instalasi LiveKit Server lokal).
5. **Model Ollama** (Misal `llama3.2:3b` untuk lokal ringan, atau `gpt-oss:120b-cloud` untuk produksi).

---

## 🛠️ Cara Menjalankan (Running)

### 1. Konfigurasi Environment
Salin berkas `.env.example` menjadi `.env` di root direktori proyek:
```bash
cp .env.example .env
```
Buka berkas `.env` dan isi variabel berikut:
```env
LIVEKIT_URL=wss://project-anda.livekit.cloud
LIVEKIT_API_KEY=APIxxxxxxxxx
LIVEKIT_API_SECRET=xxxxxxxxxxxxxxxxxxxxx
CARTESIA_API_KEY=sk_xxxxxxxxxxxxxxxxx
```

### 2. Menjalankan Semua Layanan (Docker Compose)
Untuk menjalankan frontend, API, database vektor Qdrant, Redis, Ollama, dan Agent secara bersamaan:
```bash
# Menjalankan kontainer di background
docker compose up -d

# Memeriksa status kesehatan kontainer
docker compose ps
```

### 3. Mengunduh Model LLM di Ollama
Jika Anda menggunakan model Ollama lokal, Anda perlu mengunduhnya setelah container aktif:
```bash
docker compose exec ollama ollama pull llama3.2:3b
```

### 4. Mengunggah Knowledge Base (RAG Ingestion per Materi & Versi)
Anda dapat mengunggah file dokumen `.pdf` atau `.txt` yang berisi materi pembelajaran dengan menetapkan parameter `material_id` dan `version` agar AI memberikan jawaban spesifik sesuai materi yang dipilih di UI.

**Contoh Request via API (POST /ingest/pdf):**
*   **Endpoint**: `http://localhost/ingest/pdf`
*   **Body (Form-Data)**:
    *   `file`: (berkas `.pdf` materi Anda)
    *   `category`: `lms`
    *   `material_id`: `matematika` (atau `fisika`, `pemrograman`, `sejarah`)
    *   `version`: `v1` (atau `v2`, `v3`)

Dengan memetakan berkas ke materi dan versi tertentu, Viona akan secara dinamis menyaring dokumen yang relevan saat pengguna berinteraksi di browser.

---

## 🗺️ Panduan Modifikasi Komponen Viona

Berikut adalah panduan file mana saja yang perlu Anda edit untuk menyesuaikan STT, TTS, LLM, Pembersihan Kata, dan Prompt.

### 🎙️ 1. Mengganti STT (Speech-to-Text)
Untuk menyesuaikan ukuran model Whisper, akurasi, dan parameter pengenalan suara:
*   **File Konfigurasi Utama**: `backend/app/agents/worker.py` -> fungsi `_build_stt()`.
*   **File Implementasi STT**: `backend/app/infrastructure/stt/faster_whisper.py`.
*   **Konfigurasi di `.env`**:
    ```env
    WHISPER_MODEL_SIZE=small  # Ubah ke 'medium' atau 'large-v3' untuk akurasi lebih baik
    WHISPER_DEVICE=cpu        # Ubah ke 'cuda' jika menggunakan GPU NVIDIA
    ```

### 🧠 2. Mengganti LLM (Language Model)
Untuk mengatur kecerdasan, suhu (*temperature*), dan batas token respon:
*   **File Konfigurasi Utama**: `backend/app/agents/worker.py` -> fungsi `_build_llm()`.
*   **Konfigurasi di `.env`**:
    ```env
    OLLAMA_MODEL=llama3.2:3b  # Model LLM yang digunakan
    OLLAMA_BASE_URL=http://ollama:11434/v1
    ```
*   *Tips*: Naikkan parameter `temperature` ke `0.7` atau `0.8` di fungsi `_build_llm()` untuk respon yang lebih variatif dan alami.

### 🔊 3. Mengganti TTS (Text-to-Speech)
Untuk mengganti jenis suara, kecepatan berbicara, maupun bahasa:
*   **File Konfigurasi Utama**: `backend/app/agents/worker.py` -> fungsi `_build_tts()`.
*   **Konfigurasi di `.env`**:
    ```env
    CARTESIA_VOICE_ID=a167e0f3-df7e-4d52-a9c3-f949145efdab  # ID Suara Indonesia
    CARTESIA_MODEL=sonic-multilingual
    ```
*   *Tips*: Anda dapat menelusuri suara Indonesia lainnya di [Cartesia Voice Library](https://play.cartesia.ai).

### 🧹 4. Preprocessing & Pembersihan Kata (Text Cleaner)
Pembersihan kata sangat penting agar robot tidak mengeja singkatan (seperti *"dgn"* dibaca *"d-g-n"*) dan mengabaikan noise ucapan (seperti *"hmm"* atau *"aaa"*).

*   **Mode Offline (Client-Side)**:
    *   **Lokasi**: `frontend/src/components/voice-assistant/voice-assistant.tsx` -> fungsi `generateResponse()`. Anda dapat menyaring kata kunci teks masukan di sini untuk memetakan jawaban.
*   **Mode Online (Server-Side/LiveKit)**:
    *   **Lokasi**: `backend/app/utils/text_cleaner.py` *(silakan buat baru jika belum ada)*.
    *   Integrasikan pembersihan kata ini di dalam handler event transkrip STT atau sebelum output dikirim ke TTS pada `worker.py` atau `faster_whisper.py`.

### 💡 5. Prompt Sistem & Persona Viona
Untuk mengubah gaya bicara, keramahan, dan aturan Call Center Viona:
*   **Lokasi**: `backend/app/prompts/indonesian.py`.
*   Ubah variabel `CUSTOMER_SUPPORT_PROMPT` untuk memandu Viona menjawab sebagai agen profesional.

---

## 📂 Struktur Direktori Utama

```
viona/
├── backend/                        # Kode backend (Python, Clean Architecture)
│   ├── app/
│   │   ├── agents/                 # Agent logic (worker.py, support.py)
│   │   ├── infrastructure/        # STT, TTS, RAG (Qdrant), Session (Redis)
│   │   ├── prompts/                # System Prompt Bahasa Indonesia
│   │   └── api/                    # FastAPI endpoints & token generator
│   └── docker/                     # Dockerfile backend
│
├── frontend/                       # Kode frontend Next.js 16
│   ├── src/
│   │   ├── app/                    # Entry point aplikasi (page.tsx)
│   │   ├── components/             # Komponen UI utama & Voice Assistant
│   │   └── lib/                    # API client helper
│   └── docker/                     # Dockerfile frontend
│
└── docker-compose.yml              # Konfigurasi orkestrasi 7 kontainer utama
```

---

## ⚖️ Lisensi
Aplikasi ini dilisensikan di bawah [MIT License](LICENSE).
