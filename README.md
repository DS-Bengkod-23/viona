# Viona - AI Virtual Assistant for LMS

Selamat datang di repositori **Viona**! Viona adalah asisten virtual cerdas berbasis AI yang dirancang khusus untuk platform Learning Management System (LMS) seperti Bengkel Koding. Viona mendukung interaksi melalui teks dan suara (*voice agent*) secara real-time.

## ✨ Fitur Utama
1. **Interactive Voice Assistant**: Berbicara langsung dengan AI secara *real-time*. Ada **dua jalur suara**:
   - **Native (dipakai popup live)** — STT & TTS jalan di **browser** (Web Speech API). Ringan, tanpa GPU. **Wajib Google Chrome / Microsoft Edge** (Brave/Firefox/Safari tidak didukung).
   - **LiveKit/Pipecat (pipeline server)** — bot suara di server via WebRTC (LiveKit).
2. **Kontrol Suara**: **Push-to-talk** (tahan tombol/spasi untuk bicara), tombol **Stop** (potong jawaban Viona/*barge-in*), dan **Wake word** (ucapkan "Hai Viona" + pertanyaan).
3. **Text Chat Mode**: Mode chat teks biasa layaknya ChatGPT.
4. **Context-Aware (LMS Integration)**: AI mengenali & membaca materi yang sedang dibuka di LMS (konteks di-*inject* ke prompt).
5. **Pipecat Pipeline** (jalur LiveKit): Faster-Whisper (Speech-to-Text), Ollama (LLM Inference), dan **Cartesia** (Text-to-Speech cloud — engine aktif; VoxCPM2 lokal opsi cadangan, belum di-wire, butuh GPU).
6. **RAG (Di-park)**: Infrastruktur *Retrieval-Augmented Generation* (Qdrant) tersedia tapi **di-park** — jalur LMS menjawab dari *context-injection* konten halaman, bukan vector search. Qdrant mati secara default (`--profile rag` untuk menyalakan).

---

## 🚀 Cara Menjalankan Viona (Untuk Pemula)

Jika kamu baru pertama kali mencoba menjalankan proyek ini, jangan khawatir! Ikuti langkah-langkah di bawah ini secara berurutan.

### 1. Persiapan Awal
Pastikan komputer kamu sudah terinstall aplikasi berikut:
- **Docker & Docker Compose** (Sangat direkomendasikan menggunakan [Docker Desktop](https://www.docker.com/products/docker-desktop/) jika memakai Windows/Mac).
- **Git** (Untuk mendownload repositori).

### 2. Pengaturan `.env` (File Konfigurasi)
Viona membutuhkan beberapa kunci rahasia (API Keys) agar bisa terhubung ke layanan AI.
1. Buka folder `viona`.
2. Kamu akan menemukan file bernama `.env.example`.
3. **Duplikat (copy-paste)** file tersebut, lalu ubah nama hasil copy-nya menjadi **`.env`** (tanpa ekstensi `.example`).
4. Buka file `.env` dan isikan data penting berikut:
   - `LIVEKIT_URL`, `LIVEKIT_API_KEY`, dan `LIVEKIT_API_SECRET` (Dapatkan dari akun [LiveKit Cloud](https://livekit.io/)).
   - `CARTESIA_API_KEY` (Jika kamu menggunakan suara Cartesia).
   - `OLLAMA_API_KEY` (Jika menggunakan Ollama Cloud).
   *(Kamu bisa membiarkan pengaturan lainnya secara default terlebih dahulu).*

### 3. Menjalankan Server dengan Docker
Viona terdiri dari banyak bagian (Backend, Frontend, Agent, Redis, Nginx, dll). Semuanya bisa dinyalakan sekaligus dengan satu perintah Docker!

Buka **Terminal** atau **Command Prompt**, pastikan kamu berada di dalam folder `viona` (folder utama), lalu jalankan:

```bash
docker compose up -d --build
```
*Catatan: Parameter `--build` berguna untuk memastikan Docker membangun ulang (rebuild) kodenya jika ada perubahan baru. Proses pertama kali akan memakan waktu cukup lama karena Docker harus mendownload file-file sistem pendukung, menginstall Node.js, NPM, dan Composer secara otomatis untuk Frontend maupun Website (LMS).*

**Apakah ada error atau frontend tidak ter-update?**
Jika kamu mengubah sesuatu di kode frontend namun tidak muncul, atau ada kendala, kamu bisa mem-build/menjalankan ulang khusus bagian *frontend* dengan perintah ini:
```bash
docker compose up -d --no-deps --build frontend
```

**Ingin menyalakan database RAG (Qdrant)?**
Secara default, Qdrant dimatikan untuk menghemat memori. Jika kamu butuh menyalakannya, gunakan perintah:
```bash
docker compose --profile rag up -d
```

### 4. Mengakses Aplikasi
Setelah semua berjalan (status di Docker berwarna hijau / `Running`), buka browser (**pakai Chrome/Edge** agar fitur suara jalan) dan kunjungi:

| Halaman | URL |
|---------|-----|
| **Website LMS utama (landing page)** | [http://localhost/](http://localhost/) |
| **Dashboard admin** | [http://localhost/dashboard/admin](http://localhost/dashboard/admin) |
| Popup widget langsung | [http://localhost/dashboard/widget](http://localhost/dashboard/widget) |
| Demo suara standalone | [http://localhost/dashboard/demo](http://localhost/dashboard/demo) |

- **Viona Widget** otomatis muncul di pojok kanan bawah halaman LMS (`/`).
- Catatan: frontend Next.js memakai `basePath: /dashboard`, jadi **`/` = website Laravel**, sedangkan **`/dashboard/*` = frontend**. Detail rute lihat `docs/ENDPOINTS.md` & `docs/ARCHITECTURE.md`.

> ⚠️ **Kena error 502** setelah rebuild? Nginx me-resolve alamat service saat start. Jalankan `docker compose restart nginx`.

---

## 🛠️ Struktur Folder Penting
- `/frontend`: Berisi antarmuka web (Next.js) dan widget *popup* Viona.
- `/backend`: Berisi API (FastAPI) dan *Worker/Agent* pengolah suara (Pipecat & LiveKit).
- `/website`: Berisi *dummy website* / *Landing page* / Sistem LMS (Laravel) tempat Viona ditanamkan.
- `/docker`: Konfigurasi Nginx dan sistem Docker pendukung lainnya.

## 🛑 Cara Mematikan Viona
Untuk menghentikan semua layanan server, ketik perintah berikut di terminal:
```bash
docker compose down
```

Selamat bereksplorasi dengan Viona! 🚀
