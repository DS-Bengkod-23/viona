# Viona - AI Virtual Assistant for LMS

Selamat datang di repositori **Viona**! Viona adalah asisten virtual cerdas berbasis AI yang dirancang khusus untuk platform Learning Management System (LMS) seperti Bengkel Koding. Viona mendukung interaksi melalui teks dan suara (*voice agent*) secara real-time.

## ✨ Fitur Utama
1. **Interactive Voice Assistant**: Berbicara langsung dengan AI secara *real-time* menggunakan WebRTC (LiveKit).
2. **Text Chat Mode**: Mode chat teks biasa layaknya ChatGPT.
3. **Context-Aware (LMS Integration)**: AI bisa mengenali dan membaca materi yang sedang dibuka oleh pengguna di LMS.
4. **Pipecat Pipeline**: Pemrosesan suara menggunakan Faster-Whisper (Speech-to-Text), Ollama (LLM Inference), dan **Cartesia** (Text-to-Speech cloud — engine aktif; VoxCPM2 lokal adalah opsi cadangan yang belum di-wire, butuh GPU).
5. **RAG (Di-park)**: Infrastruktur *Retrieval-Augmented Generation* (Qdrant) tersedia tapi **di-park** — jalur LMS menjawab dari *context-injection* konten halaman, bukan vector search. Qdrant mati secara default (`--profile rag` untuk menyalakan).

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
Setelah semua berjalan (status di Docker berwarna hijau / `Running`), kamu bisa membuka browser dan mengunjungi:
- **Website LMS Utama:** [http://localhost](http://localhost) (atau `http://localhost:8002` tergantung pengaturan Nginx-mu).
- **Viona Widget:** Akan muncul di pojok kanan bawah pada halaman LMS.

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
