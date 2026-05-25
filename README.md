# Viona — Indonesian Voice AI & LMS Virtual Assistant

Viona adalah platform asisten suara interaktif cerdas berbahasa Indonesia yang dirancang khusus untuk asistensi virtual LMS (Learning Management System) serta layanan bantuan pengguna (customer support). Platform ini memiliki **dua mode operasional utama**:

1. **Mode Offline (Client-Side Fallback)**: Berjalan secara lokal di browser menggunakan Web Speech API bawaan (tanpa membutuhkan server AI backend, berlatensi 0ms, sangat optimal untuk demonstrasi cepat).
2. **Mode Online (Server-Side RAG + LLM)**: Terhubung ke LiveKit Server dengan pipeline end-to-end yang memproses suara (STT Whisper), kecerdasan (LLM Ollama + RAG Qdrant), dan sintesis ucapan (TTS Cartesia).

---

## 🚀 Fitur Utama

- **LMS Multi-Materi & Multi-Versi**: Mendukung pemisahan dokumen kurikulum pembelajaran (misalnya Matematika, Fisika, Pemrograman, Sejarah) dengan berbagai edisi/versi (Versi 1.0, 2.0, 3.0) menggunakan filter payload metadata di database vektor Qdrant.
- **Visualisasi Audio Real-time**: Menampilkan visualisasi gelombang suara visual (audio wave) dinamis berdasarkan status Viona (mendengarkan, berpikir, berbicara).
- **Hybrid Speech Engine**: Kombinasi transkripsi lokal browser dan pemrosesan terdistribusi server menggunakan LiveKit Agents.
- **Pembersihan Kata (Text Preprocessing)**: Penyaringan teks masukan dari noise audio (*"hmmm"*, *"aaa"*, dsb) dan konformasi ejaan bahasa Indonesia untuk menghasilkan respon suara yang lebih alami dan manusiawi.

---

## 📂 Struktur Direktori Proyek

Aplikasi ini dirancang menggunakan arsitektur modular yang memisahkan frontend (Next.js) dan backend (Python Clean Architecture):

```
viona/
├── backend/                           # 🐍 Backend (Python & API Service)
│   ├── app/
│   │   ├── agents/                    # Logika agen LiveKit / Pipecat (worker.py, support.py)
│   │   ├── api/                       # Router FastAPI (chat, ingestion, token, sessions)
│   │   ├── core/                      # File konfigurasi utama (config.py, logging.py)
│   │   ├── infrastructure/            # Adapter pihak ketiga (retriever Qdrant, stt, tts, redis)
│   │   ├── prompts/                   # Kumpulan system prompt & instruksi Bahasa Indonesia
│   │   └── utils/                     # Modul pembantu (text_cleaner.py)
│   ├── docker/                        # Dockerfile untuk deployment backend
│   ├── pyproject.toml                 # Dependensi Python via uv
│   └── Makefile                       # Script shortcut untuk mempermudah jalannya perintah
│
├── frontend/                          # ⚛️ Frontend (Next.js 16 + Tailwind CSS)
│   ├── src/
│   │   ├── app/                       # Routing halaman utama (page.tsx, layout.tsx)
│   │   ├── components/                # Komponen UI modular (voice-assistant, ui shadcn)
│   │   ├── hooks/                     # Custom react hooks untuk audio & status
│   │   └── lib/                       # Helper API client (api.ts)
│   ├── docker/                        # Dockerfile untuk deployment frontend
│   └── package.json                   # Dependensi JavaScript & Next.js
│
├── docker-compose.yml                 # 🐳 Orkestrasi 7 container (api, agent, qdrant, redis, ollama, frontend, nginx)
└── .env.example                       # Contoh template berkas konfigurasi variabel lingkungan
```

---

## 📝 Deskripsi Berkas `.env` (Environment Variables)

Berkas `.env` digunakan untuk menghubungkan modul-modul AI, database, server komunikasi, dan API kunci eksternal. Berikut adalah rincian isi `.env.example`:

