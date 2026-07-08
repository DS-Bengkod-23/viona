# Latensi & Instrumentasi Timing

Dasar untuk optimasi latensi — **ukur dulu, jangan optimasi buta** (arahan PM).
Instrumentasi ditambahkan di task E; angka baseline LLM dari task G.

## Titik instrumentasi (task E)

| Tahap | Lokasi | Log key | Terukur di |
|-------|--------|---------|-----------|
| RAG retrieval | `api/routes/chat.py` | `chat timing → rag_ms` | Jalur A (`/chat`), live |
| LLM (Ollama) | `api/routes/chat.py` | `chat timing → gen_ms, prompt_ms, tok_per_s, llm_wall_ms` | Jalur A, live |
| STT (Whisper) | `stt/faster_whisper_pipecat.py` | `stt timing → stt_ms, audio_ms, rtf` | Jalur B (butuh webhook) |
| TTS (VoxCPM2) | `tts/voxcpml2_pipecat.py` | `tts timing → tts_ms, audio_ms, rtf` | Jalur B (butuh webhook) |

**LLM timing — bedakan generasi dari overhead.** Ollama `/api/chat` mengembalikan field
nanodetik yang kita ekstrak jadi:
- `gen_ms` = **waktu generasi asli** (`eval_duration`) — lever utama, ∝ jumlah token output.
- `prompt_ms` = pemrosesan prompt input (`prompt_eval_duration`).
- `tok_per_s` = `eval_count / eval_duration` — throughput generasi (bandingkan antar model).
- `llm_wall_ms` = wall-clock end-to-end (termasuk jaringan ke cloud) — biasanya > `gen_ms`.

`/chat` mengembalikan semuanya di `timings_ms: {rag, llm_wall, llm_generation, llm_prompt_eval,
llm_total, tokens_per_sec, eff_tokens_per_sec}` untuk observasi cepat. Pipeline Pipecat
(`PipelineParams`) sudah `enable_metrics=True` — TTFB/processing per service juga terekam Pipecat.

> ⚠️ **Caveat model CLOUD (`*-cloud`):** ollama.com mengembalikan **`eval_duration=0` /
> `prompt_eval_duration=0`** → `gen_ms`, `prompt_ms`, `tok_per_s` akan **null** untuk setup
> cloud sekarang. Gunakan **`eff_tokens_per_sec`** (= `eval_count / llm_wall`) sebagai proksi
> throughput. Field durasi native hanya terisi bila LLM dijalankan **lokal**.

## Pengukuran live LLM — cloud-direct (task E, `gemma4:31b-cloud`)

Diukur langsung ke ollama.com (Docker di-bypass; container store sempat korup akibat
disk-full). Prompt sama seperti task G:

| Beban | tokens output | wall time | eff tok/s |
|-------|---------------|-----------|-----------|
| floor ("Halo") | 10 | **0.61–0.65s** (konsisten) | ~16 |
| sedang | 311 | 6.04s | ~51 |
| panjang | 604–712 | **15–33s** (varian besar) | ~34–40 |

**Dekomposisi:** floor jaringan + TTFT ≈ **0.6s** (kecil, tetap); generasi ≈ **35–40 tok/s
(~27ms/token)** yang **mendominasi**. Jawaban 600-token ≈ `0.6 + 600×0.027 ≈ 16s`.

**Keputusan arah optimasi (data-backed):** lever = **BREVITY OUTPUT**, bukan infrastruktur
jaringan. Optimasi jaringan hemat ≤0.6s; memangkas output 600→100 token hemat ~13s. Varian
provisioning cloud besar (14.96–32.66s untuk panjang serupa) → **streaming TTS per-kalimat**
(Jalur B) untuk menyembunyikannya.

Cara baca STT/TTS: **RTF (real-time factor) = waktu_proses / durasi_audio**. RTF < 1 =
lebih cepat dari realtime (syarat voice). RTF > 1 = lebih lambat dari realtime (buruk).

## Baseline LLM (task G, `gemma4:31b-cloud`, via `/chat`)

Latensi **∝ panjang output** (token generation), bukan panjang input:

| Prompt | output chars | latensi |
|--------|-------------|---------|
| "Halo" | 108 | ~0.9–1.2s |
| "2 tambah 2?" | 60 | ~0.9s |
| turunan kalkulus | 695 | ~2.1s |
| skalar vs vektor | 1421 | ~4.0s |

**A/B ukuran model** (prompt sama):

| Prompt | gemma4:31b-cloud | gpt-oss:20b-cloud |
|--------|------------------|-------------------|
| turunan | **2.96s** (971 ch) | 6.35s (646 ch) |
| skalar vs vektor | **7.70s** (2291 ch) | 29.76s (2714 ch) |

**Kesimpulan:** model nominal "lebih kecil" (20b) **lebih lambat** — untuk cloud-routed,
provisioning provider > jumlah parameter. `gemma4:31b-cloud` = tercepat yang teruji.

## Lever optimasi (prioritas)

1. **Brevity output LLM** — lever terbesar & termurah. Jawaban 1421 ch/4s adalah masalah,
   bukan modelnya. Prompt LLM jawab ringkas (1–3 kalimat, cocok untuk voice) → target
   ~1–1.5s. Encode di system prompt LMS.
2. **Streaming TTS per kalimat** (Jalur B) — kurangi *perceived* latency; user dengar
   kalimat pertama sebelum seluruh jawaban selesai.
3. **Ukuran model**: jangan turunkan secara naif (data membantahnya). Uji kandidat
   spesifik bila ada, ukur — jangan asumsi.

## Belum terukur

- **STT/TTS Jalur B**: butuh webhook LiveKit (task A) agar pipeline jalan → baru `stt/tts
  timing` menghasilkan angka.
- **STT model size** (large-v3 vs small): butuh sampel audio Indonesia + jalan di CPU/host.