| Variabel | Deskripsi | Nilai Default |
| :--- | :--- | :--- |
| **LIVEKIT_URL** | Alamat WebSocket server komunikasi LiveKit. | `wss://your-project.livekit.cloud` |
| **LIVEKIT_API_KEY** | Kunci API otentikasi LiveKit Cloud. | `APIxxxxxxxxxxxxxxxx` |
| **LIVEKIT_API_SECRET** | Token rahasia otentikasi LiveKit Cloud. | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| **CARTESIA_API_KEY** | Kunci API Cartesia untuk Text-to-Speech (TTS). | `sk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| **CARTESIA_VOICE_ID** | ID Karakter Suara Bahasa Indonesia Cartesia. | `a167e0f3-df7e-4d52-a9c3-f949145efdab` |
| **CARTESIA_MODEL** | Model sintesis suara Cartesia. | `sonic-multilingual` |
| **OLLAMA_BASE_URL** | Endpoint API LLM Ollama lokal/server. | `http://ollama:11434/v1` |
| **OLLAMA_MODEL** | Model bahasa besar (LLM) yang digunakan. | `gpt-oss:120b-cloud` / `llama3.2:3b` |
| **QDRANT_URL** | Alamat database vektor Qdrant. | `http://qdrant:6333` |
| **QDRANT_COLLECTION** | Nama koleksi indeks RAG di Qdrant. | `viona_faq` |
| **REDIS_URL** | Alamat caching Redis untuk melacak sesi percakapan. | `redis://redis:6379/0` |
| **WHISPER_MODEL_SIZE** | Ukuran model transkripsi Faster-Whisper. | `large-v3` / `small` |
| **WHISPER_LANGUAGE** | Bahasa default pendeteksian suara STT. | `id` |
| **WHISPER_DEVICE** | Perangkat komputasi Whisper (`cpu` / `cuda` GPU). | `auto` |

---

## 🛠️ Panduan Integrasi PIPECAT di Backend

Untuk memaksimalkan backend dalam menangani percakapan suara real-time berlatensi sangat rendah, Anda dapat mengintegrasikan **Pipecat** (kerangka kerja open-source untuk Voice Agent) ke dalam `backend/app/agents/worker.py`.

### Mengapa Memakai Pipecat?
Pipecat mempermudah pembuatan pipeline asisten suara berkonsep aliran data (*dataflow*):
`Input Audio -> VAD (Voice Activity Detection) -> STT -> LLM -> TTS -> Output Audio`
Ia secara otomatis menangani interupsi suara (ketika user memotong pembicaraan bot), buffering audio, dan antrean pesan secara asinkron.

### Bagian Backend yang Dapat Diperbarui dengan Pipecat:

1. **Pipeline Runner (`worker.py`)**:
   Mengganti kelas worker bawaan LiveKit Agent dengan runner Pipecat:
   ```python
   from pipecat.processors.frameworks.livekit import LiveKitFrameSerializer
   from pipecat.pipeline.runner import PipelineRunner
   from pipecat.pipeline.pipeline import Pipeline

   # Inisialisasi runner pipecat
   runner = PipelineRunner()
   ```

2. **Inisialisasi Services bawaan Pipecat**:
   Pipecat memiliki kelas adaptor bawaan untuk Cartesia, Ollama, dan Whisper. Anda bisa langsung mengimpor dan menggantikan inisialisasi manual:
   ```python
   from pipecat.services.cartesia import CartesiaTTSService
   from pipecat.services.ollama import OllamaLLMService
   from pipecat.services.whisper import WhisperSTTService

   # Buat instance service langsung
   stt = WhisperSTTService(model="large-v3", language="id")
   llm = OllamaLLMService(model="llama3.2:3b", base_url="http://ollama:11434")
   tts = CartesiaTTSService(api_key=settings.cartesia_api_key, voice_id="a167e0f3...")
   ```

3. **Manajemen Interupsi & VAD**:
   Pipecat menyediakan penganalisis aktivitas suara (Silero VAD) yang secara cerdas mendeteksi saat manusia mulai berbicara dan segera menghentikan output audio TTS dari Viona:
   ```python
   from pipecat.vad.silero import SileroVADAnalyzer
   
   vad = SileroVADAnalyzer()
   ```

4. **Context & Tool Calling (Action Handler)**:
   Anda dapat mendaftarkan fungsi Python biasa sebagai **Tools** di LLM Context Pipecat. Misalnya, jika siswa meminta tugas baru melalui suara, LLM dapat memicu fungsi backend untuk mengambil kuis secara otomatis:
   ```python
   async def fetch_lms_quiz(quiz_id: str):
       # Logika mengambil kuis lms dari database
       return {"quiz": "Selesaikan integral berikut..."}

   # Daftarkan ke context LLM Pipecat
   llm.register_action("get_quiz", fetch_lms_quiz)
   ```

---

## 🚀 Langkah Menjalankan Aplikasi

1. **Salin & Isi Environment**:
   ```bash
   cp .env.example .env
   ```
2. **Jalankan Container**:
   ```bash
   docker compose up -d --build
   ```
3. **Unduh Model LLM Lokal**:
   ```bash
   docker compose exec ollama ollama pull llama3.2:3b
   ```
4. **Unggah Dokumen LMS per Materi & Versi**:
   Kirimkan berkas `.pdf` Anda ke API Ingestion dengan parameter `material_id` dan `version`:
   ```bash
   curl -X POST http://localhost/ingest/pdf \
     -F "file=@/path/ke/materi-matematika.pdf" \
     -F "category=lms" \
     -F "material_id=matematika" \
     -F "version=v1"
   ```
5. Akses antarmuka visual Viona di browser melalui alamat **`http://localhost/`**.

---

## ⚖️ Lisensi
Aplikasi ini dilisensikan di bawah [MIT License](LICENSE).
